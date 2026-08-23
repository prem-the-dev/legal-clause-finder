"""legal-clause-finder configuration & constants.

No third-party dependencies.  Everything here is deliberately simple,
serialisable, and free of secrets.
"""
from __future__ import annotations

from pathlib import Path

# ── Security / safety constants ─────────────────────────────────────
MAX_FILE_BYTES: int = 5 * 1024 * 1024  # refuse to scan files larger than 5 MB
ALLOWED_SUFFIXES: tuple[str, ...] = (".txt", ".md", ".text")

# ── Default config ────────────────────────────────────────────────────
DEFAULT_CONFIG: dict = {
    "max_file_bytes": MAX_FILE_BYTES,
    "allowed_suffixes": list(ALLOWED_SUFFIXES),
    # whether to recurse into subdirectories when given a directory input
    "recursive": True,
}

CONFIG_PATH = Path.home() / ".legalclausefinder" / "config.json"


def ok(msg: str) -> None:
    """Print a status line (package-level helper shared with siblings)."""
    print(f"[legalclause] {msg}")


def _resolve_base(path: Path) -> Path:
    """Resolve a path to its real absolute form (no symlink escape)."""
    return path.resolve(strict=False)
