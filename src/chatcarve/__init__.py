"""chatcarve: parse WhatsApp chat exports into clean JSONL and Markdown.

WhatsApp's ``.txt`` export format is undocumented and varies by platform
(Android vs iOS) and by the phone's locale: date order, 12/24-hour clocks,
meridiem tokens, invisible direction marks, and the wording of every system
message all change. chatcarve parses the format structurally, infers the
date order from evidence in the file itself, and classifies system and
media lines against a multi-locale catalog.

Public API::

    from chatcarve import parse_chat, detect_format

    result = parse_chat(open("chat.txt", encoding="utf-8-sig").read())
    for message in result.messages:
        print(message.timestamp, message.author, message.text)
"""

from .markdown import render_markdown
from .jsonl import render_jsonl, write_jsonl
from .model import MediaRef, Message, SystemEvent
from .parser import Detection, ParseResult, detect_format, parse_chat

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Detection",
    "MediaRef",
    "Message",
    "ParseResult",
    "SystemEvent",
    "detect_format",
    "parse_chat",
    "render_jsonl",
    "render_markdown",
    "write_jsonl",
]
