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


def test_rust_ast_defect_verification(tmp_path):
    # Setup mock Rust project
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text('[package]\nname = "test_engine"\nversion = "0.1.0"\n')
    src_file = tmp_path / "src" / "store.rs"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("""pub struct DocsStore;
impl DocsStore {
    pub fn open() {
        // journal_mode = WAL, missing F_FULLFSYNC
    }
}
""")
    sandbox = ExecutionSandbox(tmp_path)
    verifier = BugVerifier(sandbox)

    # Real issue
    real_issue = Issue(
        id="RS-001",
        number=1111,
        title="[Bug]: Database corruption on hard reset / SQLite torn without F_FULLFSYNC in DocsStore",
        body="DocsStore::open corrupts database disk image on crash without fullfsync.",
        type=IssueType.BUG
    )
    res_real = verifier.verify(real_issue)
    assert res_real.verdict == VerdictStatus.VERIFIED_TRUE
    assert "store.rs" in res_real.verdict_headline
    assert res_real.evidence.adaptive_workflow == "RUST_AST_GROUNDED"

    # Fake issue (nonexistent symbol)
    fake_issue = Issue(
        id="RS-002",
        number=1112,
        title="[Bug]: Crash in QuantumSuperOptimizer",
        body="Nonexistent function fails.",
        type=IssueType.BUG
    )
    res_fake = verifier.verify(fake_issue)
    assert res_fake.verdict == VerdictStatus.FAKE_SLOP


def test_swift_ast_defect_verification(tmp_path):
    # Setup mock Swift project
    pkg = tmp_path / "Package.swift"
    pkg.write_text('// swift-tools-version:5.9\n')
    swift_file = tmp_path / "Sources" / "NowPlayingController.swift"
    swift_file.parent.mkdir(parents=True, exist_ok=True)
    swift_file.write_text("""public class NowPlayingController {
    public func terminateProcess() {}
}
""")
    sandbox = ExecutionSandbox(tmp_path)
    verifier = BugVerifier(sandbox)

    # Real issue
    real_issue = Issue(
        id="SW-001",
        number=1728,
        title="Child process leak: NowPlayingController child remains running",
        body="When app exits, NowPlayingController child process leaks.",
        type=IssueType.BUG
    )
    res_real = verifier.verify(real_issue)
    assert res_real.verdict == VerdictStatus.VERIFIED_TRUE
    assert "NowPlayingController.swift" in res_real.verdict_headline
    assert res_real.evidence.adaptive_workflow == "SWIFT_AST_GROUNDED"

    # Fake / ungrounded issue
    fake_issue = Issue(
        id="SW-002",
        number=913,
        title="[Bug] App is not macOS Tahoe ready",
        body="Shelf does not work on Tahoe 26.3 icon in icon jail.",
        type=IssueType.BUG
    )
    res_fake = verifier.verify(fake_issue)
    assert res_fake.verdict == VerdictStatus.FAKE_SLOP
    assert "No matching" in res_fake.verdict_headline


def test_adaptive_healing_on_synthetic_import_lapse(tmp_path):
    # Python repo where initial synthetic script imports a non-existent mock,
    # but the real codebase has the actual function
    py_file = tmp_path / "validator.py"
    py_file.write_text("""def validate_email(email: str) -> bool:
    if "@" not in email:
        raise ValueError("Invalid email format")
    return True
""")
    sandbox = ExecutionSandbox(tmp_path)
    verifier = BugVerifier(sandbox)

    issue = Issue(
        id="PY-001",
        number=55,
        title="Crash in validate_email on malformed input",
        body="Calling validate_email('bad_input') crashes with ValueError.",
        type=IssueType.BUG
    )
    # The default synthesizer might try to import something, but validate_email exists in validator.py
    res = verifier.verify(issue)
    # Grounding succeeds against validator.py
    assert res.verdict in [VerdictStatus.VERIFIED_TRUE, VerdictStatus.UNREPRODUCED]
    assert res.evidence is not None
