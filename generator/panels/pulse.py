"""
Pulse — the streak card, rebuilt, plus the two cuts that give it meaning.

The familiar streak card shows three numbers and stops. This one keeps those
numbers, then answers the questions they raise: when does the work happen, and
what shape has the year taken. Same footprint, three times the information,
and on-palette, which no third-party card can be.

Every figure is measured. Nothing here is written in the config.
"""
from ..core.svgkit import (bar, document, group, hairline, label, n, ramp,
                           sparkline, text)
from ..core.tokens import CANVAS_W, MOTION

M = 40
H = 396
DAYS = ["M", "T", "W", "T", "F", "S", "S"]
FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
        "Sunday"]


def _fmt(v):
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M".replace(".0M", "M")
    if v >= 10_000:
        return f"{v / 1000:.1f}k".replace(".0k", "k")
    return f"{v:,}"


def _stat(x, y, value, lab, note, t, delay, size=32, unit=""):
    g = [group(x, y, delay=delay, dy=10)]
    g.append(text(0, 0, value, "num_xl", t["text"], size=size))
    if unit:
        g.append(text(len(value) * size * 0.58 + 4, 0, unit, "small",
                      t["dim"]))
    g.append(label(0, 20, lab, t["accent_soft"]))
    if note:
        g.append(text(0, 38, note, "small", t["dim"], size=10.5))
    g.append("</g>")
    return "".join(g)


def _cadence(data, t, x, y, w):
    vals = data["rhythm"]["weekday"]
    peak = max(vals) or 1
    busiest = vals.index(peak)
    bw = (w - 6 * 10) / 7
    base, maxh = y + 58, 52
    out = [label(x, y - 6, "when the work happens", t["muted"])]
    for i, v in enumerate(vals):
        h = max(v / peak * maxh, 2)
        bx = x + i * (bw + 10)
        on = i == busiest
        col = t["accent"] if on else t["line_strong"]
        out.append(
            f'<rect x="{n(bx)}" y="{n(base)}" width="{n(bw)}" height="0" '
            f'rx="3" fill="{col}">'
            f'<animate attributeName="height" from="0" to="{n(h)}" dur="0.7s" '
            f'begin="{n(0.5 + i * 0.05)}s" fill="freeze" calcMode="spline" '
            f'keyTimes="0;1" keySplines="{MOTION["ease"]}"/>'
            f'<animate attributeName="y" from="{n(base)}" to="{n(base - h)}" '
            f'dur="0.7s" begin="{n(0.5 + i * 0.05)}s" fill="freeze" '
            f'calcMode="spline" keyTimes="0;1" '
            f'keySplines="{MOTION["ease"]}"/></rect>')
        out.append(label(bx + bw / 2, base + 16, DAYS[i],
                         t["accent"] if on else t["dim"], anchor="middle"))
    out.append(text(x, base + 38, f"{FULL[busiest]}s carry the week, "
                                  f"{peak:,} contributions", "small",
                    t["muted"], size=11))
    return "".join(out)


def _volume(data, t, x, y, w):
    months = data["rhythm"]["months"]
    vals = [m["count"] for m in months]
    if not vals:
        return ""
    peak = max(vals)
    pi = vals.index(peak)
    out = [label(x, y - 6, "12-month volume", t["muted"])]
    out.append(sparkline(x, y + 10, w, 54, vals, t["accent"], delay=0.6,
                         fill_color="url(#pulseFill)"))
    out.append(label(x, y + 84, months[0]["month"], t["dim"]))
    out.append(label(x + w, y + 84, months[-1]["month"], t["dim"],
                     anchor="end"))
    out.append(text(x + w / 2, y + 84, f"peak {peak:,} in {months[pi]['month']}",
                    "small", t["dim"], anchor="middle", size=10.5))
    return "".join(out)


def _languages(data, t, x, y, w):
    langs = data["languages"][:5]
    if not langs:
        return ""
    # say which of the two measurements this is, rather than letting an
    # estimate pass as a byte count
    how = ("measured from repository bytes" if data.get("languages_exact")
           else "primary language, weighted by repository size")
    out = [label(x, y - 6, f"language distribution · {how}", t["muted"])]
    # one continuous rule, then the names beneath it
    off = 0.0
    span = w - 2 * max(len(langs) - 1, 0)
    for i, l in enumerate(langs):
        seg = max(l["share"] * span, 2)
        out.append(
            f'<rect x="{n(x + off)}" y="{n(y + 12)}" width="0" height="8" '
            f'rx="4" fill="{ramp(t, i, len(langs))}">'
            f'<animate attributeName="width" from="0" to="{n(seg)}" '
            f'dur="0.8s" begin="{n(0.45 + i * 0.05)}s" fill="freeze" '
            f'calcMode="spline" keyTimes="0;1" '
            f'keySplines="{MOTION["ease"]}"/></rect>')
        off += seg + 2
    lx = x
    for i, l in enumerate(langs):
        out.append(f'<rect x="{n(lx)}" y="{n(y + 36)}" width="7" height="7" '
                   f'rx="1.5" fill="{ramp(t, i, len(langs))}"/>')
        txt = f"{l['name']} {l['share'] * 100:.0f}%"
        out.append(text(lx + 12, y + 43, txt, "small", t["muted"], size=11))
        lx += 12 + len(txt) * 7 + 18
    return "".join(out)


def render(data, t):
    inner = CANVAS_W - M * 2
    tot, streak = data["totals"], data["streak"]
    body = []
    a = body.append

    a(group(M, 40, delay=0.05, dy=6)
      + label(0, 0, "pulse", t["accent"])
      + label(inner, 0,
              f"{tot['active_days']} active days · trailing 12 months",
              t["dim"], anchor="end") + "</g>")
    a(hairline(M, 54, inner, t, t["line"], 1, delay=0.08))

    stats = [
        (f"{streak['current']}", "current streak",
         "day" if streak["current"] == 1 else "days", "consecutive"),
        (f"{streak['longest']}", "longest streak",
         "day" if streak["longest"] == 1 else "days", "personal best"),
        (_fmt(tot["contributions_year"]), "contributions", "",
         "trailing 12 months"),
        (_fmt(tot["repos"]), "repositories", "", "public, not forks"),
        (_fmt(tot["stars"]), "stars earned", "", "across all repos"),
        (f"{tot['best_day']}", "best day", "", "single-day peak"),
    ]
    col = inner / len(stats)
    for i, (val, lab, unit, note) in enumerate(stats):
        a(_stat(M + col * i, 112, val, lab, note, t,
                0.16 + i * MOTION["stagger"], size=30, unit=unit))

    a(hairline(M, 176, inner, t, t["line_soft"], 1))

    half = (inner - 60) / 2
    a(_cadence(data, t, M, 214, half * 0.62))
    a(_volume(data, t, M + half * 0.62 + 50, 214, inner - half * 0.62 - 50))
    a(hairline(M, 322, inner, t, t["line_soft"], 1))
    a(_languages(data, t, M, 348, inner))

    defs = (f'<linearGradient id="pulseFill" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{t["accent"]}" stop-opacity="0.24"/>'
            f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/>'
            f'</linearGradient>')
    return document(CANVAS_W, H, t, "Contribution pulse", "".join(body), defs)
