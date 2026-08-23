"""Command-line interface for legal-clause-finder.

Subcommands
  scan    Scan one or more files/directories for risky clauses.
  list    Print the curated clause library.
  version Print version and exit.

Examples
  python -m legalclause scan contract.txt
  python -m legalclause scan contracts/ --format json --out report.json
  python -m legalclause scan a.txt b.md --recursive --max-bytes 2000000
  python -m legalclause scan --quiet --format txt contracts/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import DEFAULT_CONFIG, MAX_FILE_BYTES, ok
from .reporter import write_report, to_text
from .scanner import scan_paths, list_clauses, CLAUSE_LIBRARY, HIGH, MED, LOW


# ── subcommands ───────────────────────────────────────────────────────
def cmd_scan(args: argparse.Namespace) -> int:
    """Scan file(s)/dir(s) and emit findings."""
    paths = [Path(p) for p in args.path]
    if not paths:
        print("legal-clause-finder: error: at least one path is required",
              file=sys.stderr)
        return 2

    suffixes = args.suffixes if args.suffixes else None
    result = scan_paths(
        paths,
        recursive=args.recursive,
        max_bytes=args.max_bytes,
        allowed_suffixes=suffixes,
    )

    # Always print a one-line summary to stdout for shell composition.
    if args.quiet:
        if result.total_hits:
            print(json.dumps({
                "high": result.high, "med": result.med, "low": result.low,
                "total": result.total_hits,
                "files_scanned": result.files_scanned,
                "files_skipped": result.files_skipped,
            }))
        return 1 if result.high > 0 else (0 if result.total_hits == 0 else 0)

    ok(f"scanned {result.files_scanned} file(s), "
       f"skipped {result.files_skipped}, found {result.total_hits} hit(s)")

    write_report(result, args.format, args.out)

    # Exit non-zero only when HIGH-risk clauses are present (useful in CI).
    return 1 if result.high > 0 else 0


def cmd_list(args: argparse.Namespace) -> int:
    """Print the curated clause library."""
    clauses = list_clauses()
    if args.format == "json":
        print(json.dumps(clauses, indent=2, ensure_ascii=False))
        return 0
    print(f"legal-clause-finder v{__version__} — curated clause library "
          f"({len(clauses)} rules)\n")
    print(f"{'RISK':<6} {'CATEGORY':<24} {'LABEL':<28} PATTERN")
    print("-" * 100)
    for c in clauses:
        print(f"{c['risk']:<6} {c['category']:<24} {c['label']:<28} {c['pattern']}")
    print("")
    print("Risk levels: HIGH = serious contractual hazard, "
          "MED = worth reviewing, LOW = informational.")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    print(f"legal-clause-finder {__version__}")
    return 0


# ── parser ────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="legal-clause-finder",
        description="Flag risky contract clauses via curated heuristic scan. "
                    "Zero API key, pure Python stdlib.",
    )
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="cmd")

    # scan
    ps = sub.add_parser("scan", help="scan file(s)/dir(s) for risky clauses")
    ps.add_argument("path", nargs="*", help="file(s) or dir(s) to scan")
    ps.add_argument("--format", "-f", default="text",
                    choices=["text", "txt", "markdown", "md", "json"],
                    help="output format (default: text)")
    ps.add_argument("--out", "-o", default=None,
                    help="write report to this file (default: stdout)")
    ps.add_argument("--recursive", "-r", action="store_true", default=True,
                    help="recurse into directories (default: on)")
    ps.add_argument("--no-recursive", dest="recursive", action="store_false",
                    help="do not recurse into directories")
    ps.add_argument("--suffixes", nargs="*", default=None,
                    help="override allowed file suffixes (default: .txt .md .text)")
    ps.add_argument("--max-bytes", type=int, default=MAX_FILE_BYTES,
                    help=f"max file size in bytes (default: {MAX_FILE_BYTES})")
    ps.add_argument("--quiet", "-q", action="store_true",
                    help="print only a JSON summary line")
    ps.set_defaults(func=cmd_scan)

    # list
    pl = sub.add_parser("list", help="show the curated clause library")
    pl.add_argument("--format", "-f", default="table",
                    choices=["table", "json"], help="output format (default: table)")
    pl.set_defaults(func=cmd_list)

    p.set_defaults(func=lambda a: cmd_version(a) if a.version else (
        p.print_help() or 1))

    return p


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) if getattr(args, "func", None) else (
        parser.print_help() or 1)


if __name__ == "__main__":
    sys.exit(main())
