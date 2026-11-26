# PhishTrap Chrome Extension 🛡️
### Real-Time AI Phishing Link & Website Shield

The PhishTrap Chrome Extension protects users while browsing the web by analyzing visited websites and links against PhishTrap's calibrated hybrid ML classifier in real-time.

---

## Features
- **Live Tab Risk Scoring**: Automatically evaluates the active tab's URL and displays a dynamic toolbar badge:
  - 🟢 **OK**: Safe benign website ($p < 0.05$).
  - 🟡 **?**: Suspicious or ambiguous site flagged for SecOps review ($0.05 \le p < 0.85$).
  - 🔴 **!**: High-risk phishing threat ($p \ge 0.85$).
- **In-Page Interception Banner**: If the user visits a confirmed phishing site, an unmissable top banner warns the user and provides a **"Leave to Safety"** button.
- **Right-Click Link Inspection**: Right-click any link on any webpage and select **"🛡️ Scan link with PhishTrap"** to inspect its risk score before clicking.
- **Quick URL Scanner**: Click the extension icon to paste and test any suspicious URL from an email, SMS, or chat.
- **Cloud & Local Ready**: Configurable API endpoint so it works with local servers (`http://localhost:8000`) or cloud deployments (`https://your-phishtrap.onrender.com`).

---

## 30-Second Installation Guide

### Step 1: Start the PhishTrap Server
Ensure the PhishTrap API is running on your machine (or deployed on the cloud):
```powershell
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

### Step 2: Load Extension in Chrome / Edge / Brave
1. Open Google Chrome (or Microsoft Edge / Brave).
2. Navigate to:
   ```text
   chrome://extensions
   ```
3. Toggle on **Developer mode** in the top-right corner.
4. Click **Load unpacked** in the top-left corner.
5. Select the **`extension/`** folder inside your `PhishTrap` project directory:
   ```text
   c:\Users\Arsh\College\Semester 5\INT - 395\PhishTrap\extension
   ```
6. The PhishTrap shield icon will appear in your Chrome toolbar! (Click the puzzle piece icon to pin it).

---

## How to Test

### Test 1: Active Tab Badge
1. Open [https://python.org](https://python.org) in a tab. Notice the green **`OK`** badge.
2. Click the PhishTrap extension icon: it shows **`ALLOW (0.6% Risk)`** and the verified features.

### Test 2: Quick URL Scanner in Popup
1. Click the PhishTrap icon in your toolbar.
2. In the "Quick URL Scanner" input box, paste:
   ```text
   http://secure-login-paypa1.pages.dev/update-account-token
   ```
3. Click **Scan**.
4. Result: 🔴 **QUARANTINE (92.7% Risk)** with top lexical signals like `host_num_hyphens=2`, `entropy_host=3.98`.

### Test 3: Right-Click Link Inspection
1. On any webpage, right-click a hyperlink.
2. Click **"🛡️ Scan link with PhishTrap"**.
3. A popup card appears at the bottom-right of your screen showing the safety verdict.
