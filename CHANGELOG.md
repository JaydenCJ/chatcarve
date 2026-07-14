# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-12

### Added

- Structural parser for WhatsApp `.txt` exports covering both platform
  dialects: Android (`12/31/23, 8:03 PM - …`) and iOS
  (`[14/02/2024, 09:15:03] …`), with multi-line message folding, CRLF and
  BOM tolerance, and U+200E/U+200F direction-mark handling.
- Locale-tolerant timestamp grammar: `/`, `.`, `-` separators, Korean
  spaced-dot dates, 12/24-hour clocks, suffix *and prefix* meridiem tokens
  (`PM`, `p. m.`, `م`, `오후`, `下午`, `午後`, `μ.μ.`), U+202F/U+00A0
  spaces, and Arabic-Indic digit forms.
- Whole-file date-order inference with reported evidence
  (`four-digit-year`, `day-over-12`, `monotonic`, `default`) and a
  `--order` override for genuinely ambiguous files.
- Multi-locale system-message catalog (13 languages) mapping to canonical
  events (`e2e_encrypted`, `member_added`, `missed_voice_call`, …);
  structural detection guarantees unknown locales degrade to
  `event: "unknown"` instead of fake text messages.
- Media handling for all three placeholder shapes — Android
  `<Media omitted>`, Android `(file attached)`, iOS `<attached: …>` and
  typed "omitted" stubs — with filenames preserved and media types
  classified from wording or WhatsApp filename conventions.
- Deleted-message tombstone detection in 13 languages.
- JSONL writer (sorted keys, stable schema, `docs/output-format.md`) and
  Markdown writer (day grouping, image embeds, `--media-dir` links,
  content escaping).
- `chatcarve` CLI: `parse` (JSONL + Markdown), `detect` (dialect report
  with inference evidence), `stats` (authors, kinds, date range); exit
  codes 0/1/2 and pipe-safe stdout.
- Fifteen-fixture locale corpus with frozen golden JSONL
  (`tests/corpus/`), en-US through ko-KR — 89 tests total, plus
  `scripts/smoke.sh`.

### Notes

- The repository ships no CI workflow; verification is local —
  `pip install -e '.[dev]' && pytest && bash scripts/smoke.sh`.

[0.1.0]: https://github.com/JaydenCJ/chatcarve/releases/tag/v0.1.0
