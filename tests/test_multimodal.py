"""Tests for Multimodal Screenshot and Video Verifier."""

from pathlib import Path
from claim_sentry.models import Issue, IssueType, VerdictStatus
from claim_sentry.sandbox import ExecutionSandbox
from claim_sentry.verifiers.multimodal_verifier import MultimodalVerifier


def test_verified_stacktrace_screenshot():
    base_dir = Path(__file__).resolve().parent.parent
    repo_dir = base_dir / "examples" / "target_repo"
    img_path = base_dir / "examples" / "sample_screenshots" / "stacktrace_long_url.png"

    sandbox = ExecutionSandbox(repo_dir)
    verifier = MultimodalVerifier(sandbox)

    issue = Issue(
        id="MM-001",
        number=5,
        title="Production crash stacktrace screenshot",
        body="Attaching terminal screenshot of parser crash.",
        type=IssueType.MULTIMODAL,
        has_screenshot=True,
        screenshot_path=str(img_path)
    )

    verified = verifier.verify(issue)
    assert verified.verdict == VerdictStatus.VERIFIED_TRUE
    assert "AI Verified Claim" in verified.verdict_headline
    assert any("parser.py" in f for f in verified.evidence.matched_repo_files)


def test_mismatched_alien_screenshot():
    base_dir = Path(__file__).resolve().parent.parent
    repo_dir = base_dir / "examples" / "target_repo"
    img_path = base_dir / "examples" / "sample_screenshots" / "fake_unrelated.png"

    sandbox = ExecutionSandbox(repo_dir)
    verifier = MultimodalVerifier(sandbox)

    issue = Issue(
        id="MM-002",
        number=6,
        title="Alien OS crash proof",
        body="Screenshot of kernel crash.",
        type=IssueType.MULTIMODAL,
        has_screenshot=True,
        screenshot_path=str(img_path)
    )

    verified = verifier.verify(issue)
    assert verified.verdict == VerdictStatus.MISMATCHED_MEDIA
    assert "Fake/Mismatched Media" in verified.verdict_headline


def test_video_keyframe_extraction_and_speed():
    base_dir = Path(__file__).resolve().parent.parent
    repo_dir = base_dir / "examples" / "target_repo"
    vid_path = base_dir / "examples" / "sample_videos" / "crash_demo.mp4"

    sandbox = ExecutionSandbox(repo_dir)
    verifier = MultimodalVerifier(sandbox)

    issue = Issue(
        id="MM-003",
        number=7,
        title="Video recording of UI crash on long URL input",
        body="Video demo attached.",
        type=IssueType.MULTIMODAL,
        has_video=True,
        video_path=str(vid_path)
    )

    verified = verifier.verify(issue)
    # Ensure keyframes were generated (3 keyframes: start, middle, crash)
    assert len(verified.evidence.media_keyframes) == 3
    # Check that keyframe files actually exist on disk
    for kf in verified.evidence.media_keyframes:
        assert Path(kf).exists()
