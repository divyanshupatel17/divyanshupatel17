"""
SVG primitives.

A tiny drawing vocabulary shared by every panel: text that respects the type
scale, hairlines, panels, chips, sparklines, rings, bars, and a single
entrance-animation helper. Panels compose these; they never emit raw markup
for anything that appears more than once.

Everything returns a string. No DOM, no dependencies.
"""
from html import escape as _esc

from .tokens import MOTION, RADIUS, SPACE, TYPE


def esc(s):
    return _esc(str(s), quote=True)


def n(v):
    """Trim floats so generated files stay small and diffs stay readable."""
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


# ─── motion ──────────────────────────────────────────────────────────────────

def enter(delay=0.0, dy=10, dur=None):
    """Fade + rise, once, then freeze. The system's only entrance gesture."""
    dur = dur or MOTION["enter"]
    a = (f'<animate attributeName="opacity" from="0" to="1" dur="{n(dur)}s" '
         f'begin="{n(delay)}s" fill="freeze" calcMode="spline" keyTimes="0;1" '
         f'keySplines="{MOTION["ease"]}"/>')
    if dy:
        a += (f'<animateTransform attributeName="transform" type="translate" '
              f'additive="sum" from="0 {n(dy)}" to="0 0" dur="{n(dur)}s" '
              f'begin="{n(delay)}s" fill="freeze" calcMode="spline" '
              f'keyTimes="0;1" keySplines="{MOTION["ease"]}"/>')
    return a


def group(x=0, y=0, delay=None, dy=10, extra=""):
    """Open a positioned <g>, optionally with an entrance. Close with '</g>'."""
    if delay is None:
        return f'<g transform="translate({n(x)},{n(y)})" {extra}>'
    return (f'<g transform="translate({n(x)},{n(y)})" opacity="0" {extra}>'
            f'{enter(delay, dy)}')


def draw_in(delay=0.0, length=100.0, dur=None):
    """Stroke reveal for paths and arcs."""
    dur = dur or MOTION["draw"]
    return (f'stroke-dasharray="{n(length)}" stroke-dashoffset="{n(length)}">'
            f'<animate attributeName="stroke-dashoffset" to="0" '
            f'dur="{n(dur)}s" begin="{n(delay)}s" fill="freeze" '
            f'calcMode="spline" keyTimes="0;1" keySplines="{MOTION["ease"]}"/>')


# ─── type ────────────────────────────────────────────────────────────────────

def text(x, y, content, style="body", fill="#fff", anchor="start",
         opacity=None, weight=None, size=None, extra="", raw=False):
    sz, wt, tr, fam = TYPE[style]
    sz = size if size is not None else sz
    wt = weight if weight is not None else wt
    op = f' opacity="{n(opacity)}"' if opacity is not None else ""
    body = content if raw else esc(content)
    return (f'<text x="{n(x)}" y="{n(y)}" font-family="{fam}" font-size="{n(sz)}" '
            f'font-weight="{wt}" letter-spacing="{n(tr)}" fill="{fill}" '
            f'text-anchor="{anchor}"{op} {extra}>{body}</text>')


def label(x, y, content, fill, anchor="start", opacity=None):
    """Uppercase mono eyebrow — the system's section marker."""
    return text(x, y, str(content).upper(), "label", fill, anchor, opacity)


def tspan(content, fill=None, dx=0, dy=0, weight=None, size=None):
    bits = ""
    if fill:
        bits += f' fill="{fill}"'
    if dx:
        bits += f' dx="{n(dx)}"'
    if dy:
        bits += f' dy="{n(dy)}"'
    if weight:
        bits += f' font-weight="{weight}"'
    if size:
        bits += f' font-size="{n(size)}"'
    return f'<tspan{bits}>{esc(content)}</tspan>'


def truncate(s, max_chars):
    s = str(s)
    return s if len(s) <= max_chars else s[: max_chars - 1].rstrip() + "…"


def wrap(s, max_chars, max_lines=2):
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if lines and len(" ".join(lines)) < len(s):
        lines[-1] = truncate(lines[-1] + " …", max_chars)
    return lines


# ─── surfaces ────────────────────────────────────────────────────────────────

def panel(x, y, w, h, t, radius=None, fill=None, stroke=None):
    r = RADIUS["panel"] if radius is None else radius
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" '
            f'rx="{n(r)}" fill="{fill or t["panel"]}" '
            f'stroke="{stroke or t["line"]}" stroke-width="1"/>')


def hairline(x, y, w, t, color=None, opacity=1, delay=None):
    """A 1px rule. With a delay it sweeps open from the left, once."""
    c = color or t["line"]
    if delay is None:
        return (f'<line x1="{n(x)}" y1="{n(y)}" x2="{n(x + w)}" y2="{n(y)}" '
                f'stroke="{c}" stroke-width="1" opacity="{n(opacity)}"/>')
    return (f'<line x1="{n(x)}" y1="{n(y)}" x2="{n(x + w)}" y2="{n(y)}" '
            f'stroke="{c}" stroke-width="1" opacity="{n(opacity)}" '
            f'{draw_in(delay, w, MOTION["sweep"])}</line>')


def chip(x, y, content, t, fill=None, stroke=None, tone=None, pad=9, h=19):
    """Small metadata pill. Width is derived from the mono advance width."""
    tone = tone or t["muted"]
    w = len(str(content)) * 5.9 + pad * 2
    r = h / 2
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" '
            f'rx="{n(r)}" fill="{fill or t["panel_alt"]}" '
            f'stroke="{stroke or t["line"]}"/>'
            + text(x + w / 2, y + h / 2 + 3.6, content, "code", tone, "middle")), w


def live_dot(x, y, t, r=4):
    """The one perpetual animation in the system — it encodes state."""
    return (f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="{t["live"]}"/>'
            f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="none" '
            f'stroke="{t["live"]}" stroke-width="1.2" opacity="0.9">'
            f'<animate attributeName="r" values="{n(r)};{n(r * 2.6)}" '
            f'dur="{MOTION["pulse"]}s" repeatCount="indefinite" '
            f'calcMode="spline" keyTimes="0;1" keySplines="{MOTION["ease"]}"/>'
            f'<animate attributeName="opacity" values="0.7;0" '
            f'dur="{MOTION["pulse"]}s" repeatCount="indefinite"/></circle>')


def link(href, body):
    return f'<a href="{esc(href)}" target="_blank" rel="noopener">{body}</a>'


# ─── terminal marks ──────────────────────────────────────────────────────────

def leader(x1, x2, y, color, gap=5, opacity=0.55):
    """The dotted rule that carries the eye from a key to its value. Drawn as
    a dashed line rather than repeated glyphs so it stays crisp at any width
    and costs a single element."""
    return (f'<line x1="{n(x1)}" y1="{n(y)}" x2="{n(x2)}" y2="{n(y)}" '
            f'stroke="{color}" stroke-width="1" stroke-linecap="round" '
            f'stroke-dasharray="0.5 {n(gap)}" opacity="{n(opacity)}"/>')


def caret(x, y, t, w=8, h=15, color=None):
    """Block caret. Blinks forever, because a terminal that stops blinking
    reads as a screenshot."""
    from .tokens import MOTION
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" '
            f'fill="{color or t["accent"]}">'
            f'<animate attributeName="opacity" values="1;1;0;0" '
            f'dur="{MOTION["caret"]}s" repeatCount="indefinite" '
            f'calcMode="discrete"/></rect>')


def prompt(x, y, lines, style, fill, t, hold=2.8, clear=0.4, lead=1.0,
           caret_color=None):
    """A prompt that types each line, holds it, clears it, and moves on.

    Every line shares one cycle length, so the schedule is expressed as
    keyTimes on a single animation per line instead of a chain of `begin`
    dependencies, which browsers and GitHub's proxy handle inconsistently.
    A reveal is a clip rectangle widening in character-width steps; the caret
    is a second rectangle following the same schedule, so it sits exactly at
    the writing head rather than parked at a guessed offset.
    """
    from .tokens import ADVANCE, MOTION, TYPE
    sz = TYPE[style][0]
    adv = sz * ADVANCE + TYPE[style][2]

    spans = [len(s) * MOTION["type"] for s in lines]
    slots = [lead + sp + hold + clear for sp in spans]
    cycle = sum(slots)

    out = []
    start = 0.0
    for i, line in enumerate(lines):
        w = adv * len(line) + 2
        t0 = start + lead
        t1 = t0 + spans[i]
        t2 = t1 + hold
        t3 = t2 + clear
        kt = [0, start / cycle, t0 / cycle, t1 / cycle, t2 / cycle,
              t3 / cycle, 1]
        vals = [0, 0, 0, w, w, 0, 0]
        kts = ";".join(f"{k:.5f}" for k in kt)

        uid = f"pr{abs(hash((line, i, int(x), int(y)))) % 1000000}"
        out.append(
            f'<defs><clipPath id="{uid}">'
            f'<rect x="{n(x)}" y="{n(y - sz)}" width="0" '
            f'height="{n(sz * 1.7)}">'
            f'<animate attributeName="width" '
            f'values="{";".join(n(v) for v in vals)}" keyTimes="{kts}" '
            f'dur="{n(cycle)}s" repeatCount="indefinite"/>'
            f'</rect></clipPath></defs>'
            f'<g clip-path="url(#{uid})">'
            + text(x, y, line, style, fill) + '</g>')

        # caret rides the writing head, then blinks through the hold
        cx = [x, x, x, x + w, x + w, x, x]
        out.append(
            f'<rect x="{n(x)}" y="{n(y - sz * 0.86)}" width="8" '
            f'height="{n(sz * 1.15)}" fill="{caret_color or t["accent"]}">'
            f'<animate attributeName="x" '
            f'values="{";".join(n(v) for v in cx)}" keyTimes="{kts}" '
            f'dur="{n(cycle)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;0;1;1;1;0;0" '
            f'keyTimes="{kts}" dur="{n(cycle)}s" repeatCount="indefinite" '
            f'calcMode="discrete"/></rect>')
        start += slots[i]
    return "".join(out)


# ─── colour ──────────────────────────────────────────────────────────────────

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, k):
    """Blend two hex colours. k=0 -> a, k=1 -> b."""
    ra, rb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(ra[i] + (rb[i] - ra[i]) * k):02x}" for i in range(3))


def ramp(t, i, count):
    """Ordered series colour. One accent, stepped toward the muted end — so a
    six-language chart still reads as one palette instead of six brands."""
    if count <= 1:
        return t["accent"]
    return mix(t["accent_soft"], t["dim"], (i / (count - 1)) ** 0.85 * 0.82)


# ─── data marks ──────────────────────────────────────────────────────────────

def sparkline(x, y, w, h, values, color, delay=0.0, fill_color=None,
              width=1.6, smooth=True):
    """Area + line. Draws itself once, left to right."""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = w / max(len(values) - 1, 1)
    pts = [(x + i * step, y + h - (v - lo) / span * h) for i, v in enumerate(values)]

    if smooth and len(pts) > 2:
        d = f"M{n(pts[0][0])},{n(pts[0][1])}"
        for i in range(1, len(pts)):
            px, py = pts[i - 1]
            cx, cy = pts[i]
            mx = (px + cx) / 2
            d += f" C{n(mx)},{n(py)} {n(mx)},{n(cy)} {n(cx)},{n(cy)}"
    else:
        d = "M" + " L".join(f"{n(px)},{n(py)}" for px, py in pts)

    out = ""
    if fill_color:
        area = d + (f" L{n(pts[-1][0])},{n(y + h)} L{n(pts[0][0])},{n(y + h)} Z")
        out += (f'<path d="{area}" fill="{fill_color}" opacity="0">'
                f'<animate attributeName="opacity" from="0" to="1" dur="0.7s" '
                f'begin="{n(delay + 0.35)}s" fill="freeze"/></path>')
    out += (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{n(width)}" '
            f'stroke-linecap="round" stroke-linejoin="round" '
            f'{draw_in(delay, w * 1.9)}</path>')
    return out


def bar(x, y, w, h, pct, t, color=None, delay=0.0, track=None):
    """Horizontal proportion bar that grows to width, once."""
    c = color or t["accent"]
    target = max(w * min(max(pct, 0), 1), 2)
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" '
            f'rx="{n(h / 2)}" fill="{track or t["raise"]}"/>'
            f'<rect x="{n(x)}" y="{n(y)}" width="0" height="{n(h)}" '
            f'rx="{n(h / 2)}" fill="{c}">'
            f'<animate attributeName="width" from="0" to="{n(target)}" '
            f'dur="0.85s" begin="{n(delay)}s" fill="freeze" calcMode="spline" '
            f'keyTimes="0;1" keySplines="{MOTION["ease"]}"/></rect>')


def cell(x, y, size, color, delay=0.0, radius=2):
    """A single contribution square, faded in on a stagger."""
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(size)}" height="{n(size)}" '
            f'rx="{n(radius)}" fill="{color}" opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.4s" '
            f'begin="{n(delay)}s" fill="freeze"/></rect>')


# ─── document ────────────────────────────────────────────────────────────────

def document(w, h, t, title, body, defs=""):
    from .tokens import SANS
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{n(w)}" height="{n(h)}" viewBox="0 0 {n(w)} {n(h)}" '
        f'font-family="{SANS}" role="img" aria-label="{esc(title)}">'
        f'<title>{esc(title)}</title>'
        f'<defs>{defs}</defs>'
        f'<rect width="{n(w)}" height="{n(h)}" fill="{t["bg"]}"/>'
        f'{body}</svg>'
    )


# convenience re-export so panels can `from .svgkit import *` sparingly
__all__ = [
    "esc", "n", "enter", "group", "draw_in", "text", "label", "tspan",
    "truncate", "wrap", "panel", "hairline", "chip", "live_dot", "link",
    "sparkline", "bar", "cell", "document", "mix", "ramp", "SPACE", "RADIUS",
]
