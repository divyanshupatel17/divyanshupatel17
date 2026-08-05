"""
Halftone portrait.

Turns a photograph into a dot matrix that can live inside an SVG terminal.

The hard part is not the halftone, it is the photograph. A GitHub avatar is
usually a backlit phone snap against a busy outdoor background, which is the
worst possible input for a naive tone map: the sky comes out denser than the
face. Three things fix that, in this order.

  1. Local contrast, not global tone. Each cell is compared against a blurred
     copy of its own neighbourhood, so a pixel is inked for being darker
     *than what surrounds it* rather than darker in absolute terms. Backlight
     gradients cancel out, and smooth regions like open sky produce no ink at
     all because they match their own blur.
  2. A chroma key on blue, which removes whatever sky survives step one.
  3. An elliptical spotlight with a floor fade, which drops the shoulders and
     the scenery at the edges of frame.

Output is cached to assets/portrait.json. The expensive part runs once; the
renderer stays deterministic and needs neither Pillow nor the network.
"""
import colorsys
import io
import json
import math
import os
import urllib.request

TILE = 7.0                    # cell pitch in SVG units


def _load(source, cache_png):
    from PIL import Image
    if source.startswith("http"):
        req = urllib.request.Request(source, headers={"User-Agent": "profile"})
        raw = urllib.request.urlopen(req, timeout=25).read()
        if cache_png:
            os.makedirs(os.path.dirname(cache_png), exist_ok=True)
            with open(cache_png, "wb") as f:
                f.write(raw)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    return Image.open(source).convert("RGB")


def analyse(cfg, cache_png=None):
    """Photo in, tone matrix out. Requires Pillow; only ever runs at build."""
    from PIL import Image, ImageFilter, ImageOps

    p = cfg["portrait"]
    im = _load(p["source"], cache_png)
    w, h = im.size

    # crop box is stored as fractions so it survives a change of avatar size
    x0, y0, x1, y1 = p["crop"]
    im = im.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))

    gw, gh = p["grid"]
    small = im.resize((gw, gh), Image.LANCZOS)
    gray = ImageOps.grayscale(small)
    blur = gray.filter(ImageFilter.GaussianBlur(radius=p.get("radius", 3.2)))
    cp, gp, bp = small.load(), gray.load(), blur.load()

    cx, cy = gw * p["centre"][0], gh * p["centre"][1]
    rx, ry = gw * p["spot"][0], gh * p["spot"][1]
    gain = p.get("gain", 2.4)
    floor = p.get("floor", 0.12)

    rows = []
    for y in range(gh):
        row = []
        for x in range(gw):
            r, g, b = [c / 255 for c in cp[x, y]]
            hue, sat, val = colorsys.rgb_to_hsv(r, g, b)

            sky = 0.0
            if 0.45 < hue < 0.78:
                sky = (min(1.0, max(0.0, (sat - 0.06) / 0.26))
                       * min(1.0, max(0.0, (val - 0.20) / 0.28)))

            local = gp[x, y] / 255
            around = max(bp[x, y] / 255, 0.02)
            ink = max(0.0, 1.0 - local / around) * gain

            d = math.hypot((x - cx) / rx, (y - cy) / ry)
            spot = max(0.0, 1.0 - max(0.0, d - 0.60) / 0.40) ** 1.3
            # fade the last fifth of the frame so shoulders dissolve rather
            # than ending on a hard edge
            fade = min(1.0, max(0.0, (gh - 1 - y) / (gh * 0.22)))

            v = min(1.0, ink) * (1 - sky * 0.85) * spot * fade
            row.append(round(v, 3) if v >= floor else 0.0)
        rows.append(row)

    # Trim to the bounding box of lit cells. The spotlight and the sky key
    # both zero out large margins, so without this the renderer would centre a
    # small subject inside a mostly empty grid and the portrait would float in
    # its frame instead of filling it.
    lit = [(x, y) for y, r in enumerate(rows) for x, v in enumerate(r) if v]
    if lit:
        x0 = min(p[0] for p in lit)
        x1 = max(p[0] for p in lit) + 1
        y0 = min(p[1] for p in lit)
        y1 = max(p[1] for p in lit) + 1
        rows = [r[x0:x1] for r in rows[y0:y1]]
        gw, gh = x1 - x0, y1 - y0

    return {"grid": [gw, gh], "floor": floor, "rows": rows}


def build(cfg, out_path, cache_png=None):
    data = analyse(cfg, cache_png)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    lit = sum(1 for r in data["rows"] for v in r if v)
    print(f"portrait.json — {data['grid'][0]}x{data['grid'][1]} grid, "
          f"{lit} lit cells")
    return data


# ─── render ──────────────────────────────────────────────────────────────────

def render(pdata, t, x, y, tile=TILE, delay=0.0, reveal=1.6):
    """Draw the matrix as one path per phosphor level.

    Grouping by level means five path elements instead of several thousand
    circles, which is the difference between a 400 KB hero and a 90 KB one.
    Squares rather than circles: they hold their shape when GitHub's proxy
    downscales the asset, and they read as pixels, which is the point.
    """
    from .svgkit import n

    gw, gh = pdata["grid"]
    levels = len(t["glow"])
    buckets = [[] for _ in range(levels)]

    for gy, row in enumerate(pdata["rows"]):
        for gx, v in enumerate(row):
            if not v:
                continue
            lv = min(levels - 1, int((1.0 - v) * levels))
            size = 1.6 + v * (tile * 0.62)
            px = x + gx * tile + (tile - size) / 2
            py = y + gy * tile + (tile - size) / 2
            buckets[lv].append(
                f"M{px:.1f} {py:.1f}h{size:.1f}v{size:.1f}h-{size:.1f}z")

    out = []
    for lv, d in enumerate(buckets):
        if not d:
            continue
        out.append(f'<path d="{"".join(d)}" fill="{t["glow"][lv]}" '
                   f'shape-rendering="crispEdges"/>')

    # the image resolves out of the dark like a CRT warming up: a soft-edged
    # wipe travelling down the frame, once
    uid = f"warm{int(x)}{int(y)}"
    body = "".join(out)
    return (
        f'<defs><linearGradient id="{uid}g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="1"/>'
        f'<stop offset="0.85" stop-color="#fff" stop-opacity="1"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        f'</linearGradient>'
        f'<mask id="{uid}">'
        f'<rect x="{n(x)}" y="{n(y - gh * tile)}" width="{n(gw * tile)}" '
        f'height="{n(gh * tile)}" fill="url(#{uid}g)">'
        f'<animate attributeName="y" from="{n(y - gh * tile)}" to="{n(y)}" '
        f'dur="{n(reveal)}s" begin="{n(delay)}s" fill="freeze" '
        f'calcMode="spline" keyTimes="0;1" keySplines="0.3 0 0.2 1"/>'
        f'</rect></mask></defs>'
        f'<g mask="url(#{uid})">{body}</g>'
    )
