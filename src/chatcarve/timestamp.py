"""Locale-tolerant WhatsApp timestamp parsing.

WhatsApp writes timestamps in whatever shape the phone's locale dictates,
and the export contains no locale declaration. Observed axes of variation:

- **Date order**: ``12/31/23`` (en-US), ``31/12/2023`` (most of the world),
  ``2023/12/31`` (ja-JP), ``2023. 12. 31.`` (ko-KR).
- **Date separator**: ``/``, ``.``, ``-``; Korean adds spaces and a
  trailing period.
- **Clock**: 24-hour, or 12-hour with a meridiem token that may sit before
  or after the time (``11:59 PM``, ``p. m.``, ``오후 11:59``, ``下午11:59``).
- **Digits**: Arabic-Indic digit forms in some RTL exports.

This module parses a timestamp string into its raw numeric fields without
committing to a date order (:func:`parse_raw`), infers the order for a whole
file from evidence (:func:`infer_date_order`), and only then resolves fields
into :class:`datetime.datetime` values (:func:`resolve`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

from .textnorm import clean_for_matching

#: The three date orders a WhatsApp export can use.
ORDERS = ("dmy", "mdy", "ymd")

# Tokens meaning "before noon" / "after noon", normalized by _normalize_token
# (casefolded, dots and spaces removed). Sources: WhatsApp exports produced
# under the corresponding system locales; see docs/locale-support.md.
_AM_TOKENS = frozenset(
    [
        "am",  # en, es ("a. m."), fr, pt and many others
        "πμ",  # el
        "ص",  # ar (صباحًا)
        "午前",  # ja (prefix position)
        "上午",  # zh (prefix position)
        "오전",  # ko (prefix position)
        "vorm",  # de, older exports ("vorm.")
    ]
)

_PM_TOKENS = frozenset(
    [
        "pm",  # en, es ("p. m."), fr, pt and many others
        "μμ",  # el
        "م",  # ar (مساءً)
        "午後",  # ja (prefix position)
        "下午",  # zh (prefix position)
        "오후",  # ko (prefix position)
        "nachm",  # de, older exports ("nachm.")
    ]
)

# Date shapes. Field widths are captured so 4-digit-first can be recognized
# as an unambiguous year-month-day date.
_DATE_YMD_RE = re.compile(
    r"^(?P<a>\d{4})(?P<sep>[./-]) ?(?P<b>\d{1,2})(?P=sep) ?(?P<c>\d{1,2})\.?"
)
_DATE_GENERIC_RE = re.compile(
    r"^(?P<a>\d{1,2})(?P<sep>[./-]) ?(?P<b>\d{1,2})(?P=sep) ?(?P<c>\d{2,4})"
)
_TIME_RE = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2})(?::(?P<s>\d{2}))?")


@dataclass(frozen=True)
class RawTimestamp:
    """A timestamp split into fields, before the date order is known.

    ``first``/``mid``/``last`` are the three date fields in file order;
    ``year_first`` is True when the first field had four digits, which is
    the only unambiguous signal for year-month-day order.
    """

    first: int
    mid: int
    last: int
    year_first: bool
    hour: int
    minute: int
    second: Optional[int]
    meridiem: Optional[str]  # "am" | "pm" | None

    @property
    def has_seconds(self) -> bool:
        return self.second is not None


def _normalize_token(token: str) -> str:
    """Casefold a meridiem candidate and drop dots/spaces: ``p. m.`` -> ``pm``."""
    return token.casefold().replace(".", "").replace(" ", "")


def _classify_meridiem(token: str) -> Optional[str]:
    normalized = _normalize_token(token)
    if not normalized:
        return None
    if normalized in _AM_TOKENS:
        return "am"
    if normalized in _PM_TOKENS:
        return "pm"
    return None


def parse_raw(text: str) -> Optional[RawTimestamp]:
    """Parse a candidate timestamp string into a :class:`RawTimestamp`.

    Returns None when *text* is not a complete, well-formed WhatsApp
    timestamp. The check is strict on purpose: header detection relies on
    rejecting message text that merely *contains* digits and colons.
    """
    text = clean_for_matching(text).strip()
    date_match = _DATE_YMD_RE.match(text)
    year_first = date_match is not None
    if date_match is None:
        date_match = _DATE_GENERIC_RE.match(text)
    if date_match is None:
        return None

    remainder = text[date_match.end():].lstrip(" ,")
    time_match = _TIME_RE.search(remainder)
    if time_match is None:
        return None

    prefix = remainder[: time_match.start()].strip()
    suffix = remainder[time_match.end():].strip()
    meridiem = None
    if prefix:
        meridiem = _classify_meridiem(prefix)
        if meridiem is None:  # unknown junk before the time: not a timestamp
            return None
    if suffix:
        suffix_meridiem = _classify_meridiem(suffix)
        if suffix_meridiem is None:
            return None
        if meridiem is not None:  # a marker on both sides is malformed
            return None
        meridiem = suffix_meridiem

    hour = int(time_match.group("h"))
    minute = int(time_match.group("m"))
    second = int(time_match.group("s")) if time_match.group("s") else None
    if hour > 23 or minute > 59 or (second is not None and second > 59):
        return None
    if meridiem is not None and not 1 <= hour <= 12:
        return None

    return RawTimestamp(
        first=int(date_match.group("a")),
        mid=int(date_match.group("b")),
        last=int(date_match.group("c")),
        year_first=year_first,
        hour=hour,
        minute=minute,
        second=second,
        meridiem=meridiem,
    )


def _expand_year(value: int) -> int:
    """WhatsApp launched in 2009, so every two-digit year is 20xx."""
    return value if value >= 100 else 2000 + value


def resolve(raw: RawTimestamp, order: str) -> Optional[datetime]:
    """Materialize a :class:`RawTimestamp` under a chosen date *order*.

    Returns None when the fields do not form a valid calendar date under
    that order (e.g. month 31), which is exactly the signal
    :func:`infer_date_order` uses to discard impossible hypotheses.
    """
    if order == "ymd":
        year, month, day = _expand_year(raw.first), raw.mid, raw.last
    elif order == "dmy":
        day, month, year = raw.first, raw.mid, _expand_year(raw.last)
    elif order == "mdy":
        month, day, year = raw.first, raw.mid, _expand_year(raw.last)
    else:
        raise ValueError(f"unknown date order: {order!r}")

    hour = raw.hour
    if raw.meridiem == "pm" and hour < 12:
        hour += 12
    elif raw.meridiem == "am" and hour == 12:
        hour = 0

    try:
        return datetime(year, month, day, hour, raw.minute, raw.second or 0)
    except ValueError:
        return None


def _is_monotonic(stamps: List[Optional[datetime]]) -> bool:
    """True when every timestamp resolves and the sequence never goes back.

    Chat exports are chronological, so a hypothesis that makes the file
    jump backwards in time (e.g. reading 03/04 then 04/03 as April 3rd then
    March 4th) can be rejected.
    """
    previous: Optional[datetime] = None
    for stamp in stamps:
        if stamp is None:
            return False
        if previous is not None and stamp < previous:
            return False
        previous = stamp
    return True


def infer_date_order(raws: Iterable[RawTimestamp]) -> Tuple[str, str]:
    """Infer the date order for a whole export.

    Returns ``(order, evidence)`` where *evidence* is one of:

    - ``"four-digit-year"`` — a 4-digit first field forces year-month-day.
    - ``"day-over-12"`` — some field exceeds 12, so it must be the day.
    - ``"monotonic"`` — only one hypothesis keeps the chat chronological.
    - ``"default"`` — genuinely ambiguous; day-month-year is assumed
      because it is the majority convention among WhatsApp locales.

    Callers should surface the evidence to users (the CLI's ``detect``
    command does) so an ambiguous file is never silently misread.
    """
    raws = list(raws)
    if not raws:
        return "dmy", "default"

    if any(raw.year_first for raw in raws):
        return "ymd", "four-digit-year"

    first_over = any(raw.first > 12 for raw in raws)
    mid_over = any(raw.mid > 12 for raw in raws)
    if first_over and not mid_over:
        return "dmy", "day-over-12"
    if mid_over and not first_over:
        return "mdy", "day-over-12"
    if first_over and mid_over:
        # Contradictory evidence (corrupt or concatenated file). Pick the
        # order that leaves fewer unresolvable dates; ties go to dmy.
        dmy_bad = sum(1 for raw in raws if resolve(raw, "dmy") is None)
        mdy_bad = sum(1 for raw in raws if resolve(raw, "mdy") is None)
        return ("mdy", "day-over-12") if mdy_bad < dmy_bad else ("dmy", "day-over-12")

    dmy_ok = _is_monotonic([resolve(raw, "dmy") for raw in raws])
    mdy_ok = _is_monotonic([resolve(raw, "mdy") for raw in raws])
    if dmy_ok and not mdy_ok:
        return "dmy", "monotonic"
    if mdy_ok and not dmy_ok:
        return "mdy", "monotonic"
    return "dmy", "default"
