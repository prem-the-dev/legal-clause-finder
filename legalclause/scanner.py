"""Scanner: the curated clause library + matching engine.

The clause library is the core intellectual asset of this tool.  Each
rule is a tuple of (category, label, regex, risk_level) where:

  * ``category`` groups related clauses (e.g. "Liability & indemnity")
  * ``label``   short human name for the clause type
  * ``regex``   compiled once, anchored to the start of the pattern via
                ``re.compile`` with ``re.I``.  Patterns are intentionally
                word/substring oriented — no nested quantifiers or
                backreferences — so they cannot exhibit catastrophic
                backtracking on adversarial input.
  * ``risk_level`` is one of HIGH / MED / LOW.

Risk ranking order (HIGH is most severe):
  HIGH > MED > LOW
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import ALLOWED_SUFFIXES  # noqa: E402  (config has no back-import)

# ── Risk levels ───────────────────────────────────────────────────────
HIGH = "HIGH"
MED = "MED"
LOW = "LOW"
RISK_LEVELS = (HIGH, MED, LOW)
_RISK_RANK = {HIGH: 0, MED: 1, LOW: 2}

# ── Clause library ────────────────────────────────────────────────────
# (category, label, regex_pattern, risk_level)
CLAUSE_LIBRARY: list[tuple[str, str, str, str]] = [
    # ── Liability & indemnity ──
    ("Liability & indemnity", "Indemnification",
     r"\bindemnif(?:y|ies|ied|ying)\b", HIGH),
    ("Liability & indemnity", "Hold harmless",
     r"\bhold(?:ing|\s+)?harmless\b", MED),
    ("Liability & indemnity", "Limitation of liability",
     r"\blimit(?:ation|ed)?\s+of\s+liability\b", MED),
    ("Liability & indemnity", "Unlimited / uncapped liability",
     r"\bwithout\s+limitation\b", MED),

    # ── Termination rights ──
    ("Termination", "Termination without cause / notice",
     r"\bterminate\s+without\s+(?:cause|notice)\b", HIGH),
    ("Termination", "Termination for convenience",
     r"\btermination\s+for\s+convenience\b", MED),
    ("Termination", "Immediate termination",
     r"\binner\s+terminat(?:e|ion)\b", MED),

    # ── IP rights ──
    ("Intellectual property", "Perpetual license",
     r"\bperp(?:etual|etually)\b", HIGH),
    ("Intellectual property", "Exclusive license",
     r"\bexclusivity\b", MED),
    ("Intellectual property", "Work made for hire",
     r"\bwork\s+made\s+for\s+hire\b", HIGH),
    ("Intellectual property", "Assignment of IP",
     r"\bassign(?:ment|ed|s)?\s+all\s+(?:rights|ip|intellectual)\b", MED),

    # ── Renewal & billing ──
    ("Renewal & billing", "Auto-renewal",
     r"\b(?:auto|automatic)[- ]?renew(?:al)?\b", MED),
    ("Renewal & billing", "Non-refundable",
     r"\bnon-?refundable\b", MED),
    ("Renewal & billing", "Evergreen clause",
     r"\bevergreen\b", LOW),
    ("Renewal & billing", "Material breach / automatic termination",
     r"\bmaterial\s+breach\b", MED),

    # ── Dispute resolution ──
    ("Dispute resolution", "Class action waiver",
     r"\bclass[\s-]+action\s+waiver\b", MED),
    ("Dispute resolution", "Arbitration clause",
     r"\barbitrat(?:e|ion)\b", MED),
    ("Dispute resolution", "Waiver of rights",
     r"\bwaiv(?:e|al|es|en)\s+(?:rights|claims|defences?)\b", MED),
    ("Dispute resolution", "Forum selection",
     r"\bforum\s+(?:selection\s+)?(?:provision|clause)\b", LOW),
    ("Dispute resolution", "Governing law (jurisdiction)",
     r"\bgoverning\s+law\b", LOW),

    # ── Confidentiality ──
    ("Confidentiality", "Confidentiality / NDA survival",
     r"\bconfidential(?:ity)?\b", LOW),

    # ── Miscellaneous risky ──
    ("Miscellaneous", "Sole discretion",
     r"\bsole\s+discretion\b", MED),
    ("Miscellaneous", "Right to change / modify unilaterally",
     r"\bright\s+to\s+(?:change|modif(?:y|ication))\b", MED),
    ("Miscellaneous", "No warranty / as is",
     r"\b(?:as[\s-]+is|without\s+warranty)\b", MED),
    ("Miscellaneous", "No solicitation restriction",
     r"\bnosolf[eo]?\b|no.?soli?\b", LOW),
    ("Miscellaneous", "Jurisdiction clawback",
     r"\bjurisdiction\b", LOW),
]

# Pre-compile patterns once (case-insensitive).  Patterns avoid nested
# quantifiers / backreferences to guarantee linear matching behaviour.
_COMPILED: list[tuple[str, str, "re.Pattern[str]", str]] = [
    (cat, label, re.compile(pat, re.IGNORECASE), risk)
    for (cat, label, pat, risk) in CLAUSE_LIBRARY
]


# ── Data model ─────────────────────────────────────────────────────────
@dataclass
class ClauseHit:
    """One matched clause in a document."""
    rule_category: str
    rule_label: str
    risk: str
    line: int
    col: int
    snippet: str
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "category": self.rule_category,
            "label": self.rule_label,
            "risk": self.risk,
            "line": self.line,
            "col": self.col,
            "snippet": self.snippet,
            "context": self.context,
        }


@dataclass
class ScanResult:
    """Aggregated result of scanning one or more files."""
    files_scanned: int = 0
    files_skipped: int = 0
    skipped_reasons: list[str] = field(default_factory=list)
    hits: list[ClauseHit] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_hits(self) -> int:
        return len(self.hits)

    @property
    def high(self) -> int:
        return sum(1 for h in self.hits if h.risk == HIGH)

    @property
    def med(self) -> int:
        return sum(1 for h in self.hits if h.risk == MED)

    @property
    def low(self) -> int:
        return sum(1 for h in self.hits if h.risk == LOW)

    def ranked(self) -> list[ClauseHit]:
        return sorted(self.hits, key=lambda h: _RISK_RANK.get(h.risk, 99))

    def to_dict(self) -> dict:
        return {
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "skipped_reasons": self.skipped_reasons,
            "hits": [h.to_dict() for h in self.ranked()],
            "high": self.high,
            "med": self.med,
            "low": self.low,
            "total": self.total_hits,
            "errors": self.errors,
        }


# ── Matching engine ───────────────────────────────────────────────────
_SNIPPET_LEN = 160
_DEFAULT_MAX = 5 * 1024 * 1024


def _context(lines: list[str], line_no: int, window: int = 1) -> str:
    """Return surrounding context for a line (excluding the matched line)."""
    parts = []
    for i in range(max(0, line_no - 1 - window), line_no - 1):
        parts.append(lines[i].strip()[:80])
    for i in range(line_no, min(len(lines), line_no + window)):
        parts.append(lines[i].strip()[:80])
    return " | ".join(parts)


def scan_line(line: str, line_no: int) -> list[ClauseHit]:
    """Scan a single line of text, returning all matching ClauseHits.

    A single line may match multiple categories; all distinct matches are
    returned (deduplicated by label so one line doesn't double-count the
    same rule).  The first matching rule per category wins to avoid noise.
    """
    hits: list[ClauseHit] = []
    seen_labels: set[str] = set()
    for category, label, pattern, risk in _COMPILED:
        m = pattern.search(line)
        if not m:
            continue
        if label in seen_labels:
            continue
        seen_labels.add(label)
        start = m.start()
        col = len(line[:start].rstrip())  # 0-based column of match start
        snippet = line.strip()
        if len(snippet) > _SNIPPET_LEN:
            snippet = snippet[:_SNIPPET_LEN - 1] + "…"
        hits.append(ClauseHit(
            rule_category=category,
            rule_label=label,
            risk=risk,
            line=line_no,
            col=col,
            snippet=snippet,
        ))
    return hits


def scan_text(text: str) -> list[ClauseHit]:
    """Scan a block of text line by line."""
    hits: list[ClauseHit] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        hits.extend(scan_line(line, idx))
    return hits


# ── File / path scanning ──────────────────────────────────────────────
def _validate_file(path: Path, max_bytes: int, allowed_suffixes: tuple[str, ...]) -> str | None:
    """Return an error reason string if a file should be skipped, else None."""
    try:
        if not path.is_file():
            return f"not a regular file: {path}"
        if path.suffix.lower() not in allowed_suffixes:
            return f"suffix not allowed: {path.suffix}"
        size = path.stat().st_size
        if size > max_bytes:
            return f"file too large ({size} bytes > {max_bytes} limit): {path}"
        return None
    except OSError as e:
        return f"stat error ({path}): {e}"


def scan_file(path: Path, max_bytes: int = 0, allowed_suffixes: tuple[str, ...] = ALLOWED_SUFFIXES) -> list[ClauseHit]:
    """Scan a single file.  Raises nothing on read errors — returns []."""
    if max_bytes <= 0:
        max_bytes = _DEFAULT_MAX
    reason = _validate_file(path, max_bytes, allowed_suffixes)
    if reason:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    hits = scan_text(text)
    # Annotate context (post-scan, so we only pay the cost when needed)
    lines = text.splitlines()
    for h in hits:
        h.context = _context(lines, h.line)
    return hits


_DEFAULT_MAX = 5 * 1024 * 1024
from .config import DEFAULT_CONFIG  # noqa: E402  (avoids circular import)


def scan_paths(paths: list[Path], recursive: bool = True,
               max_bytes: int = _DEFAULT_MAX,
               allowed_suffixes: tuple[str, ...] | None = None) -> ScanResult:
    """Scan a collection of file or directory paths into a ScanResult.

    * Directories (when ``recursive``) are walked for allowed-suffix files.
    * Files that fail validation are counted as skipped with a reason.
    * A single file read error is recorded in ``errors`` without aborting.
    """
    result = ScanResult()
    seen_files: set[str] = set()
    if allowed_suffixes is None:
        allowed_suffixes = ALLOWED_SUFFIXES

    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files = sorted(p.rglob("*") if recursive else p.iterdir())
            files = [f for f in files if f.is_file()]
        elif p.is_file():
            files = [p]
        else:
            result.skipped_reasons.append(f"path not found: {p}")
            result.files_skipped += 1
            continue

        for f in files:
            key = str(f.resolve(strict=False))
            if key in seen_files:
                continue
            seen_files.add(key)
            reason = _validate_file(f, max_bytes, allowed_suffixes)
            if reason:
                result.files_skipped += 1
                result.skipped_reasons.append(reason)
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                result.errors.append(str(e))
                continue
            result.files_scanned += 1
            lines = text.splitlines()
            for idx, line in enumerate(lines, 1):
                for h in scan_line(line, idx):
                    h.context = _context(lines, h.line)
                    result.hits.append(h)

    return result


def build_result(hits: list[ClauseHit], files_scanned: int = 1,
                 files_skipped: int = 0,
                 skipped_reasons: list[str] | None = None) -> ScanResult:
    """Construct a ScanResult from already-computed hits."""
    return ScanResult(
        files_scanned=files_scanned,
        files_skipped=files_skipped,
        skipped_reasons=skipped_reasons or [],
        hits=hits,
    )


def list_clauses() -> list[dict]:
    """Return the clause library as a list of plain dicts (for CLI `list`)."""
    return [
        {"category": cat, "label": label, "pattern": pat, "risk": risk}
        for (cat, label, pat, risk) in CLAUSE_LIBRARY
    ]
