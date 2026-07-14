"""The parsing pipeline: detect, infer, classify.

Parsing is two-pass by design. Pass one (:mod:`chatcarve.linesplit`) finds
message headers and collects every raw timestamp *without* interpreting
dates. Between the passes the date order for the whole file is inferred
from evidence (:func:`chatcarve.timestamp.infer_date_order`) — a per-line
guess would happily read ``03/04/24`` and ``04/03/24`` as different months
in the same chat. Pass two resolves timestamps, splits authors, and
classifies each message as text, media, system, or deleted.

Classification rules (documented because they encode format knowledge):

- **Android system lines have no author** — the ``Author: `` part is
  simply absent. Any authorless block is a system message; the catalog
  only refines its event name.
- **iOS marks system and media lines with U+200E**. iOS attributes some
  system messages to a sender (the e2e notice carries the chat partner's
  name), so an authored iOS line with the mark is checked against the
  system catalog before being accepted as text. Authored lines *without*
  the mark are never system-classified: a human typing "I added sugar"
  must not become a ``member_added`` event.
- **Deleted-message tombstones are authored** and matched exactly against
  the deleted catalog, in any supported language.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .linesplit import Block, split_blocks
from .media import match_media
from .model import Message, SystemEvent
from .system import classify, is_deleted_tombstone
from .textnorm import strip_marks
from .timestamp import ORDERS, infer_date_order, resolve


@dataclass(frozen=True)
class Detection:
    """What chatcarve worked out about an export's dialect."""

    platform: str  # "ios" | "android" | "unknown"
    date_order: str  # "dmy" | "mdy" | "ymd"
    order_evidence: str  # see timestamp.infer_date_order
    twelve_hour: bool  # any meridiem token seen
    has_seconds: bool  # iOS exports carry seconds, Android does not
    message_count: int

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "date_order": self.date_order,
            "order_evidence": self.order_evidence,
            "twelve_hour": self.twelve_hour,
            "has_seconds": self.has_seconds,
            "message_count": self.message_count,
        }


@dataclass(frozen=True)
class ParseResult:
    """Messages plus everything a caller needs to trust them."""

    messages: List[Message]
    detection: Detection
    preamble: List[str]  # lines before the first header, kept verbatim

    @property
    def unresolved_timestamps(self) -> int:
        """Messages whose date was invalid under the chosen order."""
        return sum(1 for m in self.messages if m.timestamp is None)


def _split_author(rest: str) -> Tuple[Optional[str], str]:
    """Split ``"Alice: hi"`` into ``("Alice", "hi")``.

    The separator is the *first* ``": "`` — WhatsApp forbids colons in
    contact-name display but pasted numbers like ``+1 555 0100`` are safe
    either way because they contain no colon. A line without the separator
    has no author (Android system message).
    """
    pos = rest.find(": ")
    if pos <= 0:
        # Also handle an author with an empty body: "Alice:" at end of line.
        if rest.endswith(":") and len(rest) > 1 and ": " not in rest:
            return strip_marks(rest[:-1]).strip() or None, ""
        return None, rest
    author = strip_marks(rest[:pos]).strip()
    return (author or None), rest[pos + 2 :]


def _clean_text(lines: List[str]) -> str:
    """Join body lines, dropping direction marks but nothing visible."""
    return "\n".join(strip_marks(line).rstrip() for line in lines).strip("\n")


def _classify_block(block: Block, index: int, order: str) -> Message:
    timestamp = resolve(block.raw, order)
    author, first_line = _split_author(block.rest)
    body_lines = [first_line, *block.continuation]
    text = _clean_text(body_lines)
    common = {
        "index": index,
        "timestamp": timestamp,
        "raw_timestamp": block.raw_timestamp,
        "line": block.line,
    }

    # Authorless block: structurally a system message (Android shape, and
    # iOS lines like call notices that carry no sender).
    if author is None:
        event = classify(text) or SystemEvent(event="unknown")
        return Message(author=None, kind="system", text=text, system=event, **common)

    # Media placeholders are single-line bodies; captions arrive as
    # separate messages, so continuation lines rule media out.
    if not block.continuation:
        media = match_media(first_line)
        if media is not None:
            return Message(author=author, kind="media", text=text, media=media, **common)

    if is_deleted_tombstone(text):
        return Message(author=author, kind="deleted", text=text, **common)

    # iOS attributes some system messages to a sender but flags them with
    # U+200E; only then is an authored line eligible for the catalog.
    if block.lrm:
        event = classify(text)
        if event is not None:
            return Message(author=None, kind="system", text=text, system=event, **common)

    return Message(author=author, kind="text", text=text, **common)


def _detect_platform(blocks: List[Block]) -> str:
    if not blocks:
        return "unknown"
    ios = sum(1 for b in blocks if b.platform == "ios")
    return "ios" if ios * 2 >= len(blocks) else "android"


def _build_detection(blocks: List[Block], order: str, evidence: str) -> Detection:
    return Detection(
        platform=_detect_platform(blocks),
        date_order=order,
        order_evidence=evidence,
        twelve_hour=any(b.raw.meridiem is not None for b in blocks),
        has_seconds=any(b.raw.has_seconds for b in blocks),
        message_count=len(blocks),
    )


def parse_chat(text: str, order: Optional[str] = None) -> ParseResult:
    """Parse a full WhatsApp export.

    *order* forces a date order (``"dmy"``, ``"mdy"``, ``"ymd"``); when
    None it is inferred from the file. Forcing is the escape hatch for the
    genuinely ambiguous short chat where every day-of-month is <= 12.
    """
    if order is not None and order not in ORDERS:
        raise ValueError(f"order must be one of {ORDERS}, got {order!r}")

    split = split_blocks(text)
    if order is None:
        order, evidence = infer_date_order(b.raw for b in split.blocks)
    else:
        evidence = "forced"

    messages = [
        _classify_block(block, index, order)
        for index, block in enumerate(split.blocks)
    ]
    detection = _build_detection(split.blocks, order, evidence)
    return ParseResult(messages=messages, detection=detection, preamble=split.preamble)


def detect_format(text: str, order: Optional[str] = None) -> Detection:
    """Detect an export's dialect without materializing messages."""
    if order is not None and order not in ORDERS:
        raise ValueError(f"order must be one of {ORDERS}, got {order!r}")
    split = split_blocks(text)
    if order is None:
        order, evidence = infer_date_order(b.raw for b in split.blocks)
    else:
        evidence = "forced"
    return _build_detection(split.blocks, order, evidence)
