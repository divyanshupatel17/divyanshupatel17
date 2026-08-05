#!/usr/bin/env python3
"""
Build orchestrator.

    python -m generator.build --fetch          refresh data, then render
    python -m generator.build --fetch --photo  also re-dither the portrait
    python -m generator.build                  render from cached data.json

Renders every panel in both themes into assets/, then regenerates README.md
from README.template.md so the config file stays the only thing a human edits.

The portrait step is separate because it is the one part that needs Pillow and
a download. Its output is cached to assets/portrait.json, so a normal build
stays stdlib-only and offline.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator.core import github                          # noqa: E402
from generator.core.tokens import THEMES, WIDGET           # noqa: E402
from generator.panels import (hero, mascot, production, pulse,  # noqa: E402
                              skyline)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "profile.config.json")
DATA = os.path.join(ROOT, "generator", "data.json")
PORTRAIT = os.path.join(ROOT, "assets", "portrait.json")
AVATAR = os.path.join(ROOT, "assets", "avatar.png")
ASSETS = os.path.join(ROOT, "assets")
TEMPLATE = os.path.join(ROOT, "README.template.md")
README = os.path.join(ROOT, "README.md")

PANELS = {"hero": hero, "production": production, "pulse": pulse,
          "skyline": skyline, "mascot": mascot}


def tidy(svg):
    """Collapse generator whitespace. Keeps assets small and diffs readable."""
    return re.sub(r"\s{2,}", " ", re.sub(r">\s+<", "><", svg)).strip()


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            if f.read() == content:
                return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


# ─── readme ──────────────────────────────────────────────────────────────────

def _badge(name, slug, theme):
    w = WIDGET[theme]
    lbl = name.replace(" ", "%20").replace("-", "--").replace("+", "%2B")
    return (f"https://img.shields.io/badge/{lbl}-{w['bg']}"
            f"?style=flat-square&logo={slug}&logoColor={w['accent']}"
            f"&labelColor={w['bg']}&color={w['line']}")


def shields(cfg):
    """The badge wall, themed and theme-aware.

    shields.io has no notion of the reader's colour scheme, so each badge is
    wrapped in a <picture> with a dark and a light source. Verbose to read and
    trivial to generate, which is the correct trade when a machine writes it:
    a third-party service ends up rendering inside our palette in both themes
    instead of punching a hole in it.
    """
    out = []
    for grp in cfg["stack"]["shields"]:
        row = [f"<sub><b>{grp['group'].upper()}</b></sub><br>"]
        for name, slug in grp["items"]:
            row.append(
                f'<picture>'
                f'<source media="(prefers-color-scheme: dark)" '
                f'srcset="{_badge(name, slug, "dark")}">'
                f'<img alt="{name}" src="{_badge(name, slug, "light")}">'
                f'</picture>')
        out.append("\n".join(row))
    return "\n\n".join(out)


def links_row(cfg):
    li = cfg["links"]
    return (f'<a href="{li["portfolio"]}"><b>Portfolio</b></a>'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;'
            f'<a href="{li["linkedin"]}"><b>LinkedIn</b></a>'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;'
            f'<a href="mailto:{li["email"]}"><b>Email</b></a>')


def production_links(cfg):
    return "&nbsp;&nbsp;·&nbsp;&nbsp;".join(
        f'<a href="{p["url"]}"><b>{p["name"]}</b></a>'
        for p in cfg["production"])


def render_readme(data):
    if not os.path.exists(TEMPLATE):
        return False
    with open(TEMPLATE, encoding="utf-8") as f:
        md = f.read()
    cfg = data["config"]
    repl = {
        "{{LOGIN}}": cfg["identity"]["login"],
        "{{NAME}}": cfg["identity"]["name"],
        "{{ROLE}}": cfg["identity"]["role"],
        "{{STATEMENT}}": cfg["identity"]["statement"],
        "{{LINKS}}": links_row(cfg),
        "{{PRODUCTION_LINKS}}": production_links(cfg),
        "{{SHIELDS}}": shields(cfg),
        "{{ACCENT_DARK}}": WIDGET["dark"]["accent"],
        "{{ACCENT_LIGHT}}": WIDGET["light"]["accent"],
        "{{BG_DARK}}": WIDGET["dark"]["bg"],
        "{{BG_LIGHT}}": WIDGET["light"]["bg"],
        "{{TEXT_DARK}}": WIDGET["dark"]["text"],
        "{{TEXT_LIGHT}}": WIDGET["light"]["text"],
        "{{MUTED_DARK}}": WIDGET["dark"]["muted"],
        "{{MUTED_LIGHT}}": WIDGET["light"]["muted"],
        "{{EMBER_DARK}}": WIDGET["dark"]["ember"],
        "{{EMBER_LIGHT}}": WIDGET["light"]["ember"],
        "{{MASCOT}}": cfg["mascot"]["name"],
        "{{GENERATED}}": data["generated_at"][:10],
    }
    for k, v in repl.items():
        md = md.replace(k, v)
    return write(README, md)


# ─── main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true",
                    help="refresh data.json from GitHub and probe production")
    ap.add_argument("--photo", action="store_true",
                    help="re-dither the portrait (needs Pillow)")
    ap.add_argument("--out", default=ASSETS)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()

    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)

    if args.photo or not os.path.exists(PORTRAIT):
        from generator.core import portrait
        try:
            portrait.build(cfg, PORTRAIT, cache_png=AVATAR)
        except ImportError:
            sys.exit("portrait needs Pillow: pip install -r requirements.txt")

    if args.fetch:
        data = github.build(CONFIG, DATA)
    else:
        if not os.path.exists(DATA):
            sys.exit("no generator/data.json — run once with --fetch")
        with open(DATA, encoding="utf-8") as f:
            data = json.load(f)
        data["config"] = cfg          # copy edits never need a re-fetch

    with open(PORTRAIT, encoding="utf-8") as f:
        data["portrait"] = json.load(f)

    changed, total = 0, 0
    for name in (args.only or list(PANELS)):
        for theme_name, theme in THEMES.items():
            svg = tidy(PANELS[name].render(data, theme))
            path = os.path.join(args.out, f"{name}-{theme_name}.svg")
            hit = write(path, svg)
            changed += hit
            total += 1
            print(f"  {'~' if hit else ' '} {name}-{theme_name}.svg"
                  f"{'':<{max(1, 18 - len(name) - len(theme_name))}}"
                  f"{len(svg.encode()) / 1024:6.1f} KB")

    if os.path.abspath(args.out) == os.path.abspath(ASSETS):
        total += 1
        if render_readme(data):
            changed += 1
            print("  ~ README.md")

    print(f"\n{changed} of {total} outputs changed · "
          f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
