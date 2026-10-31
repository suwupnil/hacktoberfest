# Contributing to ClaimSentry

Thank you for your interest in contributing to **ClaimSentry**! We welcome bug fixes, new verifiers, documentation improvements, UI enhancements, and general feedback.

ClaimSentry is an autonomous, air-gapped triage engine designed to verify GitHub bug reports, security vulnerability claims, PR diff coverage, and multimodal evidence through runnable sandbox execution.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please keep discussions respectful, constructive, and focused on building reliable, verifiable open-source software.

---

## Getting Started

### Prerequisites

- **Python**: Version 3.10+ (tested up to Python 3.12)
- **Git** (and optionally the GitHub CLI `gh` for authenticated repository ingestion)
- **Ollama** (optional, recommended for local bug reproduction script synthesis):
  - macOS: `brew install ollama`
  - Linux: `curl -fsSL https://ollama.com/install.sh | sh`
  - Model: `ollama pull qwen2.5-coder:7b` (or `qwen2.5-coder:1.5b` for resource-constrained systems)

### Local Environment Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/suwupnil/hacktoberfest.git
   cd hacktoberfest
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install python-multipart  # For file uploads via FastAPI
   ```

4. **Verify the installation:**
   ```bash
   pytest tests/ -v
   ```

5. **Run the local development server:**
   ```bash
   python3 run.py
   ```
   Open your browser to `http://127.0.0.1:8000`.

---

## Development Workflow

1. **Create a branch:**
   Use a concise, descriptive branch name reflecting your changes:
   ```bash
   git checkout -b feat/support-cargo-test
   # or
   git checkout -b fix/ast-multiline-comment
   ```

2. **Follow Coding Standards:**
   - **Python**: Clean, PEP 8 conforming code with type annotations where practical. Use Pydantic models for data interchange (`claim_sentry/models.py`).
   - **Frontend**: The user interface follows a high-contrast Brutalist theme (`claim_sentry/static/`). Vanilla JS and clean CSS without bloated external runtime frameworks.
   - **Sandbox Safety**: Any sandbox execution logic in `claim_sentry/sandbox.py` must enforce zero network access (monkey-patched socket connections), secret scrubbing (filtering environment variables), and strict process execution timeouts. Never weaken sandbox security guarantees.

3. **Add Tests:**
   - All verifiers and new core functions must include unit or integration tests under `tests/`.
   - Run tests locally with `pytest`:
     ```bash
     pytest tests/ -v
     ```

4. **Commit Guidelines:**
   - Write clear, concise commit messages.
   - Follow standard conventions (e.g. `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`).

---

## Submitting Pull Requests

When you are ready to submit a pull request:

1. Push your branch to your GitHub fork:
   ```bash
   git push origin <branch-name>
   ```
2. Open a Pull Request against the main branch of `suwupnil/hacktoberfest`.
3. Complete all sections of the [Pull Request Template](.github/pull_request_template.md):
   - **What this PR does**: Clear summary of functionality, improvements, or fixes.
   - **Models used in this PR**: Any open-weight AI models utilized (e.g., `qwen2.5-coder:7b via Ollama` or `none`).
   - **AI coding assistants that helped write it**: Any tools used during development (e.g., `Claude Code`, `Cursor`, `GitHub Copilot`, or `none`).
   - **How we tested it**: Details on reproduction steps, unit tests, and validation.

---

## Architecture Reference

For details on the two-tier hybrid architecture, air-gapped sandboxing, AST scanning, and verifier implementations, consult:
- [README.md](README.md) - System overview and quickstart guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - In-depth system design specification
- [claim_sentry/README.md](claim_sentry/README.md) - Core package reference
- [AGENTS.md](AGENTS.md) - Instructions and guidance for autonomous coding agents
