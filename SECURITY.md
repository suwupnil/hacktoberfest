# Security Policy

At **ClaimSentry**, security is at the core of what we do. Our product executes untrusted code, reproductions, and pull request diffs submitted by unknown parties to verify vulnerability claims. Because untrusted code execution presents inherent security challenges, we implement strict defense-in-depth isolation mechanisms and take all vulnerability reports seriously.

---

## Supported Versions

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| `main` (trunk) | :white_check_mark: | Actively supported and maintained |
| `< 1.0.0` | :white_check_mark: | Current pre-release / hackathon versions |

---

## Reporting a Vulnerability

If you discover a security vulnerability or sandbox escape in ClaimSentry:

1. **Do not create a public GitHub issue.** Public issues disclose vulnerabilities before patches can be developed and deployed.
2. Report the vulnerability privately by contacting the maintainers:
   - Reach out via private GitHub Advisory on the repository: [https://github.com/suwupnil/hacktoberfest/security/advisories/new](https://github.com/suwupnil/hacktoberfest)
   - Or contact maintainers directly: **Swapnil Pradhan** or **Akshat Kumar** via GitHub profiles.
3. Please include:
   - A detailed description of the vulnerability.
   - Proof-of-concept (PoC) code or steps to reproduce the issue.
   - The impact of the vulnerability (e.g., sandbox escape, secrets leakage, privilege escalation, DoS).
   - Any remediation suggestions if known.

### Response Timeline
- **Initial Response**: We will acknowledge receipt of your report within 48 hours.
- **Triage & Status**: We will provide an assessment and timeline for a fix within 7 business days.
- **Resolution & Disclosure**: A fix will be developed and released. We coordinate responsible public disclosure once users have had time to update.

---

## Sandbox Security & Threat Model

ClaimSentry is designed around the principle of **"Isolated sandbox · no secrets · no network"**. When executing untrusted bug reproduction scripts, test suites, or proof-of-concept code, ClaimSentry provides the following security guarantees:

### 1. Air-Gapped Network Isolation (`0.00 MBPS`)
- **Socket Monkey-Patching**: All socket creation and connection methods (`socket.socket.connect`, `socket.create_connection`) in untrusted child processes are intercepted and patched at process startup to raise `SandboxNetworkBlocked`.
- **Proxy Redirection**: Proxy environment variables (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, etc.) are forcibly pointed to a dead loopback port (`http://127.0.0.1:0`).
- **Telemetry Verification**: Outbound bandwidth is tracked and monitored; any outbound network attempt immediately halts execution and records 0.00 MBPS network transfer.

### 2. Environment Secret Sanitization (`0 Secrets Exposed`)
- Untrusted execution environments are stripped of all sensitive host variables.
- Any environment variable matching sensitive patterns—such as `KEY`, `SECRET`, `TOKEN`, `AUTH`, `PASS`, `PASSWORD`, `CREDENTIAL`, `API`, `AWS`, or `SSH`—is removed before the child process is launched.
- Untrusted code executes with an allowlist-only environment containing minimal paths (`PATH`, `PYTHONPATH`, `TMPDIR`, `LANG`).

### 3. Process Execution & Resource Limits
- Reproduction scripts and test executions run in isolated temporary working directories.
- Executions have strict process timeouts (default: 5.0 seconds) to prevent CPU hogging, fork bombs, and infinite loops.
- Standard input is disconnected (`/dev/null`) to prevent interactive prompts or hanging processes.

### 4. Local-First AI (Zero Cloud Data Exfiltration)
- LLM inference runs 100% locally using open-weights models (such as Qwen 2.5 Coder via local Ollama).
- Code, bug reports, and diffs are never sent to external third-party cloud APIs.
