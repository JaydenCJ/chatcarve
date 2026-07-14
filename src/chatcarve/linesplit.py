"""Split a raw export into message blocks.

A WhatsApp export is a plain text file where each message *starts* with a
timestamp header but may continue over any number of following lines
(multi-line messages are common — poems, addresses, pasted text). This
module finds the headers and folds continuation lines into blocks; it does
not interpret bodies at all.

Two header shapes exist:

- **iOS**: ``[12/31/23, 11:59:42 PM] Alice: text`` — the timestamp sits in
  square brackets, and system/media lines carry a leading U+200E mark.
- **Android**: ``12/31/23, 11:59 PM - Alice: text`` — the timestamp is
  terminated by `` - `` (space, hyphen, space).

Both are detected by *validating* the candidate timestamp with
:func:`chatcarve.timestamp.parse_raw` rather than by one giant regex, so a
message line that merely resembles a header (``Scores - 3:2 tonight``)
cannot be misread.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .textnorm import BOM, LRM, RLM, strip_marks
from .timestamp import RawTimestamp, parse_raw

#: How far into a line an Android `` - `` separator may sit. The longest
#: legitimate timestamp observed is ~26 characters ("2023. 12. 31. 오후
#: 11:59:42"); 40 leaves margin without scanning entire message bodies.
_MAX_HEADER_LEN = 40


@dataclass
class Block:
    """One message block: a validated header plus its continuation lines."""

    raw_timestamp: str
    raw: RawTimestamp
    rest: str  # everything after the header on the first line
    line: int  # 1-based line number of the header
    platform: str  # "ios" | "android"
    lrm: bool  # line carried a U+200E mark (iOS system/media signal)
    continuation: List[str] = field(default_factory=list)


@dataclass
class SplitResult:
    """Blocks plus everything that could not be attributed to a message."""

    blocks: List[Block]
    preamble: List[str]  # lines before the first header (rare, kept verbatim)


def _match_ios(line: str) -> Optional[Tuple[str, RawTimestamp, str, bool]]:
    """Try the iOS bracketed-header shape against *line*."""
    stripped = line.lstrip(LRM + RLM + BOM)
    lrm = stripped != line
    if not stripped.startswith("["):
        return None
    end = stripped.find("]")
    if end <= 1 or end > _MAX_HEADER_LEN:
        return None
    candidate = stripped[1:end]
    raw = parse_raw(candidate)
    if raw is None:
        return None
    rest = stripped[end + 1 :]
    if rest.startswith(" "):
        rest = rest[1:]
    return candidate, raw, rest, lrm


def _match_android(line: str) -> Optional[Tuple[str, RawTimestamp, str, bool]]:
    """Try the Android `` - ``-separated header shape against *line*.

    Every `` - `` occurrence inside the length budget is tested because the
    date itself may contain hyphens (``2023-12-31, 23:59 - hi``), which
    rules out splitting on the first hyphen.
    """
    stripped = line.lstrip(LRM + RLM + BOM)
    lrm = stripped != line
    search_start = 0
    while True:
        pos = stripped.find(" - ", search_start, _MAX_HEADER_LEN)
        if pos == -1:
            return None
        candidate = stripped[:pos]
        raw = parse_raw(candidate)
        if raw is not None:
            return candidate, raw, stripped[pos + 3 :], lrm
        search_start = pos + 1


def match_header(line: str) -> Optional[Block]:
    """Return a :class:`Block` (without continuations) if *line* is a header."""
    ios = _match_ios(line)
    if ios is not None:
        candidate, raw, rest, lrm = ios
        return Block(
            raw_timestamp=strip_marks(candidate).strip(),
            raw=raw,
            rest=rest,
            line=0,
            platform="ios",
            lrm=lrm or rest.startswith(LRM),
        )
    android = _match_android(line)
    if android is not None:
        candidate, raw, rest, lrm = android
        return Block(
            raw_timestamp=strip_marks(candidate).strip(),
            raw=raw,
            rest=rest,
            line=0,
            platform="android",
            lrm=lrm or rest.startswith(LRM),
        )
    return None


def split_blocks(text: str) -> SplitResult:
    """Split export *text* into message blocks.

    Handles CRLF and lone-CR line endings, a UTF-8 BOM on the first line,
    and blank lines inside multi-line messages (they belong to the message,
    not between messages — WhatsApp never emits empty separator lines).
    """
    blocks: List[Block] = []
    preamble: List[str] = []
    current: Optional[Block] = None

    for lineno, line in enumerate(text.splitlines(), start=1):
        block = match_header(line)
        if block is not None:
            block.line = lineno
            blocks.append(block)
            current = block
        elif current is not None:
            current.continuation.append(line)
        else:
            preamble.append(line)

    # Trailing blank continuation lines are export artifacts, not content.
    for block in blocks:
        while block.continuation and not block.continuation[-1].strip():
            block.continuation.pop()

    while preamble and not preamble[-1].strip():
        preamble.pop()

    return SplitResult(blocks=blocks, preamble=preamble)
