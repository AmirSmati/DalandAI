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
import sys
import shutil
import time

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


if __name__ == "__main__":
    print_banner(version="0.1.0", status="Ready")
    # print_mascot()  # <- call this alone for a lightweight loading screen
