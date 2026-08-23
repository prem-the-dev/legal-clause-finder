"""Reporters: render a ScanResult as JSON / Markdown / plain text."""
from __future__ import annotations

import json
from pathlib import Path

from .scanner import ScanResult, HIGH, MED, LOW


def to_json(result: ScanResult, indent: int = 2) -> str:
    """Serialize a ScanResult to a JSON string."""
    return json.dumps(result.to_dict(), indent=indent, default=str, ensure_ascii=False)


def to_markdown(result: ScanResult, title: str = "Contract Clause Scan Report") -> str:
    """Render a ScanResult as a GitHub-flavoured Markdown report."""
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Files scanned | {result.files_scanned} |")
    lines.append(f"| Files skipped | {result.files_skipped} |")
    lines.append(f"| Total hits | {result.total_hits} |")
    lines.append(f"| HIGH risk | {result.high} |")
    lines.append(f"| MED risk | {result.med} |")
    lines.append(f"| LOW risk | {result.low} |")
    lines.append("")

    # Risk summary colour
    emoji = {HIGH: "🔴", MED: "🟡", LOW: "🔵"}
    if result.total_hits == 0:
        lines.append("> No risky clauses detected. ✅")
        return "\n".join(lines)

    lines.append("## Summary by risk")
    lines.append("")
    lines.append("| Risk | Count |")
    lines.append("|---|---|")
    lines.append(f"| HIGH | {result.high} |")
    lines.append(f"| MED | {result.med} |")
    lines.append(f"| LOW | {result.low} |")
    lines.append("")

    # Table of hits grouped by category
    lines.append("## Findings")
    lines.append("")
    lines.append("| Risk | Line | Category | Clause | Snippet |")
    lines.append("|---|---|---|---|---|")
    for h in result.ranked():
        snip = h.snippet.replace("|", "\\|")
        if len(snip) > 60:
            snip = snip[:57] + "…"
        lines.append(
            f"| {emoji.get(h.risk, h.risk)} {h.risk} | {h.line} | "
            f"{h.rule_category} | {h.rule_label} | {snip} |"
        )
    lines.append("")

    # Detail section
    lines.append("## Detail")
    lines.append("")
    for h in result.ranked():
        lines.append(f"### {h.rule_category} — {h.rule_label} ({h.risk})")
        lines.append(f"- **Line {h.line}, col {h.col}**")
        lines.append(f"- {h.snippet}")
        if h.context:
            lines.append(f"- Context: {h.context}")
        lines.append("")
    return "\n".join(lines)


def to_text(result: ScanResult, title: str = "Contract Clause Scan Report") -> str:
    """Render a ScanResult as plain, terminal-friendly text."""
    lines: list[str] = []
    lines.append(title)
    lines.append("=" * len(title))
    lines.append(f"Files scanned: {result.files_scanned}")
    lines.append(f"Files skipped: {result.files_skipped}")
    lines.append(f"Total hits:    {result.total_hits}")
    lines.append(f"  HIGH: {result.high}")
    lines.append(f"  MED:  {result.med}")
    lines.append(f"  LOW:  {result.low}")
    lines.append("")
    if result.total_hits == 0:
        lines.append("No risky clauses detected. ✅")
        return "\n".join(lines)
    lines.append("Findings (ranked):")
    lines.append("-" * 60)
    for h in result.ranked():
        lines.append(f"[{h.risk}] L{h.line} | {h.rule_category} / {h.rule_label}")
        lines.append(f"  {h.snippet}")
        lines.append("")
    if result.skipped_reasons:
        lines.append("Skipped files:")
        for r in result.skipped_reasons:
            lines.append(f"  - {r}")
    if result.errors:
        lines.append("Errors:")
        for e in result.errors:
            lines.append(f"  - {e}")
    return "\n".join(lines)


def format_hits(result: ScanResult) -> str:
    """Convenience: plain-text rendering of just the hits."""
    out: list[str] = []
    if result.total_hits == 0:
        out.append("no risky clauses detected")
    for h in result.ranked():
        out.append(f"[{h.risk}] {h.rule_category}/{h.rule_label} @ line {h.line}: {h.snippet}")
    return "\n".join(out)


def write_report(result: ScanResult, fmt: str, path: str | Path | None) -> str:
    """Render and write a report.  Returns the rendered string.

    ``fmt`` is one of json / markdown / md / text / txt.
    If ``path`` is None, prints to stdout instead of writing a file.
    """
    fmt = (fmt or "text").lower()
    if fmt in ("md", "markdown"):
        body = to_markdown(result)
    elif fmt in ("json", "j"):
        body = to_json(result)
    elif fmt in ("text", "txt", "t"):
        body = to_text(result)
    else:
        raise ValueError(f"unknown format: {fmt!r} (use json|markdown|txt)")

    if path:
        Path(path).write_text(body, encoding="utf-8")
    else:
        print(body)
    return body
