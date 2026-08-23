# Changelog

All notable changes to this project are documented here.
Dates use the `2026-08-22` style.  See https://keepachangelog.com/.

## [1.0.0] — 2026-08-22
### Added
- Full Python CLI for scanning contract text for risky clauses.
- `scanner.py`: curated clause library of 26 regex rules across 7
  categories (Liability & indemnity, Termination, Intellectual property,
  Renewal & billing, Dispute resolution, Confidentiality, Miscellaneous),
  each labelled HIGH / MED / LOW.
- `ScanResult` aggregation model with per-risk counters, ranking, and
  `to_dict()` for stable JSON serialisation.
- `reporter.py`: three renderers — plain text, GitHub-Markdown, and JSON —
  plus a `--quiet` one-line JSON summary mode.
- `cli.py`: `scan`, `list`, and `version` subcommands with `--format`,
  `--out`, `--recursive`, `--suffixes`, `--max-bytes`, `--quiet` flags.
- `config.py`: `MAX_FILE_BYTES` (5 MB) and `ALLOWED_SUFFIXES` safety caps.
- Comprehensive offline test suite (37 assertions) covering matching,
  ranking, directory recursion, deduplication, file-size caps, output
  format rendering, and a static source audit.
- CI workflow, SECURITY.md, CHANGELOG.md, CONTRIBUTING.md, README.md.

### Security
- Pure standard library only — no third-party dependencies, no LLM,
  no API keys, no network, no subprocess invocation.
- All regex patterns are bound (no nested quantifiers/backreferences) —
  no regular-expression denial-of-service surface.
- File inputs validated: suffix allow-list, size cap, path de-duplication.
- No secrets or email addresses in repository content.
- CLI exits non-zero when HIGH-risk clauses are found, for CI gating.

## [0.1.0] — 2026-08-22
### Added
- Initial scaffold: single-file keyword scanner (replaced by the modular,
  production-grade scanner above).
