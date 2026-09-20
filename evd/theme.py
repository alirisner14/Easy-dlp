"""Visual language: colours, type scale and metrics for the glass theme."""
from __future__ import annotations

# ---------------------------------------------------------------- palette ---
BASE = "#070910"

TEXT = "#EEF2FF"
TEXT_DIM = "#9AA6C4"
TEXT_MUTE = "#6A7593"
TEXT_ON_ACCENT = "#0A0714"

ACCENT_A = (124, 92, 255)      # violet
ACCENT_B = (35, 211, 232)      # cyan
ACCENT_HEX = "#8E7BFF"
ACCENT_B_HEX = "#3FD8EA"

OK = (61, 220, 151)
OK_HEX = "#3DDC97"
WARN = (255, 186, 73)
WARN_HEX = "#FFBA49"
ERR = (255, 99, 122)
ERR_HEX = "#FF637A"
IDLE_HEX = "#7E8AA8"

# Translucent surfaces (RGBA) -- these composite over whatever is beneath.
GLASS_TINT = (255, 255, 255, 16)      # panel frost
WELL = (4, 6, 14, 128)                # recessed input background
WELL_RIM = (255, 255, 255, 30)
CARD = (255, 255, 255, 10)            # queue row
CARD_HOVER = (255, 255, 255, 20)
GHOST = (255, 255, 255, 14)
GHOST_HOVER = (255, 255, 255, 30)
RIM = (255, 255, 255, 46)
TROUGH = (255, 255, 255, 22)

# ------------------------------------------------------------------ type ---
UI_STACK = ("Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica", "TkDefaultFont")
DISPLAY_STACK = ("Segoe UI Variable Display", "Segoe UI Semibold", "Segoe UI", "TkDefaultFont")
MONO_STACK = ("Cascadia Mono", "Consolas", "Courier New", "TkFixedFont")

FONTS: dict[str, tuple] = {}


def resolve(root) -> None:
    """Pick the best available family for each role. Call once, after Tk starts."""
    from tkinter import font as tkfont

    have = {f.lower() for f in tkfont.families(root)}

    def pick(stack):
        for name in stack:
            if name.lower() in have:
                return name
        return stack[-1]

    ui, display, mono = pick(UI_STACK), pick(DISPLAY_STACK), pick(MONO_STACK)
    FONTS.update(
        title=(display, 19, "bold"),
        subtitle=(ui, 10),
        section=(ui, 9, "bold"),
        body=(ui, 10),
        body_bold=(ui, 10, "bold"),
        small=(ui, 9),
        tiny=(ui, 8),
        row_title=(ui, 11, "bold"),
        button=(ui, 10, "bold"),
        stat=(display, 15, "bold"),
        mono=(mono, 9),
    )


def f(role: str) -> tuple:
    return FONTS.get(role, ("Segoe UI", 10))


# --------------------------------------------------------------- metrics ---
PAD = 18          # window margin
GAP = 12          # between cards
CARD_R = 18       # panel corner radius
CTRL_R = 10       # control corner radius
ROW_H = 74        # queue row height
CTRL_H = 34       # standard control height
LEFT_W = 430      # options column width
