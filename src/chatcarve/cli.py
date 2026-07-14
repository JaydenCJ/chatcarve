"""Command line interface.

Subcommands:

- ``chatcarve parse <export.txt>``: emit JSONL (stdout or ``--jsonl``) and
  optionally Markdown (``--markdown``).
- ``chatcarve detect <export.txt>``: report the detected dialect —
  platform, date order and the evidence for it, clock convention.
- ``chatcarve stats <export.txt>``: per-author and per-kind counts plus
  the covered date range.

Exit codes: 0 = success, 1 = the file contained no parseable messages,
2 = usage or I/O errors. Errors are one readable line on stderr, never a
traceback.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from typing import List, Optional

from .jsonl import write_jsonl
from .markdown import write_markdown
from .model import KINDS
from .parser import ParseResult, detect_format, parse_chat
from .timestamp import ORDERS

EXIT_OK = 0
EXIT_EMPTY = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    """Build the ``chatcarve`` argument parser (exposed for testing)."""
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="chatcarve",
        description=(
            "Parse WhatsApp chat exports into clean JSONL and Markdown, "
            "media links preserved."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"chatcarve {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("export", help="path to the exported chat .txt (or - for stdin)")
        p.add_argument(
            "--order",
            choices=ORDERS,
            help="force the date order instead of inferring it from the file",
        )

    p_parse = sub.add_parser("parse", help="convert an export to JSONL / Markdown")
    add_common(p_parse)
    p_parse.add_argument(
        "--jsonl",
        metavar="PATH",
        help="write JSONL here instead of stdout (- means stdout)",
    )
    p_parse.add_argument(
        "--markdown", metavar="PATH", help="also write a Markdown document here"
    )
    p_parse.add_argument(
        "--title",
        default=None,
        help="Markdown document title (default: the export file name)",
    )
    p_parse.add_argument(
        "--media-dir",
        default=".",
        metavar="DIR",
        help="directory Markdown media links point into (default: .)",
    )

    p_detect = sub.add_parser("detect", help="report the export's dialect")
    add_common(p_detect)

    p_stats = sub.add_parser("stats", help="summarize authors, kinds, date range")
    add_common(p_stats)

    return parser


def _read_export(path: str) -> str:
    """Read an export file; tolerate a UTF-8 BOM and stray mojibake."""
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fp:
        return fp.read()


def _parse_or_fail(path: str, order: Optional[str]) -> Optional[ParseResult]:
    text = _read_export(path)
    result = parse_chat(text, order=order)
    if not result.messages:
        print(
            f"chatcarve: no messages found in {path} — is this a WhatsApp export?",
            file=sys.stderr,
        )
        return None
    return result


def _cmd_parse(args: argparse.Namespace) -> int:
    result = _parse_or_fail(args.export, args.order)
    if result is None:
        return EXIT_EMPTY

    jsonl_target = args.jsonl if args.jsonl is not None else "-"
    if jsonl_target == "-":
        write_jsonl(result.messages, sys.stdout)
    else:
        with open(jsonl_target, "w", encoding="utf-8") as fp:
            count = write_jsonl(result.messages, fp)
        print(f"chatcarve: wrote {count} records to {jsonl_target}", file=sys.stderr)

    if args.markdown is not None:
        title = args.title
        if title is None:
            title = args.export if args.export != "-" else "Chat"
        with open(args.markdown, "w", encoding="utf-8") as fp:
            write_markdown(
                result.messages, fp, title=title, media_dir=args.media_dir
            )
        print(f"chatcarve: wrote Markdown to {args.markdown}", file=sys.stderr)

    if result.unresolved_timestamps:
        count = result.unresolved_timestamps
        noun = "timestamp" if count == 1 else "timestamps"
        print(
            f"chatcarve: warning: {count} {noun} did not resolve under "
            f"order {result.detection.date_order!r}; "
            f"try --order with a different date order",
            file=sys.stderr,
        )
    return EXIT_OK


def _cmd_detect(args: argparse.Namespace) -> int:
    text = _read_export(args.export)
    detection = detect_format(text, order=args.order)
    if detection.message_count == 0:
        print(
            f"chatcarve: no messages found in {args.export} — is this a WhatsApp export?",
            file=sys.stderr,
        )
        return EXIT_EMPTY
    print(f"platform:       {detection.platform}")
    print(f"date order:     {detection.date_order} ({detection.order_evidence})")
    print(f"clock:          {'12-hour' if detection.twelve_hour else '24-hour'}")
    print(f"seconds:        {'yes' if detection.has_seconds else 'no'}")
    print(f"messages:       {detection.message_count}")
    if detection.order_evidence == "default":
        print(
            "note: date order is ambiguous in this file; "
            "re-run with --order mdy if this chat is from a US-locale phone",
            file=sys.stderr,
        )
    return EXIT_OK


def _cmd_stats(args: argparse.Namespace) -> int:
    result = _parse_or_fail(args.export, args.order)
    if result is None:
        return EXIT_EMPTY

    kinds = Counter(m.kind for m in result.messages)
    authors = Counter(m.author for m in result.messages if m.author is not None)
    stamps = [m.timestamp for m in result.messages if m.timestamp is not None]

    print(f"messages:  {len(result.messages)}")
    parts = ", ".join(f"{kinds[k]} {k}" for k in KINDS if kinds[k])
    print(f"kinds:     {parts}")
    if stamps:
        print(f"range:     {min(stamps).isoformat()} .. {max(stamps).isoformat()}")
    print("authors:")
    width = max((len(name) for name in authors), default=0)
    for name, count in authors.most_common():
        print(f"  {name.ljust(width)}  {count}")
    return EXIT_OK


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_ERROR
    try:
        if args.command == "parse":
            return _cmd_parse(args)
        if args.command == "detect":
            return _cmd_detect(args)
        if args.command == "stats":
            return _cmd_stats(args)
    except BrokenPipeError:
        # `chatcarve parse chat.txt | head` is a legitimate pipeline; dying
        # mid-write is fine, complaining about it on stderr is not.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return EXIT_OK
    except ValueError as exc:
        print(f"chatcarve: error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except OSError as exc:
        print(f"chatcarve: error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover - exercised via console script
    sys.exit(main())
