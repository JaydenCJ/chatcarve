"""Shared fixtures: corpus paths and small export builders.

Everything here is deterministic and offline — fixtures build export text
in memory or read the committed corpus files; no network, no clocks.
"""

from pathlib import Path

import pytest

CORPUS_DIR = Path(__file__).parent / "corpus"
EXPECTED_DIR = CORPUS_DIR / "expected"

LRM = "\u200e"
RLM = "\u200f"
NNBSP = "\u202f"


def corpus_names():
    """Sorted fixture basenames (without extension) in the corpus."""
    return sorted(p.stem for p in CORPUS_DIR.glob("*.txt"))


def read_corpus(name: str) -> str:
    return (CORPUS_DIR / f"{name}.txt").read_text(encoding="utf-8-sig")


def read_expected(name: str) -> str:
    return (EXPECTED_DIR / f"{name}.jsonl").read_text(encoding="utf-8")


@pytest.fixture
def android_lines():
    """Builder for Android-shape export text from (timestamp, rest) pairs."""

    def build(*rows):
        return "".join(f"{ts} - {rest}\n" for ts, rest in rows)

    return build


@pytest.fixture
def ios_lines():
    """Builder for iOS-shape export text from (timestamp, rest) pairs."""

    def build(*rows):
        return "".join(f"[{ts}] {rest}\n" for ts, rest in rows)

    return build
