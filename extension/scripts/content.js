/**
 * extension/scripts/content.js
 * In-page threat interception and warning alerts for PhishTrap.
 */

// Listen for messages from background.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "SHOW_THREAT_BANNER") {
    injectThreatBanner(message.result);
  } else if (message.action === "SHOW_LINK_POPUP") {
    injectLinkVerdictModal(message.linkUrl, message.result);
  }
});

function injectThreatBanner(result) {
  // Prevent duplicate banners
  if (document.getElementById("phishtrap-security-banner")) return;

  const score = result.max_score ? (result.max_score * 100).toFixed(1) : "95.0";
  const defanged = result.urls && result.urls[0] ? result.urls[0].defanged_url : window.location.hostname;
  const signals = result.urls && result.urls[0] && result.urls[0].top_features
    ? result.urls[0].top_features.slice(0, 3).join(", ")
    : "Suspicious lexical structure";

  const banner = document.createElement("div");
  banner.id = "phishtrap-security-banner";
  banner.setAttribute("style", `
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100% !important;
    z-index: 2147483647 !important;
    background: linear-gradient(135deg, #7F1D1D 0%, #991B1B 100%) !important;
    color: #FFFFFF !important;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    padding: 14px 24px !important;
    box-sizing: border-box !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    font-size: 14px !important;
    line-height: 1.4 !important;
  `);

  banner.innerHTML = `
    <div style="display: flex; align-items: center; gap: 14px;">
      <div style="font-size: 26px;">🛡️</div>
      <div>
        <div style="font-weight: 700; font-size: 15px; letter-spacing: 0.3px; color: #FEE2E2;">
          PhishTrap Alert: High-Risk Phishing Threat Detected! (${score}% Risk)
        </div>
        <div style="font-size: 12px; color: #FCA5A5; margin-top: 2px;">
          Target: <code style="background: rgba(0,0,0,0.25); padding: 2px 6px; border-radius: 4px; font-family: monospace;">${defanged}</code>
          &nbsp;|&nbsp; Signals: ${signals}
        </div>
      </div>
    </div>
    <div style="display: flex; align-items: center; gap: 10px;">
      <button id="phishtrap-btn-leave" style="
        background: #FFFFFF !important;
        color: #991B1B !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 8px 16px !important;
        border-radius: 6px !important;
        cursor: pointer !important;
        font-size: 13px !important;
      ">
        ← Leave to Safety
      </button>
      <button id="phishtrap-btn-dismiss" style="
        background: rgba(0, 0, 0, 0.25) !important;
        color: #FEE2E2 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        padding: 8px 14px !important;
        border-radius: 6px !important;
        cursor: pointer !important;
        font-size: 13px !important;
      ">
        Dismiss
      </button>
    </div>
  `;

  document.documentElement.appendChild(banner);

  document.getElementById("phishtrap-btn-leave").addEventListener("click", () => {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      window.location.href = "about:blank";
    }
  });

  document.getElementById("phishtrap-btn-dismiss").addEventListener("click", () => {
    banner.remove();
  });
}

function injectLinkVerdictModal(url, result) {
  const existing = document.getElementById("phishtrap-link-modal");
  if (existing) existing.remove();

  const decision = result.automated_decision || "UNKNOWN";
  const score = (result.max_score * 100).toFixed(1);
  const isPhish = decision === "QUARANTINE" || decision === "AUTO_QUARANTINE";
  const isReview = decision === "HUMAN_REVIEW" || decision === "REVIEW";

  const color = isPhish ? "#EF4444" : (isReview ? "#F59E0B" : "#10B981");
  const badgeTitle = isPhish ? "🔴 DANGEROUS PHISHING" : (isReview ? "🟡 SUSPICIOUS (Review)" : "🟢 VERIFIED SAFE");

  const modal = document.createElement("div");
  modal.id = "phishtrap-link-modal";
  modal.setAttribute("style", `
    position: fixed !important;
    bottom: 24px !important;
    right: 24px !important;
    width: 360px !important;
    z-index: 2147483647 !important;
    background: #0F172A !important;
    color: #F8FAFC !important;
    border: 1px solid ${color} !important;
    border-radius: 12px !important;
    padding: 16px !important;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
  `);

  modal.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <span style="font-size: 12px; font-weight: 700; color: ${color};">${badgeTitle}</span>
      <button id="phishtrap-modal-close" style="background:none; border:none; color:#94A3B8; font-size:16px; cursor:pointer;">✕</button>
    </div>
    <div style="font-size: 13px; font-weight: 600; margin-bottom: 6px;">
      Probability Score: <span style="color: ${color};">${score}%</span>
    </div>
    <div style="background: #1E293B; padding: 8px; border-radius: 6px; font-family: monospace; font-size: 11px; word-break: break-all; color: #CBD5E1; margin-bottom: 10px;">
      ${url}
    </div>
    <div style="text-align: right;">
      <button id="phishtrap-modal-ok" style="background: ${color}; color: #0F172A; font-weight: 700; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px;">Got It</button>
    </div>
  `;

  document.documentElement.appendChild(modal);

  const close = () => modal.remove();
  document.getElementById("phishtrap-modal-close").addEventListener("click", close);
  document.getElementById("phishtrap-modal-ok").addEventListener("click", close);

  setTimeout(close, 10000); // Auto-dismiss after 10s
}
