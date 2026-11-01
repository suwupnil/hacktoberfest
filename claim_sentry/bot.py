"""ClaimSentry GitHub App Autonomous Bot CLI.

Run ClaimSentry as a standalone GitHub Bot to audit issues and pull requests,
execute verification in an air-gapped sandbox, and post evidence comments.

Usage:
    python -m claim_sentry.bot --repo pallets/flask --limit 5
    python -m claim_sentry.bot --repo owner/repo --issue 42 --comment
"""

import sys
import argparse
from pathlib import Path

from .models import LogEvent
from .engine import ClaimSentryEngine
from .llm_engine import LocalLLMEngine
from .github_fetcher import (
    parse_github_url,
    clone_github_repo,
    fetch_github_issues,
    fetch_single_github_issue,
    get_github_token,
    post_github_comment,
    format_evidence_comment,
)


def log_to_console(event: LogEvent):
    """Outputs live triage logs to terminal."""
    print(f"[{event.timestamp}] [{event.phase:^10}] {event.message}")


def main():
    parser = argparse.ArgumentParser(description="ClaimSentry GitHub App Autonomous Bot")
    parser.add_argument("--repo", required=True, help="GitHub repository URL or 'owner/repo'")
    parser.add_argument("--issue", type=int, default=None, help="Specific issue or PR number to test")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of issues to audit")
    parser.add_argument("--comment", action="store_true", help="Post evidence verification comment to GitHub")
    args = parser.parse_args()

    try:
        owner, repo_name = parse_github_url(args.repo)
    except Exception as e:
        print(f"❌ Error parsing repo: {e}")
        sys.exit(1)

    print("=================================================================")
    print(" ⚡ CLAIM-SENTRY GITHUB APP // AUTONOMOUS CLAIM VERIFIER")
    print(f" Repository: {owner}/{repo_name}")
    print(" Sandbox: Air-gapped (0.00 MBPS network, secrets scrubbed)")
    print("=================================================================\n")

    token = get_github_token()
    cache_dir = Path("local_repos") / f"{owner}_{repo_name}"
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"📦 Cloning repository into isolated sandbox cache...")
    repo_path = clone_github_repo(owner, repo_name, cache_dir)
    if not repo_path:
        print("❌ Failed to clone repository. Aborting.")
        sys.exit(1)

    if args.issue is not None:
        print(f"📥 Ingesting Issue/PR #{args.issue}...")
        single = fetch_single_github_issue(owner, repo_name, args.issue, token=token)
        if not single:
            print(f"❌ Issue #{args.issue} not found on {owner}/{repo_name}.")
            sys.exit(1)
        issues = [single]
    else:
        print(f"📥 Ingesting open issues and PRs...")
        issues = fetch_github_issues(owner, repo_name, max_count=args.limit, token=token)
        if not issues:
            print("ℹ️ No open issues or pull requests found.")
            return

    print(f"🔍 Initializing multi-language AST scanner and local LLM...")
    llm = LocalLLMEngine()
    engine = ClaimSentryEngine(repo_dir=repo_path, llm_engine=llm)
    engine.issues = issues

    print(f"🚀 Triaging {len(issues)} claims in air-gapped sandbox...\n")
    engine.triage_all(event_callback=log_to_console)

    print("\n=================================================================")
    print(" 📊 TRIAGE SUMMARY")
    print("=================================================================")
    for issue in engine.issues:
        status_sym = "✓" if issue.is_real_issue else "✗"
        print(f"{status_sym} #{issue.number:<5} [{issue.verdict_badge or 'VERIFIED'}] {issue.title[:60]}")
        print(f"  Verdict: {issue.verdict_headline or 'Tested'}")

        if args.comment:
            comment_body = format_evidence_comment(issue)
            success = post_github_comment(owner, repo_name, issue.number, comment_body, token=token)
            if success:
                print(f"  💬 Comment successfully posted to #{issue.number}!")
            else:
                print(f"  ⚠️ Could not post comment to #{issue.number} (token or write permission missing).")
        print()


if __name__ == "__main__":
    main()
