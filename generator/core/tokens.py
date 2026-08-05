"""
Design tokens — the single source of truth for the whole profile.

Identity: PHOSPHOR. A warm amber terminal, the colour of an early CRT, on
near-black. Chosen because every other developer profile on the platform is
cyan-on-navy or green-on-black; amber is instantly recognisable and almost
nobody uses it. Warm accents also survive GitHub's image proxy better than
saturated cyan, which fringes when downscaled.

Nothing outside this file names a colour, a size or a duration.
"""

# ─── primitives ──────────────────────────────────────────────────────────────

_INK = {
    "000": "#08080A", "050": "#0C0C0F", "100": "#111116", "150": "#16161C",
    "200": "#1E1E26", "300": "#2A2A34", "400": "#61616E", "500": "#8A8A97",
    "600": "#9C9CA8", "800": "#DEDEE4", "900": "#F5F5F7",
}
_PAPER = {
    "000": "#FFFCF7", "050": "#FDF9F2", "100": "#F6F1E7", "150": "#F1EBDF",
    "200": "#E5DCCB", "300": "#D3C8B2", "400": "#8A8272", "500": "#6E6656",
    "600": "#5C5546", "800": "#2B261D", "900": "#14110C",
}

# amber phosphor, and the ember it decays to
AMBER = {"dark": "#FFA94D", "light": "#B45309"}
EMBER = {"dark": "#FF7A5C", "light": "#C2410C"}
LIVE = {"dark": "#4ADE80", "light": "#15803D"}


# ─── semantic themes ─────────────────────────────────────────────────────────

DARK = {
    "name": "dark",
    "bg": _INK["000"],
    "panel": _INK["050"],
    "panel_alt": _INK["100"],
    "raise": _INK["150"],
    "line": _INK["200"],
    "line_soft": _INK["150"],
    "line_strong": _INK["300"],
    "text": _INK["900"],
    "text_soft": _INK["800"],
    "muted": _INK["600"],
    "dim": _INK["400"],
    "accent": AMBER["dark"],
    "accent_soft": "#FFC98A",
    "accent_deep": "#C2701F",
    # manifest keys: light needs the deeper amber to hold 4.5:1 as body text,
    # dark needs the paler one. One token so panels never branch on theme.
    "spec_key": "#FFC98A",
    "ember": EMBER["dark"],
    "live": LIVE["dark"],
    # phosphor decay ramp: what a dot looks like as it cools
    "glow": ["#FFD9A8", "#FFA94D", "#F0803C", "#C2701F", "#7A4A18"],
    "veil": "rgba(255,169,77,0.06)",
}

LIGHT = {
    "name": "light",
    "bg": _PAPER["000"],
    "panel": _PAPER["050"],
    "panel_alt": _PAPER["100"],
    "raise": _PAPER["150"],
    "line": _PAPER["200"],
    "line_soft": _PAPER["150"],
    "line_strong": _PAPER["300"],
    "text": _PAPER["900"],
    "text_soft": _PAPER["800"],
    "muted": _PAPER["600"],
    "dim": _PAPER["400"],
    "accent": AMBER["light"],
    "accent_soft": "#D97706",
    "accent_deep": "#7C2D12",
    "spec_key": AMBER["light"],
    "ember": EMBER["light"],
    "live": LIVE["light"],
    "glow": ["#7C2D12", "#B45309", "#C2410C", "#D97706", "#E9A23B"],
    "veil": "rgba(180,83,9,0.05)",
}

THEMES = {"dark": DARK, "light": LIGHT}

# Hex values these themes hand to third-party widgets (shields, trophies,
# the snake, the skyline) so nothing on the page is off-system. Kept here so
# there is exactly one place to change when the accent changes.
WIDGET = {
    "dark": {"bg": "08080A", "accent": "FFA94D", "ember": "FF7A5C",
             "text": "F5F5F7", "muted": "9C9CA8", "line": "1E1E26"},
    "light": {"bg": "FFFCF7", "accent": "B45309", "ember": "C2410C",
              "text": "14110C", "muted": "5C5546", "line": "E5DCCB"},
}


# ─── type ────────────────────────────────────────────────────────────────────
# A terminal is a monospace object. Mono carries the whole page; the sans
# stack appears only where a number needs to be large enough to read as a
# headline. Both stacks resolve inside GitHub's image proxy without webfonts.

MONO = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'DejaVu Sans Mono','Liberation Mono',monospace")
SANS = ("system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',"
        "Arial,sans-serif")

TYPE = {
    #            size  weight  tracking  family
    "display":  (40,   700,    -1.2,     MONO),
    "h1":       (26,   700,    -0.4,     MONO),
    "h2":       (17,   600,    -0.2,     MONO),
    "h3":       (14,   600,     0.0,     MONO),
    "lead":     (13,   400,     0.1,     MONO),
    "body":     (12.5, 400,     0.1,     MONO),
    "small":    (11.5, 400,     0.1,     MONO),
    "label":    (10.5, 600,     1.9,     MONO),   # uppercase eyebrows
    "num_xl":   (34,   700,    -1.0,     SANS),
    "num":      (20,   700,    -0.3,     SANS),
    "code":     (11,   400,     0.2,     MONO),
}

# Mono advance width as a fraction of font size. Used to place dotted leaders
# and right-aligned values without measuring text at runtime.
ADVANCE = 0.6


# ─── space ───────────────────────────────────────────────────────────────────

SPACE = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32, "2xl": 48, "3xl": 64}
RADIUS = {"card": 10, "panel": 14, "chip": 6, "pill": 999}
STROKE = {"hair": 1, "rule": 1.5, "bar": 8}

CANVAS_W = 1200
GUTTER = 28


# ─── motion ──────────────────────────────────────────────────────────────────
# Motion resolves. Everything settles within ~3s and stops, except the three
# marks that encode state rather than decoration: the live pulse, the terminal
# caret, and the mascot's wingbeat.

MOTION = {
    "enter": 0.5,
    "stagger": 0.05,
    "draw": 0.9,
    "sweep": 1.1,
    "pulse": 2.4,
    "caret": 1.1,
    "type": 0.045,          # per character
    "ease": "0.22 0.61 0.36 1",
    "ease_soft": "0.4 0 0.2 1",
}
