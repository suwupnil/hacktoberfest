"""Data schemas and types for ClaimSentry verification engine."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time


class IssueType(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PULL_REQUEST = "pull_request"
    MULTIMODAL = "multimodal"


class VerdictStatus(str, Enum):
    VERIFIED_TRUE = "VERIFIED_TRUE"       # Neon Green #00F560
    FAKE_SLOP = "FAKE_SLOP"               # Brutal Red #FF3B30
    UNTESTED_PR = "UNTESTED_PR"           # Acid Yellow #FFD60A
    UNREPRODUCED = "UNREPRODUCED"         # Acid Yellow / Orange
    MISMATCHED_MEDIA = "MISMATCHED_MEDIA" # Brutal Red #FF3B30
    ERROR = "ERROR"


class Evidence(BaseModel):
    repro_script: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0.0
    network_bytes_sent: int = 0
    secrets_exposed_count: int = 0
    scanned_symbols: List[str] = Field(default_factory=list)
    missing_symbols: List[str] = Field(default_factory=list)
    similar_symbols: List[str] = Field(default_factory=list)
    diff_coverage_pct: Optional[float] = None
    covered_lines: List[int] = Field(default_factory=list)
    uncovered_lines: List[int] = Field(default_factory=list)
    extracted_media_text: Optional[str] = None
    media_keyframes: List[str] = Field(default_factory=list)
    matched_repo_files: List[str] = Field(default_factory=list)
    reasoning: str = ""


class Issue(BaseModel):
    id: str
    number: int
    title: str
    body: str
    type: IssueType
    author: str = "reporter"
    labels: List[str] = Field(default_factory=list)
    created_at: str = ""
    has_screenshot: bool = False
    screenshot_path: Optional[str] = None
    has_video: bool = False
    video_path: Optional[str] = None
    pr_diff: Optional[str] = None
    claim_summary: str = ""
    verdict: Optional[VerdictStatus] = None
    verdict_badge: Optional[str] = None
    verdict_headline: Optional[str] = None
    what_user_wrote: str = ""
    how_we_tested: str = ""
    our_verdict_explanation: str = ""
    is_real_issue: Optional[bool] = None
    evidence: Optional[Evidence] = None


class Telemetry(BaseModel):
    network_usage_mbps: float = 0.00
    secrets_exposed: int = 0
    active_model: str = "Qwen 2.5 Coder 1.5B (Apple Silicon M5 Metal GPU)"
    execution_time_ms: float = 0.0
    total_claims_triaged: int = 0
    verified_bugs: int = 0
    fake_slop_caught: int = 0
    untested_prs: int = 0


class LogEvent(BaseModel):
    id: str = ""
    timestamp: str = ""
    phase: str  # FETCH, SANDBOX, AST-SCAN, AI-AGENT, VERDICT, TELEMETRY
    message: str
    issue_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
