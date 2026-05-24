/**
 * AEGIS Guard — Popup (advanced)
 */

const LLM_SITES = ["chatgpt.com", "claude.ai", "gemini.google.com", "copilot.microsoft.com", "bing.com", "chat.openai.com", "openai.com"];
const DEFAULT_API = "http://localhost:8000";

async function checkBackend(apiBase) {
  const base = apiBase || DEFAULT_API;
  try {
    const r = await fetch(base.replace(/\/$/, "") + "/", { method: "GET", mode: "cors" });
    return r.ok;
  } catch (_) {
    return false;
  }
}

function isOnLLMSite() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]?.url) { resolve(false); return; }
      try {
        const host = new URL(tabs[0].url).hostname.replace(/^www\./, "");
        resolve(LLM_SITES.some((s) => host === s || host.endsWith("." + s)));
      } catch (_) {
        resolve(false);
      }
    });
  });
}

function getHost() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]?.url) { resolve("—"); return; }
      try {
        resolve(new URL(tabs[0].url).hostname);
      } catch (_) {
        resolve("—");
      }
    });
  });
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}

function fmtTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch (_) {
    return "—";
  }
}

function decisionClass(d) {
  const x = (d || "").toLowerCase();
  if (x === "approve") return "approve";
  if (x === "redact") return "redact";
  if (x === "warning") return "warning";
  return "block";
}

function decisionLabel(d) {
  const x = (d || "").toLowerCase();
  if (x === "approve") return "APPROVE";
  if (x === "redact") return "REDACT";
  if (x === "warning") return "WARNING";
  return "BLOCK";
}

function buildViolationBreakdown(last5) {
  const counts = {};
  (last5 || []).forEach((r) => {
    (r.types || []).forEach((t) => { counts[t] = (counts[t] || 0) + 1; });
  });
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return "";
  return entries.map(([type, n]) => `<span class="aegis-vio-tag">${escapeHtml(type)}: ${n}</span>`).join(" ");
}

function exportSessionLog(ses) {
  const data = JSON.stringify(ses || {}, null, 2);
  const blob = new Blob([data], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "aegis-session-" + new Date().toISOString().slice(0, 10) + ".json";
  a.click();
  URL.revokeObjectURL(url);
}

document.addEventListener("DOMContentLoaded", async () => {
  const stored = await new Promise((r) => chrome.storage.local.get(["aegis_api_base", "aegis_notify_on_block"], r));
  const apiBase = stored.aegis_api_base || DEFAULT_API;

  document.getElementById("aegis-api-input").value = apiBase;
  document.getElementById("aegis-notify-toggle").checked = !!stored.aegis_notify_on_block;

  document.getElementById("aegis-api-input").addEventListener("blur", (e) => {
    const v = (e.target.value || "").trim();
    chrome.storage.local.set({ aegis_api_base: v || DEFAULT_API });
  });
  document.getElementById("aegis-notify-toggle").addEventListener("change", (e) => {
    chrome.storage.local.set({ aegis_notify_on_block: e.target.checked });
  });

  const connected = await checkBackend(apiBase);
  const onLLM = await isOnLLMSite();
  const host = await getHost();

  document.getElementById("aegis-current-site").textContent = host;
  document.getElementById("aegis-site-status").textContent = onLLM ? "PROTECTED" : "—";
  document.getElementById("aegis-site-status").className = "aegis-status-badge " + (onLLM ? "aegis-status-protected" : "aegis-status-inactive");
  document.getElementById("aegis-backend-status").textContent = connected ? "CONNECTED" : "OFFLINE";
  document.getElementById("aegis-backend-status").className = "aegis-status-badge " + (connected ? "aegis-status-connected" : "aegis-status-offline");
  document.getElementById("aegis-live-badge").textContent = connected ? "● Live" : "● Offline";
  document.getElementById("aegis-live-badge").className = "aegis-live-badge " + (connected ? "aegis-live-on" : "aegis-live-offline");

  chrome.storage.local.get(["aegis_session", "aegis_paused"], (d) => {
    const ses = d.aegis_session || {};
    const checked = ses.total_checked || 0;
    const blocked = ses.total_blocked || 0;
    const redacted = ses.total_redacted || 0;
    const avgRisk = checked > 0 ? ((ses.risk_sum || 0) / checked).toFixed(2) : "0.00";

    document.getElementById("aegis-stat-checked").textContent = checked;
    document.getElementById("aegis-stat-blocked").textContent = blocked;
    document.getElementById("aegis-stat-redacted").textContent = redacted;
    document.getElementById("aegis-stat-risk").textContent = avgRisk;

    const breakdownHtml = buildViolationBreakdown(ses.last_5);
    const breakdownEl = document.getElementById("aegis-violation-breakdown");
    if (breakdownHtml) {
      breakdownEl.innerHTML = "<span class='aegis-breakdown-label'>Top violations:</span> " + breakdownHtml;
      breakdownEl.style.display = "block";
    } else {
      breakdownEl.style.display = "none";
    }

    const list = (ses.last_5 || []).slice(0, 5);
    const tbody = document.getElementById("aegis-log-body");
    const empty = document.getElementById("aegis-log-empty");
    if (list.length === 0) {
      tbody.innerHTML = "";
      empty.style.display = "block";
    } else {
      empty.style.display = "none";
      tbody.innerHTML = list.map((row) => `
        <tr>
          <td>${escapeHtml(fmtTime(row.ts))}</td>
          <td>${escapeHtml((row.site || "—").slice(0, 12))}</td>
          <td><span class="aegis-decision-badge aegis-dec-${decisionClass(row.decision)}">${decisionLabel(row.decision)}</span></td>
          <td>${(row.risk || 0).toFixed(2)}</td>
        </tr>
      `).join("");
    }

    document.getElementById("aegis-export-btn").addEventListener("click", () => exportSessionLog(ses));

    const toggle = document.getElementById("aegis-pause-toggle");
    toggle.checked = !!d.aegis_paused;
    toggle.addEventListener("change", (e) => {
      chrome.storage.local.set({ aegis_paused: e.target.checked });
    });
  });
});
