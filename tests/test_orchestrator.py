"""Tests for TriageOrchestrator."""

from triage.models import CommandResult, IssueInput, VerificationVerdict
from triage.orchestrator import TriageOrchestrator
from triage.runner import MockRunner


def test_orchestrator_handles_ui_issue():
    mock_runner = MockRunner()
    orchestrator = TriageOrchestrator(runner=mock_runner)
    ui_issue = IssueInput(
        repo_url="https://github.com/vercel/next.js",
        issue_title="Mobile navigation drawer cannot be dismissed by clicking backdrop",
        issue_body="Click on overlay backdrop has no effect on mobile viewport.",
    )
    report = orchestrator.run(ui_issue)
    assert report.is_ui is True
    assert report.decision.playwright_needed is True
    assert "Playwright" in report.decision.playwright_plan
    # Verify Playwright test script was written and executed on runner
    assert any("reproduce_ui.sh" in cmd["command"] for cmd in mock_runner.commands_run)
    assert any("reproduce_ui.sh" in path for path in mock_runner.files)
    md = report.to_markdown()
    assert "UI Issue Routing" in md
    assert "Playwright" in md


def test_orchestrator_handles_non_ui_issue_with_mock_runner():
    mock_runner = MockRunner()
    # Configure mock responses
    mock_runner.set_response("bash reproduce.sh", CommandResult(
        command="bash reproduce.sh",
        exit_code=42,
        stdout="",
        stderr="Reproduction confirmed: Caught std::out_of_range",
    ))

    orchestrator = TriageOrchestrator(runner=mock_runner)
    issue = IssueInput(
        repo_url="https://github.com/boostorg/boost",
        issue_title="boost::algorithm::unhex throws std::out_of_range on odd-length input",
        issue_body="Odd-length hex string causes out_of_range exception.",
    )
    report = orchestrator.run(issue)
    assert report.is_ui is False
    assert report.boilerplate_id in ("cpp-boost", "cpp-cmake")
    assert report.verdict == VerificationVerdict.CONFIRMED
    assert report.fix is not None
    assert report.fix.pseudo_code_or_plan != ""

    md = report.to_markdown()
    assert "## 1. Claims" in md
    assert "## 2. Evidence" in md
    assert "## 3. Verification" in md
    assert "## 4. Fix & Architectural Recommendations" in md
