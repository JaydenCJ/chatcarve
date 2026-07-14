"""Golden-file corpus: fifteen locale/platform fixtures, byte-exact output.

Each ``tests/corpus/<name>.txt`` is a small, realistic export in one
locale/platform dialect; ``tests/corpus/expected/<name>.jsonl`` is the
frozen JSONL. A parser change that shifts a single timestamp, author, or
classification in any locale turns exactly one of these red.

DETECTIONS pins the dialect detection per fixture so a regression in
inference is reported separately from a serialization change.
"""

import pytest

from chatcarve import parse_chat, render_jsonl
from conftest import corpus_names, read_corpus, read_expected

# (platform, date_order, order_evidence, twelve_hour, has_seconds)
DETECTIONS = {
    "ambiguous-mdy-android": ("android", "mdy", "monotonic", False, False),
    "ar-sa-ios": ("ios", "dmy", "day-over-12", True, True),
    "de-de-android": ("android", "dmy", "default", False, False),
    "en-gb-ios": ("ios", "dmy", "day-over-12", False, True),
    "en-us-android": ("android", "mdy", "day-over-12", True, False),
    "es-mx-android": ("android", "dmy", "day-over-12", True, False),
    "fr-fr-ios": ("ios", "dmy", "default", False, True),
    "it-it-android": ("android", "dmy", "day-over-12", False, False),
    "ja-jp-ios": ("ios", "ymd", "four-digit-year", False, True),
    "ko-kr-ios": ("ios", "ymd", "four-digit-year", True, True),
    "nl-nl-android": ("android", "dmy", "day-over-12", False, False),
    "pt-br-android": ("android", "dmy", "day-over-12", False, False),
    "ru-ru-android": ("android", "dmy", "default", False, False),
    "tr-tr-android": ("android", "dmy", "day-over-12", False, False),
    "zh-tw-ios": ("ios", "ymd", "four-digit-year", True, True),
}


def test_corpus_and_manifest_agree():
    """Every fixture has a detection row and vice versa."""
    assert sorted(DETECTIONS) == corpus_names()


@pytest.mark.parametrize("name", sorted(DETECTIONS))
def test_corpus_golden(name):
    result = parse_chat(read_corpus(name))
    d = result.detection
    assert (
        d.platform, d.date_order, d.order_evidence, d.twelve_hour, d.has_seconds
    ) == DETECTIONS[name]
    assert render_jsonl(result.messages) == read_expected(name)
    # Golden corpora must be fully resolved: no timestamp left behind.
    assert result.unresolved_timestamps == 0
