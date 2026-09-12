"""SETU — Alerts page.

Structural / Shock / Pressure alerts are grounded — derived directly from
each borrower's real classification and schedule (see
portfolio_data.build_alerts). Weather and Anomaly are NOT computed by
setu_core (there is no weather feed or anti-gaming detector implemented),
so each of those categories shows exactly one clearly labeled illustrative
card instead of a fabricated live signal — this keeps the filter structure
from the reference without pretending those are real detections.
"""

import streamlit as st

import portfolio_data as pf
import ui_components as ui

CATEGORIES = ["All", "Structural", "Shock", "Pressure", "Weather", "Anomaly"]

ILLUSTRATIVE_WEATHER = dict(
    category="Weather", type="Rainfall anomaly", severity="Medium",
    borrower="Sitapur block (Farmer cohort)", borrower_id="—",
    reason="District rainfall 32% below normal during the critical sowing window (IMD proxy feed).",
    recommended="Pre-flag affected borrowers for early relief window", grounded=False,
)
ILLUSTRATIVE_ANOMALY = dict(
    category="Anomaly", type="Anti-gaming anomaly", severity="High",
    borrower="Sample borrower", borrower_id="—",
    reason="Inflow pattern shifted to a secondary account shortly before an assessment window — "
           "requires verification, not an accusation.",
    recommended="Flag for field verification", grounded=False,
)


def render(records: list[dict]):
    ui.render_page_header(
        "Alerts", "Signals detected across the portfolio, ordered by severity.",
        actions=["Mark all read", "Alert rules"],
    )

    real_alerts = pf.build_alerts(records)
    all_alerts = real_alerts + [ILLUSTRATIVE_WEATHER, ILLUSTRATIVE_ANOMALY]

    counts = {c: sum(1 for a in all_alerts if a["category"] == c) for c in CATEGORIES[1:]}
    if "alert_filter" not in st.session_state:
        st.session_state.alert_filter = "All"

    st.markdown('<div class="setu-filterbar">', unsafe_allow_html=True)
    cols = st.columns(len(CATEGORIES))
    for c, cat in zip(cols, CATEGORIES):
        label = cat if cat == "All" else f"{cat} ({counts.get(cat, 0)})"
        with c:
            if st.session_state.alert_filter == cat:
                st.markdown(f'<div class="setu-nav-active" style="text-align:center;">{label}</div>',
                             unsafe_allow_html=True)
            elif st.button(label, key=f"alertcat_{cat}", width="stretch"):
                st.session_state.alert_filter = cat
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")

    filtered = all_alerts if st.session_state.alert_filter == "All" else [
        a for a in all_alerts if a["category"] == st.session_state.alert_filter
    ]
    # High severity first, same as the reference's "ordered by severity"
    order = {"High": 0, "Medium": 1, "Low": 2}
    filtered = sorted(filtered, key=lambda a: order.get(a["severity"], 3))

    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Open alerts", "Each alert carries a borrower, a reason, and a recommended action.")
    if not filtered:
        st.markdown('<div class="setu-subtext" style="padding:1rem 0;">No alerts in this category.</div>',
                     unsafe_allow_html=True)
    for a in filtered[:20]:
        ui.render_alert_card(a, simulated=not a.get("grounded", True))
    st.markdown('</div>', unsafe_allow_html=True)
