"""
Production — the two things that are actually live.

Every other section of a profile describes work. This one proves it: each card
carries an HTTP status and a response time measured against the real origin at
build time. If a product is down when the workflow runs, the card says DOWN.
A status light you cannot falsify is worth more than a paragraph claiming
uptime.
"""
from ..core.svgkit import (document, group, hairline, label, n, text, truncate,
                           wrap)
from ..core.tokens import CANVAS_W, MOTION

M = 40
GAP = 20
CARD_H = 196
H = 96 + CARD_H + 20


def _card(p, x, y, i, t, w):
    probe = p.get("probe", {})
    up = probe.get("up")
    d = 0.2 + i * 0.12
    g = [group(x, y, delay=d, dy=12)]
    a = g.append

    a(f'<rect x="0" y="0" width="{n(w)}" height="{CARD_H}" rx="12" '
      f'fill="{t["panel"]}" stroke="{t["line"]}"/>')
    # a thin accent edge on the leading side, the card's only ornament
    a(f'<rect x="0" y="16" width="3" height="0" rx="1.5" fill="{t["accent"]}">'
      f'<animate attributeName="height" from="0" to="{CARD_H - 32}" '
      f'dur="0.8s" begin="{n(d + 0.2)}s" fill="freeze" calcMode="spline" '
      f'keyTimes="0;1" keySplines="{MOTION["ease"]}"/></rect>')

    a(text(28, 46, p["name"], "h1", t["text"], size=24))

    # status light, measured not claimed
    col = t["live"] if up else t["ember"]
    sx = w - 28
    status = (f'{probe.get("status", 0)} · {probe.get("ms", 0)}ms'
              if up else "unreachable")
    a(text(sx, 42, status, "code", t["muted"], anchor="end"))
    a(f'<circle cx="{n(sx - len(status) * 6.6 - 12)}" cy="38" r="4" '
      f'fill="{col}"/>')
    if up:
        a(f'<circle cx="{n(sx - len(status) * 6.6 - 12)}" cy="38" r="4" '
          f'fill="none" stroke="{col}" stroke-width="1.2">'
          f'<animate attributeName="r" values="4;11" '
          f'dur="{MOTION["pulse"]}s" repeatCount="indefinite"/>'
          f'<animate attributeName="opacity" values="0.8;0" '
          f'dur="{MOTION["pulse"]}s" repeatCount="indefinite"/></circle>')

    a(text(28, 70, p.get("tagline", ""), "body", t["accent_soft"]))
    a(hairline(28, 88, w - 56, t, t["line"]))

    for j, line in enumerate(wrap(p.get("detail", ""), 58, 3)):
        a(text(28, 116 + j * 19, line, "small", t["muted"]))

    a(text(28, CARD_H - 26, " / ".join(p.get("stack", [])), "code", t["dim"]))
    a(text(w - 28, CARD_H - 26,
           truncate(p["url"].replace("https://", "").rstrip("/"), 38),
           "code", t["accent"], anchor="end"))
    a("</g>")
    return "".join(g)


def render(data, t):
    items = data["production"]
    inner = CANVAS_W - M * 2
    cw = (inner - GAP * (len(items) - 1)) / max(len(items), 1)
    up = sum(1 for p in items if p.get("probe", {}).get("up"))

    body = []
    a = body.append
    a(group(M, 40, delay=0.05, dy=6)
      + label(0, 0, "production", t["accent"])
      + label(inner, 0, f"{up}/{len(items)} responding · probed at build",
              t["dim"], anchor="end") + "</g>")
    a(hairline(M, 54, inner, t, t["line"], 1, delay=0.08))
    a(group(M, 78, delay=0.12, dy=8)
      + text(0, 0, "Shipped, public, and taking real traffic.", "lead",
             t["muted"]) + "</g>")

    for i, p in enumerate(items):
        a(_card(p, M + i * (cw + GAP), 96, i, t, cw))

    return document(CANVAS_W, H, t, "Products in production", "".join(body))
