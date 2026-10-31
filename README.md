# ⚡ CLAIM-SENTRY // Triage That Tests The Claims
> **Hacktoberfest HackDay Sonipat • Team Zig2 • Problem 2**  
> *An autonomous, air-gapped triage engine that verifies GitHub bug reports, security claims, PRs, and multimodal media through **runnable evidence** executed in an isolated sandbox, rather than passive LLM guessing.*

---

## 🎯 The Core Philosophy: "Triage That Tests The Claims"

Most AI triage tools simply read a GitHub issue, read a file, and make a **guess** ("This looks like a bug"). If you do this, maintainers cannot trust the output, and fake or hallucinated reports easily slip through.

**ClaimSentry acts like a Certified Food Inspector:**
- ❌ **Wrong Way (Passive Guessing):** Reading a restaurant menu and saying *"Food looks delicious, verified!"*
- ✅ **The ClaimSentry Way (Laboratory Proof):** Taking the food into an isolated cleanroom laboratory, running scientific tests, and attaching the lab report: *"Tested in isolation: salt content is 400% above limit, here is the exact trace."*

```
BUG REPORT: "Crash on long URLs" ─────────┐
                                          │     ┌─────────────────────────────────────────────────────────┐
SECURITY REPORT: "RCE in parse_url_v2()" ─┼────►│                   CLAIM-SENTRY GITHUB APP               │
                                          │     │  Air-Gapped Sandbox • Zero Network • Secrets Sanitized  │
PULL REQUEST: "Fixes #120, adds tests" ───┤     └────────────────────────────┬────────────────────────────┘
                                          │                                  │
MULTIMODAL: "Stacktrace screenshot" ──────┘                                  ▼
                                                  EVIDENCE DOSSIER & PLAIN LANGUAGE VERDICT
                                                  ✓ Reproduced in Sandbox on v2.4.1 (exit code 1)
                                                  ✗ parse_url_v2() does NOT exist in codebase [FAKE SLOP]
                                                  ! No tests cover modified diff lines [UNTESTED PR]
                                                  ✓ Visual error tokens match repository code [AI VERIFIED]
```

---

## 🏛️ System Architecture: The Two-Tier Hybrid Engine

To eliminate cloud API costs, eliminate network latency, and guarantee mathematical precision, ClaimSentry combines deterministic compilers with local open-weights AI:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              TWO-TIER HYBRID ARCHITECTURE                               │
├─────────────────────────────────────┬──────────────────────────────────────────────────┤
│ 1. Multi-Language AST Scanner       │ Microsecond RAM symbol resolution across 6+      │
│    (Python, JS/TS, Go, Rust, Java)  │ languages. Catches fake CVEs and components in    │
│                                     │ 0.0001 seconds without LLM overhead.             │
├─────────────────────────────────────┼──────────────────────────────────────────────────┤
│ 2. Air-Gapped Execution Sandbox     │ Zero network socket monkey-patch (0.00 MBPS)     │
│    (Isolated Container / Subproc)   │ and env secret sanitization (API keys wiped).    │
├─────────────────────────────────────┼──────────────────────────────────────────────────┤
│ 3. Local Edge LLM (Qwen 2.5 Coder)  │ Generates minimal reproduction scripts locally   │
│    (Apple Metal GPU / Vulkan / CPU) │ via Ollama (500+ tokens/sec prompt eval).        │
├─────────────────────────────────────┼──────────────────────────────────────────────────┤
│ 4. Native Vision & Keyframe OCR     │ Sub-20ms Apple Neural Engine OCR (Swift native)  │
│    (Apple Silicon / Tesseract)      │ with OpenCV 3-keyframe video triage.             │
└─────────────────────────────────────┴──────────────────────────────────────────────────┘
```

---

## ⚡ Quickstart: Run It On Your Machine In 2 Minutes

Copy and paste these commands directly into your terminal:

### 1. Clone & Enter Repository
```bash
git clone https://github.com/suwupnil/hacktoberfest.git
cd hacktoberfest
```

### 2. Set Up Python Environment & Dependencies
```bash
# Create and activate a clean virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Start Local Open-Source AI (Ollama)
ClaimSentry runs 100% locally with open-weight models (Zero cloud API keys needed):

```bash
# If Ollama is not installed:
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# Pull the lightweight coding model (runs on Mac/Linux/Windows):
ollama pull qwen2.5-coder:7b
# (Optional fallback for low-RAM machines: ollama pull qwen2.5-coder:1.5b)

# Start Ollama daemon in background:
ollama serve &
```

### 4. Run the Full Test Suite
Verify that all verifiers, sandboxes, and AST scanners pass:
```bash
pytest tests/ -v
```
*(All 17 tests pass with 100% success rate in under 4 seconds!)*

### 5. Launch the ClaimSentry Platform
```bash
python3 run.py
```
Open your browser and navigate to:  
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🖥️ Using The Platform

1. **Single Universal Search Bar:**
   - Paste any GitHub repository URL (e.g. `https://github.com/Newton-School/grauity` or `https://github.com/pallets/flask`).
   - Click **`⚡ START TRIAGE`** (or press Enter).
2. **Autonomous Execution:**
   - The engine shallow clones the repository into local cache.
   - Paginates and fetches **all real open issues and PRs** (filtering out closed issues).
   - Multi-language AST parser indexes every symbol, component, and function in memory.
   - Sandbox runs minimal reproduction tests, diff coverage audits, and multimodal OCR in real-time.
3. **Only 3 Focused Filters:**
   - **`ALL`**: All open claims fetched.
   - **`✓ REAL ISSUES`**: Verified bugs and tested pull requests.
   - **`✗ FAKE / UNVERIFIED`**: Hallucinated CVEs, non-existent components, and mismatched media.
4. **Structured Plain Language Cards:**
   - 👤 **1. What The User Reported:** Uncluttered report summary.
   - 🧪 **2. How We Tested It:** Exactly what sandbox or AST audit was performed.
   - ⚖️ **3. Our Verdict & Why:** Human-readable explanation with evidence badge.
   - 🔍 **`TECHNICAL PROOF ↗` Button:** Opens the exact minimal reproduction code, terminal exit code, and execution duration.

---

## 🔒 Security & Sandbox Guarantees

When testing untrusted bug reproduction scripts submitted by unknown internet users:
- **Zero Network Access:** All outgoing TCP/UDP sockets are intercepted and monkey-patched to `0.00 MBPS`. Untrusted scripts cannot phone home or exfiltrate data.
- **Wiped Secrets:** `os.environ` is thoroughly scrubbed of API tokens, SSH keys, AWS credentials, and environment passwords.
- **Air-Gapped Process Boundary:** Scripts execute in a restricted temporary directory with strict 5-second process timeouts to prevent infinite loops and fork bombs.

---

## 🧪 Supported Verification Types

| Claim Type | Test Performed | Evidence Output |
| :--- | :--- | :--- |
| **Bug Reports** | Synthesizes minimal reproduction script & executes in sandbox | Exit code, traceback, exception line, stdout |
| **Security CVEs** | Multi-language AST symbol resolution & sink audit | File location, line number, signature, or `FAKE SLOP` flag |
| **Pull Requests** | Executes test suite with line-by-line coverage intersection | Diff coverage %, covered lines, uncovered lines |
| **Multimodal UI** | Native Apple Neural Engine OCR & OpenCV video keyframes | Matched codebase string literals, error token intersection |

---

## 👥 Team Zig2

- **Swapnil Pradhan**
- **Akshat Kumar**

*Hacktoberfest HackDay Sonipat • Problem 2: Triage that tests the claims*
