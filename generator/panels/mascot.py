"""
Relay — the mascot.

The first computer bug was a literal moth, found taped into the logbook of the
Harvard Mark II in 1947. This one is drawn to the phosphor: it orbits the
lamp at the end of the page, wings beating, and never quite lands.

Built from pixel rectangles rather than curves so it belongs to the same
visual language as the portrait, and so it survives being downscaled by
GitHub's image proxy without turning to mush.
"""
from ..core.svgkit import document, label, n, text
from ..core.tokens import CANVAS_W

H = 148
M = 40


def _moth(t, scale=1.0):
    """One moth, drawn at the origin, wings already beating.

    Stepped rectangles rather than curves: it has to belong to the same
    vocabulary as the halftone portrait, and a curve at this size would just
    read as a smudge. The forewing steps outward and the hindwing steps back
    in, which is what makes a blocky silhouette read as a moth rather than as
    a plus sign.
    """
    u = 2.6 * scale
    wing, edge, body = t["accent_soft"], t["accent"], t["accent_deep"]

    def px(x, y, w, h, fill, op=1.0):
        return (f'<rect x="{n(x * u)}" y="{n(y * u)}" width="{n(w * u)}" '
                f'height="{n(h * u)}" fill="{fill}" opacity="{n(op)}"/>')

    def half(s):                       # s = -1 left, +1 right
        o = 0 if s > 0 else -1         # keep the mirror on the pixel grid
        col = lambda x, y, w, h, f, a=1.0: px(  # noqa: E731
            (x if s > 0 else -x - w) + o, y, w, h, f, a)
        return (
            col(1, -6, 3, 2, wing, 0.9) +      # forewing, upper step
            col(1, -4, 5, 3, wing) +           # forewing, wide step
            col(1, -1, 6, 2, edge, 0.92) +     # leading edge
            col(1, 1, 4, 3, wing, 0.85) +      # hindwing
            col(1, 4, 2, 2, wing, 0.6)         # hindwing tip
        )

    beat = ('<animateTransform attributeName="transform" type="scale" '
            'values="1 1;0.45 1.06;1 1" dur="0.46s" repeatCount="indefinite" '
            'calcMode="spline" keyTimes="0;0.5;1" '
            'keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/>')

    core = (px(-0.5, -5, 1, 10, body)          # thorax into abdomen
            + px(-1, -7, 2, 2, body)           # head
            + px(-2.5, -9, 1, 2, edge, 0.85)   # antennae
            + px(1.5, -9, 1, 2, edge, 0.85))

    return (f'<g><g>{beat}{half(-1)}</g><g>{beat}{half(1)}</g>{core}</g>')


def render(data, t):
    body = []
    a = body.append
    cfg = data["config"]["mascot"]
    lamp_x, lamp_y = CANVAS_W - 150, H / 2

    # the lamp: a single glowing cell, breathing
    a(f'<defs><radialGradient id="lamp">'
      f'<stop offset="0" stop-color="{t["accent"]}" stop-opacity="0.55"/>'
      f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/>'
      f'</radialGradient></defs>')
    a(f'<circle cx="{n(lamp_x)}" cy="{n(lamp_y)}" r="66" fill="url(#lamp)">'
      f'<animate attributeName="r" values="60;72;60" dur="4.5s" '
      f'repeatCount="indefinite"/></circle>')
    a(f'<rect x="{n(lamp_x - 5)}" y="{n(lamp_y - 5)}" width="10" height="10" '
      f'rx="1" fill="{t["accent"]}">'
      f'<animate attributeName="opacity" values="1;0.72;1" dur="4.5s" '
      f'repeatCount="indefinite"/></rect>')

    # orbit: an ellipse the moth is carried along, never closing on the lamp
    a(f'<ellipse cx="{n(lamp_x)}" cy="{n(lamp_y)}" rx="86" ry="34" '
      f'fill="none" stroke="{t["line"]}" stroke-dasharray="1 6" '
      f'opacity="0.6"/>')
    path = (f"M{n(lamp_x - 86)},{n(lamp_y)} "
            f"a86,34 0 1,1 172,0 a86,34 0 1,1 -172,0")
    a(f'<g>{_moth(t, 1.7)}'
      f'<animateMotion dur="11s" repeatCount="indefinite" path="{path}"/>'
      f'</g>')

    a(label(M, H / 2 - 8, cfg["name"], t["accent"]))
    a(text(M, H / 2 + 14, cfg["line"], "small", t["muted"]))

    return document(CANVAS_W, H, t, f"{cfg['name']}, the mascot",
                    "".join(body))
