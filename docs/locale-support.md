# Locale support

WhatsApp writes the export in whatever language and date convention the
*phone's system locale* dictates, and the file contains no declaration of
either. chatcarve handles this in two layers:

1. **Structure is locale-independent.** Headers are found by validating
   candidate timestamps, authors by the `: ` separator, Android system
   lines by the absence of an author, iOS system/media lines by the
   leading U+200E mark. This layer works for *any* locale, including ones
   not in the catalog — worst case, a system message is emitted with
   event `unknown` and its original text intact.
2. **Wording is catalog-driven.** System-message events, media
   placeholders, deleted-message tombstones, and meridiem tokens are
   matched against per-language pattern tables in `src/chatcarve/system.py`,
   `media.py`, and `timestamp.py`.

## Coverage matrix

Languages with catalog patterns **and** a corpus fixture frozen as a
golden file (`tests/corpus/`):

| Locale fixture | Platform | Date shape | Clock | Notable hazards exercised |
|---|---|---|---|---|
| en-us-android | Android | `12/31/23` (MDY) | 12h `PM` | month-first inference, multi-line messages |
| en-gb-ios | iOS | `14/02/2024` (DMY) | 24h+sec | U+200E marks, `" - "` inside message text |
| de-de-android | Android | `03.10.23` (dots) | 24h | ambiguous short chat → honest `default` evidence |
| es-mx-android | Android | `31/12/23` | 12h `p. m.` | U+202F narrow spaces inside the meridiem |
| fr-fr-ios | iOS | `06/01/2024` | 24h+sec | `<pièce jointe : …>` spaced colon |
| pt-br-android | Android | `24/12/23` (no comma) | 24h | comma-less header |
| it-it-android | Android | `15/08/23` | 24h | `<Media omessi>`, `(file allegato)` |
| nl-nl-android | Android | `27/04/24` | 24h | Dutch system catalog |
| ru-ru-android | Android | `09.05.24` (dots) | 24h | Cyrillic catalog, `(файл добавлен)` |
| tr-tr-android | Android | `29.10.23` (dots) | 24h | Turkish catalog |
| ja-jp-ios | iOS | `2024/1/1` (YMD) | 24h+sec | four-digit-year-first inference |
| ko-kr-ios | iOS | `2024. 1. 1.` (spaced dots) | 12h `오후` prefix | prefix meridiem, trailing period |
| zh-tw-ios | iOS | `2024/2/9` (YMD) | 12h `下午` prefix | prefix meridiem with no space |
| ar-sa-ios | iOS | `15/03/2024` | 12h `م`/`ص` | U+200F marks inside timestamps |
| ambiguous-mdy-android | Android | all fields ≤ 12 | 24h | monotonicity tie-break |

Also recognized without a dedicated fixture: Greek meridiem tokens
(`π.μ.`/`μ.μ.`) and Arabic-Indic digit forms in timestamps.

## Date-order inference

Evidence is ranked; `chatcarve detect` always reports which rule fired:

1. `four-digit-year` — a 4-digit first field can only be a year (ja, ko, zh).
2. `day-over-12` — any field > 12 must be the day.
3. `monotonic` — chats are chronological; if exactly one order keeps the
   timestamps non-decreasing, it wins.
4. `default` — genuinely ambiguous; day-month-year is assumed (the
   majority convention) and the CLI prints a warning suggesting
   `--order mdy` for US-locale exports.

## Adding a language

Add pattern rows to the tables in `system.py` / `media.py` (and meridiem
tokens in `timestamp.py` if needed), then commit a small fixture in
`tests/corpus/` plus its frozen golden under `tests/corpus/expected/`.
The corpus test picks new fixtures up automatically — see
[CONTRIBUTING.md](../CONTRIBUTING.md).
