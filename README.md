# legal-clause-finder

> Flag risky contract clauses via a curated keyword / regex heuristic scan.

A **free-stack, zero-API-key** contract scanner from the
[20 free-stack agentic AI projects](https://github.com/prem-the-dev) program.
It walks contract text — a single `--file`/`scan <path>` argument, or a
directory tree of `.txt` / `.md` files — and flags risky clauses using a
curated library of regex patterns grouped by category, labelling each
`HIGH` / `MED` / `LOW` with `file:line`, a snippet, and surrounding context.

Runs with **no LLM API keys, no paid services, and no third-party
dependencies** — pure Python 3 standard library.  Designed to slot into
CI pipelines (exits non-zero when `HIGH` risk clauses are present) and to
compose with other agents via stable JSON output.

## Install

```bash
pip install -e .
```

## Usage

```bash
# Scan a single contract (human-readable text to stdout)
legal-clause-finder scan contract.txt

# Scan a directory tree recursively, emit JSON to a file
legal-clause-finder scan contracts/ --format json --out report.json

# Markdown report
legal-clause-finder scan contracts/ --format markdown --out report.md

# Quiet: print a one-line JSON summary (good for shell composition)
legal-clause-finder scan contracts/ --quiet

# Show the curated clause library
legal-clause-finder list

# Version
legal-clause-finder --version
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Scan completed, no `HIGH` risk clauses (or zero clauses at all). |
| `1`  | Scan completed, but one or more `HIGH` risk clauses found (CI fail). |
| `2`  | Usage error (no path / bad arguments). |

## Risk levels

| Level | Meaning |
|-------|---------|
| `HIGH` | Serious contractual hazard — indemnification, perpetual license, termination without cause, work-made-for-hire. |
| `MED`  | Worth reviewing with counsel — non-refundable, auto-renewal, sole discretion, arbitration. |
| `LOW`  | Informational — governing law, confidentiality, evergreen. |

## Clause library

The library ships with ~26 rules across 7 categories.  See
`legalclause/scanner.py` → `CLAUSE_LIBRARY` to add, remove, or retune rules.
Each rule is a `(category, label, regex, risk)` tuple; patterns are compiled
once (case-insensitive) and use only bounded character classes — no nested
quantifiers or backreferences — so they cannot exhibit catastrophic
backtracking on adversarial input.

```bash
legal-clause-finder list --format json   # machine-readable library
```

## Output formats

* `text`  — terminal-friendly prose (default)
* `markdown` (`md`) — GitHub-flavoured Markdown report with tables
* `json` — stable machine-readable `ScanResult` dict

## Tests

All tests are **offline** (no network, no mocks — real temp files on disk):

```bash
python -m pytest tests/ -q
# or per the project convention:
python tests/test_legal-clause-finder.py
```

Covers: clause-library integrity, line matching, case-insensitivity,
multi-hit lines, deduplication, multi-file/directory scans, recursion,
symlink/duplicate handling, file-size caps, skipped suffixes, ranking,
JSON/Markdown/text rendering, and a static source audit asserting
`no shell=True / no os.system / no eval / no subprocess`.

## Architecture

```
legalclause/
  __init__.    package entry — version, re-exports, docstrings
  config.py    constants: MAX_FILE_BYTES, ALLOWED_SUFFIXES, ok() helper
  scanner.py   CLAUSE_LIBRARY + matching engine + ScanResult model
  reporter.py  JSON / Markdown / plain-text renderers
  cli.py       argparse front-end (scan / list / version)
  __main__.py  python -m legalclause entry point
tests/         stdlib unittest suite, offline fixtures
```

The scanner does a single linear pass per document line.  State (e.g.
per-run snapshots) is intentionally **not persisted** — this tool is a
stateless linter, not a daemon.  No `.legalclausefinder` state directory is
created by default.

## Security

See [SECURITY.md](SECURITY.md).  Highlights:

* Pure Python standard library — no third-party dependencies, no API keys,
  no network access, no subprocess invocation.
* `MAX_FILE_BYTES` (5 MB) cap prevents memory exhaustion from large files.
* Only `.txt` / `.md` / `.text` suffixes are scanned by default; paths are
  resolved and de-duplicated to prevent symlink/duplicate traversal.
* Regex patterns are bound (no nested quantifiers) — no ReDoS surface.
* No `shell=True`, `eval`, `exec`, `os.system`, or `pickle`.

## License

MIT © prem-the-dev
