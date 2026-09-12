"""
SETU — visual theme layer (pure presentation, no business logic).

Centralizes every design token (colors, spacing, badge styles) and the CSS
injected into the Streamlit app, plus small formatting/HTML-snippet helpers
used by ui_components.py. Nothing in this file reads or changes a single
calculation — it only decides how already-computed numbers are painted.
"""

# ---------------------------------------------------------------------------
# Design tokens — enterprise fintech: light neutral background, navy/charcoal
# text, subtle borders, restrained semantic colors. No gradients, no glow.
# ---------------------------------------------------------------------------
BG = "#f6f7f9"
CARD_BG = "#ffffff"
BORDER = "#e5e7eb"
BORDER_SOFT = "#eef0f2"
TEXT_PRIMARY = "#12172b"
TEXT_SECONDARY = "#6b7280"
TEXT_MUTED = "#9aa1ac"
ACCENT_DARK = "#12172b"      # primary buttons / active nav
LINK = "#2952cc"

SEMANTIC = {
    "green": {"bg": "#e9f6ee", "fg": "#1e7e34", "border": "#bfe3c8", "bar": "#22a34a"},
    "amber": {"bg": "#fff8e1", "fg": "#9a6b00", "border": "#f5dfa0", "bar": "#e0a300"},
    "red":   {"bg": "#fdecea", "fg": "#c62828", "border": "#f5c2c0", "bar": "#d9362a"},
    "blue":  {"bg": "#eaf1ff", "fg": "#2952cc", "border": "#c9dcff", "bar": "#3b6bd8"},
    "gray":  {"bg": "#f3f4f6", "fg": "#4b5563", "border": "#e5e7eb", "bar": "#9ca3af"},
}

CASE_KIND = {"A": "green", "B": "amber", "C": "red"}
CASE_ICON = {"A": "✓", "B": "⚠", "C": "✕"}  # check, warn, cross


def format_rupees(value: float, decimals: int = 0) -> str:
    """Indian-flavored rupee formatting without pulling in a new dependency."""
    sign = "-" if value < 0 else ""
    value = abs(value)
    if decimals:
        s = f"{value:,.{decimals}f}"
    else:
        s = f"{value:,.0f}"
    return f"{sign}₹{s}"


def format_pct(value: float, decimals: int = 0) -> str:
    return f"{value:.{decimals}f}%"


def clean_html(s: str) -> str:
    """
    Strip Python-source indentation from a multi-line HTML string before
    handing it to st.markdown(unsafe_allow_html=True).

    A triple-quoted f-string written with normal Python indentation embeds
    that indentation as literal leading whitespace on every continuation
    line. Streamlit's markdown renderer treats a run of 4+ leading spaces
    as an indented code block — even with unsafe_allow_html=True — so the
    HTML shows up as literal escaped-looking text in a monospace box
    instead of being rendered. Every multi-line HTML string in this app
    must be passed through this before st.markdown().
    """
    return "\n".join(line.strip() for line in s.strip("\n").splitlines())


def inject_base_css():
    """Returns the global stylesheet string. Call once via st.markdown."""
    return clean_html(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}

    /* Hide default Streamlit chrome so this doesn't read as a prototype */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{background: transparent; height: 0;}}
    div[data-testid="stToolbar"] {{display: none;}}
    div[data-testid="stDecoration"] {{display: none;}}

    .stApp {{
        background: {BG};
    }}

    .block-container {{
        padding-top: 1.1rem;
        padding-bottom: 2rem;
        max-width: 1320px;
    }}

    /* ---------------- Sidebar (compact left nav) ---------------- */
    section[data-testid="stSidebar"] {{
        background: {CARD_BG};
        border-right: 1px solid {BORDER};
        width: 232px !important;
    }}
    section[data-testid="stSidebar"] > div {{
        padding-top: 0.6rem;
    }}
    section[data-testid="stSidebar"] .stButton > button {{
        width: 100%;
        text-align: left;
        background: transparent;
        border: none;
        color: {TEXT_SECONDARY};
        font-size: 0.87rem;
        font-weight: 500;
        padding: 0.44rem 0.7rem;
        border-radius: 7px;
        box-shadow: none;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover {{
        background: {BG};
        color: {TEXT_PRIMARY};
        border: none;
    }}
    section[data-testid="stSidebar"] .stButton > button:focus:not(:active) {{
        color: {TEXT_PRIMARY};
        box-shadow: none;
    }}

    .setu-nav-active {{
        width: 100%;
        background: {ACCENT_DARK};
        color: #ffffff !important;
        font-size: 0.87rem;
        font-weight: 600;
        padding: 0.44rem 0.7rem;
        border-radius: 7px;
        margin-bottom: 0.15rem;
    }}
    .setu-nav-logo {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        letter-spacing: 0.02em;
        padding: 0.3rem 0.7rem 0.9rem 0.7rem;
        border-bottom: 1px solid {BORDER_SOFT};
        margin-bottom: 0.6rem;
    }}
    .setu-nav-logo span {{
        display:block; font-size: 0.68rem; font-weight: 500; color:{TEXT_MUTED};
        letter-spacing: 0.03em; margin-top: 2px; text-transform: uppercase;
    }}

    /* ---------------- Generic buttons in main content ---------------- */
    .stButton > button {{
        border-radius: 7px;
        border: 1px solid {BORDER};
        font-weight: 500;
        font-size: 0.86rem;
        color: {TEXT_PRIMARY};
        background: {CARD_BG};
        padding: 0.4rem 0.9rem;
    }}
    .stButton > button:hover {{
        border-color: {TEXT_PRIMARY};
        color: {TEXT_PRIMARY};
    }}
    .setu-primary-btn button {{
        background: {ACCENT_DARK} !important;
        color: #fff !important;
        border: 1px solid {ACCENT_DARK} !important;
    }}

    /* ---------------- Typography ---------------- */
    .setu-page-title {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin-bottom: 0.1rem;
        letter-spacing: -0.01em;
    }}
    .setu-page-subtitle {{
        font-size: 0.88rem;
        color: {TEXT_SECONDARY};
        margin-bottom: 1.0rem;
    }}
    .setu-section-title {{
        font-size: 1.0rem;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin: 0 0 0.05rem 0;
    }}
    .setu-section-subtitle {{
        font-size: 0.8rem;
        color: {TEXT_SECONDARY};
        margin-bottom: 0.7rem;
    }}

    /* ---------------- Topbar ---------------- */
    .setu-topbar {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.35rem 0 0.9rem 0;
        border-bottom: 1px solid {BORDER_SOFT};
        margin-bottom: 1.1rem;
    }}
    .setu-profile {{
        display: flex; align-items: center; gap: 10px;
    }}
    .setu-avatar {{
        width: 34px; height: 34px; border-radius: 50%;
        background: {ACCENT_DARK}; color: #fff;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.78rem; font-weight: 700;
    }}
    .setu-profile-name {{ font-size: 0.85rem; font-weight: 600; color: {TEXT_PRIMARY}; line-height: 1.15;}}
    .setu-profile-role {{ font-size: 0.74rem; color: {TEXT_SECONDARY}; line-height: 1.15;}}

    /* ---------------- Cards ---------------- */
    .setu-card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 1.0rem 1.15rem;
    }}
    .setu-kpi {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-left: 3px solid var(--kpi-color, {TEXT_MUTED});
        border-radius: 8px;
        padding: 0.85rem 1.0rem;
        height: 100%;
    }}
    .setu-kpi-label {{
        font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em;
        text-transform: uppercase; color: {TEXT_SECONDARY}; margin-bottom: 0.35rem;
    }}
    .setu-kpi-value {{ font-size: 1.65rem; font-weight: 700; color: {TEXT_PRIMARY}; line-height: 1.1; }}
    .setu-kpi-caption {{ font-size: 0.76rem; color: {TEXT_MUTED}; margin-top: 0.3rem; }}

    /* ---------------- Badges / chips ---------------- */
    .setu-badge {{
        display: inline-flex; align-items: center; gap: 5px;
        font-size: 0.74rem; font-weight: 600;
        padding: 0.22rem 0.55rem; border-radius: 6px; white-space: nowrap;
    }}
    .setu-dot {{
        display:inline-block; width:7px; height:7px; border-radius:50%;
    }}
    .setu-tag-sim {{
        display:inline-block; font-size: 0.62rem; font-weight: 700; letter-spacing: 0.04em;
        color: {TEXT_MUTED}; border: 1px dashed {BORDER}; border-radius: 5px;
        padding: 0.08rem 0.4rem; text-transform: uppercase; margin-left: 6px;
    }}

    /* ---------------- Table-like rows ---------------- */
    .setu-row-header {{
        font-size: 0.7rem; font-weight: 600; color: {TEXT_MUTED};
        text-transform: uppercase; letter-spacing: 0.03em;
        padding: 0 0.2rem 0.5rem 0.2rem; border-bottom: 1px solid {BORDER};
        margin-bottom: 0.35rem;
    }}
    .setu-row {{
        padding: 0.6rem 0.2rem; border-bottom: 1px solid {BORDER_SOFT};
    }}
    .setu-row:last-child {{ border-bottom: none; }}
    .setu-name {{ font-size: 0.88rem; font-weight: 600; color: {TEXT_PRIMARY}; }}
    .setu-subtext {{ font-size: 0.76rem; color: {TEXT_SECONDARY}; }}
    .setu-value {{ font-size: 0.88rem; font-weight: 600; color: {TEXT_PRIMARY}; }}
    .setu-small-muted {{ font-size: 0.74rem; color: {TEXT_MUTED}; }}
    .setu-link {{ color: {LINK}; font-weight: 600; font-size: 0.85rem; }}

    /* DSCR mini bar */
    .setu-bar-track {{ width: 68px; height: 6px; border-radius: 4px; background: #eef0f2; overflow: hidden; }}
    .setu-bar-fill {{ height: 100%; border-radius: 4px; }}

    /* Alert / recommendation cards */
    .setu-alert {{
        background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 9px;
        padding: 0.85rem 1.0rem; margin-bottom: 0.6rem;
    }}
    .setu-evidence-num {{
        display:inline-flex; align-items:center; justify-content:center;
        width: 22px; height: 22px; border-radius: 6px; background: {BG};
        border: 1px solid {BORDER}; font-size: 0.72rem; font-weight: 700; color: {TEXT_SECONDARY};
        margin-right: 8px; flex-shrink: 0;
    }}

    hr {{ border-color: {BORDER_SOFT}; }}

    /* Streamlit dataframe density */
    div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 8px; }}

    /* Filter pill buttons (secondary) */
    .setu-filterbar .stButton > button {{
        border-radius: 999px; padding: 0.3rem 0.85rem; font-size: 0.8rem;
    }}
    </style>
    """)


def badge_html(text: str, kind: str, icon: str | None = None) -> str:
    c = SEMANTIC[kind]
    prefix = f"{icon} " if icon else ""
    return (f'<span class="setu-badge" style="background:{c["bg"]};color:{c["fg"]};'
            f'border:1px solid {c["border"]};">{prefix}{text}</span>')


def dscr_bar_html(dscr: float, max_scale: float = 1.6) -> str:
    if dscr < 1.0:
        color = SEMANTIC["red"]["bar"]
    elif dscr < 1.3:
        color = SEMANTIC["amber"]["bar"]
    else:
        color = SEMANTIC["green"]["bar"]
    pct = max(0.04, min(1.0, dscr / max_scale)) * 100
    return (f'<div class="setu-bar-track"><div class="setu-bar-fill" '
            f'style="width:{pct:.0f}%;background:{color};"></div></div>')


def sim_tag(label: str = "SIMULATED") -> str:
    return f'<span class="setu-tag-sim">{label}</span>'
