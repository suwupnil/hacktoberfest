# 🤖 AGENTS.md — Instructions & Architecture for AI Coding Agents

Welcome, Agent. This file contains operational rules, repository structure, architectural constraints, and guidance for autonomous coding agents (Claude Code, Gemini, Cursor, Jules, Copilot, etc.) working on the **ClaimSentry** codebase.

---

## 🎯 What is ClaimSentry?

ClaimSentry is an autonomous, air-gapped triage engine designed for Problem 2 of Hacktoberfest HackDay Sonipat (*"Triage That Tests The Claims"*).

Rather than passively guessing whether a GitHub issue or PR is legitimate using generic LLM prompts, ClaimSentry acts like a **laboratory inspector**:
1. It parses the claims (bug reports, security CVEs, PR diffs, and multimodal screenshots/videos).
2. It statically audits symbols and ASTs across multiple programming languages.
3. It synthesizes minimal reproduction scripts and executes them inside an **air-gapped, zero-network, secret-scrubbed sandbox**.
4. It outputs mathematically grounded, reproducible verdicts accompanied by runnable evidence (exit codes, stack traces, diff coverage percentages).

---

## 🗂️ Project Directory Layout

```
├── AGENTS.md                      # This file (Agent instructions & guidelines)
├── ARCHITECTURE.md                # Detailed system architecture specification
├── CLAUDE.md                      # Pointer to AGENTS.md
├── CODE_OF_CONDUCT.md             # Contributor Covenant Code of Conduct
├── CONTRIBUTING.md                # Contribution workflow and guidelines
├── GEMINI.md                      # Pointer to AGENTS.md
├── HACKATHON.md                   # Hackathon team details and problem statement
├── LICENSE                        # Apache 2.0 License
├── README.md                      # Root project overview and quickstart
├── SECURITY.md                    # Security policy & sandbox guarantees
├── pytest.ini                     # Pytest configuration
├── requirements.txt               # Python package dependencies
├── run.py                         # Application launcher (runs server on port 8000)
├── claim_sentry/                  # Core Python package
│   ├── __init__.py                # Package initialization
│   ├── README.md                  # Package-level documentation
│   ├── ast_scanner.py             # Multi-language in-memory AST symbol scanner
│   ├── engine.py                  # Main triage orchestration engine
│   ├── github_fetcher.py          # GitHub API and `gh` CLI fetcher & cloner
│   ├── llm_engine.py              # Ollama local LLM integration (Qwen 2.5 Coder)
│   ├── models.py                  # Pydantic data models (Issue, Evidence, Telemetry)
│   ├── sandbox.py                 # Isolated execution sandbox (0 network, 0 secrets)
│   ├── server.py                  # FastAPI web server and SSE log stream endpoints
│   ├── bin/                       # Native binaries & helper scripts (Apple OCR)
│   │   ├── apple_ocr              # Precompiled Swift OCR binary for macOS Apple Silicon
│   │   └── apple_ocr.swift        # Swift source for Vision framework OCR
│   ├── static/                    # Frontend assets (Brutalist HTML/CSS/JS)
│   │   ├── app.js                 # Frontend application logic & SSE event listener
│   │   ├── index.html             # High-contrast Brutalist HTML interface
│   │   └── styles.css             # High-contrast Brutalist CSS design system
│   └── verifiers/                 # The 4 autonomous verification engines
│       ├── __init__.py            # Verifier exports
│       ├── bug_verifier.py        # Verifier A: Minimal bug reproduction runner
│       ├── security_verifier.py   # Verifier B: AST symbol resolver & fake CVE detector
│       ├── diff_coverage_verifier.py # Verifier C: PR test suite diff-coverage calculator
│       └── multimodal_verifier.py # Verifier D: Screenshot OCR & video keyframe analyzer
├── examples/                      # Example targets, test cases, and sample media
│   ├── sample_issues.json         # Mock GitHub issues for offline evaluation
│   ├── verified_evidence_output.json # Reference evidence output
│   ├── sample_screenshots/        # Test screenshots (stacktraces, UI bugs, fake errors)
│   ├── sample_videos/             # Test videos for keyframe extraction
│   └── target_repo/               # Minimal sample repo (`url_toolkit`) for tests
└── tests/                         # Pytest test suite
    ├── test_api.py                # FastAPI endpoint tests
    ├── test_bug_verifier.py       # Bug reproduction verifier tests
    ├── test_diff_coverage.py      # PR diff coverage verifier tests
    ├── test_multimodal.py         # Multimodal OCR & keyframe verifier tests
    ├── test_sandbox.py            # Sandbox air-gap & security isolation tests
    └── test_security_verifier.py  # Security symbol existence tests
```

---

## ⚙️ Development Environment & Tooling

### Setup & Dependencies
```bash
# Setup venv and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install python-multipart
```

### Running Tests
To run the automated test suite:
```bash
python3 -m pytest tests/ -v
```

### Launching the Application
```bash
python3 run.py
# Server starts at http://127.0.0.1:8000
```

---

## 🔒 Crucial Invariants for Agents

When making changes to this codebase, you **must** adhere to these principles:

1. **Air-Gapped Sandbox Integrity (`claim_sentry/sandbox.py`)**:
   - The sandbox strictly guarantees `0.00 MBPS` network access by monkey-patching socket creation in child processes.
   - The sandbox sanitizes `os.environ` by stripping any keys matching `KEY`, `SECRET`, `TOKEN`, `AUTH`, `PASS`, `PASSWORD`, `CREDENTIAL`, `API`, `AWS`, or `SSH`.
   - Never weaken or disable these security guardrails. Untrusted code must never access the real network or environment secrets.

2. **Deterministic Verification Over Hallucination**:
   - Prefer AST symbol scanning and concrete test execution over ungrounded LLM inference.
   - If local LLM synthesis fails or is unavailable, verifiers must fall back to deterministic AST synthesis and heuristics gracefully without crashing.

3. **Models & Pydantic Validation (`claim_sentry/models.py`)**:
   - All issues, evidence, verdicts, and telemetry data structures are strictly typed using Pydantic `BaseModel`.
   - When adding new fields to `Issue` or `Evidence`, update `claim_sentry/models.py` and ensure backward compatibility with serialized JSON (e.g. `examples/sample_issues.json` and `examples/verified_evidence_output.json`).

4. **Brutalist UI Consistency (`claim_sentry/static/`)**:
   - The UI adheres to a high-contrast Neo-Brutalist design language (stark borders, bold shadows `#000000`, monospace font, high-contrast badges: Neon Green `#00F560`, Brutal Red `#FF3B30`, Acid Yellow `#FFD60A`, Acid Cyan `#00E5FF`).
   - Do not replace the frontend with bloated third-party single-page app frameworks unless explicitly requested.

5. **Cross-Platform Compatibility**:
   - Native macOS Apple Silicon acceleration (e.g. Swift `apple_ocr` via Vision framework) is provided in `claim_sentry/bin/`.
   - On Linux and Windows systems where macOS Vision framework is absent, code must gracefully fall back to cross-platform OCR (Tesseract / PIL) without throwing unhandled exceptions.
