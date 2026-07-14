"""Timestamp grammar: every locale shape must parse; junk must not.

These tests pin down the exact behaviors that break single-locale parsers:
prefix vs suffix meridiem tokens, exotic spaces, Arabic-Indic digits, and
the date-order inference rules.
"""

from datetime import datetime

import pytest

from chatcarve.timestamp import RawTimestamp, infer_date_order, parse_raw, resolve

NNBSP = "\u202f"
NBSP = "\u00a0"


def make_raw(first=1, mid=2, last=24, **kwargs):
    defaults = dict(year_first=False, hour=9, minute=0, second=None, meridiem=None)
    defaults.update(kwargs)
    return RawTimestamp(first=first, mid=mid, last=last, **defaults)


# --- parse_raw: locale shapes -------------------------------------------------


def test_us_android_shape_with_suffix_meridiem():
    raw = parse_raw("12/31/23, 8:03 PM")
    assert (raw.first, raw.mid, raw.last) == (12, 31, 23)
    assert raw.meridiem == "pm"
    assert not raw.has_seconds


def test_ios_shape_with_seconds_24h():
    raw = parse_raw("14/02/2024, 09:15:03")
    assert raw.second == 3
    assert raw.meridiem is None


def test_date_separator_variants():
    # German dots, ISO-ish hyphens, and the comma-less pt-BR Android shape.
    assert parse_raw("03.10.23, 19:22").mid == 10
    assert parse_raw("2023-12-31, 23:59") is not None
    assert parse_raw("24/12/23 20:15").hour == 20


def test_date_separators_may_not_be_mixed():
    # "12/31.23" is not a WhatsApp timestamp; rejecting it keeps header
    # detection from eating message text that merely looks date-ish.
    assert parse_raw("12/31.23, 8:03 PM") is None


def test_spanish_spaced_meridiem_with_exotic_spaces():
    # Newer exports use U+202F before/inside "p. m."; older ones U+00A0.
    assert parse_raw(f"31/12/23, 11:40{NNBSP}p.{NNBSP}m.").meridiem == "pm"
    assert parse_raw(f"1/1/24, 12:05{NBSP}a.{NBSP}m.").meridiem == "am"


def test_korean_dotted_date_with_prefix_meridiem():
    raw = parse_raw("2023. 12. 31. 오후 11:58:02")
    assert raw.year_first
    assert raw.meridiem == "pm"
    assert raw.second == 2


def test_chinese_prefix_meridiem_without_space():
    raw = parse_raw("2024/2/9 下午8:01:15")
    assert raw.meridiem == "pm"
    assert raw.hour == 8


def test_japanese_year_first_24h():
    raw = parse_raw("2024/1/1 0:02:33")
    assert raw.year_first
    assert raw.hour == 0


def test_arabic_meridiem_letters_and_arabic_indic_digits():
    assert parse_raw("15/03/2024, 9:12:05 م").meridiem == "pm"
    assert parse_raw("16/03/2024, 8:00:10 ص").meridiem == "am"
    raw = parse_raw("٣١/١٢/٢٣, ٢٣:٥٩")
    assert (raw.first, raw.mid, raw.last, raw.hour) == (31, 12, 23, 23)


def test_greek_dotted_meridiem():
    assert parse_raw("31/12/23, 11:59 μ.μ.").meridiem == "pm"


# --- parse_raw: strict rejection ----------------------------------------------


def test_rejects_non_timestamps():
    rejects = [
        "hello there",  # no digits at all
        "3:2 last night",  # time-like but no date
        "12/31/23",  # date but no time
        "12/31/23, 25:00",  # impossible hour
        "12/31/23, 23:61",  # impossible minute
        "12/31/23, 13:00 PM",  # meridiem with a 24h hour is malformed
        "12/31/23, sometime 8:03",  # unknown junk between date and time
        "12/31/23, 8:03 XY",  # unknown suffix token
        "31/12/23, 오후 11:58 PM",  # meridiem on both sides
    ]
    for text in rejects:
        assert parse_raw(text) is None, f"should reject: {text!r}"


# --- resolve: meridiem arithmetic ----------------------------------------------


def test_resolve_meridiem_arithmetic():
    # PM adds twelve; 12 PM is noon, 12 AM is midnight — the classic
    # off-by-twelve; two-digit years are always 20xx (WhatsApp is younger
    # than 2000).
    assert resolve(parse_raw("12/31/23, 8:03 PM"), "mdy") == datetime(2023, 12, 31, 20, 3)
    assert resolve(parse_raw("1/1/24, 12:00 PM"), "mdy").hour == 12
    assert resolve(parse_raw("1/1/24, 12:00 AM"), "mdy").hour == 0
    assert resolve(parse_raw("1/2/09, 10:00"), "dmy").year == 2009


def test_resolve_invalid_date_returns_none():
    # 31 cannot be a month: resolving under the wrong order must fail
    # loudly (None), not wrap around.
    raw = parse_raw("31/12/23, 10:00")
    assert resolve(raw, "mdy") is None


def test_resolve_rejects_unknown_order():
    with pytest.raises(ValueError):
        resolve(make_raw(), "ydm")


# --- infer_date_order -----------------------------------------------------------


def test_infer_four_digit_year_wins():
    order, evidence = infer_date_order([make_raw(first=2024, year_first=True)])
    assert (order, evidence) == ("ymd", "four-digit-year")


def test_infer_day_over_12_in_either_position():
    assert infer_date_order([make_raw(first=31, mid=12)]) == ("dmy", "day-over-12")
    assert infer_date_order([make_raw(first=12, mid=31)]) == ("mdy", "day-over-12")


def test_infer_monotonic_breaks_tie():
    # 05/06 then 06/05: only month-first keeps the chat chronological.
    raws = [
        make_raw(first=5, mid=6, hour=9),
        make_raw(first=6, mid=5, hour=9),
        make_raw(first=6, mid=7, hour=10),
    ]
    assert infer_date_order(raws) == ("mdy", "monotonic")


def test_infer_ambiguous_and_empty_default_to_dmy():
    assert infer_date_order([make_raw(first=1, mid=2)]) == ("dmy", "default")
    assert infer_date_order([]) == ("dmy", "default")


def test_infer_conflicting_evidence_prefers_fewer_invalid_dates():
    # One line says day-first (31/12), two say month-first (12/31, 12/25).
    # The order leaving fewer unresolvable dates must win.
    raws = [
        make_raw(first=12, mid=31),
        make_raw(first=12, mid=25),
        make_raw(first=31, mid=12),
    ]
    assert infer_date_order(raws) == ("mdy", "day-over-12")
