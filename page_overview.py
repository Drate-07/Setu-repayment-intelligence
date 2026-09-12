"""SETU — Portfolio Overview page. Presentation only; all numbers come from
portfolio_data.py aggregates over the real per-borrower setu_core output."""

import streamlit as st

import portfolio_data as pf
import theme as th
import ui_components as ui


STATIC_SIGNALS = [
    ("Mandi price index", "Onion -11% w/w"),
    ("Market footfall", "Nashik -18% (4-wk)"),
]


def render(records: list[dict], essential_ratio: float, regional_signal: str = "Normal"):
    clicked = ui.render_page_header(
        "Portfolio Overview",
        "Monitor repayment health across your borrowers.",
        actions=["Export", "Run daily assessment"],
    )
    if clicked:
        st.toast(f'"{clicked}" is a prototype action — not wired to a live pipeline yet.')

    kpis = pf.kpi_counts(records)
    ui.render_kpi_row([
        {"label": "Active Borrowers", "value": f"{kpis['active']:,}",
         "caption": f"Across {kpis['branches']} branches", "color": "gray"},
        {"label": "Healthy", "value": f"{kpis['healthy']:,}",
         "caption": f"{100*kpis['healthy']/max(kpis['active'],1):.1f}% of portfolio", "color": "green"},
        {"label": "Needs Attention", "value": f"{kpis['needs_attention']:,}",
         "caption": "Temporary shock — eligible for auto-relief", "color": "amber"},
        {"label": "Human Review", "value": f"{kpis['human_review']:,}",
         "caption": "Structural deterioration", "color": "red"},
    ])

    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    top_l, top_r = st.columns([3, 1])
    with top_l:
        ui.render_section_title("Attention Required",
                                 "Borrowers whose predicted cash flow breaches the repayment threshold.")
    with top_r:
        st.markdown(f'<div style="text-align:right;padding-top:0.4rem;">'
                     f'<span class="setu-link">View all</span></div>', unsafe_allow_html=True)

    ui.render_table_header([
        ("Borrower", 2.4), ("Classification", 1.3), ("DSCR", 1.7),
        ("Predicted Cash Flow", 1.6), ("Recommendation", 1.5), ("", 1.0),
    ])
    for r in pf.attention_required(records, limit=6):
        ui.render_borrower_row(r, key_prefix="overview")
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    col_pressure, col_signals = st.columns([2, 1])
    with col_pressure:
        st.markdown('<div class="setu-card">', unsafe_allow_html=True)
        ui.render_section_title("Upcoming Repayment Pressure", "Borrowers projected below DSCR 1.00")
        months, counts = pf.upcoming_pressure(records)
        fig, ax = ui.new_fig((7.2, 3.0))
        ax.bar(months, counts, color=th.SEMANTIC["blue"]["bar"], width=0.55)
        ui.style_axes(ax)
        st.pyplot(fig, width="stretch")
        if counts:
            peak_i = counts.index(max(counts))
            st.markdown(
                f'<div class="setu-subtext">Peak month <b style="color:{th.TEXT_PRIMARY};">'
                f'{months[peak_i]} · {counts[peak_i]} borrowers</b></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_signals:
        st.markdown('<div class="setu-card">', unsafe_allow_html=True)
        ui.render_section_title("Signals feed", "External inputs used today")
        rainfall_color = th.TEXT_PRIMARY if regional_signal == "Normal" else th.SEMANTIC["amber"]["fg"]
        signals = [("Rainfall/crop-health (Farmer cohort)", regional_signal, rainfall_color)] + \
                  [(name, val, th.TEXT_PRIMARY) for name, val in STATIC_SIGNALS]
        for name, val, color in signals:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:0.4rem 0;'
                f'border-bottom:1px solid {th.BORDER_SOFT};font-size:0.83rem;">'
                f'<span style="color:{th.TEXT_SECONDARY};">{name} {th.sim_tag()}</span>'
                f'<span style="font-weight:600;color:{color};">{val}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="setu-small-muted" style="margin-top:0.4rem;">Rainfall/crop-health signal is set '
            f'in <b>Settings</b> — a supporting input for Farmer borrowers, not a separate product.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Portfolio cash-flow health",
                             "Share of borrowers who actually cleared essentials + fixed EMI, vs. what "
                             "their own seasonal baseline alone would have predicted (trailing 6 months).")
    labels, actual, predicted = pf.cashflow_health_trend(records, essential_ratio)
    fig, ax = ui.new_fig((9, 3.0))
    ax.plot(labels, actual, color=th.TEXT_PRIMARY, linewidth=2.0, label="Actual")
    ax.plot(labels, predicted, color=th.SEMANTIC["blue"]["bar"], linewidth=2.0,
            linestyle="--", label="Baseline-expected")
    ax.set_ylim(0, 105)
    ax.legend(loc="lower left", fontsize=8.5, frameon=False)
    ui.style_axes(ax)
    st.pyplot(fig, width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="setu-card">', unsafe_allow_html=True)
    ui.render_section_title("Recent decisions", "Approvals, overrides, escalations, schedule changes")
    for entry in st.session_state.get("decisions_log", [])[:6]:
        icon = {"approve": "✓", "escalate": "↗", "override": "↺", "schedule": "→", "review": "⚠"}.get(
            entry["kind"], "•")
        color = {"approve": th.SEMANTIC["green"]["fg"], "escalate": th.SEMANTIC["red"]["fg"],
                 "override": th.SEMANTIC["amber"]["fg"], "schedule": th.SEMANTIC["blue"]["fg"],
                 "review": th.SEMANTIC["amber"]["fg"]}.get(entry["kind"], th.TEXT_SECONDARY)
        st.markdown(
            th.clean_html(f"""<div style="display:flex;justify-content:space-between;align-items:flex-start;
                 padding:0.55rem 0;border-bottom:1px solid {th.BORDER_SOFT};">
                <div>
                    <span style="color:{color};font-weight:700;margin-right:8px;">{icon}</span>
                    <span style="font-weight:600;font-size:0.86rem;color:{th.TEXT_PRIMARY};">{entry['title']}</span>
                    <div class="setu-subtext" style="margin-left:22px;">{entry['detail']}</div>
                </div>
                <div class="setu-small-muted">{entry['when']}</div>
            </div>"""),
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)
