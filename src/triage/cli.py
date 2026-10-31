"""Command-line interface for the issue triage system."""

import argparse
import json
import logging
import os
from pathlib import Path
import sys
from triage.config import settings
from triage.models import IssueInput
from triage.orchestrator import TriageOrchestrator


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evidence-Based GitHub Issue Triage System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to JSON file containing the issue and GitHub repo link",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Path to save the triage JSON report (defaults to triage_report_<timestamp>.json)",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["ssh", "local"],
        default=None,
        help="Execution runner mode ('ssh' or 'local'). Overrides .env setting.",
    )
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Force deterministic offline mock LLM responses (useful for testing without live models)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.mock_llm:
        settings.FORCE_MOCK_LLM = True

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input JSON file not found at {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to parse input file {input_path} as JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        issue_input = IssueInput.model_validate(raw_data)
    except Exception as e:
        print(f"Error: Invalid issue input format: {e}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("🚀 STARTING EVIDENCE-BASED ISSUE TRIAGE")
    print(f"   Repository: {issue_input.repo_url}")
    print(f"   Issue: {issue_input.issue_title}")
    print(f"   Execution Mode: {args.mode or settings.EXECUTION_MODE}")
    print("=" * 60)

    orchestrator = TriageOrchestrator()
    report = orchestrator.run(issue_input, execution_mode=args.mode)

    # Determine output file path
    output_path = args.output
    if not output_path:
        sanitized = "".join(c for c in issue_input.issue_title[:25] if c.isalnum() or c in ("-", "_")).rstrip()
        output_path = f"triage_report_{sanitized or 'run'}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    markdown_path = str(Path(output_path).with_suffix(".md"))
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(report.to_markdown())

    print("\n" + "=" * 60)
    print("📊 TRIAGE REPORT SUMMARY")
    print("=" * 60)
    print(f"• Classification: {'UI (Bypassed to Playwright)' if report.is_ui else 'Non-UI'}")
    if not report.is_ui:
        print(f"• Environment: {report.boilerplate.name} ({'Custom' if report.is_custom_boilerplate else 'Catalog'})")
        verdict_str = report.verdict.value.upper() if report.verdict else "N/A"
        print(f"• Verdict: {verdict_str}")
        if report.fix:
            print(f"• Fix Attempt: {'Fixed' if report.fix.fixed else 'Plan & Pseudo-code Provided'}")
    print(f"• JSON Report Saved: {output_path}")
    print(f"• Markdown Report Saved: {markdown_path}")
    print("=" * 60)
    print("\n" + report.to_markdown() + "\n")


if __name__ == "__main__":
    main()
