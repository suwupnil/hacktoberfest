"""Tests for Main Agent (SWE reasoning, reproduction, verification, and fix generation)."""

from triage.agent import MainAgent
from triage.boilerplates import get_boilerplate
from triage.models import (
    CommandResult,
    IssueInput,
    ReproductionPlan,
    VerificationVerdict,
)
from triage.runner import MockRunner


def test_main_agent_plan_reproduction():
    agent = MainAgent()
    bp = get_boilerplate("cpp-boost")
    assert bp is not None

    issue = IssueInput(
        repo_url="https://github.com/boostorg/boost",
        issue_title="boost::algorithm::unhex throws std::out_of_range on odd-length input",
        issue_body="Calling unhex with odd length string throws out_of_range.",
    )
    plan = agent.plan_reproduction(issue, bp)
    assert plan.steps_description != ""
    assert plan.reproduction_script != ""
    assert "test_repro" in plan.reproduction_script or "bash" in plan.reproduction_script


def test_main_agent_classify_confirmed():
    agent = MainAgent()
    issue = IssueInput(
        repo_url="https://github.com/boostorg/boost",
        issue_title="boost::algorithm::unhex throws std::out_of_range",
        issue_body="Calling unhex with odd length throws out_of_range.",
    )
    plan = ReproductionPlan(
        steps_description="Run odd-length test",
        reproduction_script="./test_repro",
        expected_error_or_behavior="Throws out_of_range",
    )
    exec_res = CommandResult(
        command="./test_repro",
        exit_code=42,
        stdout="",
        stderr="Reproduction confirmed: Caught std::out_of_range: odd length input accessed out of range",
    )
    verification = agent.verify_reproduction(issue, plan, exec_res)
    assert verification.verdict == VerificationVerdict.CONFIRMED
    assert len(verification.extracted_claims) > 0
    assert len(verification.evidence) > 0


def test_main_agent_classify_invalid():
    agent = MainAgent()
    issue = IssueInput(
        repo_url="https://github.com/psf/requests",
        issue_title="requests.teleport() causes quantum entanglement crash",
        issue_body="Calling requests.teleport() causes segfault.",
    )
    plan = ReproductionPlan(
        steps_description="Test teleport",
        reproduction_script="python3 -c 'import requests; requests.teleport()'",
        expected_error_or_behavior="Module has no teleport",
    )
    exec_res = CommandResult(
        command="python3 -c 'import requests; requests.teleport()'",
        exit_code=1,
        stdout="",
        stderr="AttributeError: module 'requests' has no attribute 'teleport'",
    )
    verification = agent.verify_reproduction(issue, plan, exec_res)
    assert verification.verdict == VerificationVerdict.INVALID


def test_main_agent_classify_cannot_reproduce():
    agent = MainAgent()
    issue = IssueInput(
        repo_url="https://github.com/example/repo",
        issue_title="Intermittent race condition in worker loop",
        issue_body="Random crash every 1000 requests.",
    )
    plan = ReproductionPlan(
        steps_description="Run 100 requests",
        reproduction_script="python3 -c 'exit(0)'",
        expected_error_or_behavior="Crash",
    )
    exec_res = CommandResult(
        command="python3 -c 'exit(0)'",
        exit_code=0,
        stdout="All tests passed",
        stderr="",
    )
    verification = agent.verify_reproduction(issue, plan, exec_res)
    assert verification.verdict == VerificationVerdict.CANNOT_REPRODUCE


def test_main_agent_fix_and_architecture():
    agent = MainAgent()
    runner = MockRunner()
    # Mock reproduce.sh exiting with 0 after fix is applied
    runner.set_response("bash reproduce.sh", CommandResult(
        command="bash reproduce.sh",
        exit_code=0,
        stdout="Domain exception hex_decode_error caught successfully",
        stderr="",
    ))

    issue = IssueInput(
        repo_url="https://github.com/boostorg/boost",
        issue_title="boost::algorithm::unhex throws std::out_of_range",
        issue_body="Odd-length hex string throws out_of_range.",
    )
    verification = agent.verify_reproduction(
        issue,
        ReproductionPlan(steps_description="", reproduction_script="", expected_error_or_behavior=""),
        CommandResult(command="", exit_code=42, stdout="", stderr="std::out_of_range"),
    )
    fix_res = agent.formulate_fix_and_architecture(issue, verification, runner, "/tmp/test_dir")
    assert fix_res.pseudo_code_or_plan != ""
    assert fix_res.architectural_notes != ""
    assert fix_res.maintainer_comment != ""
    if fix_res.fix_applied:
        assert fix_res.fixed is True


def test_flexible_input_keys_and_leading_slash():
    from triage.models import IssueInput, VerificationVerdict

    # 1. github_repo_link with leading slash /boost/boost
    inp1 = IssueInput.model_validate({
        "github_repo_link": "/boost/boost",
        "text": "boost::algorithm::unhex throws std::out_of_range",
    })
    assert inp1.repo_url == "https://github.com/boost/boost"
    assert "boost::algorithm::unhex" in inp1.issue_body

    # 2. repo_link with problem_description
    inp2 = IssueInput.model_validate({
        "repo_link": "boostorg/boost",
        "problem_description": "Detailed problem description",
        "title": "Bug title",
    })
    assert inp2.repo_url == "https://github.com/boostorg/boost"
    assert inp2.issue_title == "Bug title"
    assert inp2.issue_body == "Detailed problem description"

    # 3. Verdict string parsing
    assert VerificationVerdict.from_str("unreproducible") == VerificationVerdict.CANNOT_REPRODUCE
    assert VerificationVerdict.from_str("false_positive") == VerificationVerdict.INVALID
    assert VerificationVerdict.from_str("confirmed") == VerificationVerdict.CONFIRMED


def test_extract_json_from_text():
    from triage.llm import extract_json_from_text

    # With conversational text around markdown code block
    noisy = """Hello! Here is the response you requested:
```json
{
  "verdict": "confirmed",
  "reasoning": "Observed crash"
}
```
Let me know if you need anything else!"""
    data = extract_json_from_text(noisy)
    assert data is not None
    assert data["verdict"] == "confirmed"

    # Raw json with commentary without code blocks
    raw_noisy = 'Sure: {"status": "ok", "count": 5} hope that helps.'
    data2 = extract_json_from_text(raw_noisy)
    assert data2 is not None
    assert data2["count"] == 5
