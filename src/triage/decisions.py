"""Decisions engine powered by Clef (clef-flash)."""

import json
import logging
import re
from typing import Optional
from triage.boilerplates import get_catalog_summary, BOILERPLATE_CATALOG, detect_heuristic_boilerplate
from triage.llm import LLMClient, decisions_client, extract_json_from_text
from triage.models import DecisionResult, IssueInput

logger = logging.getLogger("triage.decisions")


class DecisionEngine:
    """Uses Clef (decisions model) to evaluate issue type and select execution environment."""

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or decisions_client

    def evaluate(self, issue: IssueInput) -> DecisionResult:
        """Evaluates whether an issue is UI-based or Non-UI, and selects/recommends an environment."""
        # Check if client is using native Cloudflare Clef REST endpoint
        if "ai/run/@cf/cloudflare/clef" in self.client.base_url:
            cf_decision = self._evaluate_cloudflare_clef_native(issue)
            if cf_decision:
                return cf_decision

        catalog_summary = get_catalog_summary()

        system_prompt = (
            "You are Clef, a fast decision-making model specialized in triage classification.\n"
            "Your tasks:\n"
            "1. Decide whether the reported issue is a UI issue or a Non-UI issue.\n"
            "   - UI issues involve frontend web browsers, DOM elements, CSS, animations, modals, viewports, buttons, or client UI rendering.\n"
            "   - Non-UI issues involve backend services, core libraries (e.g., C++ Boost, Python libraries), algorithms, CLI tools, compilers, or server logic.\n"
            "2. If it is a UI issue:\n"
            "   - Set is_ui: true, playwright_needed: true.\n"
            "   - Provide a concise Playwright browser test plan to execute on the remote SSH instance.\n"
            "   - Set recommended_boilerplate to 'node-npm'.\n"
            "3. If it is a Non-UI issue:\n"
            "   - Set is_ui: false, playwright_needed: false, playwright_plan: null.\n"
            "   - Choose the best matching boilerplate environment from the catalog below.\n"
            "   - If no existing boilerplate matches the stack, specify 'custom'.\n\n"
            f"Available Boilerplate Environments:\n{catalog_summary}\n\n"
            "Return ONLY a valid JSON object with the following schema:\n"
            "{\n"
            '  "is_ui": boolean,\n'
            '  "reasoning": "concise explanation",\n'
            '  "playwright_needed": boolean,\n'
            '  "playwright_plan": "string or null",\n'
            '  "recommended_boilerplate": "cpp-boost" | "cpp-cmake" | "python-pytest" | "node-npm" | "rust-cargo" | "go-test" | "custom"\n'
            "}"
        )

        user_prompt = (
            f"GitHub Repository: {issue.repo_url}\n"
            f"Issue Title: {issue.issue_title}\n\n"
            f"Issue Body:\n{issue.issue_body}\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_response = self.client.chat_completion(messages, temperature=0.1, json_output=True)

        parsed = extract_json_from_text(raw_response)
        if parsed and isinstance(parsed, dict):
            decision = DecisionResult(
                is_ui=bool(parsed.get("is_ui", False)),
                reasoning=parsed.get("reasoning", "Evaluated by Clef decisions model."),
                playwright_needed=bool(parsed.get("playwright_needed", False)),
                playwright_plan=parsed.get("playwright_plan"),
                recommended_boilerplate=str(parsed.get("recommended_boilerplate", "custom")),
            )
            return decision

        logger.warning(f"Failed to parse Clef decision response. Raw response: {raw_response}")
        # Fallback heuristic
        fallback_bp = detect_heuristic_boilerplate(issue.repo_url, issue.full_text)
        return DecisionResult(
            is_ui=False,
            reasoning="Heuristic fallback decision: Non-UI backend/library issue.",
            playwright_needed=False,
            playwright_plan=None,
            recommended_boilerplate=fallback_bp,
        )

    def _evaluate_cloudflare_clef_native(self, issue: IssueInput) -> Optional[DecisionResult]:
        """Calls native Cloudflare Clef decision schema endpoint."""
        import httpx
        url = self.client.base_url
        headers = {"Content-Type": "application/json"}
        if self.client.api_key:
            headers["Authorization"] = f"Bearer {self.client.api_key}"

        model_name = "clef-flash" if "clef-flash" in url else "clef"
        payload = {
            "model": model_name,
            "state": f"Repository: {issue.repo_url}\nTitle: {issue.issue_title}\nDescription: {issue.issue_body}",
            "questions": {
                "is_ui": {
                    "type": "choice",
                    "instructions": "Is this a frontend/browser UI issue requiring DOM/CSS testing, or a backend/library non-UI issue?",
                    "criteria": {
                        "ui": "Frontend web, browser, DOM, HTML, CSS, client-side rendering",
                        "non_ui": "Backend services, core libraries, C++, Python, algorithms, CLI"
                    }
                },
                "boilerplate": {
                    "type": "choice",
                    "instructions": "Which execution boilerplate environment should run the reproduction test?",
                    "criteria": {
                        "cpp-boost": "C++ Boost libraries, CMake, GCC, Boost headers",
                        "cpp-cmake": "Standard C++ projects with CMake and Make",
                        "python-pytest": "Python applications and libraries tested with pytest",
                        "node-npm": "Node.js and JavaScript or TypeScript applications",
                        "rust-cargo": "Rust libraries and crates tested with Cargo",
                        "go-test": "Go packages and modules tested with go test",
                        "custom": "Any other stack or language"
                    }
                }
            }
        }
        try:
            with httpx.Client(timeout=self.client.timeout) as http_client:
                res = http_client.post(url, json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()
                answers = data.get("result", {}).get("answers", {})
                is_ui_choice = answers.get("is_ui", {}).get("choice", "non_ui") == "ui"
                bp_choice = answers.get("boilerplate", {}).get("choice", "custom")
                if is_ui_choice:
                    bp_choice = "node-npm"
                elif bp_choice == "custom":
                    bp_choice = detect_heuristic_boilerplate(issue.repo_url, issue.full_text)

                logger.info(f"Cloudflare Clef native decision: is_ui={is_ui_choice}, boilerplate={bp_choice}")
                return DecisionResult(
                    is_ui=is_ui_choice,
                    reasoning=f"Evaluated directly by Cloudflare {model_name} decision schema.",
                    playwright_needed=is_ui_choice,
                    playwright_plan="Run Playwright test suite on remote SSH shell" if is_ui_choice else None,
                    recommended_boilerplate=bp_choice,
                )
        except Exception as e:
            logger.warning(f"Native Cloudflare Clef request failed: {e}. Falling back.")
            return None
