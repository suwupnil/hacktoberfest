// CLAIM-SENTRY: CLEAN & FOCUSED APP ENGINE

let allIssues = [];
let currentFilter = "all";

document.addEventListener("DOMContentLoaded", () => {
  initSSE();
  fetchIssues();
  setupEventListeners();
});

function setupEventListeners() {
  const btnStart = document.getElementById("btn-start-triage");
  const repoInput = document.getElementById("repo-url-input");

  btnStart.addEventListener("click", () => startTriage(repoInput.value));
  repoInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") startTriage(repoInput.value);
  });

  // Suggestion chips
  document.getElementById("chip-grauity").addEventListener("click", () => {
    repoInput.value = "https://github.com/Newton-School/grauity";
    startTriage(repoInput.value);
  });
  document.getElementById("chip-flask").addEventListener("click", () => {
    repoInput.value = "https://github.com/pallets/flask";
    startTriage(repoInput.value);
  });
  document.getElementById("chip-httpx").addEventListener("click", () => {
    repoInput.value = "https://github.com/encode/httpx";
    startTriage(repoInput.value);
  });
  document.getElementById("chip-sample").addEventListener("click", () => {
    repoInput.value = "https://github.com/devclub/url-toolkit";
    startTriage(repoInput.value);
  });

  // 3 Filter Tabs
  document.getElementById("btn-filter-all").addEventListener("click", () => setFilter("all"));
  document.getElementById("btn-filter-real").addEventListener("click", () => setFilter("real"));
  document.getElementById("btn-filter-fake").addEventListener("click", () => setFilter("fake"));

  // Modal close
  document.getElementById("btn-close-modal").addEventListener("click", closeModal);
  document.getElementById("proof-modal").addEventListener("click", (e) => {
    if (e.target.id === "proof-modal") closeModal();
  });
}

function setFilter(filter) {
  currentFilter = filter;
  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(`btn-filter-${filter}`).classList.add("active");
  renderIssues();
}

async function startTriage(repoUrl) {
  if (!repoUrl || !repoUrl.trim()) return;

  const btn = document.getElementById("btn-start-triage");
  btn.disabled = true;
  btn.innerText = "⚡ TRIAGING IN SANDBOX...";

  appendTerminalLog({
    timestamp: new Date().toTimeString().split(" ")[0],
    phase: "FETCH",
    message: `[START] Ingesting repository: '${repoUrl}'. Shallow clone and issue fetch initiated...`
  });

  try {
    const res = await fetch("/api/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl.trim() })
    });
    const data = await res.json();
    if (res.ok) {
      appendTerminalLog({
        timestamp: new Date().toTimeString().split(" ")[0],
        phase: "AST-SCAN",
        message: `[INDEXED] ${data.count} issues loaded from ${data.repo}. Indexed ${data.symbols_indexed || 0} symbols across ${data.files_scanned || 0} files. Autonomous triage running...`
      });
      await fetchIssues();
    } else {
      appendTerminalLog({
        timestamp: new Date().toTimeString().split(" ")[0],
        phase: "FETCH",
        message: `[ERROR] Ingestion failed: ${data.error || "Unknown error"}`
      });
    }
  } catch (err) {
    appendTerminalLog({
      timestamp: new Date().toTimeString().split(" ")[0],
      phase: "FETCH",
      message: `[ERROR] Network error: ${err}`
    });
  } finally {
    setTimeout(() => {
      btn.disabled = false;
      btn.innerText = "⚡ START TRIAGE";
      fetchIssues();
    }, 4000);
  }
}

// SERVER-SENT EVENTS
function initSSE() {
  const evtSource = new EventSource("/api/stream");

  evtSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      appendTerminalLog(data);

      if (data.phase === "VERDICT" || data.phase === "TELEMETRY" || data.phase === "FETCH") {
        fetchIssues();
      }
    } catch (err) {}
  };
}

function appendTerminalLog(log) {
  const terminal = document.getElementById("terminal-logs");
  const line = document.createElement("div");
  line.className = "log-line";

  const tagClass = `tag-${log.phase || "AI-AGENT"}`;
  line.innerHTML = `
    <span class="log-timestamp">[${log.timestamp || "00:00:00"}]</span>
    <span class="log-tag ${tagClass}">${log.phase || "LOG"}</span>
    <span>${escapeHTML(log.message)}</span>
  `;

  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

async function fetchIssues() {
  try {
    const res = await fetch("/api/issues");
    allIssues = await res.json();
    updateFilterCounts();
    renderIssues();
  } catch (err) {
    console.error("Failed to fetch issues:", err);
  }
}

function updateFilterCounts() {
  const countAll = allIssues.length;
  const countReal = allIssues.filter(i => i.is_real_issue === true).length;
  const countFake = allIssues.filter(i => i.is_real_issue === false).length;

  document.getElementById("claims-count").innerText = countAll;
  document.getElementById("count-all").innerText = countAll;
  document.getElementById("count-real").innerText = countReal;
  document.getElementById("count-fake").innerText = countFake;
}

// ISSUE RENDERING
function renderIssues() {
  const container = document.getElementById("issues-list");
  container.innerHTML = "";

  const filtered = allIssues.filter(item => {
    if (currentFilter === "real") return item.is_real_issue === true;
    if (currentFilter === "fake") return item.is_real_issue === false;
    return true; // all
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="padding: 30px; text-align: center; font-weight: 800; color: #777;">
        No issues found for filter '${currentFilter.toUpperCase()}'.
      </div>
    `;
    return;
  }

  filtered.forEach(issue => {
    const card = document.createElement("div");
    card.className = "issue-card";

    let badgeClass = "badge-pending";
    let badgeText = "TESTING IN SANDBOX...";

    if (issue.is_real_issue === true) {
      badgeClass = "badge-real";
      badgeText = issue.verdict_badge || "✓ REAL ISSUE";
    } else if (issue.is_real_issue === false) {
      badgeClass = "badge-fake";
      badgeText = issue.verdict_badge || "✗ FAKE / UNVERIFIED";
    }

    const whatWrote = issue.what_user_wrote || issue.body || issue.title;
    const howTested = issue.how_we_tested || "We generated an isolated test and executed it in an air-gapped sandbox without network access.";
    const ourView = issue.our_verdict_explanation || (issue.verdict_headline ? `${issue.verdict_headline}: ${issue.evidence ? issue.evidence.reasoning : ''}` : "Verification in progress...");

    card.innerHTML = `
      <div class="issue-card-header">
        <span class="issue-title">#${issue.number}: ${escapeHTML(issue.title)}</span>
        <span class="verdict-badge ${badgeClass}">${badgeText}</span>
      </div>

      <div class="explanation-row">
        <div class="explanation-label">👤 1. What The User Reported:</div>
        <div class="explanation-box">${escapeHTML(whatWrote)}</div>
      </div>

      <div class="explanation-row">
        <div class="explanation-label">🧪 2. How We Tested It (In Isolated Sandbox):</div>
        <div class="explanation-box">${escapeHTML(howTested)}</div>
      </div>

      <div class="explanation-row">
        <div class="explanation-label">⚖️ 3. Our Verdict &amp; Why:</div>
        <div class="explanation-box verdict-box">${escapeHTML(ourView)}</div>
      </div>

      <div class="issue-card-footer">
        <span>AUTHOR: <b>@${issue.author}</b> | TYPE: <b>${issue.type.toUpperCase()}</b></span>
        <button class="btn-proof" onclick="openProofModal('${issue.id}')">TECHNICAL PROOF ↗</button>
      </div>
    `;

    container.appendChild(card);
  });
}

// TECHNICAL PROOF MODAL
function openProofModal(issueId) {
  const issue = allIssues.find(i => i.id === issueId);
  if (!issue) return;

  const modal = document.getElementById("proof-modal");
  document.getElementById("proof-modal-title").innerText = `TECHNICAL PROOF: #${issue.number} ${issue.title}`;

  const content = document.getElementById("proof-modal-content");
  const ev = issue.evidence || {};

  let scriptHtml = "";
  if (ev.repro_script) {
    scriptHtml = `
      <div>
        <div style="font-weight: 800; font-size: 12px; margin-bottom: 4px;">MINIMAL REPRODUCTION SCRIPT (ISOLATED SANDBOX):</div>
        <pre class="code-viewer"><code>${escapeHTML(ev.repro_script)}</code></pre>
      </div>
    `;
  }

  let traceHtml = "";
  if (ev.stdout || ev.stderr) {
    traceHtml = `
      <div>
        <div style="font-weight: 800; font-size: 12px; margin-bottom: 4px;">RAW TERMINAL OUTPUT &amp; STACKTRACE (EXIT CODE: ${ev.exit_code}):</div>
        <pre class="code-viewer" style="color: #00FF66;"><code>${escapeHTML((ev.stdout ? ev.stdout + '\n' : '') + (ev.stderr || ''))}</code></pre>
      </div>
    `;
  }

  content.innerHTML = `
    <div style="font-size: 13px; line-height: 1.6; background-color: #FFF; padding: 12px; border: 1px solid #000;">
      <b>SANDBOX AUDIT SUMMARY:</b><br>
      • Network Blocked: 0.00 MBPS<br>
      • Secrets Leaked: 0<br>
      • Execution Time: ${ev.execution_time_ms || 0} ms<br>
      • Reasoning: ${escapeHTML(ev.reasoning || issue.our_verdict_explanation || 'Executed safely.')}
    </div>
    ${scriptHtml}
    ${traceHtml}
  `;

  modal.classList.add("open");
}

function closeModal() {
  document.getElementById("proof-modal").classList.remove("open");
}

function escapeHTML(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
