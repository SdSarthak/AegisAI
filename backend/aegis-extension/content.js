/*
 * AEGIS Guard — Chrome Extension
 * Zero detection logic. Pure UI middleware.
 * Backend at localhost:8000 is the only brain.
 * Team Neo · TechSynapse 2026
 */

(function () {
  "use strict";

  const DEFAULT_API_BASE = "http://localhost:8000";
  const FETCH_TIMEOUT_MS = 5000;
  const FETCH_RETRY_COUNT = 2;
  const PAUSE_MS = 1800;
  const RECHECK_ON_DELETE_MS = 400;
  const PASTE_DEBOUNCE_MS = 300;
  const BLOCK_INTERVAL_MS = 150;
  const MIN_TEXT_LENGTH = 5;

  const SITE_CONFIG = {
    "chatgpt.com": {
      inputSelectors: ["#prompt-textarea"],
      submitSelectors: ['button[data-testid="send-button"]'],
    },
    "chat.openai.com": {
      inputSelectors: ["#prompt-textarea", "textarea[placeholder*='Message']", "form textarea"],
      submitSelectors: ['button[data-testid="send-button"]', 'button[aria-label*="Send"]'],
    },
    "claude.ai": {
      inputSelectors: ['.ProseMirror[contenteditable="true"]', 'div[contenteditable="true"]'],
      submitSelectors: ['button[aria-label="Send message"]', 'button[aria-label*="Send"]'],
    },
    "gemini.google.com": {
      inputSelectors: ["div.ql-editor", "rich-textarea textarea", "textarea.input-area"],
      submitSelectors: ["button.send-button", 'button[aria-label*="Send"]'],
    },
    "copilot.microsoft.com": {
      inputSelectors: ["cib-text-input textarea", "#userInput", "textarea"],
      submitSelectors: ["button#send-button", "cib-action-bar button[type='submit']", 'button[aria-label*="Send"]'],
    },
    "bing.com": {
      inputSelectors: ["cib-text-input textarea", "#userInput", "textarea"],
      submitSelectors: ["button#send-button", 'button[aria-label*="Send"]'],
    },
  };

  const FALLBACK_INPUTS = ["textarea", 'div[contenteditable="true"]'];
  const FALLBACK_SUBMITS = ['button[type="submit"]', 'button[aria-label*="Send"]', 'form button:last-of-type'];

  const INTENT_PATTERNS = [
    /my (api|auth|secret|private) key is/i,
    /my (ssn|social security) (number )?is/i,
    /my (password|passwd) is/i,
    /my credit card (number )?is/i,
    /my (passport|aadhar|pan) (number )?is/i,
  ];

  let pauseTimer = null;
  let lastAnalyzedText = "";
  let currentViolations = [];
  let aegisBlocked = false;
  let currentInputEl = null;
  let aegisOverlay = null;
  let blockInterval = null;
  let apiBase = DEFAULT_API_BASE;

  function getSiteHost() {
    return window.location.hostname.replace(/^www\./, "");
  }

  function getApiBase() {
    return apiBase;
  }

  function getApiUrl() {
    return getApiBase().replace(/\/$/, "") + "/analyze";
  }

  function getConfig() {
    const host = getSiteHost();
    const cfg = SITE_CONFIG[host];
    if (cfg) return cfg;
    return { inputSelectors: FALLBACK_INPUTS, submitSelectors: FALLBACK_SUBMITS };
  }

  function getPromptText() {
    const el = currentInputEl;
    if (!el) return "";
    if (el.tagName === "TEXTAREA") return el.value || "";
    return (el.textContent || el.innerText || "").trim();
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s || "";
    return div.innerHTML;
  }

  class AegisOverlay {
    constructor(inputEl) {
      this.input = inputEl;
      this.overlay = document.createElement("div");
      this.overlay.id = "aegis-overlay";
      this.overlay.className = "aegis-overlay";
      document.body.appendChild(this.overlay);
      this.resizeObs = new ResizeObserver(() => this.sync());
      this.resizeObs.observe(inputEl);
      document.addEventListener("scroll", () => this.sync(), true);
      this.sync();
    }

    sync() {
      const r = this.input.getBoundingClientRect();
      const s = window.getComputedStyle(this.input);
      const props = ["font", "fontSize", "fontFamily", "fontWeight", "lineHeight", "letterSpacing", "padding", "paddingTop", "paddingLeft", "paddingRight", "paddingBottom", "borderWidth", "boxSizing"];
      props.forEach((p) => { this.overlay.style[p] = s[p] || ""; });
      this.overlay.style.position = "fixed";
      this.overlay.style.left = r.left + "px";
      this.overlay.style.top = r.top + "px";
      this.overlay.style.width = r.width + "px";
      this.overlay.style.height = r.height + "px";
      this.overlay.style.background = "transparent";
      this.overlay.style.color = "transparent";
      this.overlay.style.pointerEvents = "none";
      this.overlay.style.zIndex = "9998";
      this.overlay.style.overflow = "hidden";
      this.overlay.style.whiteSpace = "pre-wrap";
      this.overlay.style.wordWrap = "break-word";
    }

    render(fullText, violations) {
      let content = this.overlay.querySelector(".aegis-overlay-content");
      if (!content) {
        content = document.createElement("div");
        content.className = "aegis-overlay-content";
        this.overlay.appendChild(content);
      }
      if (!violations || violations.length === 0) {
        content.innerHTML = escapeHtml(fullText);
        return;
      }
      const sorted = [...violations].sort((a, b) => (a.start || 0) - (b.start || 0));
      let html = "";
      let cursor = 0;
      const colors = { low: "#FFD600", medium: "#FF6D00", high: "#FF1744", critical: "#D50000" };
      sorted.forEach((v) => {
        const start = v.start ?? 0;
        const end = v.end ?? start + (v.value || "").length;
        if (start > cursor) html += escapeHtml(fullText.slice(cursor, start));
        const c = colors[v.severity] || "#FF1744";
        html += `<span class="aegis-violation" data-type="${escapeHtml(v.type)}" data-replacement="${escapeHtml(v.replacement || "[REDACTED]")}" data-original="${escapeHtml((v.value || "").slice(0, 50))}" style="text-decoration:underline wavy ${c};background:${c}18;border-radius:2px;cursor:pointer;pointer-events:all;">${escapeHtml(fullText.slice(start, end))}</span>`;
        cursor = end;
      });
      if (cursor < fullText.length) html += escapeHtml(fullText.slice(cursor));
      content.innerHTML = html;
      content.querySelectorAll(".aegis-violation").forEach((span) => {
        span.addEventListener("click", (e) => {
          e.stopPropagation();
          showReplacementTooltip(span);
        });
      });
    }

    clear() {
      const content = this.overlay.querySelector(".aegis-overlay-content");
      if (content) content.innerHTML = "";
    }

    destroy() {
      this.resizeObs?.disconnect();
      this.overlay?.remove();
    }
  }

  function showReplacementTooltip(anchorEl) {
    removeTooltip();
    const type = anchorEl.dataset.type || "PII";
    const replacement = anchorEl.dataset.replacement || "[REDACTED]";
    const original = anchorEl.dataset.original || anchorEl.textContent || "";
    const rect = anchorEl.getBoundingClientRect();
    const tip = document.createElement("div");
    tip.id = "aegis-tooltip";
    tip.className = "aegis-tooltip";
    const severityColors = { SSN: "#FF1744", CREDIT_CARD: "#FF1744", API_KEY: "#FF1744", EMAIL: "#FF6D00", PHONE: "#FF6D00", IP_ADDRESS: "#FF6D00", NAME: "#FFD600", MEDICAL: "#FF1744", FINANCIAL: "#FF6D00" };
    const color = severityColors[type] || "#FF1744";
    tip.innerHTML = `
      <div class="aegis-tooltip-header">
        <span class="aegis-tooltip-type" style="background:${color}22;color:${color};border:1px solid ${color}44;">${escapeHtml(type)}</span>
        <span class="aegis-tooltip-sub">Sensitive data detected</span>
      </div>
      <div class="aegis-tooltip-section">
        <div class="aegis-tooltip-label">Detected:</div>
        <div class="aegis-tooltip-detected">${escapeHtml(original)}</div>
      </div>
      <div class="aegis-tooltip-section">
        <div class="aegis-tooltip-label">Suggested replacement:</div>
        <div class="aegis-tooltip-replacement">${escapeHtml(replacement)}</div>
      </div>
      <div class="aegis-tooltip-actions">
        <button id="aegis-apply-replacement" class="aegis-tooltip-apply">Apply replacement</button>
        <button id="aegis-dismiss-tooltip" class="aegis-tooltip-dismiss">Ignore</button>
      </div>
      <div class="aegis-tooltip-footer">This interaction is being logged by AEGIS</div>
    `;
    tip.style.left = rect.left + "px";
    tip.style.top = (rect.bottom + 4) + "px";
    document.body.appendChild(tip);
    document.getElementById("aegis-apply-replacement").addEventListener("click", () => {
      applyReplacement(original, replacement);
      removeTooltip();
      setTimeout(() => runAnalysis(getPromptText()), 300);
    });
    document.getElementById("aegis-dismiss-tooltip").addEventListener("click", removeTooltip);
    setTimeout(() => document.addEventListener("click", removeTooltip, { once: true }), 50);
  }

  function removeTooltip() {
    const t = document.getElementById("aegis-tooltip");
    if (t) t.remove();
  }

  function applyReplacement(original, replacement) {
    const input = currentInputEl;
    if (!input) return;
    if (input.tagName === "TEXTAREA") {
      const val = input.value;
      const next = val.replace(original, replacement || "[REDACTED]");
      if (next === val) return;
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
      setter.call(input, next);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    } else if (input.contentEditable === "true") {
      const text = input.textContent || "";
      const next = text.replace(original, replacement || "[REDACTED]");
      if (next !== text) {
        input.textContent = next;
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }
  }

  function showStatusDot(state) {
    if (!aegisOverlay) return;
    let wrap = aegisOverlay.overlay.querySelector(".aegis-status-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "aegis-status-wrap";
      wrap.style.pointerEvents = "none";
      aegisOverlay.overlay.insertBefore(wrap, aegisOverlay.overlay.firstChild);
    }
    let dot = wrap.querySelector(".aegis-status-dot");
    if (!dot) {
      dot = document.createElement("span");
      dot.className = "aegis-status-dot";
      wrap.appendChild(dot);
    }
    dot.className = "aegis-status-dot aegis-status-" + (state || "none");
  }

  function removeStatusDot() {
    const w = aegisOverlay?.overlay?.querySelector(".aegis-status-wrap");
    if (w) w.remove();
  }

  function showRiskMeter(riskNorm) {
    let wrap = document.getElementById("aegis-risk-wrap");
    if (!wrap && currentInputEl) {
      wrap = document.createElement("div");
      wrap.id = "aegis-risk-wrap";
      wrap.className = "aegis-risk-wrap";
      const parent = currentInputEl.closest("form") || currentInputEl.parentElement;
      if (parent) parent.insertBefore(wrap, currentInputEl);
      else document.body.appendChild(wrap);
    }
    if (!wrap) return;
    let track = wrap.querySelector(".aegis-risk-track");
    let fill = wrap.querySelector(".aegis-risk-fill");
    let label = wrap.querySelector(".aegis-risk-label");
    if (!track) {
      track = document.createElement("div");
      track.className = "aegis-risk-track";
      wrap.appendChild(track);
    }
    if (!fill) {
      fill = document.createElement("div");
      fill.className = "aegis-risk-fill";
      track.appendChild(fill);
    }
    if (!label) {
      label = document.createElement("span");
      label.className = "aegis-risk-label";
      wrap.appendChild(label);
    }
    const r = Math.min(1, Math.max(0, riskNorm || 0));
    fill.style.width = (r * 100) + "%";
    fill.className = "aegis-risk-fill aegis-risk-" + (r <= 0.3 ? "low" : r <= 0.6 ? "med" : r <= 0.8 ? "high" : "crit");
    label.textContent = "AEGIS " + r.toFixed(2);
  }

  function removeRiskMeter() {
    const w = document.getElementById("aegis-risk-wrap");
    if (w) w.remove();
  }

  function showCheckingIndicator() {
    showStatusDot("checking");
  }

  function clearAllAegisUI() {
    if (aegisOverlay) aegisOverlay.clear();
    removeTooltip();
    removeStatusDot();
    removeRiskMeter();
    hideWarningBanner();
  }

  function updateIcon(status) {
    try { chrome.runtime.sendMessage({ type: "SET_ICON", status }).catch(() => {}); } catch (_) {}
  }

  async function runAnalysis(text) {
    if (!text || text.trim().length < MIN_TEXT_LENGTH) {
      clearAllAegisUI();
      clearBlock();
      currentViolations = [];
      aegisBlocked = false;
      updateIcon("grey");
      return;
    }
    showCheckingIndicator();
    let data;
    let lastErr;
    for (let attempt = 0; attempt <= FETCH_RETRY_COUNT; attempt++) {
      try {
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
        const res = await fetch(getApiUrl(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text }),
          mode: "cors",
          signal: ctrl.signal,
        });
        clearTimeout(t);
        if (!res.ok) throw new Error(res.statusText);
        data = await res.json();
        lastErr = null;
        break;
      } catch (e) {
        lastErr = e;
        if (attempt < FETCH_RETRY_COUNT) await new Promise((r) => setTimeout(r, 500));
      }
    }
    if (lastErr || !data) {
      clearAllAegisUI();
      clearBlock();
      aegisBlocked = false;
      showStatusDot("offline");
      updateIcon("orange");
      return;
    }
    const violations = data.violations || [];
    let riskNorm = typeof data.risk_score === "number" ? data.risk_score : 0;
    if (riskNorm > 1) riskNorm /= 100;
    for (const v of violations) {
      if (v.start == null && v.value) {
        const idx = text.indexOf(v.value);
        if (idx >= 0) v.start = idx, v.end = idx + v.value.length;
      }
    }
    lastAnalyzedText = text;
    showRiskMeter(riskNorm);

    if (data.violations && data.violations.length > 0) {
      logToBackend(text, data);
      updateSessionStorage(data.decision, riskNorm, violations.map((x) => x.type));
      currentViolations = violations;
      handleViolation(text, violations);
      enableBlock();
    } else {
      currentViolations = [];
      const intentMatch = INTENT_PATTERNS.some((re) => re.test(text));
      if (intentMatch) {
        logToBackend(text, { ...data, decision: "warning" });
        updateSessionStorage("warning", riskNorm, []);
        handleIntentWarning(text, riskNorm);
      } else {
        logToBackend(text, data);
        updateSessionStorage(data.decision, riskNorm, []);
        handleClean(text, riskNorm);
      }
      clearBlock();
    }
  }

  function handleIntentWarning(text, riskNorm) {
    aegisBlocked = false;
    if (aegisOverlay) aegisOverlay.clear();
    showStatusDot("clean");
    showRiskMeter(riskNorm);
    updateIcon("green");
    showWarningBanner();
  }

  function showWarningBanner() {
    hideWarningBanner();
    const banner = document.createElement("div");
    banner.id = "aegis-warning-banner";
    banner.className = "aegis-warning-banner";
    banner.textContent = "⚠ AEGIS: You appear to be about to share sensitive data. Proceed with caution.";
    const parent = currentInputEl?.closest("form") || currentInputEl?.parentElement;
    if (parent) parent.insertBefore(banner, currentInputEl);
    else document.body.insertBefore(banner, document.body.firstChild);
  }

  function hideWarningBanner() {
    document.getElementById("aegis-warning-banner")?.remove();
  }

  function handleViolation(text, violations) {
    aegisBlocked = true;
    if (aegisOverlay) aegisOverlay.render(text, violations);
    showStatusDot("violation");
    updateIcon("red");
    chrome.storage.local.get(["aegis_notify_on_block"], (d) => {
      if (d.aegis_notify_on_block) {
        try {
          chrome.runtime.sendMessage({ type: "NOTIFY_BLOCK", types: violations.map((v) => v.type) }).catch(() => {});
        } catch (_) {}
      }
    });
  }

  function handleClean(text, riskNorm) {
    hideWarningBanner();
    aegisBlocked = false;
    if (aegisOverlay) aegisOverlay.clear();
    showStatusDot("clean");
    showRiskMeter(riskNorm);
    updateIcon("green");
  }

  function enableBlock() {
    if (blockInterval) return;
    blockInterval = setInterval(blockSubmit, BLOCK_INTERVAL_MS);
    blockSubmit();
  }

  function clearBlock() {
    aegisBlocked = false;
    if (blockInterval) { clearInterval(blockInterval); blockInterval = null; }
    const cfg = getConfig();
    [...cfg.submitSelectors, ...FALLBACK_SUBMITS].forEach((sel) => {
      try {
        document.querySelectorAll(sel).forEach((btn) => {
          if (btn.getAttribute("data-aegis-blocked")) {
            btn.disabled = false;
            btn.removeAttribute("data-aegis-blocked");
            btn.style.cssText = btn.style.cssText.replace(/pointer-events:\s*none\s*!important;?/g, "").replace(/opacity:\s*0\.4\s*!important;?/g, "");
          }
        });
      } catch (_) {}
    });
  }

  function blockSubmit() {
    if (!aegisBlocked) return;
    const cfg = getConfig();
    const all = [...cfg.submitSelectors, ...FALLBACK_SUBMITS];
    const seen = new Set();
    all.forEach((sel) => {
      try {
        document.querySelectorAll(sel).forEach((btn) => {
          if (seen.has(btn)) return;
          seen.add(btn);
          btn.disabled = true;
          btn.setAttribute("data-aegis-blocked", "true");
          btn.style.cssText += ";pointer-events:none!important;opacity:0.4!important;";
        });
      } catch (_) {}
    });
  }

  function shakeInput() {
    const input = currentInputEl;
    if (!input) return;
    input.style.animation = "aegis-shake 0.4s ease";
    setTimeout(() => { input.style.animation = ""; }, 400);
    const first = currentViolations[0];
    if (first && aegisOverlay) {
      const span = aegisOverlay.overlay.querySelector(".aegis-violation");
      if (span) {
        span.style.animation = "aegis-flash 1s ease";
        setTimeout(() => { span.style.animation = ""; }, 1000);
        showReplacementTooltip(span);
      }
    }
  }

  function logToBackend(text, data) {
    const body = {
      user: "aegis-guard-user",
      dept: "browser-extension",
      prompt_preview: (text || "").slice(0, 60),
      decision: data.decision || "approve",
      risk_score: data.risk_score ?? 0,
      violation_types: (data.violations || []).map((v) => v.type),
      site: getSiteHost(),
      source: "AEGIS Guard",
      timestamp: new Date().toISOString(),
    };
    ["/log", "/api/log", "/decisions/log", "/kavvach/log", "/analyze/log"].forEach((path) => {
      fetch(getApiBase().replace(/\/$/, "") + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        mode: "cors",
      }).catch(() => {});
    });
  }

  function updateSessionStorage(decision, risk, types) {
    chrome.storage.local.get(["aegis_session", "aegis_paused"], (d) => {
      if (d.aegis_paused) return;
      let ses = d.aegis_session || { total_checked: 0, total_blocked: 0, total_redacted: 0, risk_sum: 0, last_5: [] };
      ses.total_checked = (ses.total_checked || 0) + 1;
      if (decision === "block") ses.total_blocked = (ses.total_blocked || 0) + 1;
      else if (decision === "redact" || decision === "warning") ses.total_redacted = (ses.total_redacted || 0) + 1;
      ses.risk_sum = (ses.risk_sum || 0) + risk;
      ses.last_5 = [{ ts: new Date().toISOString(), site: getSiteHost(), decision, risk, types: types || [] }, ...(ses.last_5 || []).slice(0, 4)];
      chrome.storage.local.set({ aegis_session: ses });
    });
  }

  function onInput(text, isPaste) {
    clearTimeout(pauseTimer);
    if (text.trim().length < MIN_TEXT_LENGTH) {
      clearAllAegisUI();
      clearBlock();
      aegisBlocked = false;
      lastAnalyzedText = "";
      currentViolations = [];
      updateIcon("grey");
      return;
    }
    const isDeleting = text.length < lastAnalyzedText.length;
    let delay = isDeleting ? RECHECK_ON_DELETE_MS : PAUSE_MS;
    if (isPaste) delay = Math.min(delay, PASTE_DEBOUNCE_MS);
    showCheckingIndicator();
    pauseTimer = setTimeout(async () => {
      if (text === lastAnalyzedText) return;
      await runAnalysis(text);
    }, delay);
  }

  function getActiveInput() {
    return currentInputEl;
  }

  document.addEventListener("submit", (e) => {
    if (aegisBlocked) { e.preventDefault(); e.stopImmediatePropagation(); return false; }
  }, true);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && aegisBlocked) {
      e.preventDefault();
      e.stopImmediatePropagation();
      shakeInput();
      return false;
    }
  }, true);

  function isLikelyPromptInput(el) {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    if (r.width < 80 || r.height < 24) return false;
    const st = window.getComputedStyle(el);
    if (st.visibility === "hidden" || st.display === "none") return false;
    return true;
  }

  function attach(inputEl) {
    if (inputEl.dataset.aegisAttached) return;
    inputEl.dataset.aegisAttached = "1";
    currentInputEl = inputEl;
    if (aegisOverlay) aegisOverlay.destroy();
    aegisOverlay = new AegisOverlay(inputEl);
    showRiskMeter(0);
    const handler = () => onInput(getPromptText(), false);
    const pasteHandler = () => {
      setTimeout(() => onInput(getPromptText(), true), 50);
    };
    inputEl.addEventListener("input", handler);
    inputEl.addEventListener("paste", pasteHandler);
    if (inputEl.contentEditable === "true") inputEl.addEventListener("keyup", handler);
  }

  function findAndAttach() {
    chrome.storage.local.get(["aegis_paused"], (d) => {
      if (d.aegis_paused) {
        clearAllAegisUI();
        clearBlock();
        const banner = document.getElementById("aegis-paused-banner");
        if (!banner) {
          const b = document.createElement("div");
          b.id = "aegis-paused-banner";
          b.className = "aegis-paused-banner";
          b.textContent = "AEGIS paused — prompts not being checked";
          document.body.appendChild(b);
        }
        return;
      }
      document.getElementById("aegis-paused-banner")?.remove();
      const cfg = getConfig();
      for (const sel of cfg.inputSelectors) {
        try {
          const els = document.querySelectorAll(sel);
          for (const el of els) {
            if (!isLikelyPromptInput(el)) continue;
            attach(el);
            return;
          }
        } catch (_) {}
      }
    });
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "REANALYZE") {
      const t = getPromptText();
      if (t.trim().length >= MIN_TEXT_LENGTH) runAnalysis(t);
    }
  });

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes.aegis_api_base?.newValue) {
      apiBase = changes.aegis_api_base.newValue || DEFAULT_API_BASE;
    }
    if (area === "local" && changes.aegis_paused?.newValue) {
      clearAllAegisUI();
      clearBlock();
      aegisBlocked = false;
    }
  });

  const obs = new MutationObserver(() => findAndAttach());
  obs.observe(document.body, { childList: true, subtree: true });
  setInterval(() => { findAndAttach(); if (aegisBlocked) blockSubmit(); }, 2000);

  chrome.storage.local.get(["aegis_api_base"], (d) => {
    apiBase = d.aegis_api_base || DEFAULT_API_BASE;
  });

  document.addEventListener("keydown", (e) => {
    if (e.altKey && e.shiftKey && e.key === "R") {
      e.preventDefault();
      const t = getPromptText();
      if (t.trim().length >= MIN_TEXT_LENGTH) runAnalysis(t);
    }
  }, true);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => setTimeout(findAndAttach, 800));
  } else {
    setTimeout(findAndAttach, 500);
  }
})();
