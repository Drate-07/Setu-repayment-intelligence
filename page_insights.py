"""SETU — Insights page. All metrics are real aggregates over the current
synthetic portfolio (see portfolio_data.insights_metrics / cohort_performance) —
labeled as back-tested / prototype since the whole portfolio is synthetic."""

import streamlit as st

import portfolio_data as pf
import theme as th
import ui_components as ui


def render(records: list[dict], essential_ratio: float):
    ui.render_page_header(
        "Insights", "Portfolio intelligence behind the classifications and recommendations.",
        actions=["Download report"],
    )

    m = pf.insights_metrics(records)
    ui.render_kpi_row([
        {"label": "Classification Accuracy", "value": f"{m['classification_accuracy']:.1f}%",
         "caption": f"Back-tested vs. scenario labels, {len(records)} synthetic borrowers", "color": "blue"},
        {"label": "Avoided Defaults", "value": f"{m['avoided_defaults']}",
         "caption": "Fixed EMI would fail DSCR; dynamic EMI recovers it", "color": "green"},
        {"label": "Relief Recovered", "value": f"{m['relief_recovered_pct']:.1f}%",
         "caption": "Deferred balance repaid via peak-month top-ups (6-mo window)", "color": "gray"},
        {"label": "Avg. Relief Size", "value": th.format_rupees(m["avg_relief_size"]),
         "caption": "Per relief month, this portfolio", "color": "amber"},
    ])
    st.markdown(
        f'<div class="setu-subtext" style="margin-top:0.5rem;">{th.sim_tag("PROTOTYPE / SYNTHETIC PORTFOLIO")} '
        f'All figures above are computed from this session\'s synthetic 48-borrower book — not a live loan book.</div>',
        unsafe_allow_html=True,
    )

    st.write("")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="setu-card">', unsafe_allow_html=True)
        ui.render_section_title("Portfolio cash-flow health",
                                 "Actual vs. baseline-expected collection rate, trailing 6 months")
        labels, actual, predicted = pf.cashflow_health_trend(records, essential_ratio)
        fig, ax = ui.new_fig((5.6, 3.0))
        ax.plot(labels, actual, color=th.TEXT_PRIMARY, linewidth=2.0, label="Actual")
        ax.plot(labels, predicted, color=th.SEMANTIC["blue"]["bar"], linewidth=2.0,
                linestyle="--", label="Baseline-expected")
        ax.set_ylim(0, 105)
        ax.legend(loc="lower left", fontsize=8, frameon=False)
        ui.style_axes(ax)
        st.pyplot(fig, width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="setu-card">', unsafe_allow_html=True)
        ui.render_section_title("Classification mix", "Share of borrowers assessed this cycle")
        mix = pf.classification_mix(records)
        rows = [("Expected seasonal dip", mix["A"], th.SEMANTIC["green"]["bar"]),
                ("Temporary shock", mix["B"], th.SEMANTIC["amber"]["bar"]),
                ("Structural deterioration", mix["C"], th.SEMANTIC["red"]["bar"])]
        for label, pct, color in rows:
            st.markdown(
                th.clean_html(f"""<div style="margin-bottom:0.65rem;">
                    <div style="display:flex;justify-content:space-between;font-size:0.83rem;margin-bottom:3px;">
                        <span style="color:{th.TEXT_PRIMARY};">{label}</span>
                        <span style="font-weight:700;color:{th.TEXT_PRIMARY};">{pct:.0f}%</span>
                    </div>
                    <div style="background:{th.BORDER_SOFT};border-radius:5px;height:8px;overflow:hidden;">
                        <div style="width:{pct:.0f}%;background:{color};height:100%;"></div>
                    </div>
                </div>"""),
                unsafe_allow_html=True,
            )
        seasonal_pct = mix["A"] + mix["B"]
        n_recoverable = sum(1 for r in records if r["case"] in ("A", "B"))
        st.markdown(
            f'<div class="setu-subtext" style="margin-top:0.4rem;">'
            f'{seasonal_pct:.0f}% of apparent distress in this book is seasonal or recoverable, not '
            f'deteriorating. Treating it as default risk would penalize {n_recoverable} borrowers who '
            f'repay in full within their own income cycle.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Upcoming repayment pressure", "Borrowers projected below DSCR 1.00")
    months, counts = pf.upcoming_pressure(records)
    fig, ax = ui.new_fig((9, 2.6))
    ax.bar(months, counts, color=th.SEMANTIC["blue"]["bar"], width=0.55)
    ui.style_axes(ax)
    st.pyplot(fig, width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Cohort performance", "Behaviour by borrower type")
    cohort_df = pf.cohort_performance(records)
    header_cols = st.columns([2, 1.2, 1.4, 1.2, 1.6])
    for c, label in zip(header_cols, ["Cohort", "Borrowers", "Median DSCR", "On Relief", "Classification Match"]):
        c.markdown(f'<div class="setu-row-header" style="border-bottom:none;">{label}</div>',
                    unsafe_allow_html=True)
    st.markdown('<hr style="margin:0 0 0.4rem 0;">', unsafe_allow_html=True)
    for _, row in cohort_df.iterrows():
        cols = st.columns([2, 1.2, 1.4, 1.2, 1.6])
        cols[0].markdown(f'<div class="setu-name">{row["Cohort"]}</div>', unsafe_allow_html=True)
        cols[1].markdown(f'<div class="setu-value">{int(row["Borrowers"])}</div>', unsafe_allow_html=True)
        dscr_color = th.SEMANTIC["green"]["fg"] if row["Median DSCR"] >= 1.0 else th.SEMANTIC["red"]["fg"]
        cols[2].markdown(f'<div class="setu-value" style="color:{dscr_color};">{row["Median DSCR"]:.2f}</div>',
                          unsafe_allow_html=True)
        cols[3].markdown(f'<div class="setu-value">{row["On Relief"]:.0f}%</div>', unsafe_allow_html=True)
        cols[4].markdown(f'<div class="setu-value">{row["Classification Match"]:.0f}%</div>',
                          unsafe_allow_html=True)
        st.markdown('<hr style="margin:0.2rem 0;border-color:#eef0f2;">', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
