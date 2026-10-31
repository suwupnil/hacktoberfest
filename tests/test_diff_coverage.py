"""Tests for Pull Request Diff-Coverage Verifier."""

from pathlib import Path
from claim_sentry.models import Issue, IssueType, VerdictStatus
from claim_sentry.sandbox import ExecutionSandbox
from claim_sentry.verifiers.diff_coverage_verifier import DiffCoverageVerifier


def test_untested_pr_detected():
    repo_dir = Path(__file__).resolve().parent.parent / "examples" / "target_repo"
    sandbox = ExecutionSandbox(repo_dir)
    verifier = DiffCoverageVerifier(sandbox)

    issue = Issue(
        id="PR-001",
        number=3,
        title="Fixes #120, adds tests for port parsing",
        body="Refactored port parsing and claims to add tests.",
        type=IssueType.PULL_REQUEST,
        pr_diff="""--- a/url_toolkit/parser.py
+++ b/url_toolkit/parser.py
@@ -38,6 +38,18 @@
+    # Custom port logic not covered by any test
+    if groups.get('port'):
+        port_val = int(groups['port'])
"""
    )

    verified = verifier.verify(issue)
    assert verified.verdict == VerdictStatus.UNTESTED_PR
    assert "! No test covers the change" in verified.verdict_headline
    assert verified.evidence.diff_coverage_pct == 0.0
    assert len(verified.evidence.uncovered_lines) > 0


def test_tested_pr_verified():
    repo_dir = Path(__file__).resolve().parent.parent / "examples" / "target_repo"
    sandbox = ExecutionSandbox(repo_dir)
    verifier = DiffCoverageVerifier(sandbox)

    issue = Issue(
        id="PR-002",
        number=4,
        title="Add schema validation with tests",
        body="Fully covered validation tests.",
        type=IssueType.PULL_REQUEST,
        pr_diff="""--- a/url_toolkit/validator.py
+++ b/url_toolkit/validator.py
@@ -1,5 +1,10 @@
+def is_valid_url(url: str) -> bool:
+    return True
--- a/tests/test_validator.py
+++ b/tests/test_validator.py
@@ -1,5 +1,10 @@
+def test_valid_urls():
+    assert is_valid_url('https://example.com') is True
"""
    )

    verified = verifier.verify(issue)
    assert verified.verdict == VerdictStatus.VERIFIED_TRUE
    assert "PR Verified" in verified.verdict_headline
    assert verified.evidence.diff_coverage_pct >= 80.0
