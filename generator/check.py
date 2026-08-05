#!/usr/bin/env python3
"""
Guardrails. Run in CI on every build; exit code is non-zero on failure, so the
workflow refuses to commit bad art.

Five things get enforced, because these are the five ways a generated design
system quietly rots.

  1. Config sanity      Copy length limits derived from the real render
                        geometry, so an over-long line fails here instead of
                        wrapping badly on the profile page.
  2. Contrast           Every text token clears WCAG AA against both surfaces,
                        in both themes, asserted rather than assumed.
  3. Well-formedness    A malformed SVG renders as a broken image and GitHub
                        gives you no error to read.
  4. Weight             Every panel is fetched through GitHub's image proxy on
                        every profile view.
  5. Palette            Every colour in every asset must be a design token or a
                        blend of two of them. This is the check that actually
                        keeps "no random colours" true a year from now.
"""
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator.core.svgkit import _rgb, ramp                # noqa: E402
from generator.core.tokens import THEMES                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGET_KB = 130           # per asset
TOTAL_KB = 320            # per theme, everything one visitor loads
BANNED = ("<script", "<foreignObject", "@import", "<image", 'href="http')
HEX = re.compile(r"#(?:[0-9a-fA-F]{6})\b")

LIMITS = {          # field: max chars, from the geometry that renders it
    "identity.statement": 46,
    "spec.value": 44,           # manifest column, truncated past this
    "spec.key": 15,
    "production.tagline": 46,
    "production.detail": 174,   # 3 lines at 58
    "typing.line": 62,
    "mascot.line": 72,
}


# ─── config ──────────────────────────────────────────────────────────────────

def check_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    fails = []

    def cap(value, key, where):
        if len(value) > LIMITS[key]:
            fails.append(f"{where}: {len(value)} chars, max {LIMITS[key]}")

    cap(cfg["identity"]["statement"], "identity.statement", "identity.statement")
    for i, row in enumerate(cfg["spec"]["rows"]):
        if row.get("gap"):
            continue
        cap(row["key"], "spec.key", f"spec.rows[{i}].key")
        if row.get("auto") and row.get("value"):
            fails.append(f"spec.rows[{i}] has both auto and value; auto wins "
                         f"and the value is dead config")
        if not row.get("auto"):
            cap(row.get("value", ""), "spec.value", f"spec.rows[{i}].value")
    for p in cfg["production"]:
        cap(p["tagline"], "production.tagline", f"production[{p['name']}]")
        cap(p["detail"], "production.detail", f"production[{p['name']}]")
        if not p["url"].startswith("https://"):
            fails.append(f"production[{p['name']}].url must be https")
    for i, line in enumerate(cfg["typing"]["lines"]):
        cap(line, "typing.line", f"typing.lines[{i}]")
    cap(cfg["mascot"]["line"], "mascot.line", "mascot.line")

    if not fails:
        print(f"  ok  config: {len(cfg['spec']['rows'])} manifest rows, "
              f"{len(cfg['production'])} products, copy within limits")
    return fails


# ─── contrast ────────────────────────────────────────────────────────────────

def contrast(fg, bg):
    def lum(h):
        ch = []
        for c in _rgb(h):
            c /= 255
            ch.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    a, b = lum(fg), lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast():
    fails = []
    for name, t in THEMES.items():
        for key, minimum in (("text", 4.5), ("text_soft", 4.5), ("muted", 4.5),
                             ("dim", 3.0), ("accent", 3.0), ("live", 3.0),
                             ("ember", 3.0), ("accent_soft", 3.0),
                             ("spec_key", 3.0)):
            for surface in ("bg", "panel"):
                r = contrast(t[key], t[surface])
                if r < minimum:
                    fails.append(f"{name}: {key} on {surface} is {r:.2f}:1, "
                                 f"needs {minimum}:1")
    if not fails:
        print("  ok  contrast: every text token clears WCAG AA on both surfaces")
    return fails


# ─── palette ─────────────────────────────────────────────────────────────────

def token_colors(theme):
    ok = set()
    for v in theme.values():
        if isinstance(v, str) and v.startswith("#"):
            ok.add(v.lower())
        elif isinstance(v, list):
            ok.update(c.lower() for c in v if isinstance(c, str))
    for count in range(1, 9):
        for i in range(count):
            ok.add(ramp(theme, i, count).lower())
    return ok


def is_blend(color, palette, tol=3):
    """True if the colour sits on the straight line between two tokens.

    Panels legitimately mix tokens (a tower face is its top face mixed toward
    the background), so a flat allow-list would reject thousands of valid
    colours. Checking for a blend keeps the rule meaningful without hardcoding
    every derived value.
    """
    c = _rgb(color)
    pal = [_rgb(p) for p in palette]
    for i, a in enumerate(pal):
        for b in pal[i + 1:]:
            span = [b[j] - a[j] for j in range(3)]
            j = max(range(3), key=lambda k: abs(span[k]))
            if abs(span[j]) < 8:
                continue
            k = (c[j] - a[j]) / span[j]
            if not -0.02 <= k <= 1.02:
                continue
            if all(abs(a[m] + span[m] * k - c[m]) <= tol for m in range(3)):
                return True
    return False


# ─── assets ──────────────────────────────────────────────────────────────────

def check_assets(directory):
    fails = []
    totals = {"dark": 0.0, "light": 0.0}
    files = sorted(glob.glob(os.path.join(directory, "*.svg")))
    if not files:
        return ["no assets found; run the build first"]

    for path in files:
        name = os.path.basename(path)
        theme_name = "dark" if name.endswith("-dark.svg") else "light"
        theme = THEMES[theme_name]
        with open(path, encoding="utf-8") as f:
            svg = f.read()

        try:
            ET.fromstring(svg)
        except ET.ParseError as e:
            fails.append(f"{name}: malformed, {e}")
            continue

        kb = len(svg.encode()) / 1024
        totals[theme_name] += kb
        if kb > BUDGET_KB:
            fails.append(f"{name}: {kb:.1f} KB over the {BUDGET_KB} KB budget")
        for bad in BANNED:
            if bad in svg:
                fails.append(f"{name}: contains banned construct {bad!r}")
        if "<title>" not in svg or 'role="img"' not in svg:
            fails.append(f"{name}: missing accessible title or role")

        palette = token_colors(theme)
        stray = sorted({c.lower() for c in HEX.findall(svg)} - palette
                       - {"#fff", "#ffffff"})
        off = [c for c in stray if not is_blend(c, palette)]
        if off:
            fails.append(f"{name}: {len(off)} off-palette colours "
                         f"{off[:6]}{' …' if len(off) > 6 else ''}")
        print(f"  ok  {name:26s} {kb:6.1f} KB"
              f"{f'  ({len(stray)} blended)' if stray else ''}")

    for theme_name, kb in totals.items():
        flag = "ok " if kb <= TOTAL_KB else "OVER"
        print(f"  {flag} {theme_name} theme total{'':<9}{kb:6.1f} KB / {TOTAL_KB} KB")
        if kb > TOTAL_KB:
            fails.append(f"{theme_name} totals {kb:.1f} KB, over {TOTAL_KB} KB")
    return fails


def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets")
    print("config");   f1 = check_config(os.path.join(ROOT, "profile.config.json"))
    print("contrast"); f2 = check_contrast()
    print("assets");   f3 = check_assets(directory)
    fails = f1 + f2 + f3
    if fails:
        print(f"\nFAILED, {len(fails)} problem(s)")
        for f in fails:
            print(f"  · {f}")
        sys.exit(1)
    print("\nall checks passed")


if __name__ == "__main__":
    main()
