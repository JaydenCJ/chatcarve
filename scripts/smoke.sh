#!/usr/bin/env bash
# Smoke test for chatcarve: parse the committed example export end-to-end
# through the real CLI — detect, parse (JSONL + Markdown), stats — plus a
# non-English corpus fixture and the ambiguity escape hatch.
# Self-contained: pure stdlib, no network, idempotent (works from a clean tree).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
if [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

# The package has zero runtime dependencies, so running from src/ needs no install.
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/chatcarve-smoke.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT

fail() { echo "SMOKE FAIL: $1" >&2; exit 1; }

echo "[smoke] python: $("$PYTHON" --version 2>&1)"

# 1. detect: the example export's dialect is identified with evidence.
detect_out="$("$PYTHON" -m chatcarve detect "$ROOT/examples/family-trip.txt")"
echo "$detect_out" | sed 's/^/[detect] /'
echo "$detect_out" | grep -q "platform:       ios" || fail "detect missed ios platform"
echo "$detect_out" | grep -q "date order:     dmy (day-over-12)" || fail "detect missed dmy evidence"
echo "$detect_out" | grep -q "messages:       11" || fail "detect message count wrong"

# 2. parse: JSONL + Markdown written; record count matches.
"$PYTHON" -m chatcarve parse "$ROOT/examples/family-trip.txt" \
  --jsonl "$WORKDIR/trip.jsonl" --markdown "$WORKDIR/trip.md" \
  --title "Trip to the seaside" --media-dir media 2>"$WORKDIR/parse.log" \
  || fail "parse exited non-zero"
sed 's/^/[parse] /' "$WORKDIR/parse.log"
[ "$(wc -l < "$WORKDIR/trip.jsonl")" -eq 11 ] || fail "expected 11 JSONL records"

# 3. JSONL is valid, media filename and system classification survive.
"$PYTHON" - "$WORKDIR/trip.jsonl" <<'PY' || fail "JSONL content checks failed"
import json, sys
records = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]
assert records[0]["system"]["event"] == "e2e_encrypted", records[0]
assert any(
    (r.get("media") or {}).get("filename") == "00000042-PHOTO-2024-08-30-11-02-19.jpg"
    for r in records
), "attachment filename lost"
assert any(r["kind"] == "deleted" for r in records), "deleted tombstone lost"
assert all(r["timestamp"] for r in records), "unresolved timestamp in output"
PY

# 4. Markdown groups by day and links media into --media-dir.
grep -q '^### 2024-08-30$' "$WORKDIR/trip.md" || fail "Markdown missing day heading"
grep -q '](media/00000042-PHOTO-2024-08-30-11-02-19.jpg)' "$WORKDIR/trip.md" \
  || fail "Markdown media link missing"

# 5. stats: authors and kinds summarized.
stats_out="$("$PYTHON" -m chatcarve stats "$ROOT/examples/family-trip.txt")"
echo "$stats_out" | sed 's/^/[stats] /'
echo "$stats_out" | grep -q "4 text, 2 media, 4 system, 1 deleted" || fail "stats kinds wrong"

# 6. Non-English dialect straight from the test corpus (Korean iOS,
#    year-first dates, prefix meridiem) parses with zero unresolved stamps.
ko_out="$("$PYTHON" -m chatcarve parse "$ROOT/tests/corpus/ko-kr-ios.txt")"
echo "$ko_out" | head -1 | grep -q '"timestamp": "2023-12-31T23:58:02"' \
  || fail "Korean prefix-meridiem timestamp misparsed"

# 7. The ambiguity escape hatch: --order flips the reading, exit code stays 0.
printf '01/02/24, 10:00 - A: hi\n' > "$WORKDIR/ambiguous.txt"
dmy_ts="$("$PYTHON" -m chatcarve parse "$WORKDIR/ambiguous.txt" | head -1)"
mdy_ts="$("$PYTHON" -m chatcarve parse --order mdy "$WORKDIR/ambiguous.txt" | head -1)"
echo "$dmy_ts" | grep -q '2024-02-01' || fail "default dmy reading wrong"
echo "$mdy_ts" | grep -q '2024-01-02' || fail "--order mdy reading wrong"

# 8. Exit codes: 1 for a non-export, 2 for a missing file.
printf 'not a chat\n' > "$WORKDIR/notes.txt"
set +e
"$PYTHON" -m chatcarve parse "$WORKDIR/notes.txt" >/dev/null 2>&1; rc_empty=$?
"$PYTHON" -m chatcarve parse "$WORKDIR/does-not-exist.txt" >/dev/null 2>&1; rc_missing=$?
set -e
[ "$rc_empty" -eq 1 ] || fail "non-export should exit 1, got $rc_empty"
[ "$rc_missing" -eq 2 ] || fail "missing file should exit 2, got $rc_missing"

# 9. --version agrees with the package version; --help lists subcommands.
version_out="$("$PYTHON" -m chatcarve --version)"
pkg_version="$("$PYTHON" -c 'import chatcarve; print(chatcarve.__version__)')"
[ "$version_out" = "chatcarve $pkg_version" ] \
  || fail "--version mismatch: '$version_out' vs package '$pkg_version'"
"$PYTHON" -m chatcarve --help | grep -q "detect" || fail "--help missing detect command"

# 10. The runnable Python-API example works end to end.
"$PYTHON" "$ROOT/examples/carve_demo.py" | grep -q "DEMO OK" \
  || fail "examples/carve_demo.py did not print DEMO OK"

echo "SMOKE OK"
