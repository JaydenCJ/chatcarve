# Contributing to chatcarve

Thanks for your interest in contributing. Issues, discussions, and pull
requests are all welcome — locale reports most of all.

## Development setup

```bash
git clone https://github.com/JaydenCJ/chatcarve
cd chatcarve
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running the checks

```bash
pytest                 # unit tests + the 15-locale golden corpus
bash scripts/smoke.sh  # end-to-end CLI smoke: detect, parse, stats
```

Both must pass before a pull request is reviewed; the smoke script must
print `SMOKE OK`. The suite runs fully offline, needs no API keys, and
never touches the network.

## Adding a locale

This is the most valuable kind of contribution and touches no logic:

1. Add pattern rows to the tables in `src/chatcarve/system.py` and/or
   `src/chatcarve/media.py` (meridiem tokens live in `timestamp.py`).
2. Commit a small fixture in `tests/corpus/<locale>-<platform>.txt` —
   **synthetic data only, never a real chat** — and its expected output in
   `tests/corpus/expected/<same-name>.jsonl`, plus a detection row in
   `tests/test_corpus.py`.
3. Add the row to the matrix in `docs/locale-support.md`.

## Ground rules

- **No new runtime dependencies.** The package is standard-library only;
  that is a feature. Test-only dependencies belong in the `dev` extra.
- **Golden files are contracts.** A parser change that alters any
  `tests/corpus/expected/*.jsonl` needs the diff explained in the PR, not
  just regenerated.
- **Structure decides, catalogs refine.** Classification of system/media
  lines must never depend on the catalog alone — an unknown locale must
  degrade to `event: "unknown"`, never to a fake text message.
- **Every public API needs an English docstring and a test.** Keep the
  three READMEs (`README.md`, `README.zh.md`, `README.ja.md`) aligned when
  you change one; English is the authoritative version.

## Reporting bugs

Please include `chatcarve --version` output, the `chatcarve detect` report
for the file, and a *minimal, anonymized* snippet (a few lines with names
replaced) that reproduces the problem. Never post a real chat export.

## Security

Do not open public issues for security problems; use GitHub's private
vulnerability reporting on this repository instead.
