"""Offline security audit: assert no forbidden execution primitives in package source.

Run in CI:  python scripts/security_audit.py
Exit 0 = clean, 1 = findings.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "legalclause"

FORBIDDEN = [
    "shell=True", "os.system", "os.popen",
    "eval(", "exec(", "pickle.loads", "marshal.loads",
    "subprocess.run", "subprocess.call", "subprocess.Popen", "subprocess.check",
    "__import__", "yaml.load(", "input(", "execfile(",
]

findings: list[str] = []
for f in sorted(PKG.rglob("*.py")):
    text = f.read_text()
    for token in FORBIDDEN:
        if token in text:
            findings.append(f"{f.name}: contains forbidden '{token}'")

if findings:
    print("SECURITY AUDIT FAILED:")
    for x in findings:
        print("  - " + x)
    sys.exit(1)
print("security audit: OK — no forbidden execution primitives in package source")
sys.exit(0)
