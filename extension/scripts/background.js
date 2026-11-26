/**
 * extension/scripts/background.js
 * Background service worker for PhishTrap Chrome Extension.
 * Intercepts tab navigation, queries PhishTrap /api/v1/predict,
 * and updates extension badge and page warning state.
 */

const DEFAULT_API_BASE = "http://localhost:8000";
const CACHE_TTL_MS = 5 * 60 * 1000; // 5-minute cache per URL
const urlCache = new Map();

// Helper to get configured API base
async function getApiBase() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["apiBaseUrl"], (res) => {
      resolve(res.apiBaseUrl || DEFAULT_API_BASE);
    });
  });
}

// Predict safety of a URL via PhishTrap API
async function evaluateUrl(url) {
  if (!url || !url.startsWith("http")) {
    return null;
  }

  // Check in-memory cache
  const cached = urlCache.get(url);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return cached.data;
  }

  const apiBase = await getApiBase();
  const endpoint = `${apiBase.replace(/\/+$/, "")}/api/v1/predict`;

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls: [url] })
    });

    if (!response.ok) {
      console.warn("[PhishTrap] API returned status", response.status);
      return null;
    }

    const data = await response.json();
    urlCache.set(url, { timestamp: Date.now(), data });
    return data;
  } catch (err) {
    console.debug("[PhishTrap] Background scan error (server may be offline):", err.message);
    return null;
  }
}

// Update the extension badge icon based on triage decision
function updateBadge(tabId, result) {
  if (!result) {
    chrome.action.setBadgeText({ tabId, text: "" });
    return;
  }

  const decision = result.automated_decision;
  const score = result.max_score || 0;

  if (decision === "QUARANTINE" || decision === "AUTO_QUARANTINE") {
    chrome.action.setBadgeText({ tabId, text: "!" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#EF4444" }); // Red
    chrome.action.setTitle({
      tabId,
      title: `PhishTrap: DANGER! High-risk phishing detected (${(score * 100).toFixed(1)}% risk)`
    });
  } else if (decision === "HUMAN_REVIEW" || decision === "REVIEW") {
    chrome.action.setBadgeText({ tabId, text: "?" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#F59E0B" }); // Amber
    chrome.action.setTitle({
      tabId,
      title: `PhishTrap: SUSPICIOUS. Flagged for SecOps review (${(score * 100).toFixed(1)}% risk)`
    });
  } else {
    chrome.action.setBadgeText({ tabId, text: "OK" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#10B981" }); // Emerald
    chrome.action.setTitle({
      tabId,
      title: `PhishTrap: SAFE site (${(score * 100).toFixed(1)}% risk)`
    });
  }
}

// Listen for tab navigation and URL changes
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url && tab.url.startsWith("http")) {
    const result = await evaluateUrl(tab.url);
    if (result) {
      updateBadge(tabId, result);

      // If threat is confirmed quarantine, send message to content script to display warning banner
      if (result.automated_decision === "QUARANTINE" || result.automated_decision === "AUTO_QUARANTINE") {
        try {
          chrome.tabs.sendMessage(tabId, {
            action: "SHOW_THREAT_BANNER",
            result
          });
        } catch (e) {
          // Tab might not be ready or content script not mounted
        }
      }
    }
  }
});

// Setup right-click context menu to scan any clicked link
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "phishtrap-scan-link",
    title: "🛡️ Scan link with PhishTrap",
    contexts: ["link"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "phishtrap-scan-link" && info.linkUrl) {
    const result = await evaluateUrl(info.linkUrl);
    if (result && tab.id) {
      chrome.tabs.sendMessage(tab.id, {
        action: "SHOW_LINK_POPUP",
        linkUrl: info.linkUrl,
        result
      });
    }
  }
});

// Handle requests from popup.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "EVALUATE_URL") {
    evaluateUrl(message.url).then((res) => sendResponse({ result: res }));
    return true; // Keep channel open for async response
  }
});
