"""
app_ui/components.py
Reusable, bespoke SOC dashboard components for PhishTrap.
Includes safe defanging rendering, status badges, and metric cards.
"""

import html
from typing import Dict, Any, List


def render_status_badge(status: str) -> str:
    """
    Renders a high-contrast cybersecurity status badge with subtle glow.
    """
    status_clean = str(status).upper().strip()
    
    configs = {
        "QUARANTINE": {
            "bg": "rgba(239, 68, 68, 0.14)",
            "border": "rgba(239, 68, 68, 0.4)",
            "color": "#FCA5A5",
            "icon": "🛡️",
            "text": "QUARANTINE"
        },
        "HUMAN_REVIEW": {
            "bg": "rgba(245, 158, 11, 0.14)",
            "border": "rgba(245, 158, 11, 0.4)",
            "color": "#FCD34D",
            "icon": "⚠️",
            "text": "HUMAN REVIEW"
        },
        "ALLOW": {
            "bg": "rgba(16, 185, 129, 0.14)",
            "border": "rgba(16, 185, 129, 0.4)",
            "color": "#6EE7B7",
            "icon": "✅",
            "text": "ALLOW"
        },
        "RELEASED": {
            "bg": "rgba(59, 130, 246, 0.14)",
            "border": "rgba(59, 130, 246, 0.4)",
            "color": "#93C5FD",
            "icon": "📬",
            "text": "RELEASED (OVERRIDE)"
        },
        "CONFIRMED_PHISH": {
            "bg": "rgba(220, 38, 38, 0.22)",
            "border": "rgba(220, 38, 38, 0.6)",
            "color": "#FECACA",
            "icon": "🚨",
            "text": "CONFIRMED PHISH"
        },
        "RELABELED": {
            "bg": "rgba(139, 92, 246, 0.14)",
            "border": "rgba(139, 92, 246, 0.4)",
            "color": "#C4B5FD",
            "icon": "🏷️",
            "text": "RELABELED"
        }
    }
    
    cfg = configs.get(status_clean, {
        "bg": "rgba(100, 116, 139, 0.14)",
        "border": "rgba(100, 116, 139, 0.4)",
        "color": "#CBD5E1",
        "icon": "ℹ️",
        "text": status_clean
    })
    
    return f"""
    <span style="
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        background: {cfg['bg']};
        border: 1px solid {cfg['border']};
        color: {cfg['color']};
        font-family: 'Plus Jakarta Sans', sans-serif;
    ">
        <span>{cfg['icon']}</span>
        <span>{cfg['text']}</span>
    </span>
    """


def render_score_bar(score: float) -> str:
    """
    Renders a color-coded confidence score bar with triage thresholds.
    """
    safe_score = max(0.0, min(1.0, float(score)))
    percent = round(safe_score * 100, 1)
    
    if safe_score >= 0.85:
        bar_color = "linear-gradient(90deg, #F59E0B, #EF4444)"
        text_color = "#EF4444"
        category = "HIGH RISK"
    elif safe_score >= 0.05:
        bar_color = "linear-gradient(90deg, #3B82F6, #F59E0B)"
        text_color = "#F59E0B"
        category = "AMBIGUOUS"
    else:
        bar_color = "linear-gradient(90deg, #10B981, #06B6D4)"
        text_color = "#10B981"
        category = "BENIGN"

    return f"""
    <div style="margin: 6px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; margin-bottom: 4px;">
            <span style="color: #94A3B8; font-family: 'JetBrains Mono', monospace;">Score: <strong style="color: {text_color}; font-size: 0.9rem;">{safe_score:.4f}</strong></span>
            <span style="color: {text_color}; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em;">{category}</span>
        </div>
        <div style="width: 100%; height: 6px; background: rgba(255, 255, 255, 0.06); border-radius: 3px; overflow: hidden;">
            <div style="width: {percent}%; height: 100%; background: {bar_color}; border-radius: 3px; transition: width 0.3s ease;"></div>
        </div>
    </div>
    """


def render_metric_card(title: str, value: Any, subtitle: str = "", trend_color: str = "#6366F1") -> str:
    """
    Renders an elegant glassmorphic KPI card with high typographic hierarchy.
    """
    return f"""
    <div class="soc-metric-box">
        <div class="soc-metric-label">{html.escape(title)}</div>
        <div class="soc-metric-value" style="color: {trend_color};">{value}</div>
        <div class="soc-metric-sub">{html.escape(subtitle)}</div>
    </div>
    """


def render_defanged_url_item(u_dict: Dict[str, Any]) -> str:
    """
    Renders a single defanged URL security card with top feature tags.
    """
    defanged = html.escape(u_dict.get("defanged_url", "unknown"))
    domain = html.escape(u_dict.get("registered_domain", "unknown"))
    score = float(u_dict.get("score", 0.0))
    top_features = u_dict.get("top_features", [])

    features_html = ""
    for feat in top_features[:6]:
        feat_name = html.escape(feat.get("feature", "feat"))
        val = feat.get("value", 0)
        formatted_val = f"{val:.2f}" if isinstance(val, float) else str(val)
        features_html += f'<span class="feature-badge">{feat_name}: {formatted_val}</span>'

    score_bar = render_score_bar(score)

    return f"""
    <div style="
        background: #0B111D;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;">
            <div style="flex-grow: 1;">
                <div style="font-size: 0.74rem; color: #64748B; font-weight: 600; text-transform: uppercase;">
                    Domain: <span style="color: #E2E8F0; font-family: 'JetBrains Mono', monospace;">{domain}</span>
                </div>
                <div style="margin-top: 4px;">
                    <span class="defanged-code">{defanged}</span>
                </div>
            </div>
            <div style="min-width: 140px;">
                {score_bar}
            </div>
        </div>
        <div style="margin-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 8px;">
            <span style="font-size: 0.7rem; color: #64748B; margin-right: 6px;">Top Signals:</span>
            {features_html if features_html else '<span style="color: #475569; font-size: 0.72rem;">No salient triggers</span>'}
        </div>
    </div>
    """
