"""SETU — Borrower detail / case review page. The core "what happened, why,
what do we do about it" screen a loan officer actually works from."""

import streamlit as st

import portfolio_data as pf
import setu_core as sc
import theme as th
import ui_components as ui

SELF_REPORT_LABELS = {
    "rough_week": "reported a rough week",
    "got_paid": "reported getting paid",
}


def _log_decision(kind: str, title: str, detail: str):
    st.session_state.setdefault("decisions_log", [])
    st.session_state.decisions_log.insert(0, {
        "kind": kind, "title": title, "detail": detail, "when": "just now",
    })


def render(record: dict | None, essential_ratio: float = 0.65, portfolio: list[dict] | None = None):
    if record is None:
        st.markdown('<div class="setu-card">Borrower not found. Go back to '
                     '<b>Borrowers</b> and select one to review.</div>', unsafe_allow_html=True)
        return

    c = record["classification"]
    explanation = record["explanation"]
    schedule = record["schedule"]
    history = record["history"]
    forecast = record["forecast"]
    case = record["case"]

    # P1 #7 — Borrower Self-Report: a simulated USSD/IVR check-in. This
    # nudges only the DISPLAYED confidence on this page; it never touches
    # classify_recent_period()'s real confidence score in `record`.
    self_reports = st.session_state.setdefault("self_reports", {})
    self_report = self_reports.get(record["borrower_id"])
    confidence_nudge = {"rough_week": -5, "got_paid": 5}.get(self_report, 0)
    displayed_confidence = max(5.0, min(99.0, record["confidence"] + confidence_nudge))

    # P1 #6 — Regional Early-Warning: a simulated stand-in for a public
    # rainfall/crop-health feed, Farmer-cohort only. Purely a UI overlay —
    # it does NOT change any setu_core calculation.
    regional_signal = st.session_state.get("regional_signal", "Normal")
    show_early_warning = record["borrower_type"] == "Farmer" and regional_signal != "Normal"

    # ---- Header: identity + officer actions ----
    top_l, top_r = st.columns([3, 2])
    with top_l:
        st.markdown(f'<div class="setu-page-title">{record["name"]}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="setu-page-subtitle">{record["borrower_type"]} · {record["borrower_id"]} · '
            f'{record["branch"]}, {record["state"]} &nbsp;&nbsp; {ui.case_badge_html(case)}</div>',
            unsafe_allow_html=True,
        )
    with top_r:
        actions = ["Escalate", "Approve"] if case != "C" else ["Add note", "Escalate"]
        cols = st.columns(len(actions) + 1)
        with cols[0]:
            if st.button("← Back", key="detail_back"):
                st.session_state.page = "Borrowers"
                st.rerun()
        with cols[1]:
            if st.button(actions[0], key="detail_act1"):
                if actions[0] == "Escalate":
                    _log_decision("escalate", "Escalated to restructuring desk",
                                   f"{record['name']} · {record['borrower_id']} · A. Menon")
                else:
                    _log_decision("override", f"Note added — {record['name']}",
                                   f"{record['borrower_id']} · A. Menon")
                st.toast(f"{actions[0]} recorded.")
        with cols[2]:
            st.markdown('<div class="setu-primary-btn">', unsafe_allow_html=True)
            if st.button(actions[1], key="detail_act2"):
                if actions[1] == "Approve":
                    _log_decision("approve", f"{record['recommendation']} approved",
                                   f"{record['name']} · {record['borrower_id']} · A. Menon")
                else:
                    _log_decision("escalate", "Escalated to restructuring desk",
                                   f"{record['name']} · {record['borrower_id']} · A. Menon")
                st.toast(f"{actions[1]} recorded.")
            st.markdown('</div>', unsafe_allow_html=True)

    # ---- P1 #6: Regional Early-Warning banner (Farmer cohort, simulated) ----
    if show_early_warning:
        st.write("")
        st.markdown(
            f'<div class="setu-alert" style="border-color:{th.SEMANTIC["amber"]["border"]};'
            f'background:{th.SEMANTIC["amber"]["bg"]};">'
            f'<b style="color:{th.SEMANTIC["amber"]["fg"]};">⚠ EARLY WARNING</b>{th.sim_tag()}'
            f'<div style="font-size:0.85rem;color:{th.TEXT_PRIMARY};margin-top:0.4rem;">'
            f'Regional signal for this area: <b>{regional_signal}</b> (simulated stand-in for real IMD '
            f'rainfall / satellite NDVI data). This pre-flags the Farmer cohort as a <b>supporting '
            f'signal</b> into the officer\'s view — it does not change {record["name"]}\'s own '
            f'classification above, which is still based only on their own cash-flow history. Not a '
            f'separate product; nothing is auto-adjusted from this alone.</div></div>',
            unsafe_allow_html=True,
        )

    # ---- P1 #7: Borrower Self-Report (simulated USSD/IVR check-in) ----
    st.write("")
    with st.container(border=True):
        st.markdown(
            f'<div style="font-size:0.83rem;font-weight:600;color:{th.TEXT_PRIMARY};">'
            f'📵 Borrower Self-Report {th.sim_tag()}</div>'
            f'<div class="setu-small-muted">Simulates a basic-phone (USSD/IVR) check-in — how a '
            f'borrower with no digital footprint can still be read by the system.</div>',
            unsafe_allow_html=True,
        )
        rcol1, rcol2, rcol3 = st.columns([1.3, 1.3, 2])
        with rcol1:
            if st.button("Borrower reported: rough week", key="self_report_rough"):
                self_reports[record["borrower_id"]] = "rough_week"
                st.rerun()
        with rcol2:
            if st.button("Borrower reported: got paid", key="self_report_paid"):
                self_reports[record["borrower_id"]] = "got_paid"
                st.rerun()
        with rcol3:
            if self_report:
                st.markdown(
                    f'<div class="setu-small-muted">Latest: borrower {SELF_REPORT_LABELS[self_report]} — '
                    f'nudges displayed confidence by {confidence_nudge:+d}pp (display only; does not '
                    f'change the engine\'s computed confidence or classification).</div>',
                    unsafe_allow_html=True,
                )

    st.write("")
    ui.render_kpi_row([
        {"label": "Predicted Cash Flow", "value": th.format_rupees(record["predicted_cash_flow_next"]),
         "caption": f"vs {th.format_rupees(record['expected_cash_flow_next'])} expected", "color": "blue"},
        {"label": "DSCR (Contract EMI)", "value": f"{record['dscr_next']:.2f}",
         "caption": "Cash available ÷ fixed EMI, next month", "color": "amber" if record["dscr_next"] < 1.3 else "green"},
        {"label": "Free Cash Buffer", "value": th.format_rupees(float(schedule["free_cash_buffer_dynamic"].iloc[0])),
         "caption": "Left over after essentials + dynamic EMI", "color": "gray"},
        {"label": "Confidence", "value": f"{displayed_confidence:.0f}%",
         "caption": ("Nudged by self-report — see below" if self_report else
                     "More history + tighter residuals = higher"), "color": "blue"},
    ])

    # ---- Cash-flow outlook chart ----
    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Cash-flow outlook", "Actual history, expected pattern, and the 6-month forecast")
    trend_full, seasonal_full, _, _ = sc.decompose(history)
    expected_full = trend_full + seasonal_full
    fig, ax = ui.new_fig((10, 3.4))
    ax.plot(history.index[-18:], history.values[-18:], color=th.TEXT_PRIMARY, linewidth=1.8, label="Actual")
    ax.plot(expected_full.index[-18:], expected_full.values[-18:], color=th.TEXT_MUTED,
            linewidth=1.3, linestyle="--", label="Expected (trend + seasonal)")
    ax.plot(forecast.index, forecast["forecast_cash_flow"], color=th.SEMANTIC["blue"]["bar"],
            linewidth=2.0, linestyle="-.", marker="o", markersize=3.5, label="Forecast")
    ax.fill_between(forecast.index, forecast["lower_80"], forecast["upper_80"],
                     color=th.SEMANTIC["blue"]["bar"], alpha=0.12, label="80% band")
    # Repayment threshold: the cash flow level below which essentials + the
    # fixed EMI can no longer both be covered (cf * (1 - essential_ratio) = EMI).
    repayment_threshold = record["fixed_emi"] / (1 - essential_ratio) if essential_ratio < 1 else None
    if repayment_threshold is not None:
        ax.axhline(repayment_threshold, color=th.SEMANTIC["red"]["bar"], linewidth=1.0, linestyle=":")
        ax.text(history.index[-18], repayment_threshold, "Repayment threshold",
                fontsize=7.5, color=th.SEMANTIC["red"]["fg"], va="bottom")
    ax.axvline(history.index[-1], color=th.BORDER, linewidth=1.0)
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=2)
    ui.style_axes(ax)
    st.pyplot(fig, width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Current assessment + SETU recommendation ----
    st.write("")
    col_assess, col_rec = st.columns([1, 1.4])
    with col_assess:
        st.markdown('<div class="setu-card" style="height:100%;">', unsafe_allow_html=True)
        ui.render_section_title("Current Assessment", f"{sc.ENGINE_NAME} — classifies TYPE, not cause")
        st.markdown(ui.case_badge_html(case), unsafe_allow_html=True)
        st.markdown(
            f'<div style="margin-top:0.6rem;font-size:0.85rem;color:{th.TEXT_SECONDARY};">'
            f'{explanation["recommended_action"]}</div>',
            unsafe_allow_html=True,
        )
        if c.get("cold_start"):
            st.markdown(f'<div style="margin-top:0.5rem;">{th.sim_tag("COLD START")}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_rec:
        st.markdown('<div class="setu-card" style="height:100%;">', unsafe_allow_html=True)
        ui.render_section_title("SETU Recommendation")
        row0 = schedule.iloc[0]

        if case == "B":
            # Temporary shock: SETU never auto-adjusts the EMI or disburses
            # anything here — see setu_core.build_repayment_schedule's Case
            # B branch. This card shows a bridge-loan BALLPARK for the
            # officer to weigh, not an automatic transaction.
            if record["any_officer_review"]:
                st.markdown(th.badge_html("Officer Review Recommended", "amber", "⚠"),
                             unsafe_allow_html=True)
                grid = st.columns(2)
                grid[0].markdown(f'<div class="setu-kpi-label">Current (contract) EMI</div>'
                                  f'<div class="setu-value" style="font-size:1.05rem;">'
                                  f'{th.format_rupees(record["fixed_emi"])} — unchanged</div>',
                                  unsafe_allow_html=True)
                grid[1].markdown(f'<div class="setu-kpi-label">Suggested bridge-loan range</div>'
                                  f'<div class="setu-value" style="font-size:1.05rem;">'
                                  f'{th.format_rupees(record["bridge_loan_low"])} – '
                                  f'{th.format_rupees(record["bridge_loan_high"])}</div>',
                                  unsafe_allow_html=True)
                st.markdown(
                    f'<div style="margin-top:0.7rem;font-size:0.8rem;color:{th.TEXT_SECONDARY};">'
                    f'Rough ballpark based on typical {record["borrower_type"].lower()} working-capital '
                    f'needs (seeds/inventory/repair) — <b>pending officer confirmation of actual need</b>. '
                    f'Nothing is auto-disbursed for a temporary shock.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(th.badge_html("Standard", "green", "✓"), unsafe_allow_html=True)
                st.markdown(
                    f'<div style="margin-top:0.7rem;font-size:0.85rem;color:{th.TEXT_SECONDARY};">'
                    f'Cash flow is healthy enough this cycle ({th.format_rupees(record["fixed_emi"])} '
                    f'contract EMI, DSCR {record["dscr_next"]:.2f}) — no officer action needed yet.</div>',
                    unsafe_allow_html=True,
                )
        else:
            # Case A (automatic schedule adjustment) and Case C (escalate,
            # no auto-relief) both show the real fixed-vs-dynamic numbers.
            relief_months = int((schedule["dynamic_emi"] < schedule["fixed_emi"] - 1e-6).sum())
            recovery_month = None
            for i in range(len(schedule)):
                if schedule["topup_applied"].iloc[i] > 0:
                    recovery_month = schedule.index[i].strftime("%b %Y")
                    break
            grid = st.columns(3)
            grid[0].markdown(f'<div class="setu-kpi-label">Current EMI</div>'
                              f'<div class="setu-value" style="font-size:1.05rem;">{th.format_rupees(record["fixed_emi"])}</div>',
                              unsafe_allow_html=True)
            grid[1].markdown(f'<div class="setu-kpi-label">SETU-adjusted EMI</div>'
                              f'<div class="setu-value" style="font-size:1.05rem;">{th.format_rupees(row0["dynamic_emi"])}</div>',
                              unsafe_allow_html=True)
            grid[2].markdown(f'<div class="setu-kpi-label">Relief period</div>'
                              f'<div class="setu-value" style="font-size:1.05rem;">{relief_months} / 2 months</div>',
                              unsafe_allow_html=True)
            st.write("")
            grid2 = st.columns(3)
            grid2[0].markdown(f'<div class="setu-kpi-label">Recovery month</div>'
                               f'<div class="setu-value" style="font-size:1.05rem;">{recovery_month or "—"}</div>',
                               unsafe_allow_html=True)
            grid2[1].markdown(f'<div class="setu-kpi-label">Catch-up top-up</div>'
                               f'<div class="setu-value" style="font-size:1.05rem;">'
                               f'{th.format_rupees(float(schedule["topup_applied"].sum()))}</div>',
                               unsafe_allow_html=True)
            grid2[2].markdown(f'<div class="setu-kpi-label">Deferred balance</div>'
                               f'<div class="setu-value" style="font-size:1.05rem;">'
                               f'{th.format_rupees(float(schedule["deferred_balance"].iloc[-1]))}</div>',
                               unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- P1 #5: Micro-Mutualization (Community Pool) ----
    # Only meaningful when there's an actual shortfall this period and the
    # case isn't structural (Case C is a lender-side/officer matter, not a
    # one-month liquidity gap a peer pool could sensibly paper over).
    if portfolio and case in ("A", "B"):
        pool = pf.build_peer_pool(record, portfolio)
        if pool["shortfall"] > 0:
            st.write("")
            st.markdown('<div class="setu-card">', unsafe_allow_html=True)
            ui.render_section_title(
                "Micro-Mutualization — Community Pool",
                f"{th.sim_tag()} A small same-cohort peer group whose spare capacity could optionally "
                f"cover this month's gap instead of a lender-side change.",
            )
            pcol1, pcol2, pcol3 = st.columns(3)
            pcol1.markdown(f'<div class="setu-kpi-label">This month\'s shortfall</div>'
                            f'<div class="setu-value" style="font-size:1.05rem;">'
                            f'{th.format_rupees(pool["shortfall"])}</div>', unsafe_allow_html=True)
            pcol2.markdown(f'<div class="setu-kpi-label">Community Pool available</div>'
                            f'<div class="setu-value" style="font-size:1.05rem;">'
                            f'{th.format_rupees(pool["pool_available"])}</div>', unsafe_allow_html=True)
            with pcol3:
                if pool["peer_covered"]:
                    st.markdown(th.badge_html("Peer-covered — no lender relief needed", "green", "✓"),
                                unsafe_allow_html=True)
                else:
                    st.markdown(th.badge_html("Pool insufficient — lender-side option above still applies",
                                               "gray"), unsafe_allow_html=True)

            st.write("")
            st.markdown(f'<div class="setu-small-muted" style="margin-bottom:0.3rem;">'
                        f'Peer group ({record["borrower_type"]} cohort) — eligible if predicted DSCR > 1.8 '
                        f'AND no relief needed in their own next 3 months:</div>', unsafe_allow_html=True)
            for peer in pool["contributors"]:
                badge = th.badge_html("Eligible", "green") if peer["eligible"] else th.badge_html("Not eligible", "gray")
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;font-size:0.82rem;'
                    f'padding:0.3rem 0;border-bottom:1px solid {th.BORDER_SOFT};">'
                    f'<span>{peer["name"]} · DSCR {peer["dscr"]:.2f} {badge}</span>'
                    f'<span style="font-weight:600;">{th.format_rupees(peer["contribution"])} contribution</span>'
                    f'</div>', unsafe_allow_html=True,
                )
            st.markdown(
                f'<div class="setu-small-muted" style="margin-top:0.5rem;">Simulated prototype mechanic — '
                f'not a real fund or transaction. Contribution capped at 20% of each eligible peer\'s own '
                f'surplus above their EMI.</div>', unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

    # ---- Why SETU recommends this + feature attribution + confidence ----
    st.write("")
    ui.render_explanation_card(explanation)

    # ---- Traditional vs SETU comparison ----
    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Traditional vs. SETU repayment comparison", "Next 6 forecasted months")
    header = st.columns([1.2, 1.5, 1.5, 1.3, 1.3, 2.2])
    for cH, label in zip(header, ["Month", "Fixed EMI", "SETU EMI", "DSCR (fixed)", "DSCR (SETU)", "Status"]):
        cH.markdown(f'<div class="setu-row-header" style="border-bottom:none;">{label}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:0 0 0.4rem 0;">', unsafe_allow_html=True)
    for month, row in schedule.iterrows():
        cols = st.columns([1.2, 1.5, 1.5, 1.3, 1.3, 2.2])
        cols[0].markdown(f'<div class="setu-value">{month.strftime("%b %Y")}</div>', unsafe_allow_html=True)
        cols[1].markdown(f'<div class="setu-value">{th.format_rupees(row["fixed_emi"])}</div>', unsafe_allow_html=True)
        cols[2].markdown(f'<div class="setu-value">{th.format_rupees(row["dynamic_emi"])}</div>', unsafe_allow_html=True)
        cols[3].markdown(th.dscr_bar_html(row["dscr_fixed"]) + f'<div class="setu-small-muted">{row["dscr_fixed"]:.2f}</div>',
                          unsafe_allow_html=True)
        cols[4].markdown(th.dscr_bar_html(row["dscr_dynamic"]) + f'<div class="setu-small-muted">{row["dscr_dynamic"]:.2f}</div>',
                          unsafe_allow_html=True)
        status_kind = "red" if row["status"].startswith("ESCALATE") else (
            "green" if row["status"] in ("Standard",) else "amber")
        cols[5].markdown(th.badge_html(row["status"], status_kind), unsafe_allow_html=True)
        st.markdown('<hr style="margin:0.2rem 0;border-color:#eef0f2;">', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Month-by-month outlook (plain-English notes) ----
    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Month-by-month outlook")
    for month, row in schedule.iterrows():
        st.markdown(
            f'<div style="padding:0.4rem 0;border-bottom:1px solid {th.BORDER_SOFT};font-size:0.85rem;">'
            f'<b style="color:{th.TEXT_PRIMARY};">{month.strftime("%b %Y")}</b> '
            f'<span style="color:{th.TEXT_SECONDARY};">— {row["note"]}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Officer actions for Case C ----
    if case == "C":
        st.write("")
        st.markdown(
            f'<div class="setu-alert" style="border-color:{th.SEMANTIC["red"]["border"]};'
            f'background:{th.SEMANTIC["red"]["bg"]};">'
            f'<b style="color:{th.SEMANTIC["red"]["fg"]};">HUMAN REVIEW REQUIRED</b>'
            f'<div style="font-size:0.85rem;color:{th.TEXT_PRIMARY};margin-top:0.4rem;">'
            f'SETU does not auto-adjust this account. Choose an action below.</div></div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(4)
        labels = ["Review", "Escalate", "Create restructuring plan", "Add decision note"]
        for c_i, label in zip(cols, labels):
            with c_i:
                if st.button(label, key=f"case_c_{label}", width="stretch"):
                    _log_decision("escalate" if label != "Add decision note" else "override",
                                   f"{label} — {record['name']}", f"{record['borrower_id']} · A. Menon")
                    st.toast(f"{label} recorded.")
