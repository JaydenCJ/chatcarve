"""End-to-end parsing behavior: classification rules and detection."""

import pytest

from chatcarve import parse_chat, detect_format

LRM = "\u200e"


def test_authorless_android_line_is_system_even_when_unmatched(android_lines):
    text = android_lines(("12/31/23, 8:03 PM", "Something brand new WhatsApp says"))
    result = parse_chat(text)
    message = result.messages[0]
    assert message.kind == "system"
    assert message.system.event == "unknown"
    assert message.text == "Something brand new WhatsApp says"


def test_authored_line_matching_system_words_stays_text(android_lines):
    # A human typing catalog vocabulary must not become an event.
    text = android_lines(("12/31/23, 8:03 PM", "Alice: I added sugar and left"))
    message = parse_chat(text).messages[0]
    assert message.kind == "text"
    assert message.author == "Alice"


def test_ios_attributed_system_line_needs_lrm():
    with_lrm = f"{LRM}[14/02/2024, 09:15:03] Priya: {LRM}Messages and calls are end-to-end encrypted.\n"
    without = "[14/02/2024, 09:15:03] Priya: Messages and calls are end-to-end encrypted.\n"
    assert parse_chat(with_lrm).messages[0].kind == "system"
    assert parse_chat(with_lrm).messages[0].author is None
    # Without the mark it is a person quoting the notice — keep it text.
    assert parse_chat(without).messages[0].kind == "text"


def test_deleted_tombstone_keeps_author(android_lines):
    text = android_lines(("12/31/23, 9:05 PM", "Rosa: This message was deleted"))
    message = parse_chat(text).messages[0]
    assert message.kind == "deleted"
    assert message.author == "Rosa"


def test_media_with_continuation_lines_is_not_media(android_lines):
    text = (
        "12/31/23, 8:03 PM - Alice: <Media omitted>\n"
        "but actually I typed this second line\n"
    )
    message = parse_chat(text).messages[0]
    assert message.kind == "text"


def test_multiline_text_joined_with_newlines(android_lines):
    text = (
        "12/31/23, 8:16 PM - Rosa: Me!\n"
        "It needs:\n"
        "corn husks\n"
    )
    message = parse_chat(text).messages[0]
    assert message.text == "Me!\nIt needs:\ncorn husks"


def test_author_with_empty_body(android_lines):
    text = "12/31/23, 8:16 PM - Rosa:\n"
    message = parse_chat(text).messages[0]
    assert message.author == "Rosa"
    assert message.text == ""
    assert message.kind == "text"


def test_forced_order_overrides_inference(android_lines):
    text = android_lines(("05/06/24, 09:00", "Ana: hello"))
    forced = parse_chat(text, order="mdy")
    assert forced.detection.order_evidence == "forced"
    assert forced.messages[0].timestamp.month == 5
    # detect_format and parse_chat must agree on the dialect.
    assert detect_format(text, order="mdy") == forced.detection


def test_invalid_order_raises():
    with pytest.raises(ValueError):
        parse_chat("", order="ydm")
    with pytest.raises(ValueError):
        detect_format("", order="ydm")


def test_empty_input_yields_empty_result():
    result = parse_chat("")
    assert result.messages == []
    assert result.detection.platform == "unknown"


def test_unresolved_timestamps_counted(android_lines):
    # Force mdy onto a day-first file: 31 cannot be a month.
    text = android_lines(("31/12/23, 10:00", "Alice: hi"))
    result = parse_chat(text, order="mdy")
    assert result.unresolved_timestamps == 1
    assert result.messages[0].timestamp is None
    # The original spelling survives for downstream repair.
    assert result.messages[0].raw_timestamp == "31/12/23, 10:00"


def test_bom_on_first_line_does_not_hide_first_message():
    text = "\ufeff12/31/23, 8:03 PM - Alice: hi\n"
    result = parse_chat(text)
    assert len(result.messages) == 1
    assert result.messages[0].author == "Alice"


def test_indexes_and_lines_are_stable(android_lines):
    text = (
        "12/31/23, 8:03 PM - Alice: one\n"
        "two\n"
        "12/31/23, 8:04 PM - Bob: three\n"
    )
    messages = parse_chat(text).messages
    assert [(m.index, m.line) for m in messages] == [(0, 1), (1, 3)]
