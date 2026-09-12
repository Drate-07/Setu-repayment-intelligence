"""
SETU — reusable Streamlit presentation components.

Every function here renders something; none of them compute a business
number. They take already-computed values (from setu_core.py /
portfolio_data.py) and paint them consistently across pages.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

import theme as th

NAV_ITEMS = ["Overview", "Demo Trio", "Borrowers", "Repayment Plans", "Alerts", "Insights", "Settings"]


# ---------------------------------------------------------------------------
# Shell: sidebar nav + topbar
# ---------------------------------------------------------------------------

def render_sidebar_nav(active: str):
    with st.sidebar:
        st.markdown(
            '<div class="setu-nav-logo">SETU<span>Repayment Intelligence</span></div>',
            unsafe_allow_html=True,
        )
        for item in NAV_ITEMS:
            if item == active:
                st.markdown(f'<div class="setu-nav-active">{item}</div>', unsafe_allow_html=True)
            else:
                if st.button(item, key=f"nav_{item}", width="stretch"):
                    st.session_state.page = item
                    st.rerun()


def render_topbar(officer_name: str = "Aditi Menon", role: str = "Loan Officer", location: str = "Nashik"):
    initials = "".join(p[0] for p in officer_name.split()[:2]).upper()
    left, right = st.columns([3, 2])
    with left:
        st.text_input("Search", placeholder="Search borrowers, IDs, plans...",
                       label_visibility="collapsed", key="setu_search_box")
    with right:
        st.markdown(
            th.clean_html(f"""
            <div style="display:flex;justify-content:flex-end;align-items:center;gap:16px;">
                <span style="font-size:1.05rem;color:{th.TEXT_SECONDARY};">&#128276;</span>
                <div class="setu-profile">
                    <div>
                        <div class="setu-profile-name">{officer_name}</div>
                        <div class="setu-profile-role">{role} · {location}</div>
                    </div>
                    <div class="setu-avatar">{initials}</div>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )
    st.markdown('<div style="border-bottom:1px solid #eef0f2;margin:0.4rem 0 1.1rem 0;"></div>',
                unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str, actions: list[str] | None = None) -> str | None:
    """Renders the title/subtitle row with optional right-aligned buttons.
    Returns the label of the clicked action button, if any."""
    col_title, col_actions = st.columns([3, 2])
    with col_title:
        st.markdown(f'<div class="setu-page-title">{title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="setu-page-subtitle">{subtitle}</div>', unsafe_allow_html=True)
    clicked = None
    if actions:
        with col_actions:
            cols = st.columns(len(actions))
            for c, label in zip(cols, actions):
                with c:
                    primary = label == actions[-1] and len(actions) > 1
                    if primary:
                        st.markdown('<div class="setu-primary-btn">', unsafe_allow_html=True)
                    if st.button(label, key=f"action_{title}_{label}", width="stretch"):
                        clicked = label
                    if primary:
                        st.markdown('</div>', unsafe_allow_html=True)
    return clicked


def render_section_title(title: str, subtitle: str | None = None):
    st.markdown(f'<div class="setu-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="setu-section-subtitle">{subtitle}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------

def render_kpi_row(kpis: list[dict]):
    """kpis: list of {label, value, caption, color} where color in theme.SEMANTIC keys."""
    cols = st.columns(len(kpis))
    for c, k in zip(cols, kpis):
        color = th.SEMANTIC.get(k.get("color", "gray"), th.SEMANTIC["gray"])["bar"]
        with c:
            st.markdown(
                th.clean_html(f"""<div class="setu-kpi" style="--kpi-color:{color};">
                    <div class="setu-kpi-label">{k['label']}</div>
                    <div class="setu-kpi-value">{k['value']}</div>
                    <div class="setu-kpi-caption">{k.get('caption','')}</div>
                </div>"""),
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Status badges
# ---------------------------------------------------------------------------

def case_badge_html(case: str) -> str:
    label_map = {"A": "Expected Seasonal Dip", "B": "Temporary Shock", "C": "Structural Deterioration"}
    return th.badge_html(label_map[case], th.CASE_KIND[case], th.CASE_ICON[case])


def severity_badge_html(severity: str) -> str:
    kind = {"High": "red", "Medium": "amber", "Low": "gray"}.get(severity, "gray")
    return th.badge_html(f"{severity} severity", kind)


def plan_status_badge_html(status: str) -> str:
    kind = {"Active": "green", "Standard": "gray", "Officer Review": "amber",
            "Withheld": "red"}.get(status, "gray")
    return th.badge_html(status, kind)


# ---------------------------------------------------------------------------
# Borrower row (used on Overview "Attention Required" + Borrowers page)
# Real st.button for the Review action so it can actually navigate.
# ---------------------------------------------------------------------------

def render_borrower_row(r: dict, key_prefix: str, show_type_branch: bool = True):
    cols = st.columns([2.4, 1.3, 1.7, 1.6, 1.5, 1.0])
    with cols[0]:
        st.markdown(f'<div class="setu-name">{r["name"]}</div>', unsafe_allow_html=True)
        if show_type_branch:
            st.markdown(
                f'<div class="setu-subtext">{r["borrower_type"]} · {r["borrower_id"]}</div>',
                unsafe_allow_html=True,
            )
    with cols[1]:
        st.markdown(case_badge_html(r["case"]), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(
            f'<div class="setu-value">{r["dscr_next"]:.2f}</div>{th.dscr_bar_html(r["dscr_next"])}',
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            f'<div class="setu-value">{th.format_rupees(r["predicted_cash_flow_next"])}</div>'
            f'<div class="setu-small-muted">vs {th.format_rupees(r["expected_cash_flow_next"])} expected</div>',
            unsafe_allow_html=True,
        )
    with cols[4]:
        st.markdown(f'<div class="setu-link">{r["recommendation"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="setu-small-muted">Confidence {r["confidence"]:.0f}%</div>',
                     unsafe_allow_html=True)
    with cols[5]:
        if st.button("Review →", key=f"{key_prefix}_review_{r['borrower_id']}", width="stretch"):
            st.session_state.selected_borrower_id = r["borrower_id"]
            st.session_state.page = "Borrower Detail"
            st.rerun()
    st.markdown('<hr style="margin:0.2rem 0 0.5rem 0;border-color:#eef0f2;">', unsafe_allow_html=True)


def render_table_header(labels_widths: list[tuple[str, float]]):
    cols = st.columns([w for _, w in labels_widths])
    for c, (label, _) in zip(cols, labels_widths):
        with c:
            st.markdown(f'<div class="setu-row-header" style="border-bottom:none;">{label}</div>',
                        unsafe_allow_html=True)
    st.markdown('<hr style="margin:0 0 0.4rem 0;">', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def render_alert_card(a: dict, simulated: bool = False):
    sim = th.sim_tag() if simulated else ""
    st.markdown(
        th.clean_html(f"""<div class="setu-alert">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <span style="font-weight:700;font-size:0.92rem;color:{th.TEXT_PRIMARY};">{a['type']}</span>
                    {sim}
                    &nbsp;&nbsp;{severity_badge_html(a['severity'])}
                    <div class="setu-subtext" style="margin-top:2px;">{a['borrower']} · {a.get('borrower_id','')}</div>
                </div>
            </div>
            <div style="font-size:0.85rem;color:{th.TEXT_PRIMARY};margin:0.5rem 0 0.3rem 0;">{a['reason']}</div>
            <div style="font-size:0.8rem;color:{th.TEXT_SECONDARY};">
                <b style="color:{th.TEXT_PRIMARY};">Recommended:</b> {a['recommended']}
            </div>
        </div>"""),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Matplotlib chart styling — one consistent look across the app
# ---------------------------------------------------------------------------

def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(th.BORDER)
    ax.spines["bottom"].set_color(th.BORDER)
    ax.tick_params(colors=th.TEXT_SECONDARY, labelsize=8.5)
    ax.grid(axis="y", color=th.BORDER_SOFT, linewidth=0.8)
    ax.set_axisbelow(True)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_color(th.TEXT_SECONDARY)


def new_fig(figsize=(9, 3.4)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    return fig, ax


def render_explanation_card(explanation: dict):
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    st.markdown(f"#### {explanation['headline']}")
    st.markdown(
        f"**Borrower:** {explanation['borrower']}  \n"
        f"**Period under review:** {explanation['period']}  \n"
        f"**Confidence:** {explanation['confidence_pct']:.0f}% — {explanation['confidence_note']}"
    )
    st.markdown(f"**Recommended action:** {explanation['recommended_action']}")
    st.markdown("**Why SETU recommends this**")
    for i, trigger in enumerate(explanation["rule_triggers"], start=1):
        text = trigger.split(". ", 1)[1] if ". " in trigger else trigger
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;margin-bottom:0.5rem;">'
            f'<span class="setu-evidence-num">{i:02d}</span>'
            f'<span style="font-size:0.87rem;color:{th.TEXT_PRIMARY};padding-top:1px;">{text}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("**Feature attribution**")
    for f in explanation["feature_attribution"]:
        val = f["rupees"]
        color = th.SEMANTIC["green"]["fg"] if val >= 0 else th.SEMANTIC["red"]["fg"]
        sign = "+" if val >= 0 else ""
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;font-size:0.85rem;'
            f'padding:0.3rem 0;border-bottom:1px solid {th.BORDER_SOFT};">'
            f'<span style="color:{th.TEXT_SECONDARY};">{f["factor"]}</span>'
            f'<span style="font-weight:600;color:{color};">{sign}{th.format_rupees(val)}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)
