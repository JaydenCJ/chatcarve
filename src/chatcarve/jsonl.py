"""JSONL output: one message per line, stable key order.

The writer sorts keys and disables ASCII escaping so records diff cleanly
in git and stay readable for the many chats that are not in English. The
schema is documented in ``docs/output-format.md`` and guaranteed stable
within a major version.
"""

from __future__ import annotations

import json
from typing import IO, Iterable, List

from .model import Message


def render_jsonl(messages: Iterable[Message]) -> str:
    """Render messages as a JSONL string (trailing newline included)."""
    lines: List[str] = [
        json.dumps(message.to_dict(), ensure_ascii=False, sort_keys=True)
        for message in messages
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def write_jsonl(messages: Iterable[Message], fp: IO[str]) -> int:
    """Write messages to *fp*; returns the number of records written."""
    count = 0
    for message in messages:
        fp.write(json.dumps(message.to_dict(), ensure_ascii=False, sort_keys=True))
        fp.write("\n")
        count += 1
    return count
