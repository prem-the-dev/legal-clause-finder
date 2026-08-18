#!/usr/bin/env python3
"""legal-clause-finder — scan document text for risky contract clauses.

Free-stack: zero API key. Uses only the Python standard library
(regex). Flags potentially unfair / one-sided clauses by keyword and
pattern matching, then prints a plain-language risk report.

Usage:
    python clauses.py contract.txt
    python clauses.py contract.txt --json report.json
    python clauses.py contract.txt --min-risk high

The contract can be plain .txt or .md. Everything is heuristic and is
NOT legal advice — it merely surfaces clauses worth a human review.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import Pattern


@dataclass
class Finding:
    clause: str
    risk: str          # low | medium | high
    category: str
    snippet: str
    line: int


# Each rule: (friendly name, risk level, category, compiled regex)
RISK_RULES: list[tuple[str, str, str, Pattern[str]]] = [
    ("Automatic renewal", "medium", "Termination",
     re.compile(r"\b(auto(?:matically)?[- ]?renew|evergreen|renew(?:s|ed|al)? automatically)\b", re.I)),
    ("Unilateral termination", "high", "Termination",
     re.compile(r"\b(terminate|cancel)[^.]{0,80}?(at (?:our|its|the company'?s|sole) discretion|without (?:cause|notice)|any time)\b", re.I)),
    ("Liability waiver / no liability", "high", "Liability",
     re.compile(r"\b(not (?:be )?liable|no liability|limited liability|disclaim(?:s|ed)? all liability|in no event (?:shall|will))\b", re.I)),
    ("Indemnification", "medium", "Liability",
     re.compile(r"\b(indemnif(?:y|ies|ication)|hold harmless)\b", re.I)),
    ("Arbitration clause", "medium", "Disputes",
     re.compile(r"\b(bind(?:ing)? arbitration|arbitrate|waive.{0,40}right to (?:sue|jury trial|class action))\b", re.I)),
    ("Class action waiver", "high", "Disputes",
     re.compile(r"\b(waive.{0,40}class action|class action waiver|no class action)\b", re.I)),
    ("Non-compete", "medium", "Restrictive",
     re.compile(r"\b(non[- ]?compete|not (?:directly or indirectly )?compete|restricted from competing)\b", re.I)),
    ("Non-disparagement", "medium", "Restrictive",
     re.compile(r"\b(non[- ]?disparage|not (?:publicly )?disparage|disparagement)\b", re.I)),
    ("Exclusive remedy", "medium", "Liability",
     re.compile(r"\b(exclusive remedy|sole and exclusive remedy|only remedy)\b", re.I)),
    ("Fee / penalty escalation", "medium", "Financial",
     re.compile(r"\b(liquidated damages|late fee|penalty of|interest.{0,20}% per)\b", re.I)),
    ("Data / privacy grab", "high", "Privacy",
     re.compile(r"\b(unlimited (?:right|license) to (?:use|sell) .{0,40}data|sell .{0,30}(?:your|the user'?s) data|perpetual.{0,30}license)\b", re.I)),
    ("Governing law / jurisdiction", "low", "Disputes",
     re.compile(r"\b(governed by (?:the )?laws of|jurisdiction of the courts of)\b", re.I)),
    ("Price change at will", "high", "Financial",
     re.compile(r"\b(change (?:the )?price|modify fees|increase (?:the )?fees|adjust prices?).{0,60}(at (?:our|its|sole) discretion|any time|without (?:notice|cause))\b", re.I)),
    ("Assignment of IP", "high", "IP",
     re.compile(r"\b(assign(?:s|ed|ment)? (?:all|any) (?:right|title|interest) in|ownership of .{0,30}(?:work product|deliverables) (?:shall|will) (?:vest|be)).{0,40}(to (?:us|the company|client))\b", re.I)),
    ("No refund", "medium", "Financial",
     re.compile(r"\b(no (?:refunds?|return of fees)|non[- ]?refundable|all sales (?:are )?final)\b", re.I)),
    ("Waiver of warranties", "high", "Liability",
     re.compile(r"\b(as[- ]?is|disclaim(?:s|ed)? (?:all )?warranties|without warranty|warranty (?:is )?(?:disclaimed|excluded))\b", re.I)),
]


def scan(text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    for name, risk, category, pattern in RISK_RULES:
        for idx, line in enumerate(lines, start=1):
            if pattern.search(line):
                snippet = line.strip()[:160]
                findings.append(Finding(name, risk, category, snippet, idx))
    # De-duplicate identical (clause, snippet) pairs while keeping order.
    seen = set()
    unique: list[Finding] = []
    for f in findings:
        key = (f.clause, f.snippet)
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    return unique


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a contract for risky clauses.")
    parser.add_argument("contract", help="Path to the contract text (.txt or .md).")
    parser.add_argument("--json", default=None, help="Also write the report to this JSON path.")
    parser.add_argument("--min-risk", choices=["low", "medium", "high"], default="low",
                        help="Hide findings below this risk level (default low).")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.contract):
        print(f"error: contract file not found: {args.contract}", file=sys.stderr)
        return 2

    with open(args.contract, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    findings = scan(text)
    min_level = RISK_ORDER[args.min_risk]
    findings = [f for f in findings if RISK_ORDER[f.risk] >= min_level]
    findings.sort(key=lambda f: (-RISK_ORDER[f.risk], f.line))

    print("=" * 64)
    print(" legal-clause-finder — risk report")
    print("=" * 64)
    if not findings:
        print(" No risky clauses matched the configured rules.")
    else:
        counts = {"high": 0, "medium": 0, "low": 0}
        for f in findings:
            counts[f.risk] += 1
            print(f"[{f.risk.upper():>6}] {f.clause}  ({f.category})")
            print(f"           line {f.line}: {f.snippet}")
        print("-" * 64)
        print(f" high={counts['high']}  medium={counts['medium']}  low={counts['low']}")
    print("=" * 64)
    print(" NOTE: heuristic scan only. Not legal advice.")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump([asdict(f) for f in findings], fh, indent=2)
        print(f"Wrote report to {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
