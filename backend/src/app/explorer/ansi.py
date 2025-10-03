RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"

BLUE_BRIGHT = "\x1b[94m"
CYAN_BRIGHT = "\x1b[96m"
GRAY = "\x1b[90m"
GREEN = "\x1b[32m"
RED = "\x1b[31m"

# Foreground helpers
FG_DEFAULT = "\x1b[39m"
FG_WHITE_BRIGHT = "\x1b[97m"
FG_BLACK = "\x1b[30m"

# Soft 256-color backgrounds (work in light/dark terminals)
# Subtle gray variants (both dark-ish, so pair with light fg for readability)
BG_SOFT_1 = "\x1b[48;5;236m"  # dark gray
BG_SOFT_2 = "\x1b[48;5;238m"  # slightly lighter gray

def bg_soft_1(s: str) -> str:
    return f"{BG_SOFT_1}{FG_WHITE_BRIGHT}{s}{RESET}"

def bg_soft_2(s: str) -> str:
    return f"{BG_SOFT_2}{FG_WHITE_BRIGHT}{s}{RESET}"

def _term_columns() -> int:
    try:
        import shutil
        return max(40, shutil.get_terminal_size(fallback=(80, 20)).columns)
    except Exception:
        return 80

def block_bg(text: str, alt: bool = False) -> str:
    """Apply a soft background to each line, padded to full width.

    - Uses alternating subtle gray backgrounds per section (alt toggle).
    - Forces a high-contrast light foreground for readability in bright rooms.
    """
    bg = BG_SOFT_2 if alt else BG_SOFT_1
    fg = FG_WHITE_BRIGHT
    width = _term_columns()
    out_lines = []
    for raw in text.splitlines():
        line = raw.expandtabs()
        # Only pad if shorter than terminal width; never truncate
        pad = width - len(line)
        pad = pad if pad > 0 else 0
        out_lines.append(f"{bg}{fg}{line}{' ' * pad}{RESET}")
    return "\n".join(out_lines)

def bold(s: str) -> str:
    return f"{BOLD}{s}{RESET}"

def blue_bright(s: str) -> str:
    return f"{BLUE_BRIGHT}{s}{RESET}"

def cyan_bright(s: str) -> str:
    return f"{CYAN_BRIGHT}{s}{RESET}"

def gray(s: str) -> str:
    return f"{GRAY}{s}{RESET}"
