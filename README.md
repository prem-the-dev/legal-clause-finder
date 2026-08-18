# legal-clause-finder

A heuristic scanner that flags potentially risky clauses in a contract
or terms-of-service document.

**Free-stack: zero API key.** Uses only the Python standard library
(`re`). No models, no accounts, no cost.

## What it does

- Reads a `.txt` or `.md` contract.
- Matches ~16 categories of commonly one-sided clauses (auto-renewal,
  unilateral termination, liability waivers, arbitration, class-action
  waivers, non-competes, IP assignment, no-refund, as-is warranties, …)
  using regex/keyword rules.
- Prints a plain-language risk report ranked by severity.
- Optionally writes a JSON report for downstream tooling.

> ⚠️ This is a heuristic aid, **not legal advice**. Have a human review
> flagged clauses.

## Usage

```bash
python clauses.py contract.txt
python clauses.py contract.txt --json report.json
python clauses.py contract.txt --min-risk high
```

## Example

```text
[HIGH  ] Liability waiver / no liability  (Liability)
           line 3: The Company shall not be liable for any damages...
[MEDIUM] Automatic renewal  (Termination)
           line 1: ...shall automatically renew for successive...
```

## License

MIT.
