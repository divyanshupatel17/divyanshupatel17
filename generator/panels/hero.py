"""
Hero — a terminal that is telling the truth.

Left: the subject, rendered as a phosphor dot matrix from the account's own
avatar. Right: a manifest. Keys on the left, values on the right, a dotted
leader carrying the eye across, which is the oldest and still the clearest way
to set a specification.

Rows marked `auto` in the config are filled from live data. Nothing in the
manifest that GitHub can measure is typed by a human.
"""
from datetime import date, datetime, timezone

from ..core import portrait as portrait_mod
from ..core.svgkit import (document, group, hairline, label, leader, n,
                           prompt, text, truncate)
from ..core.tokens import ADVANCE, CANVAS_W, MOTION, TYPE

H = 648
PAD = 10
BAR = 46
LEFT_X, LEFT_W = 34, 442
RIGHT_X, RIGHT_W = 508, 660
BODY_Y = 96
ROW_PITCH = 21


def _uptime(since):
    d = date.fromisoformat(since)
    today = datetime.now(timezone.utc).date()
    months = (today.year - d.year) * 12 + today.month - d.month
    y, m = divmod(max(months, 0), 12)
    return f"{y}y {m}mo on GitHub" if y else f"{m}mo on GitHub"


def _autofill(data):
    """Every value the manifest can derive rather than be told."""
    ident, tot, cfg = data["identity"], data["totals"], data["config"]
    langs = ", ".join(l["name"] for l in data["languages"][:3]) or "n/a"
    links = cfg["links"]
    return {
        "name": ident["name"],
        "location": ident["location"] or "Earth",
        "since": _uptime(ident["since"]),
        "languages": langs,
        "repos": f"{tot['repos']} public, {tot['stars']} stars",
        "email": links["email"],
        "portfolio": links["portfolio"].replace("https://", ""),
        "linkedin": links["linkedin"].split("/in/")[-1].strip("/"),
        "handle": f"@{ident['login']}",
    }


def _chrome(data, t):
    """Window frame. No traffic lights: this is not a screenshot of macOS,
    and borrowing its furniture is the fastest way to look like everyone
    else. A pixel mark, a path, and a live indicator instead."""
    w = CANVAS_W - PAD * 2
    out = []
    a = out.append

    a(f'<rect x="{PAD}" y="{PAD}" width="{n(w)}" height="{n(H - PAD * 2)}" '
      f'rx="16" fill="{t["panel"]}" stroke="{t["accent"]}" '
      f'stroke-opacity="0.30" stroke-width="1"/>')
    a(f'<rect x="{PAD}" y="{PAD}" width="{n(w)}" height="{BAR}" rx="16" '
      f'fill="{t["panel_alt"]}"/>')
    a(f'<rect x="{PAD}" y="{PAD + 20}" width="{n(w)}" height="{BAR - 20}" '
      f'fill="{t["panel_alt"]}"/>')
    a(hairline(PAD, PAD + BAR, w, t, t["line"]))

    # pixel mark: four cells, the smallest possible logo
    mx, my = PAD + 22, PAD + 16
    for i, (dx, dy) in enumerate(((0, 0), (7, 0), (0, 7), (7, 7))):
        col = t["accent"] if i != 2 else t["ember"]
        a(f'<rect x="{n(mx + dx)}" y="{n(my + dy)}" width="6" height="6" '
          f'rx="1" fill="{col}" opacity="{0.55 + i * 0.15:.2f}"/>')

    a(text(mx + 28, PAD + 28, f"{data['identity']['login']}", "small",
           t["muted"]))
    a(text(CANVAS_W / 2, PAD + 28,
           "~ %  ./profile.sh --live --theme=phosphor", "small", t["dim"],
           anchor="middle"))

    lx = CANVAS_W - PAD - 30
    a(text(lx, PAD + 28, "LIVE", "label", t["live"], anchor="end"))
    a(f'<circle cx="{n(lx - 38)}" cy="{PAD + 23}" r="3.5" fill="{t["live"]}"/>'
      f'<circle cx="{n(lx - 38)}" cy="{PAD + 23}" r="3.5" fill="none" '
      f'stroke="{t["live"]}" stroke-width="1.2">'
      f'<animate attributeName="r" values="3.5;9" dur="{MOTION["pulse"]}s" '
      f'repeatCount="indefinite"/>'
      f'<animate attributeName="opacity" values="0.8;0" '
      f'dur="{MOTION["pulse"]}s" repeatCount="indefinite"/></circle>')
    return "".join(out)


def _frame(t, x, y, w, h, delay):
    """Corner brackets rather than a closed rectangle. The subject reads as
    something being observed, and the frame does not compete with the dots."""
    c, s = t["accent"], 22
    seg = []
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1),
                           (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        seg.append(f'M{n(cx)},{n(cy + sy * s)}L{n(cx)},{n(cy)}'
                   f'L{n(cx + sx * s)},{n(cy)}')
    return (f'<path d="{"".join(seg)}" fill="none" stroke="{c}" '
            f'stroke-width="1.5" stroke-linecap="square" opacity="0">'
            f'<animate attributeName="opacity" from="0" to="0.85" dur="0.6s" '
            f'begin="{n(delay)}s" fill="freeze"/></path>')


def _manifest(data, t):
    rows = data["config"]["spec"]["rows"]
    auto = _autofill(data)
    size = TYPE["body"][0]
    adv = size * ADVANCE
    out = []
    a = out.append

    a(label(RIGHT_X, BODY_Y + 4, "manifest", t["accent"]))
    a(hairline(RIGHT_X, BODY_Y + 14, RIGHT_W, t, t["line"], 1, delay=0.25))

    # session pill: the one piece of contact detail worth putting up front
    mail = data["config"]["links"]["email"]
    pw = len(mail) * adv + 24
    a(group(RIGHT_X, BODY_Y + 34, delay=0.3, dy=6))
    a(f'<rect x="0" y="0" width="{n(pw)}" height="26" rx="6" '
      f'fill="{t["accent"]}"/>')
    a(text(12, 17.5, mail, "body", t["bg"], weight=700))
    a("</g>")

    y = BODY_Y + 92
    delay = 0.36
    for row in rows:
        if row.get("gap"):
            y += 11
            continue
        key = row["key"]
        val = auto.get(row["auto"], "") if row.get("auto") else row.get("value", "")
        val = truncate(val, 44)
        a(group(RIGHT_X, y, delay=delay, dy=4))
        a(text(0, 0, key, "body", t["spec_key"]))
        kx = len(key) * adv + 10
        vx = RIGHT_W - len(val) * adv - 10
        if vx > kx:
            a(leader(kx, vx, -4, t["line_strong"]))
        a(text(RIGHT_W, 0, val, "body", t["text"], anchor="end", weight=600))
        a("</g>")
        y += ROW_PITCH
        delay += 0.028

    return "".join(out), y


def render(data, t):
    body = []
    a = body.append
    a(_chrome(data, t))

    # ── subject ─────────────────────────────────────────────────────────
    a(label(LEFT_X, BODY_Y + 4, "subject", t["accent"]))
    a(hairline(LEFT_X, BODY_Y + 14, LEFT_W, t, t["line"], 1, delay=0.25))

    pdata = data.get("portrait")
    fy, fh = BODY_Y + 34, 508
    a(_frame(t, LEFT_X, fy, LEFT_W, fh, 0.3))
    if pdata:
        gw, gh = pdata["grid"]
        tile = min((LEFT_W - 28) / gw, (fh - 28) / gh)
        px = LEFT_X + (LEFT_W - gw * tile) / 2
        py = fy + (fh - gh * tile) / 2
        a(portrait_mod.render(pdata, t, px, py, tile, delay=0.45))

    # scanline: one hairline drifting down the frame, barely there. Any more
    # opaque and it reads as a rendering artefact rather than a CRT.
    a(f'<rect x="{LEFT_X}" y="{n(fy)}" width="{LEFT_W}" height="24" '
      f'fill="url(#scan)" opacity="0.5">'
      f'<animate attributeName="y" from="{n(fy - 24)}" to="{n(fy + fh)}" '
      f'dur="9s" begin="2.2s" repeatCount="indefinite"/></rect>')

    # ── manifest ────────────────────────────────────────────────────────
    manifest, _ = _manifest(data, t)
    a(manifest)

    # ── prompt ──────────────────────────────────────────────────────────
    py = H - 34
    a(text(RIGHT_X, py, "▸", "body", t["ember"]))
    a(prompt(RIGHT_X + 18, py, data["config"]["typing"]["lines"], "body",
             t["text_soft"], t))

    a(text(CANVAS_W - PAD - 24, py, f"synced {data['generated_at'][:10]}",
           "code", t["dim"], anchor="end"))

    title = (f'{data["identity"]["name"]}, {data["config"]["identity"]["role"]}. '
             f'{data["config"]["identity"]["statement"]}')
    defs = (f'<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{t["accent"]}" stop-opacity="0"/>'
            f'<stop offset="0.5" stop-color="{t["accent"]}" stop-opacity="0.10"/>'
            f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/>'
            f'</linearGradient>')
    return document(CANVAS_W, H, t, title, "".join(body), defs)
