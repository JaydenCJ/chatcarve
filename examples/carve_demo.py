#!/usr/bin/env python3
"""Runnable demo of the chatcarve Python API.

Parses ``examples/family-trip.txt`` (an iOS-shaped export committed to the
repository) and shows the pieces most people build on: detection, the
message stream, media references, and both writers. Run from the repo
root::

    PYTHONPATH=src python3 examples/carve_demo.py

Prints ``DEMO OK`` at the end; scripts/smoke.sh greps for it.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from chatcarve import parse_chat, render_jsonl, render_markdown  # noqa: E402

EXPORT = pathlib.Path(__file__).with_name("family-trip.txt")


def main() -> int:
    text = EXPORT.read_text(encoding="utf-8-sig")
    result = parse_chat(text)

    d = result.detection
    print(f"[detect] platform={d.platform} order={d.date_order} "
          f"({d.order_evidence}) messages={d.message_count}")

    kinds = {}
    for message in result.messages:
        kinds[message.kind] = kinds.get(message.kind, 0) + 1
    print(f"[kinds]  {kinds}")

    attachments = [
        m.media.filename
        for m in result.messages
        if m.media is not None and m.media.filename
    ]
    print(f"[media]  attachments preserved: {attachments}")

    jsonl = render_jsonl(result.messages)
    print(f"[jsonl]  {len(jsonl.splitlines())} records, "
          f"first: {jsonl.splitlines()[0][:60]}...")

    markdown = render_markdown(result.messages, title="Trip to the seaside",
                               media_dir="media")
    day_headings = [line for line in markdown.splitlines() if line.startswith("### ")]
    print(f"[md]     day sections: {day_headings}")

    assert result.unresolved_timestamps == 0
    print("DEMO OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
