"""Data model: the parsed message and its serializable form.

Every message in an export becomes exactly one :class:`Message`. The model
is deliberately flat and JSON-friendly: :meth:`Message.to_dict` is the
single source of truth for the JSONL schema documented in
``docs/output-format.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

#: The four message kinds chatcarve distinguishes.
KINDS = ("text", "media", "system", "deleted")


@dataclass(frozen=True)
class MediaRef:
    """A reference to an attachment.

    ``filename`` is None when the export was made without media ("media
    omitted"); ``media_type`` is chatcarve's best classification (image,
    video, audio, sticker, gif, document, contact) or None when unknown.
    """

    filename: Optional[str]
    media_type: Optional[str]
    omitted: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "media_type": self.media_type,
            "omitted": self.omitted,
        }


@dataclass(frozen=True)
class SystemEvent:
    """A classified system message.

    ``event`` is one of the canonical event names from
    :mod:`chatcarve.system` (``"unknown"`` when the line is structurally a
    system message but matches no catalog pattern — the original text is
    always preserved on the message itself).
    """

    event: str

    def to_dict(self) -> Dict[str, Any]:
        return {"event": self.event}


@dataclass(frozen=True)
class Message:
    """One parsed message.

    ``timestamp`` is naive local time exactly as written in the export
    (WhatsApp exports carry no timezone). ``raw_timestamp`` preserves the
    original spelling so nothing is lost to normalization. ``line`` is the
    1-based line number of the message header in the source file.
    """

    index: int
    timestamp: Optional[datetime]
    raw_timestamp: str
    author: Optional[str]
    kind: str
    text: str
    line: int
    media: Optional[MediaRef] = field(default=None)
    system: Optional[SystemEvent] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to the stable JSONL record shape (all keys present)."""
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "raw_timestamp": self.raw_timestamp,
            "author": self.author,
            "kind": self.kind,
            "text": self.text,
            "line": self.line,
            "media": self.media.to_dict() if self.media else None,
            "system": self.system.to_dict() if self.system else None,
        }
