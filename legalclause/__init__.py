"""legal-clause-finder: flag risky contract clauses via heuristic scan.

A free-stack, zero-API-key contract scanner.  It walks contract text
(plain ``--file`` or a directory of ``*.txt``/``*.md`` files) and flags
risky clauses using a curated library of regex patterns grouped by
category.  Each hit is labelled ``HIGH`` / ``MED`` / ``LOW``, ranked, and
emitted as human-readable prose plus a stable JSON machine-output so it
composes with other agents.

Design
  * Pure Python 3 standard library — no third-party dependencies, no LLM.
  * Regex DoS-safe: patterns use bounded character classes and a single
    linear scan per line (no nested quantifiers, no backreferences).
  * Path-safe: file inputs are validated against a configurable size cap
    and resolved under an allow-list base directory.
  * No command execution from untrusted input, no shell invocation,
    no network, no secrets.

Usage
  python -m legalclause scan contract.txt
  python -m legalclause scan contracts/ --format json --out report.json
  python -m legalclause list           # show the curated clause library
"""
from __future__ import annotations

from .scanner import (
    HIGH, MED, LOW, RISK_LEVELS, CLAUSE_LIBRARY,
    ScanResult, ClauseHit,
    scan_line, scan_text, scan_file, scan_paths, build_result,
)
from .reporter import to_json, to_markdown, to_text, format_hits
from .config import DEFAULT_CONFIG, MAX_FILE_BYTES

__version__ = "1.0.0"

__all__ = [
    "__version__",
    # config
    "DEFAULT_CONFIG", "MAX_FILE_BYTES",
    # scanner
    "HIGH", "MED", "LOW", "RISK_LEVELS", "CLAUSE_LIBRARY",
    "ScanResult", "ClauseHit",
    "scan_line", "scan_text", "scan_file",
    "scan_paths", "build_result",
    # reporter
    "to_json", "to_markdown", "to_text", "format_hits",
]
