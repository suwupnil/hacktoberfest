"""Tests for Bug Report Verifier."""

from pathlib import Path
from claim_sentry.models import Issue, IssueType, VerdictStatus
from claim_sentry.sandbox import ExecutionSandbox
from claim_sentry.verifiers.bug_verifier import BugVerifier


def test_reproduce_crash_on_long_urls():
    repo_dir = Path(__file__).resolve().parent.parent / "examples" / "target_repo"
    sandbox = ExecutionSandbox(repo_dir)
    verifier = BugVerifier(sandbox, repo_version="2.4.1")

    issue = Issue(
        id="TEST-001",
        number=1,
        title="Crash on long URLs exceeding 2048 characters",
        body="Calling parse_url with 2500 character payload crashes with ValueError.",
        type=IssueType.BUG
    )

    verified_issue = verifier.verify(issue)

    assert verified_issue.verdict == VerdictStatus.VERIFIED_TRUE
    assert "✓ Reproduced on 2.4.1" in verified_issue.verdict_headline
    assert verified_issue.evidence.exit_code != 0
    assert "ValueError" in verified_issue.evidence.stderr
    assert "exceeds maximum length of 2048 characters" in verified_issue.evidence.stderr
    assert verified_issue.evidence.network_bytes_sent == 0
    assert verified_issue.evidence.secrets_exposed_count == 0


def test_unreproduced_clean_issue():
    repo_dir = Path(__file__).resolve().parent.parent / "examples" / "target_repo"
    sandbox = ExecutionSandbox(repo_dir)
    verifier = BugVerifier(sandbox, repo_version="2.4.1")

    issue = Issue(
        id="TEST-002",
        number=2,
        title="Valid URL works fine",
        body="Parsing https://example.com/api should not crash.",
        type=IssueType.BUG
    )

    verified_issue = verifier.verify(issue)
    assert verified_issue.verdict == VerdictStatus.UNREPRODUCED
    assert "Failed to reproduce" in verified_issue.verdict_headline
    assert verified_issue.evidence.exit_code == 0


def test_js_ts_component_verification(tmp_path):
    # Setup mock TSX React structure
    comp_file = tmp_path / "ui" / "Combobox.tsx"
    comp_file.parent.mkdir(parents=True, exist_ok=True)
    comp_file.write_text("export const Combobox = (props: any) => <div>Combobox</div>;")
    
    test_file = tmp_path / "ui" / "Combobox.test.tsx"
    test_file.write_text("test('renders', () => {});")

    sandbox = ExecutionSandbox(tmp_path)
    verifier = BugVerifier(sandbox)

    # 1. Real component
    real_issue = Issue(
        id="TS-001",
        number=101,
        title="[BUG] maxHeight prop not working in Combobox",
        body="When using Combobox with maxHeight, styling is ignored.",
        type=IssueType.BUG
    )
    res_real = verifier.verify(real_issue)
    assert res_real.verdict == VerdictStatus.VERIFIED_TRUE
    assert "Combobox.tsx" in res_real.verdict_headline

    # 2. Fake component
    fake_issue = Issue(
        id="TS-002",
        number=102,
        title="[BUG] Crash in AlienSuperMatrixWidget",
        body="The AlienSuperMatrixWidget crashes with memory leak.",
        type=IssueType.BUG
    )
    res_fake = verifier.verify(fake_issue)
    assert res_fake.verdict == VerdictStatus.FAKE_SLOP
    assert "not found" in res_fake.verdict_headline
