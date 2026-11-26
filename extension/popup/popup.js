/**
 * extension/popup/popup.js
 * Controller for PhishTrap popup UI.
 */

const DEFAULT_API_BASE = "http://localhost:8000";

let currentApiBase = DEFAULT_API_BASE;

document.addEventListener("DOMContentLoaded", async () => {
  // Load saved theme preference
  const storedTheme = await chrome.storage.local.get(["theme"]);
  const themeIcon = document.getElementById("theme-icon");
  if (storedTheme.theme === "light") {
    document.body.classList.add("light-theme");
    if (themeIcon) themeIcon.textContent = "🌙";
  } else {
    document.body.classList.remove("light-theme");
    if (themeIcon) themeIcon.textContent = "☀️";
  }

  // Load saved API base URL
  const stored = await chrome.storage.local.get(["apiBaseUrl"]);
  if (stored.apiBaseUrl) {
    currentApiBase = stored.apiBaseUrl;
    document.getElementById("api-url-input").value = currentApiBase;
  }
  updateConsoleLink(currentApiBase);

  // Check API health
  checkApiHealth();

  // Inspect current tab
  inspectCurrentTab();

  // Theme toggle listener
  document.getElementById("theme-toggle").addEventListener("click", async () => {
    const isLight = document.body.classList.toggle("light-theme");
    const icon = document.getElementById("theme-icon");
    if (isLight) {
      if (icon) icon.textContent = "🌙";
      await chrome.storage.local.set({ theme: "light" });
    } else {
      if (icon) icon.textContent = "☀️";
      await chrome.storage.local.set({ theme: "dark" });
    }
  });

  // Setup event listeners
  document.getElementById("btn-scan").addEventListener("click", handleManualScan);
  document.getElementById("manual-url").addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleManualScan();
  });

  document.getElementById("btn-settings-toggle").addEventListener("click", () => {
    const panel = document.getElementById("settings-panel");
    panel.style.display = panel.style.display === "none" ? "flex" : "none";
  });

  document.getElementById("btn-save-settings").addEventListener("click", async () => {
    const newBase = document.getElementById("api-url-input").value.trim() || DEFAULT_API_BASE;
    currentApiBase = newBase;
    await chrome.storage.local.set({ apiBaseUrl: newBase });
    updateConsoleLink(newBase);
    checkApiHealth();
    inspectCurrentTab();
    document.getElementById("settings-panel").style.display = "none";
  });
});

function updateConsoleLink(baseUrl) {
  const consoleLink = document.getElementById("btn-open-console");
  consoleLink.href = baseUrl;
}

async function checkApiHealth() {
  const dot = document.querySelector(".status-dot");
  const indicator = document.getElementById("api-status");
  try {
    const res = await fetch(`${currentApiBase.replace(/\/+$/, "")}/health`, { method: "GET" });
    if (res.ok) {
      dot.className = "status-dot online";
      indicator.title = "Connected to PhishTrap API";
    } else {
      dot.className = "status-dot offline";
      indicator.title = "PhishTrap API returned an error";
    }
  } catch (err) {
    dot.className = "status-dot offline";
    indicator.title = "PhishTrap API offline (start server on port 8000)";
  }
}

async function inspectCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const urlDisplay = document.getElementById("tab-url");
  const badge = document.getElementById("tab-badge");
  const scoreVal = document.getElementById("tab-score");
  const progress = document.getElementById("tab-progress");
  const signalsBox = document.getElementById("tab-signals");
  const signalsList = document.getElementById("tab-signals-list");

  if (!tab || !tab.url || !tab.url.startsWith("http")) {
    urlDisplay.textContent = tab ? tab.url || "Internal browser page" : "No active tab";
    badge.textContent = "SKIPPED";
    badge.className = "badge";
    scoreVal.textContent = "N/A";
    progress.style.width = "0%";
    return;
  }

  urlDisplay.textContent = tab.url;

  try {
    const res = await fetch(`${currentApiBase.replace(/\/+$/, "")}/api/v1/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls: [tab.url] })
    });

    if (!res.ok) throw new Error("API error");

    const data = await res.json();
    renderVerdict(data, badge, scoreVal, progress, signalsBox, signalsList, urlDisplay);
  } catch (err) {
    badge.textContent = "OFFLINE";
    badge.className = "badge";
    scoreVal.textContent = "N/A";
    urlDisplay.textContent = `${tab.url} (Server offline)`;
  }
}

function renderVerdict(data, badgeElem, scoreElem, progressElem, signalsBox, signalsList, urlDisplay) {
  const decision = data.automated_decision;
  const score = data.max_score || 0;
  const pct = Math.round(score * 100);

  scoreElem.textContent = `${pct}%`;
  progressElem.style.width = `${pct}%`;

  if (decision === "QUARANTINE" || decision === "AUTO_QUARANTINE") {
    badgeElem.textContent = "QUARANTINE";
    badgeElem.className = "badge quarantine";
    progressElem.className = "progress-bar-fill quarantine";
  } else if (decision === "HUMAN_REVIEW" || decision === "REVIEW") {
    badgeElem.textContent = "REVIEW";
    badgeElem.className = "badge review";
    progressElem.className = "progress-bar-fill review";
  } else {
    badgeElem.textContent = "ALLOW";
    badgeElem.className = "badge allow";
    progressElem.className = "progress-bar-fill allow";
  }

  // Defanged URL display if available
  if (data.urls && data.urls[0]) {
    urlDisplay.textContent = data.urls[0].defanged_url || data.urls[0].raw_url;

    const feats = data.urls[0].top_features || [];
    if (feats.length > 0) {
      signalsList.innerHTML = feats.map(f => `<li>${f}</li>`).join("");
      signalsBox.style.display = "block";
    } else {
      signalsBox.style.display = "none";
    }
  }
}

async function handleManualScan() {
  const input = document.getElementById("manual-url");
  const resultDiv = document.getElementById("manual-result");
  const raw = input.value.trim();

  if (!raw) return;

  resultDiv.style.display = "block";
  resultDiv.innerHTML = `<span style="color: #94A3B8;">Analyzing URL...</span>`;

  try {
    const res = await fetch(`${currentApiBase.replace(/\/+$/, "")}/api/v1/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls: [raw] })
    });

    if (!res.ok) throw new Error("API error");

    const data = await res.json();
    const decision = data.automated_decision;
    const score = (data.max_score * 100).toFixed(1);

    let color = "#10B981";
    let label = "SAFE";
    if (decision === "QUARANTINE" || decision === "AUTO_QUARANTINE") {
      color = "#EF4444";
      label = "QUARANTINE (Phishing)";
    } else if (decision === "HUMAN_REVIEW" || decision === "REVIEW") {
      color = "#F59E0B";
      label = "SUSPICIOUS (Review)";
    }

    const defanged = data.urls && data.urls[0] ? data.urls[0].defanged_url : raw;
    const signals = data.urls && data.urls[0] && data.urls[0].top_features
      ? data.urls[0].top_features.slice(0, 2).join("<br>")
      : "";

    resultDiv.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
        <span style="font-weight:700; color:${color};">${label}</span>
        <span style="font-weight:700; color:${color};">${score}%</span>
      </div>
      <div style="font-family:monospace; font-size:11px; color:var(--text-url); word-break:break-all; margin-bottom:4px;">
        ${defanged}
      </div>
      ${signals ? `<div style="font-size:10px; color:var(--text-muted); font-family:monospace;">${signals}</div>` : ""}
    `;
  } catch (err) {
    resultDiv.innerHTML = `<span style="color: #EF4444;">Scan failed: Is the PhishTrap API running?</span>`;
  }
}
