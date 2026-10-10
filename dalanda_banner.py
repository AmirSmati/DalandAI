"""
Dalanda AI — CLI Banner
------------------------
Zero-dependency, cross-platform colorful splash screen for your agent's CLI.
Drop this file into your project (e.g. `banner.py`) and call `print_banner()`
from your entry point before the main loop starts.

Usage:
    from banner import print_banner
    print_banner(version="0.1.0", status="Ready")
"""

import os
import re
import sys
import shutil
import time
import textwrap
import unicodedata

# --- Enable ANSI colors on Windows terminals -------------------------------
if sys.platform == "win32":
    os.system("")  # harmless no-op that flips Windows into ANSI-aware mode

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

# A smooth purple -> pink -> orange -> gold gradient (feel free to restyle)
GRADIENT = [
    (124, 77, 255),
    (149, 92, 245),
    (186, 85, 230),
    (224, 84, 210),
    (240, 98, 168),
    (247, 122, 122),
    (250, 158, 90),
]

# "ANSI Shadow" style block font for D A L N
LOGO = {
    "D": [
        "██████╗ ",
        "██╔══██╗",
        "██║  ██║",
        "██║  ██║",
        "██████╔╝",
        "╚═════╝ ",
    ],
    "A": [
        " █████╗ ",
        "██╔══██╗",
        "███████║",
        "██╔══██║",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
    "L": [
        "██╗     ",
        "██║     ",
        "██║     ",
        "██║     ",
        "███████╗",
        "╚══════╝",
    ],
    "N": [
        "███╗   ██╗",
        "████╗  ██║",
        "██╔██╗ ██║",
        "██║╚██╗██║",
        "██║ ╚████║",
        "╚═╝  ╚═══╝",
    ],
}


def _build_word(word: str, spacing: int = 1) -> list[str]:
    """Stitch letter glyphs into one multi-line word."""
    rows = ["" for _ in range(6)]
    gap = " " * spacing
    for i, ch in enumerate(word):
        glyph = LOGO[ch]
        for r in range(6):
            rows[r] += glyph[r] + (gap if i < len(word) - 1 else "")
    return rows


def _gradient_line(text: str, line_index: int, total_lines: int) -> str:
    """Color a single logo line with a left-to-right slice of the gradient."""
    steps = len(GRADIENT)
    # blend two gradient stops based on vertical position for a subtle diagonal feel
    pos = line_index / max(total_lines - 1, 1)
    idx_f = pos * (steps - 1)
    i0, i1 = int(idx_f), min(int(idx_f) + 1, steps - 1)
    t = idx_f - i0
    r = int(GRADIENT[i0][0] + (GRADIENT[i1][0] - GRADIENT[i0][0]) * t)
    g = int(GRADIENT[i0][1] + (GRADIENT[i1][1] - GRADIENT[i0][1]) * t)
    b = int(GRADIENT[i0][2] + (GRADIENT[i1][2] - GRADIENT[i0][2]) * t)
    return f"{rgb(r, g, b)}{BOLD}{text}{RESET}"


# --- Abstract mascot: a minimal "sensor orb" avatar ------------------------
# No face, no human likeness — just a glowing node with a single "eye"/lens,
# evoking a small AI presence. Works as a standalone avatar or above the logo.
MASCOT = [
    "    .:▓▓▓▓▓:.    ",
    "  .▓▓▓▓▓▓▓▓▓▓▓.  ",
    " ▓▓▓▓▓▓●▓▓▓▓▓▓▓ ",
    " ▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ",
    "  '▓▓▓▓▓▓▓▓▓▓▓'  ",
    "    ':▓▓▓▓▓:'    ",
    "        ╲│╱      ",
    "         ▼       ",
]


def print_mascot(width: int | None = None):
    """Print just the mascot avatar, centered — e.g. for a loading screen."""
    width = width or shutil.get_terminal_size(fallback=(80, 24)).columns
    pad = max((width - len(MASCOT[0])) // 2, 0)
    print()
    for i, row in enumerate(MASCOT):
        print(" " * pad + _gradient_line(row, i, len(MASCOT)))
    print()


def print_banner(version: str = "0.1.0", status: str = "Online", tagline: str = "Autonomous Agent Framework", show_mascot: bool = True):
    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    logo_rows = _build_word("DALANDA")
    logo_width = len(logo_rows[0])
    pad = max((width - logo_width) // 2, 0)

    print()
    if show_mascot:
        mascot_pad = max((width - len(MASCOT[0])) // 2, 0)
        for i, row in enumerate(MASCOT):
            print(" " * mascot_pad + _gradient_line(row, i, len(MASCOT)))
        print()

    for i, row in enumerate(logo_rows):
        print(" " * pad + _gradient_line(row, i, len(logo_rows)))

    subtitle = f"{rgb(250, 158, 90)}{BOLD}A I{RESET}{DIM}  ·  {tagline}{RESET}"
    sub_pad = max((width - (len("A I") + 3 + len(tagline))) // 2, 0)
    print(" " * sub_pad + subtitle)
    print()

    # status bar
    box_text = f" v{version}  │  status: {status}  │  {time.strftime('%Y-%m-%d %H:%M')} "
    box_pad = max((width - len(box_text) - 2) // 2, 0)
    top = "╭" + "─" * (len(box_text)) + "╮"
    mid = f"│{box_text}│"
    bot = "╰" + "─" * (len(box_text)) + "╯"
    color = rgb(149, 92, 245)
    print(" " * box_pad + f"{color}{top}{RESET}")
    print(" " * box_pad + f"{color}│{RESET}{DIM}{box_text}{RESET}{color}│{RESET}")
    print(" " * box_pad + f"{color}{bot}{RESET}")
    print()


# --- Description + feature list --------------------------------------------
DESCRIPTION = (
    "Dalanda AI is an autonomous agent that plans, reasons, and executes "
    "tasks on its own — from research and data lookups to multi-step "
    "workflows — while keeping you in the loop."
)

FEATURES = [
    ("🧠", "Reasoning engine", "Breaks down complex goals into ordered, executable steps"),
    ("🔌", "Tool use", "Calls external APIs, scripts, and services as needed"),
    ("💾", "Memory", "Recalls context and past actions across sessions"),
    ("🗣️", "Natural language", "Understands plain-English instructions, no rigid syntax"),
    ("🔁", "Self-correction", "Detects failed steps and retries or re-plans automatically"),
    ("🔒", "Sandboxed execution", "Runs actions safely, with permission checks before it acts"),
]


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _visible_len(text: str) -> int:
    """Length of a string as it appears on screen, ignoring ANSI color codes.
    Wide emoji (icons) render as ~2 terminal columns in most terminals, so we
    count each emoji as 2 to keep the right-hand border aligned."""
    stripped = _ANSI_RE.sub("", text)
    length = 0
    for ch in stripped:
        length += 2 if unicodedata.east_asian_width(ch) in ("W", "F") or ord(ch) > 0x1F300 else 1
    return length


def _draw_box(title: str, body_lines: list, color_rgb=(149, 92, 245), content_width: int = 58):
    """Draw a left-aligned bordered box, centered on the terminal."""
    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    color = rgb(*color_rgb)
    box_pad = max((width - content_width - 4) // 2, 0)
    indent = " " * box_pad

    print(indent + f"{color}╭─ {BOLD}{title}{RESET}{color} " + "─" * (content_width - len(title) - 1) + "╮" + RESET)
    print(indent + f"{color}│{RESET}" + " " * (content_width + 2) + f"{color}│{RESET}")
    for line in body_lines:
        padding = " " * max(content_width - _visible_len(line), 0)
        print(indent + f"{color}│{RESET}  {line}{padding}  {color}│{RESET}")
    print(indent + f"{color}│{RESET}" + " " * (content_width + 2) + f"{color}│{RESET}")
    print(indent + f"{color}╰" + "─" * (content_width + 2) + f"╯{RESET}")


def print_features(description: str = DESCRIPTION, features: list = FEATURES, content_width: int = 58):
    """Print the description paragraph and feature list in a bordered box."""
    body = []
    for wrapped in textwrap.wrap(description, width=content_width):
        body.append(f"{DIM}{wrapped}{RESET}")
    body.append("")

    for icon, name, desc in features:
        prefix = f"{icon} {BOLD}{name}{RESET}{DIM} — "
        prefix_len = _visible_len(f"{icon} {name} — ")
        wrapped_desc = textwrap.wrap(desc, width=max(content_width - prefix_len, 10))
        if not wrapped_desc:
            wrapped_desc = [""]
        body.append(f"{prefix}{wrapped_desc[0]}{RESET}")
        cont_indent = " " * prefix_len
        for extra in wrapped_desc[1:]:
            body.append(f"{cont_indent}{DIM}{extra}{RESET}")

    print()
    _draw_box("WHAT DALANDA AI CAN DO", body, content_width=content_width)
    print()


if __name__ == "__main__":
    print_banner(version="0.1.0", status="Ready")
    print_features()
    # print_mascot()  # <- call this alone for a lightweight loading screen