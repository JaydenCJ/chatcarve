"""Markdown output: a readable archive document.

Messages are grouped under one ``###`` heading per calendar day. Media
references become real links — images as embeds, everything else as plain
links — pointing into ``--media-dir`` (default ``.``), so a Markdown
export dropped next to the exported attachment folder just works.
"""

from __future__ import annotations

import posixpath
from typing import IO, Iterable, List, Optional

from .model import Message

#: Characters that would change Markdown structure if left bare in chat text.
_ESCAPES = str.maketrans(
    {c: "\\" + c for c in ("\\", "`", "*", "_", "[", "]", "#", ">", "|")}
)


def escape(text: str) -> str:
    """Escape chat text for safe embedding in Markdown."""
    return text.translate(_ESCAPES)


def _time_label(message: Message) -> str:
    if message.timestamp is not None:
        return message.timestamp.strftime("%H:%M")
    return message.raw_timestamp


def _media_line(message: Message, media_dir: str) -> str:
    media = message.media
    assert media is not None
    if media.omitted or not media.filename:
        kind = media.media_type or "media"
        return f"_[{escape(kind)} omitted from export]_"
    href = posixpath.join(media_dir, media.filename) if media_dir else media.filename
    label = escape(media.filename)
    if media.media_type == "image":
        return f"![{label}]({href})"
    return f"[{label}]({href})"


def _message_lines(message: Message, media_dir: str) -> List[str]:
    time = _time_label(message)
    if message.kind == "system":
        return [f"- *{time} — {escape(message.text)}*"]
    author = escape(message.author or "?")
    if message.kind == "media":
        return [f"- **{time}** **{author}**: {_media_line(message, media_dir)}"]
    if message.kind == "deleted":
        return [f"- **{time}** **{author}**: _(message deleted)_"]
    body = escape(message.text).replace("\n", "<br>")
    return [f"- **{time}** **{author}**: {body}"]


def render_markdown(
    messages: Iterable[Message],
    title: str = "Chat",
    media_dir: str = ".",
) -> str:
    """Render messages to a Markdown document string."""
    lines: List[str] = [f"# {escape(title)}", ""]
    current_day: Optional[str] = None
    for message in messages:
        day = (
            message.timestamp.strftime("%Y-%m-%d")
            if message.timestamp is not None
            else "Unknown date"
        )
        if day != current_day:
            if current_day is not None:
                lines.append("")
            lines.append(f"### {day}")
            lines.append("")
            current_day = day
        lines.extend(_message_lines(message, media_dir))
    lines.append("")
    return "\n".join(lines)


def write_markdown(
    messages: Iterable[Message],
    fp: IO[str],
    title: str = "Chat",
    media_dir: str = ".",
) -> None:
    """Write the Markdown document to *fp*."""
    fp.write(render_markdown(messages, title=title, media_dir=media_dir))
