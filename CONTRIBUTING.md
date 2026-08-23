# Contributing

Contributions welcome!  This project is part of the
[20 free-stack agentic AI projects](https://github.com/prem-the-dev) program —
everything here is **zero API key, pure Python stdlib, $0 to run**.

## Quick start

```bash
pip install -e .
python -m legalclause scan contract.txt            # text report
python -m legalclause scan contracts/ --format json --out report.json
python -m legalclause list                          # show the clause library
```

## Tests

All tests are **offline** (no network, no mocks — real temp files):

```bash
python -m pytest tests/ -q
# or per the project convention:
python tests/test_legal-clause-finder.py
```

## Architecture

```
legalclause/
  __init__.    package entry — version, re-exports
  config.py    constants: MAX_FILE_BYTES, ALLOWED_SUFFIXES, ok()
  scanner.py   CLAUSE_LIBRARY + matching engine + ScanResult model
  reporter.py  JSON / Markdown / plain-text renderers
  cli.py       argparse front-end (scan / list / version)
  __main__.py  python -m legalclause entry point
tests/         stdlib unittest suite, offline fixtures
```

## Adding a clause rule

Rules live in `legalclause/scanner.py` → `CLAUSE_LIBRARY`, as a tuple:

```python
("Category", "Label", r"\bregex\b", HIGH)   # HIGH / MED / LOW
```

Guidelines:

1. **Keep it bound.** Avoid nested quantifiers (`(a+)+`, `(a*)*`) and
   backreferences — they can cause catastrophic backtracking on adversarial
   input.  Prefer `\w`, `\b`, and optional single quantifiers.
2. **Compile-test.** Run `python -m pytest tests/ -q` after adding a rule;
   the test suite asserts every pattern compiles.
3. **Sort by risk.** Order matters for the `test_library_nonempty`-style
   integrity checks; HIGH first is preferred.

## Pull requests

- No secrets, tokens, or email addresses in commits (policy).
- All new logic needs offline tests (no network, no mocks).
- CI must be green before merge.
