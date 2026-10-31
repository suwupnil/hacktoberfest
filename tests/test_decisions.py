"""Tests for Clef decisions model (UI classification & boilerplate selection)."""

from triage.decisions import DecisionEngine
from triage.models import IssueInput


def test_clef_identifies_ui_issue_and_playwright():
    engine = DecisionEngine()
    ui_issue = IssueInput(
        repo_url="https://github.com/vercel/next.js",
        issue_title="Navigation drawer backdrop click fails on mobile viewport",
        issue_body="Clicking the blurred modal backdrop overlay does not close drawer menu on viewport 375x667.",
    )
    decision = engine.evaluate(ui_issue)
    assert decision.is_ui is True
    assert decision.playwright_needed is True
    assert decision.playwright_plan is not None
    assert "Playwright" in decision.playwright_plan or "playwright" in decision.playwright_plan.lower()


def test_clef_identifies_non_ui_boost_issue():
    engine = DecisionEngine()
    boost_issue = IssueInput(
        repo_url="https://github.com/boostorg/boost",
        issue_title="boost::algorithm::unhex throws std::out_of_range on odd-length input",
        issue_body="Calling unhex with odd-length hex string throws out_of_range instead of hex_decode_error.",
    )
    decision = engine.evaluate(boost_issue)
    assert decision.is_ui is False
    assert decision.playwright_needed is False
    assert decision.recommended_boilerplate in ("cpp-boost", "cpp-cmake")


def test_clef_identifies_non_ui_python_issue():
    engine = DecisionEngine()
    python_issue = IssueInput(
        repo_url="https://github.com/psf/requests",
        issue_title="requests.utils.parse_dict_header corrupts dictionary on unquoted semicolons",
        issue_body="Header parser fails to split cookies with unquoted values.",
    )
    decision = engine.evaluate(python_issue)
    assert decision.is_ui is False
    assert decision.recommended_boilerplate == "python-pytest"
