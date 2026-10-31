"""Pydantic models and data structures for the triage system."""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator


class VerificationVerdict(str, Enum):
    """The three possible verification verdicts required by specification."""
    CONFIRMED = "confirmed"
    CANNOT_REPRODUCE = "cannot reproduce"
    INVALID = "invalid"

    @classmethod
    def from_str(cls, val: str) -> VerificationVerdict:
        normalized = val.strip().lower()
        if "confirm" in normalized:
            return cls.CONFIRMED
        if "cannot" in normalized or "can not" in normalized or "unable" in normalized or "unreproduc" in normalized:
            return cls.CANNOT_REPRODUCE
        if "invalid" in normalized or "not a bug" in normalized or "hallucinat" in normalized or "bogus" in normalized or "false_positive" in normalized:
            return cls.INVALID
        # Default fallback
        return cls.CANNOT_REPRODUCE


class IssueInput(BaseModel):
    """Input payload containing an issue and a GitHub repo link."""
    repo_url: str = Field(description="URL or name of GitHub repository (e.g. https://github.com/boostorg/boost or boost/boost)")
    issue_title: str = Field(default="", description="Title of the issue")
    issue_body: str = Field(default="", description="Description and body of the issue")
    raw_issue: Optional[Union[str, Dict[str, Any]]] = Field(default=None, description="Raw issue object or text")

    @model_validator(mode="before")
    @classmethod
    def parse_flexible_input(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary or JSON object")

        # Extract repo URL from various common naming conventions
        repo_url = (
            data.get("repo_url")
            or data.get("github_repo_link")
            or data.get("repo_link")
            or data.get("github_repo")
            or data.get("repo")
            or data.get("repository")
            or data.get("github_url")
            or data.get("url")
            or data.get("link")
            or ""
        )
        if isinstance(repo_url, str):
            repo_url = repo_url.strip()
            # Normalize paths like /boost/boost, boost/boost, or https://github.com/...
            if repo_url and not repo_url.startswith("http://") and not repo_url.startswith("https://"):
                cleaned = repo_url.strip("/")
                repo_url = f"https://github.com/{cleaned}"

        issue_data = data.get("issue")
        issue_title = data.get("issue_title") or data.get("title") or ""
        issue_body = (
            data.get("issue_body")
            or data.get("body")
            or data.get("description")
            or data.get("text")
            or data.get("content")
            or data.get("problem_description")
            or data.get("problem_statement")
            or ""
        )

        if isinstance(issue_data, dict):
            issue_title = issue_title or issue_data.get("title") or ""
            issue_body = (
                issue_body
                or issue_data.get("body")
                or issue_data.get("description")
                or issue_data.get("text")
                or issue_data.get("content")
                or ""
            )
        elif isinstance(issue_data, str):
            if not issue_body:
                issue_body = issue_data
            if not issue_title:
                # First line as title
                lines = issue_data.strip().split("\n")
                issue_title = lines[0].strip("# ") if lines else "Issue"

        return {
            "repo_url": repo_url,
            "issue_title": issue_title or "Reported Issue",
            "issue_body": issue_body,
            "raw_issue": issue_data or data,
        }

    @property
    def full_text(self) -> str:
        """Combined title and body for LLM analysis."""
        return f"Title: {self.issue_title}\n\nDescription:\n{self.issue_body}".strip()


class DecisionResult(BaseModel):
    """Decision made by Clef (the decisions model)."""
    is_ui: bool = Field(description="True if this is a UI issue, False for non-UI")
    reasoning: str = Field(description="Reasoning behind UI/non-UI classification")
    playwright_needed: bool = Field(default=False, description="Whether Playwright test instance on SSH is needed")
    playwright_plan: Optional[str] = Field(default=None, description="Playwright test plan / script if UI issue")
    recommended_boilerplate: str = Field(
        default="custom",
        description="ID of chosen boilerplate environment, or 'custom' if new one needed"
    )


class BoilerplateEnvironment(BaseModel):
    """Definition of an execution environment to run on SSH shell."""
    id: str
    name: str
    description: str
    languages: List[str] = Field(default_factory=list)
    setup_commands: List[str] = Field(default_factory=list)
    test_runner_command: str = Field(default="echo 'No default test command'")
    docker_image: Optional[str] = None


class CommandResult(BaseModel):
    """Result of running a command on the SSH or local runner."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float = 0.0

    @property
    def success(self) -> bool:
        return self.exit_code == 0


class ReproductionPlan(BaseModel):
    """Steps and script derived by Main Agent to recreate the issue."""
    steps_description: str
    reproduction_script: str
    script_filename: str = "reproduce.sh"
    expected_error_or_behavior: str


class VerificationResult(BaseModel):
    """Verification outcome produced by Main Agent."""
    verdict: VerificationVerdict
    reasoning: str
    reproduction_command: str
    reproduction_script: str
    execution_output: CommandResult
    extracted_claims: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)


class FixResult(BaseModel):
    """Fix attempt and architectural comments produced by Main Agent."""
    fix_applied: bool = False
    fix_diff: Optional[str] = None
    fix_description: str = ""
    fixed: bool = False
    fix_verification_output: Optional[CommandResult] = None
    pseudo_code_or_plan: str = ""
    architectural_notes: str = ""
    maintainer_comment: str = ""


class TriageReport(BaseModel):
    """Comprehensive final output report of the triage session."""
    timestamp: str
    repo_url: str
    issue_title: str
    is_ui: bool
    decision: DecisionResult
    boilerplate_id: str
    is_custom_boilerplate: bool
    boilerplate: BoilerplateEnvironment
    verdict: Optional[VerificationVerdict] = None
    verification: Optional[VerificationResult] = None
    fix: Optional[FixResult] = None
    summary: str = ""
    claims: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    uncertainty: List[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Formats the assessment into Evidence-Based markdown report."""
        lines = []
        lines.append(f"# Evidence-Based Issue Assessment: {self.issue_title}")
        lines.append(f"**Repository:** `{self.repo_url}`  ")
        lines.append(f"**Timestamp:** `{self.timestamp}`  ")
        lines.append(f"**Issue Classification:** `{'UI' if self.is_ui else 'Non-UI'}`  ")

        if self.is_ui:
            lines.append("\n## 🎭 UI Issue Routing")
            lines.append(f"- **Decision:** Routed to Playwright instance on SSH shell.")
            lines.append(f"- **Reasoning:** {self.decision.reasoning}")
            if self.decision.playwright_plan:
                lines.append(f"- **Playwright Execution Plan:**\n```\n{self.decision.playwright_plan}\n```")
            return "\n".join(lines)

        lines.append(f"**Selected Environment:** `{self.boilerplate.name}` (`{self.boilerplate_id}`) "
                     f"{'(Custom Generated)' if self.is_custom_boilerplate else '(Catalog Boilerplate)'}  ")
        
        status_badge = "UNKNOWN"
        if self.verdict:
            status_badge = self.verdict.value.upper()
        lines.append(f"**Verdict:** `{status_badge}`\n")

        lines.append("## 1. Claims")
        if self.claims:
            for claim in self.claims:
                lines.append(f"- {claim}")
        else:
            lines.append(f"- Technical claim: {self.issue_title}")

        lines.append("\n## 2. Evidence")
        if self.evidence:
            for ev in self.evidence:
                lines.append(f"- {ev}")
        if self.verification and self.verification.execution_output:
            lines.append("\n### Reproduction Execution Log")
            lines.append(f"Command: `{self.verification.execution_output.command}` (Exit Code: {self.verification.execution_output.exit_code})")
            lines.append("```")
            stdout_snippet = self.verification.execution_output.stdout.strip()
            stderr_snippet = self.verification.execution_output.stderr.strip()
            if stdout_snippet:
                lines.append(f"[stdout]\n{stdout_snippet[:2000]}")
            if stderr_snippet:
                lines.append(f"[stderr]\n{stderr_snippet[:2000]}")
            if not stdout_snippet and not stderr_snippet:
                lines.append("[no output produced]")
            lines.append("```")

        lines.append("\n## 3. Verification")
        if self.verdict:
            lines.append(f"- **Status:** `{self.verdict.value}`")
        if self.verification:
            lines.append(f"- **Reasoning:** {self.verification.reasoning}")

        if self.fix:
            lines.append("\n## 4. Fix & Architectural Recommendations")
            lines.append(f"- **Fix Status:** `{'Successfully Fixed' if self.fix.fixed else 'Not Fully Fixed / Guidance Provided'}`")
            if self.fix.fix_diff:
                lines.append(f"\n### Proposed Patch\n```diff\n{self.fix.fix_diff}\n```")
            if self.fix.pseudo_code_or_plan:
                lines.append(f"\n### Proposed Solution / Pseudo-code\n```\n{self.fix.pseudo_code_or_plan}\n```")
            if self.fix.architectural_notes:
                lines.append(f"\n### Architectural & Maintainer Notes\n{self.fix.architectural_notes}")
            if self.fix.maintainer_comment:
                lines.append(f"\n### Maintainer Comment\n> {self.fix.maintainer_comment}")

        lines.append("\n## 5. Uncertainty & Limitations")
        if self.uncertainty:
            for u in self.uncertainty:
                lines.append(f"- {u}")
        else:
            lines.append("- Verification was performed in an isolated clean environment. Further integration testing across platforms is recommended.")

        return "\n".join(lines)
