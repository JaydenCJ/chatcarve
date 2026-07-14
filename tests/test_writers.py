"""JSONL and Markdown writers: stable schema, safe escaping, real links."""

import io
import json

from chatcarve import parse_chat, render_jsonl, render_markdown, write_jsonl

SAMPLE = (
    "12/31/23, 8:03 PM - Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them.\n"
    "12/31/23, 8:15 PM - Aunt May: Who wants the tamale recipe?\n"
    "12/31/23, 8:20 PM - Aunt May: IMG-20231231-WA0012.jpg (file attached)\n"
    "12/31/23, 9:00 PM - Rosa: <Media omitted>\n"
    "1/1/24, 10:30 AM - Rosa: This message was deleted\n"
)


def messages():
    return parse_chat(SAMPLE).messages


def test_jsonl_one_valid_object_per_line_with_stable_keys():
    lines = render_jsonl(messages()).splitlines()
    assert len(lines) == 5
    for line in lines:
        record = json.loads(line)
        assert list(record) == sorted(record)
        assert set(record) == {
            "author", "index", "kind", "line", "media",
            "raw_timestamp", "system", "text", "timestamp",
        }


def test_jsonl_iso_timestamps_and_unescaped_unicode():
    record = json.loads(render_jsonl(messages()).splitlines()[0])
    assert record["timestamp"] == "2023-12-31T20:03:00"
    japanese = parse_chat("31/12/23, 20:00 - あや: 新年おめでとう\n")
    assert "新年おめでとう" in render_jsonl(japanese.messages)


def test_write_jsonl_count_matches_render_and_empty_is_empty():
    buffer = io.StringIO()
    assert write_jsonl(messages(), buffer) == 5
    assert buffer.getvalue() == render_jsonl(messages())
    assert render_jsonl([]) == ""


def test_markdown_groups_by_day():
    doc = render_markdown(messages(), title="Family recipes")
    assert doc.startswith("# Family recipes")
    assert doc.count("### 2023-12-31") == 1
    assert doc.count("### 2024-01-01") == 1
    # Day heading order follows the chat.
    assert doc.index("### 2023-12-31") < doc.index("### 2024-01-01")


def test_markdown_image_becomes_embed_with_media_dir():
    doc = render_markdown(messages(), media_dir="media")
    assert "![IMG-20231231-WA0012.jpg](media/IMG-20231231-WA0012.jpg)" in doc


def test_markdown_omitted_and_deleted_are_labelled_not_linked():
    doc = render_markdown(messages())
    assert "_[media omitted from export]_" in doc
    assert "_(message deleted)_" in doc


def test_markdown_system_lines_are_italic_without_author():
    doc = render_markdown(messages())
    assert "*20:03 — Messages and calls are end-to-end encrypted." in doc


def test_markdown_escapes_markup_and_breaks_lines():
    result = parse_chat(
        "31/12/23, 20:00 - Eve: *bold* [link](x) # heading\nline two\n"
    )
    doc = render_markdown(result.messages)
    assert r"\*bold\*" in doc
    assert r"\[link\](x)" in doc
    assert r"\# heading<br>line two" in doc


def test_markdown_non_image_media_is_plain_link():
    result = parse_chat("31/12/23, 20:00 - Eve: VID-20231231-WA0001.mp4 (file attached)\n")
    doc = render_markdown(result.messages, media_dir=".")
    assert "[VID-20231231-WA0001.mp4](./VID-20231231-WA0001.mp4)" in doc
    assert "![" not in doc
