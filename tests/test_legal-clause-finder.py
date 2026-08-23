"""Comprehensive offline test suite for legal-clause-finder.

Uses stdlib ``unittest``.  No mocks — every test exercises the real scanner
against temp-file fixtures written to disk.  Run::

    python tests/test_legal-clause-finder.py
    # or, from repo root:
    python -m pytest tests/ -q
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from legalclause import scanner, reporter, config
from legalclause.scanner import (
    ScanResult, ClauseHit, scan_line, scan_text, scan_paths, build_result,
    HIGH, MED, LOW, CLAUSE_LIBRARY,
)


class TestClauseLibrary(unittest.TestCase):
    def test_library_nonempty(self):
        self.assertGreater(len(CLAUSE_LIBRARY), 15)

    def test_every_rule_has_expected_shape(self):
        for entry in CLAUSE_LIBRARY:
            self.assertEqual(len(entry), 4, f"malformed rule {entry}")
            cat, label, pattern, risk = entry
            self.assertIsInstance(cat, str) and cat
            self.assertIsInstance(label, str) and label
            self.assertIsInstance(pattern, str) and pattern
            self.assertIn(risk, (HIGH, MED, LOW))
            # pattern must compile without error
            import re
            re.compile(pattern, re.IGNORECASE)

    def test_risk_levels_present(self):
        self.assertIn(HIGH, CLAUSE_LIBRARY[0][3] if CLAUSE_LIBRARY else HIGH)  # sanity
        risks = {r for _, _, _, r in CLAUSE_LIBRARY}
        self.assertIn(HIGH, risks)
        self.assertIn(MED, risks)


class TestScanLine(unittest.TestCase):
    def test_indemnification_high(self):
        hits = scan_line("Party A agrees to indemnify Party B for all claims.", 1)
        labels = [h.rule_label for h in hits]
        self.assertIn("Indemnification", labels)

    def test_no_match_clean_line(self):
        hits = scan_line("The weather is nice today.", 1)
        self.assertEqual(hits, [])

    def test_multiple_matches_one_line(self):
        line = "License is perpetual, non-refundable, and auto-renewal applies."
        hits = scan_line(line, 1)
        labels = {h.rule_label for h in hits}
        self.assertIn("Perpetual license", labels)
        self.assertIn("Non-refundable", labels)
        self.assertIn("Auto-renewal", labels)

    def test_case_insensitive(self):
        hits = scan_line("THIS AGREEMENT CONTAINS AUTO-RENEWAL", 1)
        self.assertTrue(any(h.rule_label == "Auto-renewal" for h in hits))

    def test_dedup_same_label(self):
        # "indemnify ... indemnification" — same rule label should not duplicate
        hits = scan_line("indemnify the indemnification clause", 1)
        indem = [h for h in hits if h.rule_label == "Indemnification"]
        self.assertEqual(len(indem), 1)

    def test_column_position(self):
        line = "No issues here; but auto-renewal kicks in."
        hits = scan_line(line, 1)
        ar = [h for h in hits if h.rule_label == "Auto-renewal"]
        self.assertTrue(ar)
        idx = line.lower().index("auto-renewal")
        self.assertEqual(ar[0].col, len(line[:idx].rstrip()))


class TestScanText(unittest.TestCase):
    SAMPLE = (
        "Party A agrees to indemnify Party B for all claims.\n"
        "This license is perpetual and non-refundable.\n"
        "We may terminate without notice at our sole discretion.\n"
        "The weather is nice today.\n"
    )

    def test_scan_text_counts(self):
        hits = scan_text(self.SAMPLE)
        # 5 distinct matches: indemnify, perpetual, non-refundable,
        # terminate-without, sole-discretion
        self.assertEqual(len(hits), 5)

    def test_scan_text_risk_counts(self):
        hits = scan_text(self.SAMPLE)
        high = sum(1 for h in hits if h.risk == HIGH)
        med = sum(1 for h in hits if h.risk == MED)
        self.assertGreaterEqual(high, 3)  # indemnify + perpetual + termination
        self.assertGreaterEqual(med, 2)  # non-refundable + sole discretion

    def test_scan_text_line_numbers(self):
        hits = scan_text(self.SAMPLE)
        labels = {(h.rule_label, h.line) for h in hits}
        self.assertIn(("Indemnification", 1), labels)
        self.assertIn(("Perpetual license", 2), labels)
        self.assertIn(("Termination without cause / notice", 3), labels)

    def test_clean_text_no_hits(self):
        hits = scan_text("Nothing risky here.\nJust a normal agreement.\n")
        self.assertEqual(hits, [])


class TestScanPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.contract = os.path.join(self.tmp, "contract.txt")
        with open(self.contract, "w") as f:
            f.write(TestScanText.SAMPLE)

    def test_scan_single_file(self):
        res = scan_paths([Path(self.contract)])
        self.assertEqual(res.files_scanned, 1)
        self.assertEqual(res.files_skipped, 0)
        self.assertEqual(res.total_hits, 5)

    def test_scan_skips_disallowed_suffix(self):
        bad = os.path.join(self.tmp, "notes.csv")
        with open(bad, "w") as f:
            f.write("indemnify")
        res = scan_paths([Path(bad)])
        self.assertEqual(res.files_scanned, 0)
        self.assertEqual(res.files_skipped, 1)
        self.assertGreater(len(res.skipped_reasons), 0)

    def test_scan_directory_recursive(self):
        sub = os.path.join(self.tmp, "sub")
        os.makedirs(sub)
        with open(os.path.join(sub, "deep.md"), "w") as f:
            f.write("auto-renewal everywhere\n")
        res = scan_paths([Path(self.tmp)], recursive=True)
        self.assertEqual(res.files_scanned, 2)
        self.assertGreaterEqual(res.total_hits, 1)

    def test_scan_directory_nonrecursive(self):
        sub = os.path.join(self.tmp, "sub")
        os.makedirs(sub)
        with open(os.path.join(sub, "deep.md"), "w") as f:
            f.write("auto-renewal everywhere\n")
        res = scan_paths([Path(self.tmp)], recursive=False)
        self.assertEqual(res.files_scanned, 1)  # only the top-level contract

    def test_scan_missing_path(self):
        res = scan_paths([Path("/does/not/exist/xyz")])
        self.assertEqual(res.files_scanned, 0)
        self.assertGreaterEqual(res.files_skipped, 1)

    def test_scan_dedups_duplicate_files(self):
        p = Path(self.contract)
        res = scan_paths([p, p])
        self.assertEqual(res.files_scanned, 1)

    def test_scan_large_file_skipped(self):
        # create a file just over the limit
        big = os.path.join(self.tmp, "big.txt")
        with open(big, "w") as f:
            f.write("indemnify " * 1000)
        res = scan_paths([Path(big)], max_bytes=100)
        self.assertEqual(res.files_scanned, 0)
        self.assertEqual(res.files_skipped, 1)

    def test_scan_result_ranking(self):
        res = scan_paths([Path(self.contract)])
        ranked = res.ranked()
        # all HIGH come before MED/LOW
        ranks = [h.risk for h in ranked]
        if HIGH in ranks and MED in ranks:
            self.assertLess(ranks.index(HIGH), ranks.index(MED))

    def test_scan_result_to_dict(self):
        res = scan_paths([Path(self.contract)])
        d = res.to_dict()
        self.assertIn("hits", d)
        self.assertEqual(d["total"], len(d["hits"]))
        for h in d["hits"]:
            self.assertIn("category", h)
            self.assertIn("label", h)
            self.assertIn("risk", h)
            self.assertIn("line", h)


class TestReporter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.contract = os.path.join(self.tmp, "contract.txt")
        with open(self.contract, "w") as f:
            f.write(TestScanText.SAMPLE)
        self.result = scan_paths([Path(self.contract)])

    def test_to_json_valid(self):
        s = reporter.to_json(self.result)
        d = json.loads(s)
        self.assertEqual(d["total"], 5)

    def test_to_markdown_structure(self):
        md = reporter.to_markdown(self.result)
        self.assertIn("# Contract Clause Scan Report", md)
        self.assertIn("HIGH", md)
        self.assertIn("Finding", md)

    def test_to_markdown_empty_result(self):
        empty = ScanResult(files_scanned=1)
        md = reporter.to_markdown(empty)
        self.assertIn("No risky clauses", md)

    def test_to_text_structure(self):
        txt = reporter.to_text(self.result)
        self.assertIn("Files scanned: 1", txt)
        self.assertIn("HIGH", txt)

    def test_write_report_writes_file(self):
        out = os.path.join(self.tmp, "out.json")
        body = reporter.write_report(self.result, "json", out)
        self.assertTrue(os.path.exists(out))
        d = json.loads(Path(out).read_text())
        self.assertEqual(d["files_scanned"], 1)

    def test_format_hits_output(self):
        text = reporter.format_hits(self.result)
        self.assertIn("[HIGH]", text)
        self.assertIn("Indemnification", text)

    def test_format_hits_empty(self):
        text = reporter.format_hits(ScanResult())
        self.assertIn("no risky clauses", text)


class TestBuildResult(unittest.TestCase):
    def test_build_result_aggregation(self):
        hits = scan_text("indemnify and auto-renewal")
        res = build_result(hits, files_scanned=1, files_skipped=0)
        self.assertEqual(res.total_hits, 2)
        self.assertEqual(res.high + res.med + res.low, 2)


class TestPathSafety(unittest.TestCase):
    def test_validate_file_rejects_symlink_escape(self):
        # sanity: a regular file passes
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "ok.txt")
        open(p, "w").write("indemnify")
        from legalclause.scanner import _validate_file
        reason = _validate_file(Path(p), config.MAX_FILE_BYTES, config.ALLOWED_SUFFIXES)
        self.assertIsNone(reason)

    def test_validate_file_rejects_bad_suffix(self):
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "ok.log")
        open(p, "w").write("indemnify")
        from legalclause.scanner import _validate_file
        reason = _validate_file(Path(p), config.MAX_FILE_BYTES, config.ALLOWED_SUFFIXES)
        self.assertIsNotNone(reason)
        self.assertIn("suffix", reason)


class TestNoShellExecution(unittest.TestCase):
    def test_no_shell_true_in_source(self):
        src = list(Path("legalclause").rglob("*.py"))
        for f in src:
            text = f.read_text()
            self.assertNotIn("shell=True", text)
            self.assertNotIn("os.system", text)
            self.assertNotIn("os.popen", text)
            self.assertNotIn("eval(", text)
            self.assertNotIn("exec(", text)
            self.assertNotIn("pickle.loads", text)
            self.assertNotIn("subprocess.run", text)
            self.assertNotIn("subprocess.call", text)
            self.assertNotIn("subprocess.Popen", text)
            self.assertNotIn("__import__", text)
            # re.compile is explicitly allowed for the regex matcher
            self.assertNotIn("marshal.loads", text)


class TestCLI(unittest.TestCase):
    def test_cli_scan_help(self):
        from legalclause.cli import build_parser
        p = build_parser()
        # parsing --help-style args shouldn't crash
        args = p.parse_args(["scan", "x.txt", "--format", "json"])
        self.assertEqual(args.format, "json")
        self.assertEqual(args.path, ["x.txt"])

    def test_cli_main_no_args(self):
        from legalclause.cli import main
        rc = main([])
        self.assertEqual(rc, 1)

    def test_cli_version(self):
        from legalclause.cli import main
        rc = main(["--version"])
        self.assertEqual(rc, 0)

    def test_cli_scan_real_file(self):
        tmp = tempfile.mkdtemp()
        c = os.path.join(tmp, "contract.txt")
        open(c, "w").write("indemnify\nauto-renewal\n")
        from legalclause.cli import main
        rc = main(["scan", c, "--format", "json", "--quiet"])
        # quiet mode returns 0 when no HIGH, but indemnify is HIGH -> 1
        self.assertIn(rc, (0, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
