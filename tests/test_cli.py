"""CLI behavior: subcommands, exit codes, output files.

Everything runs in-process through ``chatcarve.cli.main`` — no
subprocesses, no installation required.
"""

import io
import json

import pytest

from chatcarve import __version__
from chatcarve.cli import EXIT_EMPTY, EXIT_ERROR, EXIT_OK, main

SAMPLE = (
    "12/31/23, 8:03 PM - Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them.\n"
    "12/31/23, 8:15 PM - Aunt May: Who wants the tamale recipe?\n"
    "12/31/23, 8:20 PM - Aunt May: IMG-20231231-WA0012.jpg (file attached)\n"
    "1/1/24, 10:30 AM - Rosa: happy new year\n"
)


@pytest.fixture
def export(tmp_path):
    path = tmp_path / "chat.txt"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"chatcarve {__version__}"


def test_no_command_prints_help_and_exits_2(capsys):
    assert main([]) == EXIT_ERROR
    assert "parse" in capsys.readouterr().out


def test_parse_writes_jsonl_to_stdout(export, capsys):
    assert main(["parse", str(export)]) == EXIT_OK
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 4
    assert json.loads(lines[3])["author"] == "Rosa"


def test_parse_writes_jsonl_and_markdown_files(export, tmp_path, capsys):
    jsonl_path = tmp_path / "out.jsonl"
    md_path = tmp_path / "out.md"
    code = main(
        [
            "parse", str(export),
            "--jsonl", str(jsonl_path),
            "--markdown", str(md_path),
            "--title", "Family",
            "--media-dir", "media",
        ]
    )
    assert code == EXIT_OK
    assert len(jsonl_path.read_text(encoding="utf-8").splitlines()) == 4
    md = md_path.read_text(encoding="utf-8")
    assert md.startswith("# Family")
    assert "(media/IMG-20231231-WA0012.jpg)" in md
    assert "wrote 4 records" in capsys.readouterr().err


def test_parse_reads_stdin_dash(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(SAMPLE))
    assert main(["parse", "-"]) == EXIT_OK
    assert len(capsys.readouterr().out.strip().splitlines()) == 4


def test_parse_forced_order_changes_timestamps(export, capsys):
    main(["parse", str(export), "--order", "mdy"])
    first = json.loads(capsys.readouterr().out.splitlines()[0])
    assert first["timestamp"] == "2023-12-31T20:03:00"


def test_error_exit_codes(tmp_path, capsys):
    # Missing file: I/O error, exit 2. Readable file with no messages:
    # exit 1 — distinguishable in shell scripts.
    assert main(["parse", str(tmp_path / "nope.txt")]) == EXIT_ERROR
    assert "error" in capsys.readouterr().err
    notes = tmp_path / "notes.txt"
    notes.write_text("just some notes\nnothing chatty\n", encoding="utf-8")
    assert main(["parse", str(notes)]) == EXIT_EMPTY
    assert "no messages found" in capsys.readouterr().err


def test_detect_reports_dialect(export, capsys):
    assert main(["detect", str(export)]) == EXIT_OK
    out = capsys.readouterr().out
    assert "platform:       android" in out
    assert "date order:     mdy (day-over-12)" in out
    assert "clock:          12-hour" in out
    assert "messages:       4" in out


def test_detect_warns_on_ambiguous_order(tmp_path, capsys):
    path = tmp_path / "chat.txt"
    path.write_text("01/02/24, 10:00 - A: hi\n", encoding="utf-8")
    assert main(["detect", str(path)]) == EXIT_OK
    captured = capsys.readouterr()
    assert "(default)" in captured.out
    assert "ambiguous" in captured.err


def test_stats_counts_authors_kinds_and_range(export, tmp_path, capsys):
    assert main(["stats", str(export)]) == EXIT_OK
    out = capsys.readouterr().out
    assert "messages:  4" in out
    assert "2 text, 1 media, 1 system" in out
    assert "Aunt May" in out
    assert "range:     2023-12-31T20:03:00 .. 2024-01-01T10:30:00" in out
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    assert main(["stats", str(empty)]) == EXIT_EMPTY
