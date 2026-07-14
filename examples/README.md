# Examples

- `family-trip.txt` — a small iOS-shaped WhatsApp export (en-GB) with the
  invisible U+200E marks real exports carry, a multi-line message, an
  attachment reference, an "image omitted" stub, a deleted message, and
  system messages. Safe synthetic data; no real people.
- `carve_demo.py` — parses the export through the Python API and prints
  detection, kind counts, preserved media filenames, and both output
  formats. Ends with `DEMO OK`.

Run from the repository root (no installation needed — the package has
zero runtime dependencies):

```bash
PYTHONPATH=src python3 examples/carve_demo.py
```

Or use the CLI on the same file:

```bash
PYTHONPATH=src python3 -m chatcarve detect examples/family-trip.txt
PYTHONPATH=src python3 -m chatcarve parse examples/family-trip.txt --markdown trip.md
```

For a multi-locale tour, point the same commands at any fixture in
[`tests/corpus/`](../tests/corpus/) — fifteen dialects from `en-us-android`
to `ko-kr-ios`.
