# `claim_sentry` Package

`claim_sentry` is the core Python engine powering the ClaimSentry autonomous claim triage system. It implements the two-tier hybrid architecture combining static multi-language AST scanning with an isolated, air-gapped execution sandbox and local LLM-assisted reproduction synthesis.

---

## 📦 Package Architecture & File Structure

```
claim_sentry/
├── __init__.py                # Package entrypoint & version export
├── README.md                  # This document
├── ast_scanner.py             # Multi-language in-memory AST symbol scanner
├── engine.py                  # Main triage orchestration engine (ClaimSentryEngine)
├── github_fetcher.py          # GitHub issue & PR fetcher with shallow git cloning
├── llm_engine.py              # Local Ollama client (Qwen 2.5 Coder)
├── models.py                  # Pydantic data schemas (Issue, Evidence, Telemetry, etc.)
├── sandbox.py                 # Isolated execution sandbox (0 network, 0 secrets)
├── server.py                  # FastAPI server, REST API & Server-Sent Events (SSE)
├── bin/                       # Native helper binaries
│   ├── apple_ocr              # Precompiled Swift binary for Apple Neural Engine OCR
│   └── apple_ocr.swift        # Swift Vision framework OCR source code
├── static/                    # Frontend assets for Hacktoberfest Brutalist UI
│   ├── app.js                 # Frontend application controller & SSE streaming client
│   ├── index.html             # High-contrast Brutalist HTML interface
│   └── styles.css             # High-contrast Brutalist styling
└── verifiers/                 # The 4 autonomous claim verifier engines
    ├── __init__.py            # Verifier module exports
    ├── bug_verifier.py        # Verifier A: Minimal bug reproduction runner
    ├── security_verifier.py   # Verifier B: AST symbol resolver & fake CVE detector
    ├── diff_coverage_verifier.py # Verifier C: PR test suite diff-coverage calculator
    └── multimodal_verifier.py # Verifier D: Screenshot OCR & video keyframe analyzer
```

---

## 🔍 Module Overview

### 1. `models.py`
Defines standard Pydantic models for data interchange across the engine:
- `Issue`: Represents a claim (bug report, security vulnerability, pull request, or multimodal issue).
- `Evidence`: Detailed telemetry captured during verification (sandbox exit code, execution time, stdout/stderr, diff coverage %, matched code symbols, missing symbols).
- `Telemetry`: Real-time system telemetry (network bandwidth, secrets count, active local model, duration).
- `VerdictStatus`: The verdict classification (`VERIFIED_TRUE`, `FAKE_SLOP`, `UNTESTED_PR`, `UNREPRODUCED`, `MISMATCHED_MEDIA`, `ERROR`).

### 2. `sandbox.py` (`ExecutionSandbox`)
The isolated execution environment enforcing the problem requirement: **"Isolated sandbox · no secrets · no network"**:
- **Network Blocking (`0.00 MBPS`)**: Injects socket monkey-patches into the child process that immediately raise `SandboxNetworkBlocked` when attempting external network calls. Also points HTTP/HTTPS proxy environment variables to `http://127.0.0.1:0`.
- **Secret Sanitization (`0 Secrets Exposed`)**: Scrubs host environment variables containing sensitive keywords (`KEY`, `SECRET`, `TOKEN`, `AUTH`, `PASS`, etc.) and runs under an allowlisted environment (`PATH`, `PYTHONPATH`, `TMPDIR`, `LANG`).
- **Resource Limits**: Implements a strict execution timeout (default: 5.0 seconds) to prevent infinite loops and runaway processes.

### 3. `ast_scanner.py` (`ASTScanner`)
High-speed in-memory multi-language symbol resolution engine:
- Extracts function definitions, classes, methods, and exported components.
- Supports Python (via `ast` module), JavaScript/TypeScript (regex/token parser for components and functions), Go, Rust, and Java.
- Performs Levenshtein fuzzy symbol matching to suggest nearest candidate symbols when a reported symbol does not exist in the repository.

### 4. `github_fetcher.py` (`GitHubFetcher`)
Handles repository acquisition and live data extraction:
- Uses GitHub API or local `gh` CLI token authentication (5,000 requests/hour).
- Performs shallow git clones (`git clone --depth 1`) into temporary directories or cached paths.
- Fetches open issues, pull request diffs, and attached markdown media assets.

### 5. `llm_engine.py` (`LLMEngine`)
Local-first inference client for Ollama:
- Connects to local Ollama endpoints (default: `http://localhost:11434`).
- Prompts Qwen 2.5 Coder (`qwen2.5-coder:7b` or `qwen2.5-coder:1.5b`) to synthesize standalone minimal reproduction scripts for bug reports.
- Includes fallback AST synthesis for offline and zero-LLM environments.

### 6. `verifiers/`
The 4 specialized verification engines:
- **`bug_verifier.py` (Verifier A)**: Synthesizes or extracts reproduction scripts and executes them in the sandbox. If an unhandled exception or non-zero exit code matching the report occurs, the bug is marked `VERIFIED_TRUE`.
- **`security_verifier.py` (Verifier B)**: Resolves security CVE claims against the AST symbol index. If the claimed vulnerable function or component does not exist in the target repo, it flags it as `FAKE_SLOP` with closest symbol suggestions. If it exists, it executes a safe sandboxed PoC.
- **`diff_coverage_verifier.py` (Verifier C)**: Parses unified git diff patches and runs the repository test suite under `coverage`. Computes line-by-line intersection to verify whether the modified lines are actually exercised by tests.
- **`multimodal_verifier.py` (Verifier D)**: Extracts text from screenshots (using native Apple Silicon Neural Engine OCR or Tesseract fallback) and keyframes from screen-recording videos (using OpenCV at 0%, 50%, and 95% timestamps). Intersects extracted tokens with repository symbols and source code strings to confirm authenticity.

### 7. `engine.py` (`ClaimSentryEngine`)
Orchestrates the complete lifecycle:
- Ingests repository files and indexes symbols via `ASTScanner`.
- Routes each issue/PR/claim to the appropriate verifier.
- Dispatches execution logs to listeners in real-time.
- Packages resulting evidence into structured verdicts.

### 8. `server.py`
FastAPI web application exposing:
- Web dashboard serving Brutalist UI from `static/`.
- REST endpoints:
  - `POST /api/triage`: Triggers repository ingestion and triage.
  - `GET /api/stream`: Server-Sent Events (SSE) log stream for real-time telemetry.
  - `POST /api/upload`: Handles uploaded screenshots and video files for multimodal triage.
  - `POST /api/webhook/github`: Webhook receiver for GitHub App automated triage.

---

## 🚀 Programmatic Usage Example

```python
from pathlib import Path
from claim_sentry.engine import ClaimSentryEngine
from claim_sentry.models import Issue, IssueType

# Initialize engine targeting a repository
repo_path = Path("/path/to/target_repository")
engine = ClaimSentryEngine(repo_dir=repo_path)

# Index codebase symbols
engine.index_repository()

# Create a sample bug claim
issue = Issue(
    id="BUG-101",
    number=101,
    title="Crash on long URLs in parse_url()",
    body="Calling parse_url('http://' + 'a' * 5000) raises ValueError.",
    type=IssueType.BUG
)

# Run triage and inspect evidence
verified_issue = engine.verify_issue(issue)

print(f"Verdict: {verified_issue.verdict}")
print(f"Badge: {verified_issue.verdict_badge}")
print(f"Exit Code: {verified_issue.evidence.exit_code}")
print(f"Network Sent: {verified_issue.evidence.network_bytes_sent} bytes")
print(f"Secrets Exposed: {verified_issue.evidence.secrets_exposed_count}")
```
