"""
Skyline — a year of contributions, extruded.

The 3D contribution graph everyone links to is a third-party action rendering
in a palette that is not ours. This draws the same idea from the same data, in
system colours, as plain SVG: 364 days on a projected grid, each day a tower
whose height is that day's contribution count.

The projection is dimetric rather than the usual 45 degree isometric. A true
isometric view of 52 weeks by 7 days produces a long thin diagonal ribbon that
wastes most of a 1200px canvas; tilting the week axis nearly flat and steepening
the weekday axis lays the same year out as a wide city block that fills the
frame. The two basis vectors below are the only thing that controls it.

Towers are drawn back to front, so the painter's algorithm resolves occlusion
with no z-sorting machinery. Empty days stay as flat plates rather than
disappearing, so a quiet month reads as quiet instead of as missing data.
"""
from datetime import date

from ..core.svgkit import document, group, hairline, label, mix, n, text
from ..core.tokens import CANVAS_W, MOTION

H = 430
M = 40
U = (19.6, 3.4)          # one week: right, slightly down
V = (-15.0, 11.0)        # one weekday: left, down
MAX_TOWER = 86
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _quad(pts, fill, stroke=None, sw=0.5):
    d = "M" + "L".join(f"{n(x)},{n(y)}" for x, y in pts) + "Z"
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<path d="{d}" fill="{fill}"{s}/>'


def _tower(px, py, h, top, left, right):
    """Extrude one tile. A, B, C, D are the tile corners; C is the front
    corner, so the two faces the viewer can see are B-C and D-C."""
    a = (px, py)
    b = (px + U[0], py + U[1])
    c = (px + U[0] + V[0], py + U[1] + V[1])
    d = (px + V[0], py + V[1])
    up = lambda p: (p[0], p[1] - h)          # noqa: E731
    return (
        _quad([b, c, up(c), up(b)], right)
        + _quad([d, c, up(c), up(d)], left)
        + _quad([up(a), up(b), up(c), up(d)], top)
    )


def render(data, t):
    inner = CANVAS_W - M * 2
    cal = data.get("calendar")
    if not cal:
        return document(CANVAS_W, 1, t, "skyline", "")

    window, counts = cal["window"], cal["counts"]
    start = date.fromisoformat(window[0])
    offset = start.weekday()
    peak = max(counts.values()) or 1

    cells = []
    for i, key in enumerate(window):
        col, row = (i + offset) // 7, (i + offset) % 7
        cells.append((col, row, key, counts.get(key, 0)))
    cols = max(c[0] for c in cells) + 1

    xs = [c[0] * U[0] + c[1] * V[0] for c in cells]
    ox = (CANVAS_W - (max(xs) - min(xs) + U[0])) / 2 - min(xs)
    oy = 168

    body = []
    a = body.append

    a(group(M, 40, delay=0.05, dy=6)
      + label(0, 0, "skyline", t["accent"])
      + label(inner, 0,
              f"{data['totals']['contributions_year']:,} contributions · "
              f"peak {peak} in a day", t["dim"], anchor="end") + "</g>")
    a(hairline(M, 54, inner, t, t["line"], 1, delay=0.08))
    a(group(M, 78, delay=0.1, dy=6)
      + text(0, 0, f"{len(window)} days, extruded. Every tower is one day.",
             "lead", t["muted"]) + "</g>")

    # Month ticks ride the front-bottom edge. Towers grow upward, so anything
    # labelled along the back edge gets buried by the buildings in front of it.
    seen = set()
    for col, row, key, _ in cells:
        d = date.fromisoformat(key)
        if row == 6 and d.day <= 7 and key[:7] not in seen:
            seen.add(key[:7])
            a(label(ox + col * U[0] + 6 * V[0], oy + col * U[1] + 6 * V[1] + 24,
                    MONTHS[d.month - 1], t["dim"], anchor="middle",
                    opacity=0.85))

    # painter's algorithm: front-most last
    for col, row, key, v in sorted(cells,
                                   key=lambda c: c[0] * U[1] + c[1] * V[1]):
        px = ox + col * U[0] + row * V[0]
        py = oy + col * U[1] + row * V[1]
        lvl = v / peak

        if not v:
            a(_quad([(px, py), (px + U[0], py + U[1]),
                     (px + U[0] + V[0], py + U[1] + V[1]),
                     (px + V[0], py + V[1])],
                    t["panel"], t["line_soft"], 0.5))
            continue

        # a floor under the exponent so a single contribution still
        # reads as a building rather than a bump in the pavement
        h = (0.18 + (lvl ** 0.55) * 0.82) * MAX_TOWER
        # Height is continuous; colour is not. Tops snap to the five-stop
        # phosphor ramp, so a tower's brightness is a readable band rather
        # than an arbitrary interpolation, and every face stays a two-token
        # blend the palette check can verify.
        glow = t["glow"]
        top = glow[max(0, len(glow) - 1 - int(lvl ** 0.5 * (len(glow) - 0.01)))]
        left = mix(top, t["bg"], 0.58)
        right = mix(top, t["bg"], 0.30)
        d0 = 0.25 + col * 0.011
        a(f'<g opacity="0">'
          f'<animate attributeName="opacity" from="0" to="1" dur="0.4s" '
          f'begin="{n(d0)}s" fill="freeze"/>'
          f'<g><animateTransform attributeName="transform" type="translate" '
          f'from="0 {n(h)}" to="0 0" dur="0.7s" begin="{n(d0)}s" '
          f'fill="freeze" calcMode="spline" keyTimes="0;1" '
          f'keySplines="{MOTION["ease"]}"/>'
          + _tower(px, py, h, top, left, right) +
          f'</g></g>')

    return document(CANVAS_W, H, t, "Contribution skyline", "".join(body))
