"""
SETU — "Three Borrowers, Side by Side" showcase page.

Built specifically for the pitch-video demo: a FIXED, reproducible trio of
synthetic borrowers (portfolio_data.SHOWCASE_TRIO), one per Case, each
verified (via a curated seed — see portfolio_data._find_seed_for_scenario)
to reliably land on its intended classification. Requires zero user input
and loads instantly — every number on this page comes straight from the
unmodified setu_core.py pipeline, run on 3 borrowers instead of 48.
"""

import streamlit as st

import setu_core as sc
import theme as th
import ui_components as ui

EXPECTED_STORY = {
    "A": "Expected outcome: Case A — Expected Seasonal Dip. Standard EMI, auto-adjusts only if DSCR runs tight.",
    "B": "Expected outcome: Case B — Temporary Shock. Never auto-adjusted; flagged for officer review with a bridge-loan ballpark.",
    "C": "Expected outcome: Case C — Structural Deterioration. Never auto-adjusted; escalated to a loan officer.",
}


def render(records: list[dict]):
    ui.render_page_header(
        "Three Borrowers, Side by Side",
        "A fixed, reproducible demo trio — one per shortfall type — powered by SETU's "
        f"{sc.ENGINE_NAME}. Same pipeline as the full portfolio, just 3 pre-verified borrowers.",
    )

    cols = st.columns(3)
    for col, r in zip(cols, records):
        with col:
            st.markdown('<div class="setu-card" style="height:100%;">', unsafe_allow_html=True)

            st.markdown(f'<div class="setu-name" style="font-size:1.0rem;">{r["name"]}</div>'
                        f'<div class="setu-subtext">{r["borrower_type"]} · {r["scenario"]}</div>',
                        unsafe_allow_html=True)
            st.write("")
            st.markdown(ui.case_badge_html(r["case"]), unsafe_allow_html=True)
            st.markdown(
                f'<div class="setu-small-muted" style="margin-top:4px;">{EXPECTED_STORY[r["expected_case"]]}</div>',
                unsafe_allow_html=True,
            )

            # --- mini cash-flow chart: actual, expected, forecast ---
            history = r["history"]
            forecast = r["forecast"]
            trend_full, seasonal_full, _, _ = sc.decompose(history)
            expected_full = trend_full + seasonal_full

            fig, ax = ui.new_fig((4.0, 2.4))
            ax.plot(history.index[-15:], history.values[-15:], color=th.TEXT_PRIMARY, linewidth=1.4, label="Actual")
            ax.plot(expected_full.index[-15:], expected_full.values[-15:], color=th.TEXT_MUTED,
                    linewidth=1.0, linestyle="--", label="Expected")
            ax.plot(forecast.index, forecast["forecast_cash_flow"], color=th.SEMANTIC["blue"]["bar"],
                    linewidth=1.6, linestyle="-.", marker="o", markersize=2.5, label="Forecast")
            ax.axvline(history.index[-1], color=th.BORDER, linewidth=0.8)
            ax.legend(loc="upper left", fontsize=6.5, frameon=False)
            ax.tick_params(labelsize=6.5)
            ui.style_axes(ax)
            st.pyplot(fig, width="stretch")

            st.markdown(
                f'<div class="setu-link" style="font-size:0.85rem;">{r["recommendation"]}</div>'
                f'<div class="setu-small-muted">Confidence {r["confidence"]:.0f}%</div>',
                unsafe_allow_html=True,
            )

            with st.expander("Why? (XAI explanation)"):
                ui.render_explanation_card(r["explanation"])

            st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    all_match = all(r["case_matches_expected"] for r in records)
    check_color = th.SEMANTIC["green"]["fg"] if all_match else th.SEMANTIC["red"]["fg"]
    check_text = ("✓ All 3 borrowers classified as expected (A / B / C) this run."
                  if all_match else
                  "✗ One or more borrowers did NOT match the expected case this run — see portfolio_data.SHOWCASE_TRIO.")
    st.markdown(f'<div class="setu-subtext" style="color:{check_color};font-weight:600;">{check_text}</div>',
                unsafe_allow_html=True)
