"""Real GitHub Repository and Issue Ingestion Engine.

Fetches live issues, pull requests, diffs, and attached screenshots/videos
from any GitHub repository using authenticated gh CLI token or public REST API,
and performs shallow git clone into local_cache for locked-down sandbox analysis.
"""

import os
import re
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .models import Issue, IssueType


def get_github_token() -> Optional[str]:
    """Retrieves authenticated GitHub token from environment or gh CLI."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()

    try:
        proc = subprocess.run(
            ["gh", "auth", "token"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass

    return None


def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parses GitHub URL or 'owner/repo' shorthand into (owner, repo).
    Handles '/issues', '/pulls', '.git', etc.
    Examples:
      - 'https://github.com/Newton-School/grauity/issues' -> ('Newton-School', 'grauity')
      - 'https://github.com/pallets/flask' -> ('pallets', 'flask')
      - 'pallets/flask' -> ('pallets', 'flask')
    """
    clean = url.strip()
    clean = re.sub(r"^https?://github\.com/", "", clean)
    clean = re.sub(r"/(?:issues|pulls|tree/.*|blob/.*)?$", "", clean)
    clean = re.sub(r"\.git$", "", clean)
    clean = clean.strip("/")

    parts = clean.split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    raise ValueError(f"Invalid GitHub repository specifier: '{url}'. Expected 'owner/repo' or 'https://github.com/owner/repo'.")


def clone_github_repo(owner: str, repo: str, target_dir: Path) -> Path:
    """Performs a shallow clone of the target repository for local sandbox verification."""
    target_dir.mkdir(parents=True, exist_ok=True)
    repo_path = target_dir / repo

    if (repo_path / ".git").exists():
        return repo_path

    clone_url = f"https://github.com/{owner}/{repo}.git"
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(repo_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45.0
        )
    except Exception:
        repo_path.mkdir(parents=True, exist_ok=True)

    return repo_path


def download_attached_media(image_url: str, output_path: Path, token: Optional[str] = None) -> bool:
    """Downloads an image or video attached in a GitHub issue markdown body."""
    try:
        req = urllib.request.Request(image_url)
        req.add_header("User-Agent", "ClaimSentry-Bot")
        if token and "api.github.com" in image_url:
            req.add_header("Authorization", f"Bearer {token}")

        with urllib.request.urlopen(req, timeout=10.0) as resp:
            content = resp.read()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)
            return True
    except Exception:
        return False


def fetch_github_issues(owner: str, repo: str, max_count: Optional[int] = None, media_dir: Optional[Path] = None) -> List[Issue]:
    """
    Fetches ALL real open issues and pull requests from GitHub API using pagination.
    Supports repositories with hundreds or thousands of issues without hard limits.
    """
    token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ClaimSentry-Autonomous-Triage"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    items: List[Dict[str, Any]] = []
    page = 1
    per_page = 100

    # Paging loop to fetch all open issues
    while True:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=open&per_page={per_page}&page={page}"
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                page_items = json.loads(resp.read().decode("utf-8"))
        except Exception:
            # Fallback to search endpoint if standard issues endpoint fails
            if page == 1:
                search_url = f"https://api.github.com/search/issues?q=repo:{owner}/{repo}+state:open&sort=created&order=desc&per_page={per_page}&page={page}"
                try:
                    s_req = urllib.request.Request(search_url, headers=headers)
                    with urllib.request.urlopen(s_req, timeout=15.0) as s_resp:
                        s_data = json.loads(s_resp.read().decode("utf-8"))
                        page_items = s_data.get("items", [])
                except Exception:
                    page_items = []
            else:
                break

        if not page_items or not isinstance(page_items, list):
            break

        items.extend(page_items)

        # If user specified a limit and we reached it
        if max_count is not None and len(items) >= max_count:
            items = items[:max_count]
            break

        # If fewer items than per_page returned, this was the last page
        if len(page_items) < per_page:
            break

        page += 1

    parsed_issues: List[Issue] = []
    media_download_count = 0
    pr_diff_fetch_count = 0

    for item in items:
        # Strictly ignore closed issues
        if item.get("state", "open") == "closed":
            continue

        number = item.get("number", 1)
        title = item.get("title", f"Issue #{number}")
        body = item.get("body") or ""
        labels = [l.get("name", "") for l in item.get("labels", [])]
        is_pr = "pull_request" in item
        author = item.get("user", {}).get("login", "contributor")

        # Extract image / video links from markdown body
        img_matches = re.findall(r"!\[.*?\]\((https?://[^\s\)]+)\)", body)
        asset_matches = re.findall(r"(https?://github\.com/user-attachments/assets/[a-zA-Z0-9\-]+)", body)
        all_media = img_matches + asset_matches

        has_screenshot = False
        screenshot_path = None
        has_video = False
        video_path = None

        if all_media:
            first_media_url = all_media[0]
            if media_dir and media_download_count < 20:
                filename = f"gh_{number}_{first_media_url.split('/')[-1][:20]}"
                if not filename.endswith((".png", ".jpg", ".jpeg", ".mp4", ".gif")):
                    filename += ".png"

                dest_path = media_dir / filename
                if download_attached_media(first_media_url, dest_path, token):
                    media_download_count += 1
                    if filename.endswith(".mp4"):
                        has_video = True
                        video_path = str(dest_path)
                    else:
                        has_screenshot = True
                        screenshot_path = str(dest_path)
            else:
                has_screenshot = True
                screenshot_path = first_media_url

        # PR Diff fetching (capped to top 5 during batch ingest to maintain sub-second speed)
        pr_diff = None
        if is_pr and token and pr_diff_fetch_count < 5:
            try:
                diff_req = urllib.request.Request(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3.diff",
                        "User-Agent": "ClaimSentry"
                    }
                )
                with urllib.request.urlopen(diff_req, timeout=2.0) as diff_resp:
                    pr_diff = diff_resp.read().decode("utf-8", errors="ignore")[:4000]
                    pr_diff_fetch_count += 1
            except Exception:
                pr_diff = None

        # Issue type classification
        combined_text = f"{title}\n{body}".lower()
        if has_screenshot or has_video:
            issue_type = IssueType.MULTIMODAL
        elif is_pr:
            issue_type = IssueType.PULL_REQUEST
        elif any(sec in combined_text for sec in ["cve", "vulnerability", "security", "rce", "injection", "overflow", "leak"]):
            issue_type = IssueType.SECURITY
        else:
            issue_type = IssueType.BUG

        clean_what_user_wrote = body.strip() if body.strip() else f"User reported: '{title}'"

        parsed_issues.append(Issue(
            id=f"GH-{number}",
            number=number,
            title=title,
            body=body,
            type=issue_type,
            author=author,
            labels=labels,
            created_at=item.get("created_at", ""),
            has_screenshot=has_screenshot,
            screenshot_path=screenshot_path,
            has_video=has_video,
            video_path=video_path,
            pr_diff=pr_diff,
            claim_summary=title,
            what_user_wrote=clean_what_user_wrote[:500]
        ))

    return parsed_issues
