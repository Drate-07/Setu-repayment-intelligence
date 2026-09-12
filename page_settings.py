"""SETU — Settings page: the loan-term assumptions applied portfolio-wide
(there is no per-borrower loan record in this prototype, so these controls
apply the same contract terms to every synthetic borrower, exactly like the
original single-borrower sidebar controls did)."""

import streamlit as st

import setu_core as sc
import theme as th
import ui_components as ui

REGIONAL_SIGNAL_OPTIONS = ["Normal", "Mild Deficit", "Severe Deficit"]


def render():
    ui.render_page_header("Settings", "Portfolio-wide loan assumptions used to compute every schedule below.")

    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Loan terms", "Applied to every borrower's contract EMI in this prototype")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.loan_amount = st.number_input(
            "Loan amount (Rs)", min_value=5000, max_value=2_000_000,
            value=st.session_state.loan_amount, step=5000)
        st.session_state.annual_rate = st.slider(
            "Annual interest rate (%)", min_value=6.0, max_value=36.0,
            value=st.session_state.annual_rate, step=0.5)
    with c2:
        st.session_state.tenure_months = st.slider(
            "Tenure (months)", min_value=6, max_value=60,
            value=st.session_state.tenure_months, step=1)
        st.session_state.essential_ratio = st.slider(
            "Essential expenses (% of monthly cash flow)", min_value=30, max_value=90,
            value=int(st.session_state.essential_ratio * 100), step=5) / 100.0
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title(f"{sc.ENGINE_NAME} — guardrails", "Fixed in this prototype (see setu_core.py)")
    st.markdown(
        f'<div class="setu-subtext" style="margin-bottom:0.6rem;">'
        f'The {sc.ENGINE_NAME} classifies the <b>type</b> of a shortfall (seasonal / temporary / '
        f'structural) from the shape of a borrower\'s own cash-flow history — it does not, and does '
        f'not claim to, know the specific <b>cause</b> behind it.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "- **Case A (Expected Seasonal Dip):** the only case with automatic schedule adjustment — "
        "relief capped at **2 months per rolling 12-month window**, and deferred balance capped at "
        "**20% of loan principal**.\n"
        "- **Case B (Temporary Shock):** **never** auto-adjusted or auto-disbursed — moral-hazard risk "
        "is too high on an unexplained, unverified dip. Instead: **\"Officer Review Recommended\"** "
        "with a rough bridge-loan ballpark (typical seed/inventory/repair cost for that borrower type), "
        "pending the officer's own confirmation of actual need.\n"
        "- **Case C (Structural Deterioration):** **never** auto-adjusted — always escalated to a "
        "loan officer.\n"
        "- Any catch-up top-up (Case A only) is capped so it never pushes that month's own DSCR below 1.0.",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title(
        "Regional Early-Warning (Farmer cohort)",
        "A SIMULATED stand-in for a public rainfall / satellite crop-health feed (e.g. IMD rainfall, "
        "NDVI) for the current region.",
    )
    st.markdown(
        f'<div class="setu-subtext" style="margin-bottom:0.5rem;">{th.sim_tag()} This is a '
        f'<b>supporting signal</b> shown alongside a Farmer borrower\'s case — it does NOT feed into '
        f'or change the {sc.ENGINE_NAME}\'s classification math in this prototype, and it is not a '
        f'separate product. In production this would let SETU pre-flag affected borrowers before '
        f'their own cash flow shows a dip.</div>',
        unsafe_allow_html=True,
    )
    st.session_state.regional_signal = st.selectbox(
        "Current regional signal", REGIONAL_SIGNAL_OPTIONS,
        index=REGIONAL_SIGNAL_OPTIONS.index(st.session_state.regional_signal),
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Officer profile")
    st.text_input("Name", value="Aditi Menon", disabled=True)
    st.text_input("Branch", value="Nashik", disabled=True)
    st.markdown('</div>', unsafe_allow_html=True)
