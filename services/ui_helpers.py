"""Ortak UI bileşenleri ve CSS enjeksiyonu."""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Reset & Base ────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background: radial-gradient(circle at top left, rgba(99,102,241,0.18), transparent 26%),
                radial-gradient(circle at bottom right, rgba(14,165,233,0.1), transparent 28%),
                linear-gradient(180deg, #04080f 0%, #07111f 100%);
}

/* ── Sidebar ─────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #07101f !important;
    border-right: 1px solid rgba(148,163,184,0.1);
}
[data-testid="stSidebarNav"] { padding-top: 0.25rem; }
[data-testid="stSidebarNav"] a {
    border-radius: 12px;
    padding: 0.7rem 0.9rem !important;
    color: #cbd5e1 !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    transition: all 0.18s;
    margin: 0.15rem 0;
}
[data-testid="stSidebarNav"] a:hover {
    background: rgba(99,102,241,0.12) !important;
    color: #ffffff !important;
}
[data-testid="stSidebarNav"] [aria-selected="true"] {
    background: rgba(99,102,241,0.18) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}
/* "app" → "Ana Sayfa" */
[data-testid="stSidebarNav"] a[href="/"] span,
[data-testid="stSidebarNav"] li:first-child span {
    visibility: hidden; position: relative;
}
[data-testid="stSidebarNav"] a[href="/"] span::after,
[data-testid="stSidebarNav"] li:first-child span::after {
    content: "Ana Sayfa"; visibility: visible;
    position: absolute; left: 0;
}

/* ── Metric kartları ─────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: rgba(8, 18, 34, 0.95);
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 20px;
    padding: 1.25rem 1.35rem !important;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s, transform 0.16s;
}
[data-testid="metric-container"]:hover {
    border-color: rgba(79,70,229,0.35);
    transform: translateY(-2px);
}
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 40%, #06b6d4 100%);
    opacity: 0.55;
}
[data-testid="stMetricLabel"] p {
    color: #3d5475 !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
[data-testid="stMetricValue"] {
    color: #e8f0fe !important;
    font-size: 1.65rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em;
}
[data-testid="stMetricDelta"] svg { display: none; }
[data-testid="stMetricDelta"] > div {
    font-size: 0.8rem !important;
    font-weight: 600 !important;
}

/* ── Form ────────────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: #0a1522;
    border: 1px solid #0f2035;
    border-radius: 16px;
    padding: 1.5rem !important;
}

/* ── Butonlar ────────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.01em;
    box-shadow: 0 4px 15px rgba(99,102,241,0.3);
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 22px rgba(99,102,241,0.5) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #059669 0%, #0891b2 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(5,150,105,0.25);
    transition: all 0.2s !important;
}
[data-testid="stFormSubmitButton"] > button:hover {
    box-shadow: 0 6px 22px rgba(5,150,105,0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #1a2e47 !important;
    border-radius: 10px !important;
    color: #3d5475 !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #2d4a6a !important;
    color: #7c9cbf !important;
    background: #0a1522 !important;
}

/* ── Tabs ────────────────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
    background: #0a1522 !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 2px !important;
    border: 1px solid #0f2035;
}
[data-baseweb="tab"] {
    border-radius: 9px !important;
    font-weight: 500 !important;
    color: #3d5475 !important;
    font-size: 0.85rem !important;
    transition: all 0.15s !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: #111e35 !important;
    color: #818cf8 !important;
    font-weight: 600 !important;
}

/* ── Input alanları ──────────────────────────────────────────────── */
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input,
.stDateInput > div > div > input,
.stTextArea textarea {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(148,163,184,0.12) !important;
    border-radius: 14px !important;
    color: #e2e8f0 !important;
    font-size: 0.95rem !important;
    transition: border-color 0.2s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
    border-color: rgba(99,102,241,0.55) !important;
    box-shadow: 0 0 0 4px rgba(99,102,241,0.12) !important;
}

/* ── DataFrame ───────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 14px !important;
    border: 1px solid #0f2035 !important;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}

/* ── Expander ────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #0f2035 !important;
    border-radius: 12px !important;
    background: #0a1522 !important;
    overflow: hidden;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #7c9cbf !important;
    font-size: 0.875rem !important;
}

/* ── Alerts ──────────────────────────────────────────────────────── */
.stAlert { border-radius: 12px !important; }

/* ── Progress bar ────────────────────────────────────────────────── */
.stProgress > div > div > div {
    border-radius: 8px !important;
    background: linear-gradient(90deg, #4f46e5, #7c3aed) !important;
}
.stProgress > div > div {
    border-radius: 8px !important;
    background: #0a1522 !important;
}

/* ── Divider ─────────────────────────────────────────────────────── */
hr { border-color: #0f1c2e !important; margin: 1.5rem 0 !important; }

/* ── Chat ────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    border-radius: 14px !important;
    border: 1px solid #0f2035 !important;
    background: #0a1522 !important;
    margin-bottom: 0.75rem !important;
}
[data-testid="stChatInputTextArea"] textarea {
    background: #0a1522 !important;
    border: 1px solid #0f2035 !important;
    border-radius: 12px !important;
}
[data-testid="stChatInputTextArea"] textarea:focus {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}

/* ── Başlıklar ───────────────────────────────────────────────────── */
h1 { color: #e8f0fe !important; font-weight: 800 !important; letter-spacing: -0.04em; }
h2 { color: #c8d8ea !important; font-weight: 700 !important; letter-spacing: -0.025em; }
h3 { color: #7c9cbf !important; font-weight: 600 !important; }
[data-testid="stMarkdownContainer"] p { color: #7c9cbf; line-height: 1.65; }

/* ── Yardımcı sınıflar ───────────────────────────────────────────── */
.status-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 1rem; }
.status-chip {
    display: inline-flex; align-items: center; gap: 0.5rem;
    border-radius: 999px; padding: 0.45rem 1rem;
    font-size: 0.8rem; font-weight: 700; border: 1px solid transparent;
}
.status-chip.ok   { background: rgba(34,197,94,0.12);  border-color: rgba(34,197,94,0.18);  color: #4ade80; }
.status-chip.warn { background: rgba(245,158,11,0.12); border-color: rgba(245,158,11,0.18); color: #fbbf24; }
.status-chip.err  { background: rgba(239,68,68,0.12);  border-color: rgba(239,68,68,0.18);  color: #f87171; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.status-dot.ok   { background: #4ade80; box-shadow: 0 0 9px rgba(74,222,128,0.35); }
.status-dot.warn { background: #fbbf24; box-shadow: 0 0 9px rgba(251,191,36,0.25); }
.status-dot.err  { background: #f87171; box-shadow: 0 0 9px rgba(248,113,113,0.25); }

.section-title {
    font-size: 0.72rem; font-weight: 800; color: #8b93c7;
    text-transform: uppercase; letter-spacing: 0.18em;
    margin: 1.75rem 0 0.75rem;
}
.badge {
    display: inline-flex; align-items: center;
    border-radius: 999px; padding: 0.3rem 0.8rem;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em;
    background: rgba(99,102,241,0.12); color: #c7d2fe;
}
.badge-blue { background: rgba(99,102,241,0.12); color: #c7d2fe; }

.hero-card {
    background: rgba(9, 16, 31, 0.96);
    border: 1px solid rgba(99,102,241,0.22);
    border-radius: 28px;
    padding: 2rem;
    box-shadow: 0 36px 80px rgba(0, 0, 0, 0.27);
}
.hero-card h1 { font-size: 3rem; line-height: 1.05; margin-bottom: 0.8rem; }
.hero-card p { color: #cbd5e1; font-size: 1rem; max-width: 620px; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 0.85rem; margin-top: 1.5rem; }
.hero-action {
    padding: 1rem 1.2rem; border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.08); min-width: 210px;
    background: rgba(255,255,255,0.03); color: #e2e8f0;
    font-weight: 700; transition: transform 0.18s, border-color 0.18s;
}
.hero-action:hover { border-color: rgba(99,102,241,0.4); transform: translateY(-2px); }
.hero-action span { display: block; opacity: 0.78; margin-top: 0.35rem; font-size: 0.88rem; }

.feature-card,
.panel-card,
.action-card {
    background: rgba(9, 16, 31, 0.95);
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 22px;
    padding: 1.5rem;
    transition: border-color 0.2s, transform 0.18s;
}
.feature-card:hover,
.panel-card:hover,
.action-card:hover { border-color: rgba(79,70,229,0.35); transform: translateY(-1px); }
.feature-card h4,
.panel-card h4 { margin-top: 0; margin-bottom: 0.7rem; }
.feature-card p,
.panel-card p { color: #9fb7d6; line-height: 1.7; }

.action-card {
    display: flex; flex-direction: column; justify-content: space-between;
    min-height: 170px;
}
.action-card .label { color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.65rem; }
.action-card h4 { color: #ffffff; }
.action-card small { color: #94a3b8; }

.tip-box {
    background: rgba(99,102,241,0.05);
    border: 1px solid rgba(99,102,241,0.15);
    border-left: 3px solid #4f46e5;
    border-radius: 0 10px 10px 0;
    padding: 0.8rem 1.1rem;
    color: #7c9cbf; font-size: 0.83rem; line-height: 1.6;
}
.tip-box strong { color: #818cf8; }
.tip-box a { color: #818cf8; }

/* ── Boş durum ───────────────────────────────────────────────────── */
.empty-state {
    background: #0a1522;
    border: 1px dashed #0f2035;
    border-radius: 16px;
    padding: 3rem 2rem;
    text-align: center;
}
.empty-icon  { font-size: 2.4rem; margin-bottom: 0.75rem; }
.empty-title { color: #7c9cbf; font-weight: 600; font-size: 1rem; margin-bottom: 0.4rem; }
.empty-desc  { color: #3d5475; font-size: 0.83rem; line-height: 1.6; max-width: 360px; margin: 0 auto; }

/* ── Step kartlar ────────────────────────────────────────────────── */
.step-card {
    background: #0a1522;
    border: 1px solid #0f2035;
    border-radius: 14px;
    padding: 1.3rem 1.4rem;
    height: 100%;
    transition: border-color 0.2s;
}
.step-card:hover { border-color: #1e3a5f; }
.step-card.done  { border-color: rgba(34,197,94,0.2); }
.step-num {
    width: 26px; height: 26px; border-radius: 50%;
    background: #111e35; color: #818cf8;
    font-size: 0.72rem; font-weight: 800;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 0.75rem;
}
.step-num.done { background: rgba(34,197,94,0.12); color: #4ade80; }
.step-title { color: #c8d8ea; font-weight: 700; font-size: 0.9rem; margin-bottom: 0.3rem; }
.step-desc  { color: #3d5475; font-size: 0.8rem; line-height: 1.55; }

/* ── Sidebar stats ───────────────────────────────────────────────── */
.sidebar-stat-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.3rem 0;
}
.sidebar-stat-label { color: #1e3a5f; font-size: 0.78rem; }
.sidebar-stat-value { font-size: 0.8rem; font-weight: 700; }
</style>
<!-- Page transition overlay (görsel yükleme efekti) -->
<div id="page-overlay" style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:9999;pointer-events:none;">
    <div style="background:linear-gradient(135deg,rgba(79,70,229,0.95),rgba(6,182,212,0.9));padding:1.2rem 1.6rem;border-radius:12px;display:flex;gap:0.9rem;align-items:center;box-shadow:0 20px 50px rgba(2,6,23,0.6);transform:translateY(0);opacity:1;animation:overlayFade 700ms ease-out forwards;">
        <div style="width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,0.12);display:flex;align-items:center;justify-content:center">
            <svg width="20" height="20" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg"><path fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" d="M25 5a20 20 0 1 0 20 20" style="stroke-dasharray:90;stroke-dashoffset:0;animation:spin 1s linear infinite"></path></svg>
        </div>
        <div style="color:#fff;font-weight:700;font-size:0.95rem">Yükleniyor...</div>
    </div>
</div>

<style>
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes overlayFade { 0% { opacity: 1; transform: translateY(0); } 80% { opacity: 1; } 100% { opacity: 0; pointer-events: none; transform: translateY(-6px); } }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    sub = (f'<p style="color:#3d5475;font-size:0.85rem;margin:0.3rem 0 0;'
           f'font-weight:400">{subtitle}</p>') if subtitle else ""
    st.markdown(
        f'<div style="padding:1.5rem 0 1.8rem">'
        f'<h1 style="margin:0;font-size:1.8rem">{icon} {title}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )


def section_title(text: str, badge: str = "") -> None:
    badge_html = (f'<span class="badge badge-blue" style="margin-left:0.5rem;'
                  f'vertical-align:middle">{badge}</span>') if badge else ""
    st.markdown(f'<p class="section-title">{text}{badge_html}</p>', unsafe_allow_html=True)


def tip(text: str) -> None:
    st.markdown(f'<div class="tip-box">{text}</div>', unsafe_allow_html=True)


def empty_state(icon: str, title: str, desc: str) -> None:
    st.markdown(f"""
    <div class="empty-state">
        <div class="empty-icon">{icon}</div>
        <div class="empty-title">{title}</div>
        <div class="empty-desc">{desc}</div>
    </div>""", unsafe_allow_html=True)


def status_chip(label: str, state: str) -> str:
    return (f'<span class="status-chip {state}">'
            f'<span class="status-dot {state}"></span>{label}</span>')


def sidebar_stats(summary: dict) -> None:
    with st.sidebar:
        st.markdown(
            '<p class="section-title" style="padding:0 0.5rem;margin-top:1.2rem">Bu Ay</p>',
            unsafe_allow_html=True,
        )
        savings_rate = summary.get("savings_rate", 0)
        rate_color = "#4ade80" if savings_rate >= 20 else "#f87171"
        st.markdown(f"""
        <div style="padding:0 0.5rem;display:flex;flex-direction:column;gap:0.45rem">
            <div class="sidebar-stat-row">
                <span class="sidebar-stat-label">Gelir</span>
                <span class="sidebar-stat-value" style="color:#4ade80">
                    {summary['income']:,.0f} ₺</span>
            </div>
            <div class="sidebar-stat-row">
                <span class="sidebar-stat-label">Gider</span>
                <span class="sidebar-stat-value" style="color:#f87171">
                    {summary['expense']:,.0f} ₺</span>
            </div>
            <div class="sidebar-stat-row">
                <span class="sidebar-stat-label">Tasarruf</span>
                <span class="sidebar-stat-value" style="color:{rate_color}">
                    %{summary['savings_rate']:.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
