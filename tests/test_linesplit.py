"""Block splitting: header detection and continuation folding.

The failure mode being guarded against throughout: message *text* that
resembles a header (scores, times, hyphens) must never start a new block,
and real headers must never be swallowed into the previous message.
"""

from chatcarve.linesplit import match_header, split_blocks

LRM = "\u200e"
RLM = "\u200f"


def test_both_header_shapes_detected():
    android = match_header("12/31/23, 8:03 PM - Alice: hi")
    assert android is not None
    assert (android.platform, android.rest) == ("android", "Alice: hi")
    ios = match_header("[14/02/2024, 09:15:03] Sam: hello")
    assert (ios.platform, ios.rest) == ("ios", "Sam: hello")


def test_header_lookalikes_are_rejected():
    # " - " plus colons but no valid date; and a " - " far into a long
    # line, past the bounded header-length budget.
    assert match_header("Scores - 3:2 last night") is None
    assert match_header(("x" * 80) + " - not a header") is None


def test_hyphenated_date_does_not_confuse_android_split():
    # The date itself contains hyphens; the splitter must keep scanning
    # past them to the real " - " separator.
    block = match_header("2023-12-31, 23:59 - Alice: hi")
    assert block is not None
    assert block.rest == "Alice: hi"


def test_direction_marks_recorded_and_stripped():
    ios = match_header(f"{LRM}[14/02/2024, 09:18:22] Priya: {LRM}image omitted")
    assert ios.lrm
    assert ios.raw_timestamp == "14/02/2024, 09:18:22"
    arabic = match_header(f"{RLM}[15/03/2024, 9:12:05 م] جدتي: مرحبا")
    assert arabic is not None
    assert arabic.raw.meridiem == "pm"


def test_continuation_lines_fold_into_previous_block():
    text = (
        "12/31/23, 8:16 PM - Rosa: Me!\n"
        "It needs:\n"
        "corn husks\n"
        "1/1/24, 10:30 AM - May: happy new year\n"
    )
    result = split_blocks(text)
    assert len(result.blocks) == 2
    assert result.blocks[0].continuation == ["It needs:", "corn husks"]


def test_blank_lines_kept_inside_but_trimmed_at_end():
    # Blank lines inside a multi-line message are content (verse breaks);
    # blank lines after the last text are export artifacts.
    inside = split_blocks(
        "12/31/23, 8:16 PM - Rosa: verse one\n\nverse two\n"
        "12/31/23, 8:17 PM - May: nice\n"
    )
    assert inside.blocks[0].continuation == ["", "verse two"]
    trailing = split_blocks("12/31/23, 8:16 PM - Rosa: bye\n\n\n")
    assert trailing.blocks[0].continuation == []


def test_crlf_line_endings():
    text = "12/31/23, 8:16 PM - Rosa: hi\r\n12/31/23, 8:17 PM - May: yo\r\n"
    result = split_blocks(text)
    assert [b.rest for b in result.blocks] == ["Rosa: hi", "May: yo"]


def test_preamble_kept_and_line_numbers_one_based():
    text = (
        "some tool banner\n"
        "12/31/23, 8:16 PM - Rosa: a\n"
        "continued\n"
        "12/31/23, 8:17 PM - May: b\n"
    )
    result = split_blocks(text)
    assert result.preamble == ["some tool banner"]
    assert [b.line for b in result.blocks] == [2, 4]
