"""
app_ui/theme.py
Custom CSS and Design System for PhishTrap SOC Console.
Professional, high-contrast, human-crafted dark cybersecurity UI.
"""

SOC_CUSTOM_CSS = """
<style>
/* Import High-Caliber Typography */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* Base Root Configuration */
:root {
    --bg-cockpit: #080C14;
    --bg-surface: #0E1526;
    --bg-surface-elevated: #141E34;
    --bg-glass: rgba(14, 21, 38, 0.75);
    
    --border-subtle: rgba(255, 255, 255, 0.07);
    --border-focus: rgba(99, 102, 241, 0.45);
    
    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    
    --accent-indigo: #6366F1;
    --accent-cyan: #06B6D4;
    --status-danger: #EF4444;
    --status-warning: #F59E0B;
    --status-success: #10B981;
    --status-info: #3B82F6;
    --status-relabel: #8B5CF6;
}

/* Global Application Body */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-cockpit) !important;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text-primary) !important;
}

/* Header & Top Bar */
[data-testid="stHeader"] {
    background-color: rgba(8, 12, 20, 0.85) !important;
    backdrop-filter: blur(16px) !important;
    border-bottom: 1px solid var(--border-subtle) !important;
}

/* Main Content Container Padding */
.main .block-container {
    max-width: 1400px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
}

/* Sidebar Customization */
[data-testid="stSidebar"] {
    background-color: #0A0F1A !important;
    border-right: 1px solid var(--border-subtle) !important;
}

[data-testid="stSidebar"] hr {
    border-color: var(--border-subtle) !important;
}

/* Modern Tab Navigation */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background-color: #0B111F !important;
    padding: 6px !important;
    border-radius: 12px !important;
    border: 1px solid var(--border-subtle) !important;
}

.stTabs [data-baseweb="tab"] {
    padding: 10px 18px !important;
    border-radius: 8px !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    border: none !important;
    background-color: transparent !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.18), rgba(6, 182, 212, 0.18)) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(99, 102, 241, 0.35) !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12) !important;
}

/* Button Refinement */
.stButton > button {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 0.55rem 1.25rem !important;
    border: 1px solid var(--border-subtle) !important;
    background-color: var(--bg-surface-elevated) !important;
    color: var(--text-primary) !important;
    transition: all 0.15s ease-in-out !important;
}

.stButton > button:hover {
    border-color: var(--accent-indigo) !important;
    box-shadow: 0 0 16px rgba(99, 102, 241, 0.25) !important;
    transform: translateY(-1px) !important;
    color: #FFFFFF !important;
}

/* Input Fields & Text Areas */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background-color: #0B111F !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent-indigo) !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}

/* Custom SOC Header Card */
.soc-hero {
    background: linear-gradient(135deg, #0E1526 0%, #131E34 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.soc-title-wrap h1 {
    font-size: 1.65rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.025em !important;
    margin: 0 !important;
    background: linear-gradient(135deg, #FFFFFF 0%, #94A3B8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.soc-subtitle {
    color: var(--text-secondary);
    font-size: 0.88rem;
    margin-top: 0.25rem;
}

.soc-live-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 9999px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #10B981;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10B981;
    box-shadow: 0 0 8px #10B981;
    animation: livePulse 2s infinite;
}

@keyframes livePulse {
    0% { transform: scale(0.95); opacity: 0.8; }
    50% { transform: scale(1.3); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.8; }
}

/* Glassmorphism Card Box */
.soc-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 4px 20px -4px rgba(0, 0, 0, 0.4);
    transition: border-color 0.2s ease;
}

.soc-card:hover {
    border-color: rgba(255, 255, 255, 0.12);
}

/* Metric Display Card */
.soc-metric-box {
    background: #0C1220;
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: left;
}

.soc-metric-label {
    font-size: 0.76rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.soc-metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #FFFFFF;
    font-family: 'JetBrains Mono', monospace;
    margin-top: 0.25rem;
}

.soc-metric-sub {
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-top: 0.2rem;
}

/* Defanged Code Blocks */
.defanged-code {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #070B14 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 6px !important;
    padding: 6px 10px !important;
    font-size: 0.82rem !important;
    color: #38BDF8 !important;
    word-break: break-all !important;
    display: inline-block;
}

/* Feature Badge Tags */
.feature-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    background: rgba(99, 102, 241, 0.12);
    border: 1px solid rgba(99, 102, 241, 0.25);
    color: #A5B4FC;
    margin: 2px 4px 2px 0;
}
</style>
"""

