# Evidence-Based Issue Triage System

An intelligent multi-model triage system that evaluates incoming open-source GitHub issues based on their technical claims and empirical evidence.

## Overview

The triage system separates high-level routing decisions from deep software engineering verification:
1. **Decisions Model (`clef-flash`)**: Rapidly analyzes the issue text and repository context to decide whether an issue is **UI** or **Non-UI**:
   - **UI Issues**: Clef flags the issue for **Playwright** browser testing executed inside a remote SSH shell environment (with host, user, and credentials defined in `.env`).
   - **Non-UI Issues**: Clef evaluates the project stack and selects the best matching environment from a set of popular boilerplate environments (e.g. C++ Boost, Python, Node, Rust, Go). If none fits, the **Main Agent** dynamically generates a new custom environment.
2. **Main SWE Agent (`qwen3.5:9b`)**:
   - Derives the exact reproduction steps and writes a self-contained reproduction script (`reproduce.sh`).
   - Executes the reproduction steps inside the SSH shell environment.
   - Evaluates the resulting execution logs and classifies the claim into:
     - `confirmed`: The bug was reproduced as claimed.
     - `cannot reproduce`: The reproduction ran without the claimed failure.
     - `invalid`: The claim is technically impossible, fabricated, or contradictory.
   - If `confirmed`, the Main Agent formulates a code patch/diff, applies it in the environment, and verifies if the fix resolved the failure.
   - Regardless of outcome, the agent outputs pseudo-code, an architectural plan, or maintainer guidance.

---

## Architecture

```
                       ┌────────────────────────┐
                       │  Input JSON (Issue +   │
                       │   GitHub Repo Link)    │
                       └───────────┬────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │    Clef Decisions Model      │
                    │         (clef-flash)         │
                    └──────────────┬───────────────┘
                                   │
                 ┌─────────────────┴─────────────────┐
                 │                                   │
        [UI Issue Detected]                [Non-UI Issue Detected]
                 │                                   │
                 ▼                                   ▼
   ┌───────────────────────────┐       ┌───────────────────────────┐
   │ Route to Playwright Suite │       │ Select / Create Popular   │
   │ on Remote SSH Shell       │       │ Boilerplate Environment   │
   └───────────────────────────┘       └─────────────┬─────────────┘
                                                     │
                                                     ▼
                                       ┌───────────────────────────┐
                                       │ SSH Shell Execution       │
                                       │ (Paramiko remote shell)   │
                                       └─────────────┬─────────────┘
                                                     │
                                                     ▼
                                       ┌───────────────────────────┐
                                       │ Main Agent (qwen3.5:9b)   │
                                       │ Recreate Steps & Verify   │
                                       └─────────────┬─────────────┘
                                                     │
                         ┌───────────────────────────┼───────────────────────────┐
                         ▼                           ▼                           ▼
                   [ confirmed ]            [ cannot reproduce ]            [ invalid ]
                         │
                         ▼
        ┌───────────────────────────────────┐
        │ Main Agent Formulates Fix:        │
        │ - Applies Patch in Environment    │
        │ - Re-runs Verification Test       │
        │ - Generates Pseudo-code & Plan    │
        └─────────────────┬─────────────────┘
                          │
                          ▼
        ┌───────────────────────────────────┐
        │ Final Evidence-Based Assessment   │
        │ (JSON & Markdown Report)          │
        └───────────────────────────────────┘
```

---

## Popular Boilerplate Environments

The system includes pre-configured, isolated boilerplate execution environments:
- **`cpp-boost`**: C++ environment with Boost libraries, CMake, GCC/Clang, and b2.
- **`cpp-cmake`**: Modern C++ toolchain with CMake and Make.
- **`python-pytest`**: Python 3 runtime with venv, pip, pytest, and standard toolkits.
- **`node-npm`**: Node.js runtime with npm/pnpm and JavaScript/TypeScript test runners.
- **`rust-cargo`**: Rust toolchain with cargo and rustc.
- **`go-test`**: Go development environment with go test.
- **`custom`**: Dynamically synthesized by the Main Agent when an unlisted stack is encountered.

---

## Configuration (`.env`)

Configuration is stored in `.env` (refer to `.env.example`):

```bash
# 1. Main Agent Configuration (qwen3.5:9b)
MAIN_AGENT_URL=http://localhost:11434/v1
MAIN_AGENT_NAME=qwen3.5:9b
MAIN_AGENT_API_KEY=

# 2. Decisions Model Configuration (clef-flash)
DECISIONS_MODEL_URL=http://localhost:11435/v1
DECISIONS_MODEL_NAME=clef-flash
DECISIONS_MODEL_API_KEY=

# 3. SSH Remote Environment Configuration
SSH_HOST=127.0.0.1
SSH_PORT=22
SSH_USER=ubuntu
SSH_KEY_PATH=~/.ssh/id_rsa
SSH_PASSWORD=
SSH_REMOTE_WORKDIR=/tmp/triage_workspace
SSH_TIMEOUT=30

# 4. Execution Mode ("ssh" or "local")
EXECUTION_MODE=ssh
```

---

## Usage

### 1. Run Triage CLI on Boost Issue (`/boost/boost`)

```bash
python run_triage.py --input issue_boost.json --mode local
```

Or for SSH execution against remote runner:

```bash
python run_triage.py --input issue_boost.json --mode ssh
```

### 2. Run Triage on UI Issue (Routes to Playwright)

```bash
python run_triage.py --input examples/ui_issue_playwright.json
```

### 3. Run Test Suite

```bash
uv run pytest -v
```

---

## Assessment Output Format

Each generated assessment report separates:
1. **Claims**: The specific technical statements made in the issue.
2. **Evidence**: Command logs, reproduction outputs, error traces, and exit codes.
3. **Verification**: Verdict (`confirmed`, `cannot reproduce`, or `invalid`) backed by execution results.
4. **Fix & Architectural Recommendations**: Proposed patch diff, validation of fix, pseudo-code plan, and maintainer guidance.
5. **Uncertainty & Limitations**: Explicit caveats, assumptions, and environments tested.
