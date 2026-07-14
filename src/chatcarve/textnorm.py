"""Unicode normalization helpers for WhatsApp export text.

WhatsApp exports are littered with invisible characters that break naive
parsers the moment a chat leaves en-US:

- U+200E LEFT-TO-RIGHT MARK precedes system/media lines in iOS exports and
  is the most reliable structural signal that a line is not a normal text
  message.
- U+200F RIGHT-TO-LEFT MARK appears throughout Arabic and Hebrew exports,
  including *inside* timestamps.
- U+202F NARROW NO-BREAK SPACE separates the time from the meridiem token
  in exports produced by recent iOS versions (``11:59:42 PM``).
- U+00A0 NO-BREAK SPACE shows up in French and Spanish meridiem spellings
  (``p. m.``).

These helpers strip or normalize those characters for matching while the
parser records where the marks were, so no information is silently lost.
"""

from __future__ import annotations

LRM = "\u200e"
RLM = "\u200f"
BOM = "\ufeff"
NBSP = "\u00a0"
NNBSP = "\u202f"
ZWSP = "\u200b"
ZWJ = "\u200d"

#: Invisible characters that carry no meaning for parsing.
_DIRECTION_MARKS = (LRM, RLM, BOM, ZWSP, ZWJ)

#: Space look-alikes normalized to a plain ASCII space for matching.
_SPACE_LOOKALIKES = (NBSP, NNBSP)

#: Arabic-Indic (U+0660..U+0669) and Extended Arabic-Indic (U+06F0..U+06F9)
#: digits map to ASCII so timestamps written with them parse like any other.
_DIGIT_TABLE = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩"
    "۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)


def strip_marks(text: str) -> str:
    """Remove direction marks and other zero-width characters."""
    for mark in _DIRECTION_MARKS:
        if mark in text:
            text = text.replace(mark, "")
    return text


def normalize_spaces(text: str) -> str:
    """Replace no-break space variants with a plain ASCII space."""
    for space in _SPACE_LOOKALIKES:
        if space in text:
            text = text.replace(space, " ")
    return text


def normalize_digits(text: str) -> str:
    """Translate Arabic-Indic digit forms to ASCII digits."""
    return text.translate(_DIGIT_TABLE)


def clean_for_matching(text: str) -> str:
    """Full normalization pipeline used before any pattern matching."""
    return normalize_spaces(normalize_digits(strip_marks(text)))
