# SETU

🔗 **Live demo:** https://setu-repayment-intelligence.streamlit.app/

**SETU** ("bridge" in Hindi/Sanskrit) is a prototype for **dynamic microloan
repayment and cash-flow planning**, built for borrowers with irregular
income — farmers, market vendors, gig workers — who are underserved by
fixed-EMI (equated monthly installment) loan products. It targets **SDG 8
(Decent Work and Economic Growth)**.

## The problem

Microfinance borrowers rarely earn the same amount every month. A farmer's
income spikes at harvest and dips for the rest of the year; a market
vendor's footfall drops in the monsoon and jumps in festival season; a gig
worker's earnings are simply noisy week to week. Traditional loans charge a
**fixed EMI** every month regardless of this rhythm, which means a
perfectly healthy borrower can be marked as "defaulting" during their own
normal seasonal low — an *artificial default* that damages their credit
record and the lender's relationship with them for no real reason. At the
same time, a lender cannot just forgive every dip either: some dips are a
genuine, sustained decline in the borrower's business, and treating those
the same as a seasonal lull just delays a real problem and lets bad debt
build up. SETU's job is to look at a borrower's own cash-flow history,
tell these situations apart using transparent, explainable statistics (not
a black-box model), and resize the EMI automatically only when it is
actually safe to do so — always showing its reasoning so a loan officer can
verify or override it.

The classification-and-decision logic is formally called the **Shortfall
Classification & Intervention Engine**. That name is deliberate: the engine
classifies the **type** of a shortfall — seasonal, temporary, or structural
— from the shape of a borrower's own cash-flow history. It does **not**
claim to know the specific **cause** (a particular weather event, a family
emergency, a stolen scooter). Every explanation SETU produces should read
as "this looks like a temporary shock," never as "this shortfall was
caused by X" — the engine has no information that could support that
stronger claim.

## The two numbers SETU tracks

Everything the repayment engine does comes down to two numbers, computed
fresh every month for every borrower:

- **DSCR (Debt Service Coverage Ratio)** — a ratio: *"for every rupee I owe
  this month, how many rupees do I actually have on hand to pay it?"*
  DSCR = (cash available after essential expenses) ÷ EMI due. Below 1.0 it's
  mathematically impossible to pay without skipping food, rent, or business
  costs — that's the moment a good borrower gets pushed toward a predatory
  moneylender, not because they're dishonest, but because the schedule is
  wrong for their life.
- **Free Cash Buffer** — the same idea as a rupee amount instead of a ratio:
  *"after I've paid for essentials AND this month's EMI, how much is left in
  my pocket?"* DSCR is good for comparing risk across borrowers of different
  sizes; Free Cash Buffer is good for a loan officer to instantly see how
  much slack — or how much of a hole — a borrower is in. SETU shows both,
  side by side, for every forecasted month.

## How to run

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app is a multi-page loan-officer console — Overview, **Demo Trio**,
Borrowers, Alerts, Insights, Repayment Plans, Settings, and a per-borrower
case-review page — built around a 48-borrower synthetic portfolio that
recomputes from `setu_core.py` on every loan-term change made in
**Settings**. There is no login, no database, no persistence beyond the
current session.

**Demo Trio** is a fixed, reproducible set of 3 borrowers — one per Case
(A/B/C) — meant for a pitch video: it needs no input, loads instantly, and
is verified (via `portfolio_data.SHOWCASE_TRIO`, a curated-seed approach,
not a classifier change) to land on its intended case every time the app
starts.

To check the classifier on its own (no UI, no Streamlit needed):

```bash
python validate_classifier.py
```

This runs all 9 combinations of borrower type x scenario and confirms each
one lands on the expected classification — the same check that was used to
tune the model before it was wired into the app.

## Project layout

**Backend (locked — no Streamlit import, independently testable):**

- **`setu_core.py`** — all the logic (synthetic data, decomposition,
  classification, forecasting, the repayment engine, the explanation card).
- **`validate_classifier.py`** — the mandatory validation script that
  proves the classifier behaves as intended across borrower types and
  scenarios (9/9, checked across 5 seeds each).

**Data layer (orchestration only — calls the backend, invents no new math):**

- **`portfolio_data.py`** — builds a 48-borrower synthetic portfolio by
  running the unmodified `setu_core.py` pipeline once per borrower, and
  aggregates the real per-borrower outputs into portfolio-level views
  (classification mix, cohort performance, upcoming repayment pressure,
  alerts, plan register). Every aggregate is a direct roll-up of a real
  `setu_core` output — nothing here is invented to look impressive.

**Frontend (presentation only):**

- **`streamlit_app.py`** — the entry point / router: page shell, session
  state, and dispatch to the page below matching the active nav item.
- **`theme.py`** — design tokens and the injected CSS (colors, badges, KPI
  cards, tables) — the single place the app's look is defined.
- **`ui_components.py`** — reusable render functions (topbar, sidebar nav,
  KPI row, borrower row, alert card, explanation card, chart styling) shared
  across every page.
- **`page_overview.py`, `page_showcase.py`, `page_borrowers.py`,
  `page_alerts.py`, `page_insights.py`, `page_plans.py`,
  `page_borrower_detail.py`, `page_settings.py`** — one module per screen
  in the nav (Overview, the Demo Trio showcase, Borrowers, Alerts, Insights,
  Repayment Plans, the per-borrower case-review page, and Settings).
- **`requirements.txt`** — `streamlit`, `pandas`, `numpy`, `matplotlib`.

A note on honesty in the UI: a few reference-screenshot elements aren't
backed by any real calculation in `setu_core.py` — there's no weather feed
and no anti-gaming detector implemented. Those are shown as single,
clearly labeled "SIMULATED" example cards (on the Alerts and Overview
pages) rather than presented as live signals. Similarly, the Insights
page's "Classification Accuracy" figure is a genuine back-test — the
portfolio's ~42 unnamed borrowers use plain, uncurated random seeds, so
that number reflects the classifier's real behavior (including a known
limitation: on a baseline under 3 full seasonal cycles, in-sample seasonal
averaging over only 2-3 observations per calendar month understates the
residual std, which occasionally over-flags a normal month as a shock).

## How the classifier works (plain English)

Every borrower has their own rhythm — a farmer's income doesn't look like a
gig worker's, and one farmer's harvest month doesn't look like another
farmer's. So instead of comparing a borrower to some generic average, SETU
first learns **that specific borrower's own pattern**: it splits their cash
flow history into a slow-moving **trend** (is their business growing or
shrinking, in general), a repeating **seasonal shape** (what a typical
January, typical October, etc. looks like for them), and whatever's left
over (**noise**) — the ordinary month-to-month unpredictability once you've
accounted for the first two.

Here's the important trick: when SETU checks the *most recent* few months,
it deliberately learns the trend and seasonal shape from **everything
except those recent months**, then asks "given everything I knew before
this recent period, what did I expect to happen?" If it let the recent dip
itself influence what "normal" looks like, a real decline could partly hide
itself — the expectation would quietly bend to match the bad news. Holding
the recent months out keeps the comparison honest.

SETU then measures how far off the actual recent cash flow is from that
expectation, in units of the borrower's own typical noise level (this is a
standard statistical z-score — "how many standard deviations away is
this?"). From there it asks three questions, in plain terms:

1. **Is the latest month within the borrower's normal range?** If yes,
   that's just an **Expected Seasonal Dip (Case A)** — no action needed.
2. If not, **is the gap getting worse over the last several months, or is
   it already recovering?** A shock that showed up sharply but is healing
   is very different from one that keeps digging deeper.
3. **Has it lasted long enough to rule out a one-off?** A single bad month
   can happen to anyone; several months in a row, each worse than the
   last, looks like something structural.

Only when the deviation is abnormal **and** getting worse **and** has
persisted for several months does SETU call it a **Structural Deterioration
(Case C)** — and in that case, it deliberately does **not** auto-adjust the
EMI. It flags the account for a human loan officer instead, because
auto-relief for a genuine decline just postpones the problem. Anything
abnormal but not (yet) meeting that bar is a **Temporary Shock (Case B)** —
and here too, SETU does **not** auto-adjust anything: a shock is, by
definition, a pattern the borrower's own history can't explain, so
auto-granting relief (or auto-disbursing a loan) on it carries real
moral-hazard risk. Instead it's flagged "Officer Review Recommended," with
a rough bridge-loan ballpark attached for the officer to weigh — see "How
the repayment engine works" below. SETU also reports a confidence score
(more history and a steadier track record mean higher confidence) and, for
every decision, prints the three checks above in plain language plus a
rupee-by-rupee breakdown of how much of the gap is "normal seasonal
pattern," how much is the underlying trend, and how much is genuinely
unexplained — the same breakdown a bank auditor would want to see before
trusting the system's call.

## How the repayment engine works

Once a month is classified, SETU turns the next 6 months of forecasted
cash flow into an actual schedule. Only **Case A** ever gets an automatic
schedule change — Case B and Case C both stop short of that, for different
reasons:

- **DSCR ≥ 1.5, any case:** standard EMI, no change.
- **Case A, 1.0 ≤ DSCR < 1.5:** a "Seasonal Light EMI" — halved for that
  month, with the other half deferred (tracked and capitalized onto the
  balance, never forgiven). This is safe to automate because the dip
  matches the borrower's own known seasonal rhythm.
- **Case A, DSCR < 1.0:** an "Interest-only / Skip" month (~15% of the
  normal EMI), for the same reason — the shortfall is too deep for a half
  measure.
- **Case B (Temporary Shock), DSCR < 1.5:** SETU does **not** auto-adjust
  the EMI, and does **not** auto-disburse anything. A shock is by
  definition a pattern the borrower's own seasonal history can't explain —
  automating relief on an unverified, unexplained dip is exactly the kind
  of moral hazard a rule-based auto-approval would create. Instead the
  month is marked **"Officer Review Recommended"** with a rough,
  borrower-type-specific bridge-loan ballpark attached (e.g. Rs
  8,000–25,000 for a farmer's seed/fertilizer costs, Rs 5,000–15,000 for a
  vendor's inventory restock) — a number for the officer to weigh, not a
  transaction SETU carries out.
- **Case C, any DSCR:** the EMI is **never** auto-adjusted either. The
  month is flagged "ESCALATE — loan officer review" instead, with tenure
  extension, partial settlement, and credit counseling offered as the
  officer's options. This is deliberate: auto-relief for a genuine decline
  just delays the borrower's problem and lets bad debt build up quietly.
- **Catch-up top-ups (Case A only):** whenever a later month is a relative
  income peak (top ~35% of the 6-month forecast) and the borrower still
  owes a deferred balance, SETU adds a top-up on top of that month's EMI to
  pay it down — capped so it can never push that month's own DSCR below
  1.0. Relief in one month can never manufacture a crisis in another.

**Guardrails, so this can't quietly bleed the lender dry:** Case A relief
is capped at 2 months per rolling 12-month window, *and* the running
deferred balance can never exceed 20% of the loan principal — whichever
limit is hit first, further shortfall months escalate to a human instead
of granting more relief. Total interest and principal owed over the life
of the loan does not shrink because of Case A relief — this is timing
flexibility, not a discount.

## Cold start (a brand-new borrower with thin history)

A borrower who has only been on file for a few months hasn't lived through
enough of their own seasonal cycle for SETU to learn their personal
pattern reliably. Rather than guessing blind, SETU borrows the seasonal
shape from that borrower's peer cohort — "other farmers," "other market
vendors," "other gig workers" — the same reasoning a loan officer already
uses ("onion farmers in this taluk dip in July"). As the borrower
accumulates their own months of data, SETU shifts weight smoothly toward
their own actual pattern and away from the cohort average. This only ever
engages for genuinely short histories (under ~2 years of baseline); every
borrower shown in this prototype has 3 years of history, so it never
changes what you see in the demo — it's there for the real-world edge case.
