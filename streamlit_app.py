"""
SETU — Streamlit UI entry point (presentation only, router).

This file owns NO business logic. It:
  1. Sets up the page shell (theme CSS, session state, sidebar nav, topbar).
  2. Builds (and caches) the synthetic portfolio by calling portfolio_data.py,
     which in turn only calls the unmodified functions in setu_core.py.
  3. Routes to the page module for whichever nav item is active.

Every number shown anywhere in the app traces back to setu_core.py's
decomposition/classification/forecast/repayment/explanation functions —
see that file (and validate_classifier.py) for the actual logic and its
validation. This file only decides what to draw and where.
"""

import streamlit as st

import page_alerts
import page_borrower_detail
import page_borrowers
import page_insights
import page_overview
import page_plans
import page_settings
import page_showcase
import portfolio_data as pf
import theme as th
import ui_components as ui

st.set_page_config(page_title="SETU — Repayment Intelligence", layout="wide", page_icon="🌉")
st.markdown(th.inject_base_css(), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
defaults = {
    "page": "Overview",
    "selected_borrower_id": None,
    "loan_amount": 100000,
    "annual_rate": 14.0,
    "tenure_months": 24,
    "essential_ratio": 0.65,
    # P1 #6: Regional Early-Warning — a simulated stand-in for a public
    # rainfall/crop-health feed, Farmer-cohort only. Purely a UI overlay —
    # see page_borrower_detail.py; it does NOT feed classify_recent_period().
    "regional_signal": "Normal",
    # P1 #7: Borrower Self-Report — simulated USSD/IVR check-ins, keyed by
    # borrower_id. Nudges only the DISPLAYED confidence, never the engine's
    # real confidence score.
    "self_reports": {},
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


@st.cache_data(show_spinner="Recomputing portfolio from setu_core...")
def get_portfolio(loan_amount, annual_rate, tenure_months, essential_ratio):
    return pf.build_portfolio(loan_amount, annual_rate, tenure_months, essential_ratio)


@st.cache_data(show_spinner=False)
def get_showcase_trio(loan_amount, annual_rate, tenure_months, essential_ratio):
    # Small (3-borrower) and fast — cached anyway so the demo page is
    # instant even right after a Settings change reruns everything else.
    return pf.build_showcase_trio(loan_amount, annual_rate, tenure_months, essential_ratio)


records = get_portfolio(st.session_state.loan_amount, st.session_state.annual_rate,
                         st.session_state.tenure_months, st.session_state.essential_ratio)
records_by_id = {r["borrower_id"]: r for r in records}

if "decisions_log" not in st.session_state:
    # Seed a few plausible, GROUNDED entries (real recommendation for a real
    # borrower) with cosmetic relative timestamps, so "Recent decisions"
    # isn't empty on first load. New entries from officer actions are
    # inserted for real during the session (see page_borrower_detail.py).
    seed_pool = [r for r in records if r["case"] in ("A", "B", "C")]
    seed = []
    for r in seed_pool:
        if r["case"] == "A" and r["any_relief"] and not any(e["kind"] == "approve" for e in seed):
            seed.append({"kind": "approve", "title": f"{r['recommendation']} approved",
                         "detail": f"{r['name']} · {r['borrower_id']} · A. Menon", "when": "14 min ago"})
        elif r["case"] == "C" and not any(e["kind"] == "escalate" for e in seed):
            seed.append({"kind": "escalate", "title": "Escalated to restructuring desk",
                         "detail": f"{r['name']} · {r['borrower_id']} · A. Menon", "when": "1 hr ago"})
        elif r["case"] == "B" and r["any_officer_review"] and not any(e["kind"] == "review" for e in seed):
            # Case B is never auto-adjusted, so this is a flag for a human,
            # not an automatic schedule change — see setu_core's Case B branch.
            seed.append({"kind": "review", "title": f"Flagged for officer review · {r['recommendation']}",
                         "detail": f"{r['name']} · {r['borrower_id']} · SETU auto-flag", "when": "6 hrs ago"})
        if len(seed) >= 3:
            break
    st.session_state.decisions_log = seed

# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------
ui.render_sidebar_nav(st.session_state.page)
ui.render_topbar()

page = st.session_state.page
if page == "Overview":
    page_overview.render(records, st.session_state.essential_ratio, st.session_state.regional_signal)
elif page == "Demo Trio":
    trio = get_showcase_trio(st.session_state.loan_amount, st.session_state.annual_rate,
                              st.session_state.tenure_months, st.session_state.essential_ratio)
    page_showcase.render(trio)
elif page == "Borrowers":
    page_borrowers.render(records)
elif page == "Repayment Plans":
    page_plans.render(records)
elif page == "Alerts":
    page_alerts.render(records)
elif page == "Insights":
    page_insights.render(records, st.session_state.essential_ratio)
elif page == "Settings":
    page_settings.render()
elif page == "Borrower Detail":
    selected = records_by_id.get(st.session_state.selected_borrower_id)
    page_borrower_detail.render(selected, st.session_state.essential_ratio, portfolio=records)
else:
    page_overview.render(records, st.session_state.essential_ratio, st.session_state.regional_signal)
