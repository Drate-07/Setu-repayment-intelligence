"""SETU — Borrowers list page."""

import streamlit as st

import portfolio_data as pf
import ui_components as ui

FILTERS = ["All", "Farmer", "Market Vendor", "Gig Worker", "Needs attention", "Human review"]


def _matches(r: dict, f: str) -> bool:
    if f == "All":
        return True
    if f in ("Farmer", "Market Vendor", "Gig Worker"):
        return r["borrower_type"] == f
    if f == "Needs attention":
        return r["case"] == "B"
    if f == "Human review":
        return r["case"] == "C"
    return True


def render(records: list[dict]):
    branches = len({r["branch"] for r in records})
    ui.render_page_header(
        "Borrowers", "",
        actions=["Filters", "Add borrower"],
    )
    st.markdown(
        f'<div class="setu-page-subtitle" style="margin-top:-0.8rem;">'
        f'{len(records)} active borrowers · {branches} branches · updated 06:00 IST</div>',
        unsafe_allow_html=True,
    )

    if "borrower_filter" not in st.session_state:
        st.session_state.borrower_filter = "All"

    st.markdown('<div class="setu-filterbar">', unsafe_allow_html=True)
    cols = st.columns(len(FILTERS))
    for c, f in zip(cols, FILTERS):
        with c:
            if st.session_state.borrower_filter == f:
                st.markdown(
                    f'<div class="setu-nav-active" style="text-align:center;">{f}</div>',
                    unsafe_allow_html=True,
                )
            elif st.button(f, key=f"filter_{f}", width="stretch"):
                st.session_state.borrower_filter = f
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")

    filtered = [r for r in records if _matches(r, st.session_state.borrower_filter)]

    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_table_header([
        ("Borrower", 2.4), ("Classification", 1.3), ("DSCR", 1.7),
        ("Predicted Cash Flow", 1.6), ("Recommendation", 1.5), ("", 1.0),
    ])
    if not filtered:
        st.markdown('<div class="setu-subtext" style="padding:1rem 0;">No borrowers match this filter.</div>',
                     unsafe_allow_html=True)
    for r in filtered:
        ui.render_borrower_row(r, key_prefix="borrowers")
    st.markdown('</div>', unsafe_allow_html=True)
