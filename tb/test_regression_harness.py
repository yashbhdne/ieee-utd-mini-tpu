"""Tests for the regression harness's pass/failure acceptance rules."""
import subprocess
import unittest
import contextlib
import io
from unittest.mock import patch

import test_shared
from test_shared import negative_ok, positive_ok


class VerdictTests(unittest.TestCase):
    def result(self, code=0, stdout="", stderr=""):
        return subprocess.CompletedProcess([], code, stdout, stderr)

    def test_positive_requires_clean_exit_and_exact_pass_line(self):
        self.assertTrue(positive_ok(self.result(stdout="cover x = 1\nPASS\n")))
        self.assertFalse(positive_ok(self.result(stdout="NOT PASS\n")))
        self.assertFalse(positive_ok(self.result(1, "PASS\n")))
        self.assertFalse(positive_ok(self.result(stdout="SKIP: stub\nPASS\n")))

    def test_negative_requires_both_failure_and_specific_diagnostic(self):
        self.assertTrue(negative_ok(self.result(1, stderr="bad BRESP 10"), "bad BRESP"))
        self.assertFalse(negative_ok(self.result(stdout="bad BRESP"), "bad BRESP"))
        self.assertFalse(negative_ok(self.result(1, stderr="watchdog"), "bad BRESP"))

    def test_excluded_binary_is_not_executed_and_suite_stays_incomplete(self):
        with patch.object(test_shared, "TAGS", ["blocked"]), \
             patch.object(test_shared, "CASES", []), \
             patch.object(test_shared, "run") as execute, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            verdict = test_shared.main(["--skip-build", "--exclude-tag", "blocked"])
        execute.assert_not_called()
        self.assertNotEqual(verdict, 0)
        self.assertIn("0 passed, 3 not run", output.getvalue())


if __name__ == "__main__":
    unittest.main()
