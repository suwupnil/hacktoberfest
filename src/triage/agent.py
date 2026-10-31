"""Main reasoning and SWE agent powered by Qwen3.5:9b."""

import json
import logging
import re
from typing import List, Optional, Tuple
from triage.boilerplates import BoilerplateEnvironment, register_boilerplate
from triage.llm import LLMClient, main_agent_client, extract_json_from_text
from triage.models import (
    CommandResult,
    FixResult,
    IssueInput,
    ReproductionPlan,
    VerificationResult,
    VerificationVerdict,
)
from triage.runner import CommandRunner

logger = logging.getLogger("triage.agent")


class MainAgent:
    """Main SWE and reasoning agent (qwen3.5:9b)."""

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or main_agent_client

    def create_custom_boilerplate(self, issue: IssueInput) -> BoilerplateEnvironment:
        """Dynamically creates a new boilerplate environment when none in catalog fits."""
        system_prompt = (
            "You are an expert systems and SWE agent (Qwen3.5:9b).\n"
            "The triage decisions model could not find a matching boilerplate environment.\n"
            "Analyze the repository and issue, then specify the minimal environment setup commands\n"
            "needed to clone, build, and test this project on an Ubuntu/Debian Linux shell.\n"
            "Return ONLY a valid JSON object matching:\n"
            "{\n"
            '  "id": "short-identifier",\n'
            '  "name": "Human Readable Name",\n'
            '  "description": "Short description of stack",\n'
            '  "languages": ["lang1", "lang2"],\n'
            '  "setup_commands": ["command1", "command2"],\n'
            '  "test_runner_command": "command to run tests"\n'
            "}"
        )

        user_prompt = (
            f"Repository: {issue.repo_url}\n"
            f"Issue Title: {issue.issue_title}\n\n"
            f"Issue Body:\n{issue.issue_body}\n"
        )

        raw = self.client.chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_output=True,
        )

        data = extract_json_from_text(raw)
        if data and isinstance(data, dict):
            custom_env = BoilerplateEnvironment(
                id=data.get("id", "custom-env"),
                name=data.get("name", "Custom Environment"),
                description=data.get("description", "Agent-generated environment"),
                languages=data.get("languages", ["custom"]),
                setup_commands=data.get("setup_commands", []),
                test_runner_command=data.get("test_runner_command", "echo 'No test command'"),
            )
            register_boilerplate(custom_env)
            return custom_env

        logger.warning(f"Failed to generate custom boilerplate via LLM. Using fallback.")
        fallback = BoilerplateEnvironment(
            id="custom-fallback",
            name="Custom Agent Environment",
            description="Auto-generated fallback environment",
            languages=["general"],
            setup_commands=["sudo apt-get update || true"],
            test_runner_command="echo 'Running generic test'",
        )
        register_boilerplate(fallback)
        return fallback

    def plan_reproduction(
        self, issue: IssueInput, boilerplate: BoilerplateEnvironment
    ) -> ReproductionPlan:
        """Derives steps and executable reproduction script to recreate the issue."""
        system_prompt = (
            "You are an expert SWE verification agent (Qwen3.5:9b).\n"
            "Your job is to read the bug report and generate a self-contained shell script (`reproduce.sh`)\n"
            "that inputs the exact steps to recreate the issue.\n"
            "The reproduction script must:\n"
            "- Set up test inputs or a minimal isolated test file (e.g. C++ test_repro.cpp, Python test_repro.py, or bash test)\n"
            "- Compile or run the code under test\n"
            "- If the bug reproduces, produce relevant error logs or non-zero exit code\n"
            "- Exit with code 42 if bug is successfully reproduced, or 0 if bug did not occur\n\n"
            "Return ONLY a JSON object:\n"
            "{\n"
            '  "steps_description": "summary of steps to recreate",\n'
            '  "reproduction_script": "#!/usr/bin/env bash\\n...",\n'
            '  "expected_error_or_behavior": "expected error message or behavior"\n'
            "}"
        )

        user_prompt = (
            f"Repository: {issue.repo_url}\n"
            f"Environment: {boilerplate.name} ({boilerplate.id})\n"
            f"Issue Title: {issue.issue_title}\n\n"
            f"Issue Description:\n{issue.issue_body}\n"
        )

        raw = self.client.chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_output=True,
        )

        data = extract_json_from_text(raw)
        if data and isinstance(data, dict):
            return ReproductionPlan(
                steps_description=data.get("steps_description", "Execute reproduction script"),
                reproduction_script=data.get("reproduction_script", "#!/usr/bin/env bash\nexit 1"),
                expected_error_or_behavior=data.get("expected_error_or_behavior", ""),
            )

        logger.warning(f"Failed to parse reproduction plan. Using default script.")
        return ReproductionPlan(
            steps_description="Manual reproduction execution",
            reproduction_script="#!/usr/bin/env bash\necho 'Running verification...'\nexit 1",
            expected_error_or_behavior="Error",
        )

    def verify_reproduction(
        self,
        issue: IssueInput,
        plan: ReproductionPlan,
        result: CommandResult,
    ) -> VerificationResult:
        """Evaluates execution evidence to classify verdict as confirmed, cannot reproduce, or invalid."""
        system_prompt = (
            "You are an evidence-based SWE verification agent (Qwen3.5:9b).\n"
            "Analyze the original issue report and the actual execution output from recreating the steps.\n"
            "You must classify the outcome into EXACTLY one of three verdicts:\n"
            "1. 'confirmed' — the reported bug/claim was observed and reproduced as described.\n"
            "2. 'cannot reproduce' — the reproduction script ran but the reported failure did not occur (or encountered an unrelated failure).\n"
            "3. 'invalid' — the claim is technically impossible, fabricated, contradictory, or referencing non-existent features/APIs.\n\n"
            "Return ONLY a JSON object:\n"
            "{\n"
            '  "verdict": "confirmed" | "cannot reproduce" | "invalid",\n'
            '  "reasoning": "detailed technical explanation backed by the execution evidence",\n'
            '  "extracted_claims": ["claim 1", "claim 2"],\n'
            '  "evidence": ["evidence log 1", "evidence log 2"]\n'
            "}"
        )

        user_prompt = (
            f"Issue Title: {issue.issue_title}\n"
            f"Issue Body:\n{issue.issue_body}\n\n"
            f"Reproduction Script Executed:\n{plan.reproduction_script}\n\n"
            f"Execution Exit Code: {result.exit_code}\n"
            f"Execution Stdout:\n{result.stdout}\n"
            f"Execution Stderr:\n{result.stderr}\n"
        )

        raw = self.client.chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_output=True,
        )

        data = extract_json_from_text(raw)
        if data and isinstance(data, dict):
            verdict_str = data.get("verdict", "cannot reproduce")
            verdict = VerificationVerdict.from_str(verdict_str)

            return VerificationResult(
                verdict=verdict,
                reasoning=data.get("reasoning", "Verification evaluation completed."),
                reproduction_command=result.command,
                reproduction_script=plan.reproduction_script,
                execution_output=result,
                extracted_claims=data.get("extracted_claims", [issue.issue_title]),
                evidence=data.get("evidence", [f"Exit code: {result.exit_code}"]),
            )

        logger.warning("Failed to parse verification result from LLM. Using heuristic evaluation.")
        # Heuristic verdict based on exit code and error
        verdict = VerificationVerdict.CONFIRMED if result.exit_code == 42 else VerificationVerdict.CANNOT_REPRODUCE
        return VerificationResult(
            verdict=verdict,
            reasoning=f"Execution completed with exit code {result.exit_code}.",
            reproduction_command=result.command,
            reproduction_script=plan.reproduction_script,
            execution_output=result,
            extracted_claims=[issue.issue_title],
            evidence=[f"Command exited with code {result.exit_code}"],
        )

    def formulate_fix_and_architecture(
        self,
        issue: IssueInput,
        verification: VerificationResult,
        runner: CommandRunner,
        workdir: str,
    ) -> FixResult:
        """Formulates a fix, applies it in the environment, verifies if it worked,
        and generates pseudo code, architectural plan, and maintainer comments.
        """
        system_prompt = (
            "You are an expert SWE agent (Qwen3.5:9b).\n"
            "The issue has been triaged and verified.\n"
            "Your tasks:\n"
            "1. If the issue is confirmed, formulate a possible fix (as a git diff or code edit) to resolve it.\n"
            "2. Provide pseudo code, an architectural plan, or structured guidelines for a proper long-term solution.\n"
            "3. Provide maintainer comments summarizing your technical findings.\n\n"
            "Return ONLY a JSON object:\n"
            "{\n"
            '  "fix_diff": "unified diff string or null",\n'
            '  "fix_description": "explanation of what the patch modifies",\n'
            '  "pseudo_code_or_plan": "pseudo code or architectural plan",\n'
            '  "architectural_notes": "architectural considerations, performance, compatibility",\n'
            '  "maintainer_comment": "summary comment to post on the issue"\n'
            "}"
        )

        user_prompt = (
            f"Repository: {issue.repo_url}\n"
            f"Issue Title: {issue.issue_title}\n"
            f"Issue Description:\n{issue.issue_body}\n\n"
            f"Verification Verdict: {verification.verdict.value}\n"
            f"Verification Reasoning: {verification.reasoning}\n"
            f"Reproduction Output:\n{verification.execution_output.stdout}\n{verification.execution_output.stderr}\n"
        )

        raw = self.client.chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_output=True,
        )

        fix_diff = None
        fix_desc = ""
        pseudo_plan = ""
        arch_notes = ""
        maintainer_comment = ""

        data = extract_json_from_text(raw)
        if data and isinstance(data, dict):
            fix_diff = data.get("fix_diff")
            fix_desc = data.get("fix_description", "")
            pseudo_plan = data.get("pseudo_code_or_plan", "")
            arch_notes = data.get("architectural_notes", "")
            maintainer_comment = data.get("maintainer_comment", "")
        else:
            logger.warning("Failed to parse fix recommendations from LLM. Using fallback guidance.")
            pseudo_plan = "Review input boundary conditions and enforce domain exceptions."
            arch_notes = "Standardize error handling and exception contracts."
            maintainer_comment = "Reproduction triage completed."

        fix_applied = False
        fixed = False
        fix_verification_output = None

        # If confirmed and fix diff was provided, apply it and test
        if verification.verdict == VerificationVerdict.CONFIRMED and fix_diff:
            try:
                # Save diff to file and attempt application via git apply or patch
                patch_file = f"{workdir}/fix_patch.diff"
                runner.write_file(patch_file, fix_diff)

                apply_res = runner.run(f"git apply --ignore-whitespace '{patch_file}'", cwd=workdir)
                if not apply_res.success:
                    apply_res = runner.run(f"patch -p1 --batch -N < '{patch_file}'", cwd=workdir)
                if not apply_res.success:
                    apply_res = runner.run(f"patch -p0 --batch -N < '{patch_file}'", cwd=workdir)

                if apply_res.success:
                    fix_applied = True
                    logger.info("Patch applied successfully. Re-running reproduction script to verify fix...")
                    retest_res = runner.run("bash reproduce.sh", cwd=workdir)
                    fix_verification_output = retest_res
                    if retest_res.exit_code == 0:
                        fixed = True
                        logger.info("Fix successfully resolved the issue!")
                    else:
                        fixed = False
                        logger.info(f"Fix applied but reproduction re-test exited with code {retest_res.exit_code}")
                else:
                    fix_applied = False
                    logger.warning(f"Could not apply patch: {apply_res.stderr or apply_res.stdout}")
            except Exception as ex:
                logger.warning(f"Failed to apply/verify patch: {ex}")

        return FixResult(
            fix_applied=fix_applied,
            fix_diff=fix_diff,
            fix_description=fix_desc,
            fixed=fixed,
            fix_verification_output=fix_verification_output,
            pseudo_code_or_plan=pseudo_plan,
            architectural_notes=arch_notes,
            maintainer_comment=maintainer_comment,
        )

    def _clean_json(self, raw: str) -> str:
        """Strip markdown ticks and whitespace from LLM output."""
        cleaned = raw.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        return cleaned
