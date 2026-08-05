"""
Data layer.

Every number on the profile is fetched here and written to data.json. Panels
never call the network, so a render is deterministic and a rate-limit blip
degrades to yesterday's figures instead of a broken image.

Two modes, same output shape:

  · with a token   GraphQL, one round trip, includes private contributions
  · without one    REST plus the public contributions endpoint

The tokenless path exists so the build is reproducible on any machine without
handing out credentials, and so CI can verify a change without a secret. It is
the reason there is no fixture file: real data is always available.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

API = "https://api.github.com/graphql"
REST = "https://api.github.com"
UA = "profile-generator"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")


def _get(url, data=None, headers=None, timeout=25):
    h = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    h.update(headers or {})
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    body = json.dumps(data).encode() if data else None
    if body:
        h["Content-Type"] = "application/json"
    with urllib.request.urlopen(
            urllib.request.Request(url, data=body, headers=h), timeout=timeout) as r:
        return r.read()


def gql(query, **variables):
    out = json.loads(_get(API, {"query": query, "variables": variables}))
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]


def rest(path):
    return json.loads(_get(f"{REST}{path}"))


# ─── contributions ───────────────────────────────────────────────────────────

Q_CAL = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      restrictedContributionsCount
      contributionCalendar{
        totalContributions
        weeks{contributionDays{date contributionCount}}
      }
    }
  }
}
"""

_TD = re.compile(r"<td([^>]*class=\"ContributionCalendar-day\")")
_TIP = re.compile(r"<tool-tip[^>]*for=\"([^\"]+)\"[^>]*>([^<]*)</tool-tip>")
_COUNT = re.compile(r"\s*(\d[\d,]*)\s+contribution")


def _calendar_public(login):
    """Parse the same calendar GitHub renders on the profile page. No token,
    no scraping of anything that is not already public HTML."""
    raw = _get(f"https://github.com/users/{login}/contributions",
               headers={"User-Agent": "Mozilla/5.0",
                        "X-Requested-With": "XMLHttpRequest"}).decode()
    tips = dict(_TIP.findall(raw))
    days = {}
    for attrs in _TD.findall(raw):
        d = re.search(r'data-date="([\d-]+)"', attrs)
        i = re.search(r'id="([^"]+)"', attrs)
        if not (d and i):
            continue
        m = _COUNT.match(tips.get(i.group(1), ""))
        days[d.group(1)] = int(m.group(1).replace(",", "")) if m else 0
    if not days:
        raise RuntimeError("could not parse the public contribution calendar")
    return days


def _calendar_token(login, years):
    days, extra = {}, {}
    for y in years:
        d = gql(Q_CAL, login=login,
                **{"from": f"{y}-01-01T00:00:00Z", "to": f"{y}-12-31T23:59:59Z"})
        cc = d["user"]["contributionsCollection"]
        for week in cc["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                days[day["date"]] = day["contributionCount"]
        extra[y] = {
            "commits": cc["totalCommitContributions"],
            "prs": cc["totalPullRequestContributions"],
            "reviews": cc["totalPullRequestReviewContributions"],
            "issues": cc["totalIssueContributions"],
            "private": cc["restrictedContributionsCount"],
        }
    return days, extra


# ─── derivation ──────────────────────────────────────────────────────────────

def _streaks(days):
    """Current and longest daily streak. Today is graced: an empty today does
    not retroactively break a streak that was alive yesterday."""
    if not days:
        return {"current": 0, "longest": 0, "current_start": None}
    longest = run = 0
    prev = None
    for k in sorted(days):
        d = date.fromisoformat(k)
        if days[k] > 0:
            run = run + 1 if (prev and (d - prev).days == 1 and run) else 1
            longest = max(longest, run)
        else:
            run = 0
        prev = d

    today = datetime.now(timezone.utc).date()
    cursor = today if days.get(today.isoformat(), 0) else today - timedelta(days=1)
    cur, start = 0, None
    while days.get(cursor.isoformat(), 0) > 0:
        cur += 1
        start = cursor.isoformat()
        cursor -= timedelta(days=1)
    return {"current": cur, "longest": longest, "current_start": start}


def _languages(repos, ignore, top=6):
    sizes = Counter()
    for r in repos:
        for name, size in (r.get("langs") or {}).items():
            if name.lower() not in ignore:
                sizes[name] += size
    total = sum(sizes.values()) or 1
    return ([{"name": k, "bytes": v, "share": v / total}
             for k, v in sizes.most_common(top)], total)


def _rhythm(days, window):
    weekday = [0] * 7
    months = defaultdict(int)
    for k in window:
        v = days.get(k, 0)
        weekday[date.fromisoformat(k).weekday()] += v
        months[k[:7]] += v
    return {"weekday": weekday,
            "months": [{"month": m, "count": c}
                       for m, c in sorted(months.items())[-12:]]}


# ─── production probes ───────────────────────────────────────────────────────

def _probe(url):
    """Ask each shipped product whether it is actually up, and how fast.

    This is the only honest way to put a live badge on a product card. If the
    probe fails the card says so rather than claiming a status it cannot see.
    """
    started = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(200_000).decode("utf-8", "ignore")
            ms = int((time.time() - started) * 1000)
            title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S)
            return {"status": r.status, "ms": ms, "up": 200 <= r.status < 400,
                    "title": re.sub(r"\s+", " ", title.group(1)).strip()[:80]
                    if title else ""}
    except Exception as exc:
        print(f"warn: probe {url}: {exc}", file=sys.stderr)
        return {"status": 0, "ms": 0, "up": False, "title": ""}


# ─── build ───────────────────────────────────────────────────────────────────

def build(config_path, out_path):
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)

    login = cfg["identity"]["login"]
    ignore = {s.lower() for s in cfg["stack"].get("ignore_languages", [])}

    user = rest(f"/users/{login}")
    raw_repos = []
    page = 1
    while page <= 4:
        chunk = rest(f"/users/{login}/repos?per_page=100&page={page}"
                     f"&type=owner&sort=pushed")
        raw_repos += chunk
        if len(chunk) < 100:
            break
        page += 1

    repos = [r for r in raw_repos if not r["fork"] and not r["archived"]]

    # Language split. With a token the real byte breakdown is one cheap call
    # per repository, so take it. Without one that would burn the entire
    # unauthenticated hourly quota, so fall back to attributing each repo's
    # size to its primary language and say so on the panel rather than
    # presenting an estimate as a measurement.
    exact = bool(TOKEN)
    for r in repos:
        if exact:
            try:
                r["langs"] = rest(f"/repos/{login}/{r['name']}/languages")
                continue
            except Exception as exc:
                print(f"warn: languages {r['name']}: {exc}", file=sys.stderr)
                exact = False
        r["langs"] = ({r["language"]: max(r.get("size", 1), 1)}
                      if r.get("language") else {})

    extra = {}
    if TOKEN:
        try:
            years = list(range(datetime.now(timezone.utc).year - 2,
                               datetime.now(timezone.utc).year + 1))
            days, extra = _calendar_token(login, years)
            mode = "graphql"
        except Exception as exc:
            print(f"warn: graphql failed, falling back to public: {exc}",
                  file=sys.stderr)
            days, mode = _calendar_public(login), "public"
    else:
        days, mode = _calendar_public(login), "public"

    today = datetime.now(timezone.utc).date()
    window = [(today - timedelta(days=i)).isoformat() for i in range(363, -1, -1)]

    langs, code_bytes = _languages(repos, ignore)
    this_year = extra.get(today.year, {})

    products = []
    for p in cfg.get("production", []):
        products.append({**p, "probe": _probe(p["url"])})

    stars = sum(r["stargazers_count"] for r in repos)
    year_total = sum(days.get(k, 0) for k in window)

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "config": cfg,
        "identity": {
            "name": user.get("name") or login,
            "login": login,
            "bio": user.get("bio") or "",
            "avatar": user["avatar_url"],
            "location": user.get("location") or cfg["identity"].get("location", ""),
            "since": user["created_at"][:10],
            "blog": user.get("blog") or "",
        },
        "totals": {
            "repos": len(repos),
            "repos_public": user.get("public_repos", len(repos)),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "stars": stars,
            "forks": sum(r["forks_count"] for r in repos),
            "contributions_year": year_total,
            "commits": this_year.get("commits", 0),
            "prs": this_year.get("prs", 0),
            "reviews": this_year.get("reviews", 0),
            "issues": this_year.get("issues", 0),
            "private": this_year.get("private", 0),
            "active_days": sum(1 for k in window if days.get(k, 0) > 0),
            "best_day": max((days.get(k, 0) for k in window), default=0),
            "code_bytes": code_bytes,
        },
        "streak": _streaks(days),
        "calendar": {"window": window,
                     "counts": {k: days.get(k, 0) for k in window}},
        "rhythm": _rhythm(days, window),
        "languages": langs,
        "languages_exact": exact,
        "production": products,
        "top_repos": sorted(
            ({"name": r["name"], "url": r["html_url"],
              "stars": r["stargazers_count"], "language": r.get("language"),
              "pushed_at": r["pushed_at"]} for r in repos),
            key=lambda r: (-r["stars"], r["pushed_at"]))[:5],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print(f"data.json — {mode} mode, {len(repos)} repos, {year_total} "
          f"contributions, {len(langs)} languages, {len(products)} products")
    return data


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "profile.config.json",
          sys.argv[2] if len(sys.argv) > 2 else "generator/data.json")
