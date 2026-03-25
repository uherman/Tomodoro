from typing import List, Tuple, Set

# Color type constants used by the renderer
C_BODY = "body"
C_STEM = "stem"
C_LABEL = "label"

# Braille blank character
_B = "⠀"

# ---------------------------------------------------------------------------
# Braille tomato art with per-character color
#
# Each entry: (text, color_mask)
# color_mask: same length as text, one char per character:
#   'S' = stem/leaf (green)
#   'R' = body/fruit (red)
#   ' ' = blank (invisible)
#
# Lines 0-3: stem and leaves (green)
# Line 4: transition — center is calyx (green), edges are fruit (red)
# Lines 5-14: fruit body (red)
# ---------------------------------------------------------------------------

_TOMATO_TEXT: List[str] = [
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",  # 0  stem tip
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",  # 1  stem
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠛⠻⣶⡆⠀⠿⠀⣶⠒⠊⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",  # 2  leaves
    "⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣴⠾⠛⢹⣶⡤⢶⣿⡟⠶⠦⠄⠀⠀⠀⠀⠀⠀⠀⠀",  # 3  calyx
    "⠀⠀⠀⠀⠀⣠⣶⣤⣤⣤⣤⣴⠂⠸⠋⢀⣄⡉⠓⠀⠲⣶⣾⣿⣷⣄⠀⠀⠀⠀",  # 4  transition
    "⠀⠀⠀⢀⣾⡿⠋⠁⣠⣤⣿⡟⢀⣠⣾⣿⣿⣿⣷⣶⣤⣼⣿⣿⣿⣿⣆⠀⠀⠀",  # 5  body
    "⠀⠀⠀⣾⡟⠀⣰⣿⣿⣿⣿⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀",  # 6
    "⠀⠀⢸⡿⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀",  # 7
    "⠀⠀⢸⡇⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀",  # 8
    "⠀⠀⢸⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀",  # 9
    "⠀⠀⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⠀⠀",  # 10
    "⠀⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⠀⠀",  # 11
    "⠀⠀⠀⠀⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀",  # 12
    "⠀⠀⠀⠀⠀⠀⠉⠛⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⠋⠀⠀⠀⠀⠀⠀⠀",  # 13
    "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠉⠉⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",  # 14
]

# Lines 0-2: stem and leaves (green)
# Line 3: calyx — center (pos 13-17) green, outer edges red
# Line 4: transition — only pos 14-16 green (tiny calyx base)
# Lines 5-14: fruit body (red)
_GREEN_MAP = {
    0: None,        # stem tip
    1: None,        # stem
    2: None,        # leaves
    3: None,        # calyx
    4: set(range(12, 19)),  # calyx base (center green, edges red)
}


def _build_color_mask(line_idx: int, text: str) -> str:
    """Generate a per-character color mask for a line."""
    green_range = _GREEN_MAP.get(line_idx)
    mask = []
    for j, ch in enumerate(text):
        if ch == _B:
            mask.append(" ")
        elif line_idx in _GREEN_MAP:
            if green_range is None or j in green_range:
                mask.append("S")
            else:
                mask.append("R")
        else:
            mask.append("R")
    return "".join(mask)


# Build the full art data with generated color masks
TOMATO_ART: List[Tuple[str, str]] = [
    (text, _build_color_mask(i, text))
    for i, text in enumerate(_TOMATO_TEXT)
]

TOTAL_LINES = len(TOMATO_ART)
LINE_WIDTH = len(TOMATO_ART[0][0])

# Precompute the reveal order: list of (line_index, char_index) for
# non-blank characters only, ordered bottom-up then left-to-right.
_REVEAL_ORDER: List[Tuple[int, int]] = []
for _line_idx in range(TOTAL_LINES - 1, -1, -1):
    _text = TOMATO_ART[_line_idx][0]
    for _char_idx, _ch in enumerate(_text):
        if _ch != _B:
            _REVEAL_ORDER.append((_line_idx, _char_idx))

TOTAL_VISIBLE_CHARS = len(_REVEAL_ORDER)


def get_tomato_progress(progress: float) -> List[Tuple[str, str]]:
    """Return tomato art filled bottom-up, left-to-right per line.

    Only non-blank characters count toward progress.
    Returns list of (text, color_mask) tuples — the renderer draws
    character-by-character using the color_mask.
    """
    count = int(progress * TOTAL_VISIBLE_CHARS)
    count = max(0, min(TOTAL_VISIBLE_CHARS, count))

    revealed: Set[Tuple[int, int]] = set(_REVEAL_ORDER[:count])

    lines: List[Tuple[str, str]] = []
    for i, (text, colors) in enumerate(TOMATO_ART):
        chars = list(text)
        for j, ch in enumerate(chars):
            if ch != _B and (i, j) not in revealed:
                chars[j] = _B
        lines.append(("".join(chars), colors))

    return lines
