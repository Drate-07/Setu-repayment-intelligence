"""
SETU — core logic module (NO Streamlit import here on purpose).

This module implements SETU's Shortfall Classification & Intervention
Engine: everything the app needs — synthetic borrower data, classical
time-series decomposition, "seasonal dip vs real decline" classification,
a 6-month forecast, a dynamic EMI engine, and a plain-English explanation
card — lives in this one file so it can be unit-tested from the command
line without touching the UI. streamlit_app.py only calls into this module.

IMPORTANT SCOPE NOTE (read this before touching classify_recent_period):
the engine classifies the TYPE of a shortfall — Expected Seasonal Dip,
Temporary Shock, or Structural Deterioration — using only the shape of the
borrower's own cash-flow history. It does NOT claim to know the specific
CAUSE (a particular weather event, a family emergency, a stolen scooter,
etc.). Every explanation this module produces should read as "this looks
like a temporary shock" (a pattern classification), never as "this
shortfall was caused by X" (a causal diagnosis) — the classifier has no
information that could support that stronger claim, and overclaiming it
would be misleading to the loan officer relying on it.

Read top to bottom, it mirrors the pipeline:
    generate_synthetic_history()   -> raw monthly cash flow
    decompose()                    -> trend + seasonal + residual
    classify_recent_period()       -> Case A / B / C + confidence
    forecast_next_months()         -> 6-month cash flow projection
    standard_emi()                 -> fixed amortized EMI
    build_repayment_schedule()     -> fixed vs dynamic EMI, month by month
    build_explanation_card()       -> the XAI text for the loan officer
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# The formal name of this subsystem, used consistently in UI copy so the
# product is never described as inferring a shortfall's cause — only its
# type. See the module docstring above for why that distinction matters.
ENGINE_NAME = "Shortfall Classification & Intervention Engine"

# ---------------------------------------------------------------------------
# 1. SYNTHETIC DATA GENERATOR
# ---------------------------------------------------------------------------

# Each borrower type has (a) a base monthly income level, (b) a raw seasonal
# shape (rupees added/removed relative to the base, by calendar month), and
# (c) a noise level. The seasonal shape does not need to sum to zero by hand
# — generate_synthetic_history() centers it for us, exactly like the
# decomposition step will later do with real data.
BORROWER_PROFILES = {
    "Farmer": {
        "base_level": 18000.0,
        "monthly_trend": 45.0,       # slow underlying growth per month
        "noise_std": 1500.0,         # fairly predictable once you know the crop cycle
        # Strong single harvest peak (Kharif, ~Oct), lean sowing months
        "seasonal_raw": {
            1: -2000, 2: -3000, 3: -1000, 4: 1000, 5: -1500, 6: -4000,
            7: -3000, 8: -1000, 9: 2000, 10: 15000, 11: 8000, 12: -1000,
        },
    },
    "Market Vendor": {
        "base_level": 14000.0,
        "monthly_trend": 35.0,
        "noise_std": 1800.0,
        # Monsoon dip (Jun-Sep, footfall drops) + festive spike (Oct-Nov)
        "seasonal_raw": {
            1: 1000, 2: 500, 3: 0, 4: 500, 5: -500, 6: -3000,
            7: -4000, 8: -4000, 9: -2000, 10: 5000, 11: 6000, 12: 1000,
        },
    },
    "Gig Worker": {
        "base_level": 11000.0,
        "monthly_trend": 25.0,
        "noise_std": 2600.0,         # noisiest of the three, weak seasonality
        "seasonal_raw": {
            1: 200, 2: 0, 3: -200, 4: -300, 5: -200, 6: -500,
            7: -600, 8: -400, 9: 0, 10: 800, 11: 900, 12: 300,
        },
    },
}

SCENARIOS = ("Normal Seasonal Rhythm", "Temporary Shock", "Structural Decline")

# Rough, borrower-type-specific ballpark ranges for a short-term bridge loan
# (seed/fertilizer, inventory restock, vehicle-repair-style working-capital
# gaps). Used ONLY to give a loan officer a sane starting number during
# manual review of a Case B (Temporary Shock) month — see
# build_repayment_schedule()'s Case B branch. This is a static, illustrative
# range, not a computed "correct" amount, and SETU never disburses anything
# from it automatically; a human always confirms actual need first.
TYPICAL_BRIDGE_LOAN_RANGE = {
    "Farmer": (8000.0, 25000.0),          # seed, fertilizer, irrigation repair
    "Market Vendor": (5000.0, 15000.0),   # inventory restock
    "Gig Worker": (3000.0, 10000.0),      # vehicle repair, phone, fuel float
}
DEFAULT_BRIDGE_LOAN_RANGE = (5000.0, 15000.0)


def suggested_bridge_loan_range(borrower_type: str | None) -> tuple[float, float]:
    """A rough ballpark bridge-loan range for a Case B (Temporary Shock)
    month, based on typical input costs for this borrower type. NOT a
    computed "right" amount, and nothing is disbursed from it
    automatically — it exists purely so a loan officer has a sane
    starting number, pending their own confirmation of actual need."""
    return TYPICAL_BRIDGE_LOAN_RANGE.get(borrower_type, DEFAULT_BRIDGE_LOAN_RANGE)


def _centered_seasonal_map(seasonal_raw: dict) -> dict:
    """Center a 12-month seasonal shape so its values sum to ~0."""
    mean_val = np.mean(list(seasonal_raw.values()))
    return {m: v - mean_val for m, v in seasonal_raw.items()}


def _cohort_blended_seasonal_map(baseline: pd.Series, borrower_type: str | None) -> dict:
    """
    Cold-start helper (masterplan Phase 2.2): a brand-new borrower doesn't
    have enough of their own history to learn a reliable seasonal shape, so
    we borrow it from their peer cohort — "other borrowers of this type" —
    the same way a loan officer would reason ("onion farmers in this taluk
    dip in July"). Here the cohort shape is simply the borrower_type's own
    known seasonal pattern (BORROWER_PROFILES).

    We blend the cohort shape with whatever thin individual signal the
    borrower does have, with weight shifting toward the individual's own
    data as it accumulates (a simple Bayesian-shrinkage idea — explainable,
    not a trained model): 0 personal observations for a calendar month =
    100% cohort, 1 observation = 50/50, 2 observations = 2/3 individual,
    and so on.
    """
    cohort_map = (
        _centered_seasonal_map(BORROWER_PROFILES[borrower_type]["seasonal_raw"])
        if borrower_type in BORROWER_PROFILES else {m: 0.0 for m in range(1, 13)}
    )
    if len(baseline) == 0:
        return cohort_map

    # Not enough data for a real centered-moving-average trend, so use a
    # crude "remove the overall baseline mean" detrend just to isolate a
    # rough per-month seasonal signal from the little data there is.
    detrended = baseline - baseline.mean()
    months = baseline.index.month
    blended = {}
    for m in range(1, 13):
        vals = detrended.values[months == m]
        n_obs = len(vals)
        individual_est = float(np.mean(vals)) if n_obs > 0 else 0.0
        weight = n_obs / (n_obs + 1.0)
        blended[m] = weight * individual_est + (1 - weight) * cohort_map[m]

    mean_val = np.mean(list(blended.values()))
    return {m: v - mean_val for m, v in blended.items()}


def generate_synthetic_history(
    borrower_type: str,
    scenario: str,
    n_months: int = 36,
    seed: int = 42,
) -> pd.Series:
    """
    Build n_months of synthetic monthly net cash flow for one borrower.

    We deliberately default to 36 months (3 full seasonal cycles). With
    fewer than ~24 months the seasonal-index estimate is averaged over too
    few observations per calendar month and becomes noisy enough to cause
    misclassification later — so callers should not go below 24 without
    re-validating (see validate_classifier.py).

    The scenario only touches the *last few months* of the series — it
    represents something happening to the borrower "recently", layered on
    top of (not replacing) their normal seasonal pattern:
      - "Normal Seasonal Rhythm": no extra perturbation at all.
      - "Temporary Shock": one sharp, unexplained dip a couple of months
        back, with cash flow substantially recovering afterwards.
      - "Structural Decline": a genuine multi-month downward slide across
        the last 5-6 months (the kind that should NOT be auto-forgiven).
    """
    if borrower_type not in BORROWER_PROFILES:
        raise ValueError(f"Unknown borrower_type: {borrower_type}")
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")

    profile = BORROWER_PROFILES[borrower_type]
    seasonal_map = _centered_seasonal_map(profile["seasonal_raw"])
    rng = np.random.default_rng(seed)

    dates = pd.date_range(end=pd.Timestamp.today().normalize().replace(day=1),
                           periods=n_months, freq="MS")

    values = np.zeros(n_months)
    for i, date in enumerate(dates):
        trend_component = profile["base_level"] + profile["monthly_trend"] * i
        seasonal_component = seasonal_map[date.month]
        noise = rng.normal(0, profile["noise_std"])
        values[i] = trend_component + seasonal_component + noise

    # --- apply the scenario perturbation to the tail of the series only ---
    if scenario == "Normal Seasonal Rhythm":
        pass  # nothing extra — pure seasonal + noise

    elif scenario == "Temporary Shock":
        # A sharp, unexplained dip two months before the most recent month,
        # then a RECOVERING tail: each following month claws back most of
        # the shortfall, so the deviation shrinks (in noise-std units) as
        # we approach "now" rather than growing. That shrinking-deviation
        # shape is exactly what should read as "temporary", not "worsening",
        # to the classifier later. Sized in units of this borrower's own
        # noise level so it behaves consistently across borrower types.
        noise = profile["noise_std"]
        shock_idx = n_months - 3
        if shock_idx >= 0:
            values[shock_idx] -= 6.0 * noise    # the sharp dip itself
        if shock_idx + 1 < n_months:
            values[shock_idx + 1] -= 3.0 * noise  # partial rebound
        if shock_idx + 2 < n_months:
            values[shock_idx + 2] -= 1.8 * noise  # mostly, not fully, recovered

    elif scenario == "Structural Decline":
        # A genuine downward slide over the last 6 months: each month digs
        # a progressively DEEPER hole than the last, on top of the normal
        # seasonal pattern — the opposite shape of the shock's recovery.
        # Sized in noise-std units so it scales sensibly per borrower type.
        noise = profile["noise_std"]
        decline_span = 6
        start_idx = max(0, n_months - decline_span)
        span = n_months - start_idx
        for j, i in enumerate(range(start_idx, n_months)):
            depth = (j + 1) / span               # 1/span ... 1.0
            values[i] -= depth * 7.0 * noise     # glides from mild to a deep, sustained hole

    series = pd.Series(values, index=dates, name="cash_flow")
    series.attrs["borrower_type"] = borrower_type
    series.attrs["scenario"] = scenario
    series.attrs["seed"] = seed
    return series


# ---------------------------------------------------------------------------
# 2. CLASSICAL DECOMPOSITION (additive): cash flow = trend + seasonal + residual
# ---------------------------------------------------------------------------

def _centered_moving_average(values: np.ndarray, window: int = 12) -> np.ndarray:
    """
    Centered moving average for an EVEN window (default 12), using the
    standard "2x12" trick: the two months exactly on the edge of the window
    get half weight so the window is symmetric around each point. This is
    the classical textbook way to get a centered trend from monthly data
    with a 12-month seasonal cycle.

    Returns an array the same length as `values`, with NaN wherever there
    isn't a full window on both sides (the first/last `window/2` points).
    """
    n = len(values)
    trend = np.full(n, np.nan)
    half = window // 2  # 6 for window=12
    if window % 2 == 0:
        for t in range(half, n - half):
            edge = 0.5 * values[t - half] + 0.5 * values[t + half]
            middle = values[t - half + 1 : t + half].sum()
            trend[t] = (edge + middle) / window
    else:
        for t in range(half, n - half):
            trend[t] = values[t - half : t + half + 1].mean()
    return trend


def decompose(series: pd.Series, window: int = 12):
    """
    Classical additive decomposition, fit ONLY on the data handed to it.

    Returns:
        trend    : pd.Series (NaN at the edges — no full window there)
        seasonal : pd.Series (each date mapped to its calendar month's
                   seasonal index; defined everywhere, no NaNs)
        residual : pd.Series = series - trend - seasonal (NaN where trend is)
        seasonal_map : dict {1..12 -> seasonal index in rupees}, centered to
                   sum to ~0 across the 12 calendar months
    """
    values = series.values.astype(float)
    trend_vals = _centered_moving_average(values, window=window)
    trend = pd.Series(trend_vals, index=series.index, name="trend")

    detrended = series - trend
    months = series.index.month
    seasonal_raw = {}
    for m in range(1, 13):
        vals = detrended.values[months == m]
        vals = vals[~np.isnan(vals)]
        seasonal_raw[m] = float(np.mean(vals)) if len(vals) > 0 else 0.0
    seasonal_map = _centered_seasonal_map(seasonal_raw)

    seasonal_vals = np.array([seasonal_map[m] for m in months])
    seasonal = pd.Series(seasonal_vals, index=series.index, name="seasonal")

    residual = series - trend - seasonal
    residual.name = "residual"

    return trend, seasonal, residual, seasonal_map


# ---------------------------------------------------------------------------
# 3. CLASSIFYING THE MOST RECENT PERIOD (Case A / B / C)
# ---------------------------------------------------------------------------

# Tuned against validate_classifier.py across all 9 (borrower x scenario)
# combinations — see that script for the pass/fail table. These are the
# knobs to retune first if a new borrower profile or scenario is added.
Z_THRESHOLD = -1.5              # below this = "abnormal" deviation
WORSENING_SLOPE_THRESHOLD = -0.35   # z-score regression slope this negative = "getting worse"
PERSISTENCE_MONTHS = 3          # consecutive abnormal months required for Case C
MIN_BASELINE_MONTHS = 18        # below this we shrink the holdout (cold start)
HOLDOUT_MONTHS = 6


def _trailing_slope(y: np.ndarray) -> tuple[float, float]:
    """Simple linear regression y ~ a*x + b over equally spaced points."""
    if len(y) < 2:
        return 0.0, float(y[0]) if len(y) == 1 else 0.0
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def compute_confidence(baseline_len: int, resid_std: float, baseline_mean: float,
                        cold_start: bool) -> float:
    """
    More history + tighter (lower-noise) residuals = higher confidence.
    Returns a percentage 5-99.
    """
    history_factor = min(1.0, baseline_len / 30.0)
    denom = abs(baseline_mean) if abs(baseline_mean) > 1e-6 else 1.0
    noise_ratio = resid_std / denom
    noise_factor = 1.0 / (1.0 + noise_ratio * 3.0)
    confidence = 0.4 * history_factor + 0.6 * noise_factor
    if cold_start:
        confidence *= 0.7
    return round(float(np.clip(confidence, 0.05, 0.99)) * 100, 1)


def classify_recent_period(series: pd.Series,
                            holdout: int = HOLDOUT_MONTHS,
                            z_threshold: float = Z_THRESHOLD,
                            worsening_slope_threshold: float = WORSENING_SLOPE_THRESHOLD,
                            persistence_months: int = PERSISTENCE_MONTHS,
                            borrower_type: str | None = None) -> dict:
    """
    The heart of SETU's Shortfall Classification & Intervention Engine.
    Decide which TYPE of shortfall the most recent period looks like — this
    is a pattern classification against the borrower's OWN history, not a
    claim about what specifically caused it:

      Case A — Expected Seasonal Dip: normal, matches the borrower's own
               history for this time of year. No action needed; eligible
               for automatic EMI relief if DSCR is tight this month.
      Case B — Temporary Shock: an unusual dip, but not (yet) a sustained
               worsening trend. NEVER auto-adjusted — flagged for a human
               loan officer ("Officer Review Recommended") with a rough
               bridge-loan ballpark to consider, pending their own
               confirmation of the borrower's actual need. Nothing is
               disbursed automatically for Case B.
      Case C — Structural Deterioration: an abnormal AND worsening AND
               persistent decline. The system must NOT auto-adjust — this
               gets escalated to a human loan officer instead.

    Critically, the baseline trend+seasonal fit EXCLUDES the recent months
    being judged (a holdout), then extrapolates that baseline forward. If we
    instead fit the trend using all the data including the recent dip, the
    trend line "chases" the dip and partially hides it — a real decline
    would then be able to disguise itself as normal. Holding the recent
    months out avoids that trap.
    """
    n = len(series)
    cold_start = False

    if n - holdout < MIN_BASELINE_MONTHS:
        # Not enough history to hold out the full 6 months and still have a
        # usable baseline — shrink the holdout instead of crashing. This
        # lowers confidence rather than failing outright.
        holdout = max(1, n - MIN_BASELINE_MONTHS)
        cold_start = True
    if n - holdout < 6:
        # Extremely short history — do the best we can with a small holdout.
        holdout = max(1, min(holdout, n - 2)) if n > 2 else 0
        cold_start = True

    baseline = series.iloc[: n - holdout] if holdout > 0 else series.iloc[:0]
    recent = series.iloc[n - holdout :] if holdout > 0 else series.iloc[-1:]

    if len(baseline) < 6:
        # Genuine cold start: not enough data for a real trend fit, but we
        # can still do better than a flat mean by borrowing the peer
        # cohort's seasonal shape (see _cohort_blended_seasonal_map).
        # Confidence will reflect how little individual history this is.
        overall_mean = series.mean()
        overall_std = series.std() if series.std() > 0 else 1.0
        cohort_seasonal_map = _cohort_blended_seasonal_map(baseline, borrower_type)
        expected = [overall_mean + cohort_seasonal_map[d.month] for d in recent.index]
        z_scores = np.array([(float(series.loc[d]) - e) / overall_std for d, e in zip(recent.index, expected)])
        latest_z = float(z_scores[-1])
        case = "A" if latest_z >= z_threshold else "B"
        return {
            "case": case,
            "latest_z": latest_z,
            "z_scores": z_scores,
            "confidence": compute_confidence(len(baseline), overall_std, overall_mean, True),
            "resid_std": float(overall_std),
            "seasonal_map": cohort_seasonal_map,
            "trend_slope": 0.0,
            "cold_start": True,
            "holdout": holdout,
            "recent_dates": recent.index,
            "expected": expected,
            "baseline": baseline,
        }

    trend_b, seasonal_b, resid_b, seasonal_map = decompose(baseline)
    if borrower_type is not None and len(baseline) < 24:
        # Less than 2 full seasonal cycles of individual data — the
        # decompose() seasonal estimate above is unreliable (some calendar
        # months may have only 0-1 observations), so replace it with the
        # peer-cohort-blended estimate instead. This only ever engages for
        # short-history (cold-start) borrowers; a borrower with 2+ years on
        # file (like every combination validate_classifier.py checks) is
        # completely unaffected — n - holdout is 30 months there, well
        # above this 24-month cutoff.
        seasonal_map = _cohort_blended_seasonal_map(baseline, borrower_type)
    valid_resid = resid_b.dropna()
    resid_std = float(np.std(valid_resid.values)) if len(valid_resid) > 0 else float("nan")
    if resid_std <= 1e-6 or np.isnan(resid_std):
        resid_std = max(float(baseline.std()) * 0.1, 1.0)

    valid_trend = trend_b.dropna()
    tail = valid_trend.iloc[-12:] if len(valid_trend) >= 2 else valid_trend
    slope, _ = _trailing_slope(tail.values)
    last_trend_value = float(valid_trend.iloc[-1]) if len(valid_trend) > 0 else float(baseline.mean())
    last_valid_date = valid_trend.index[-1] if len(valid_trend) > 0 else baseline.index[-1]

    expected = []
    z_scores = []
    for date in recent.index:
        months_ahead = (date.year - last_valid_date.year) * 12 + (date.month - last_valid_date.month)
        expected_trend = last_trend_value + slope * months_ahead
        expected_val = expected_trend + seasonal_map[date.month]
        actual_val = float(series.loc[date])
        z = (actual_val - expected_val) / resid_std
        expected.append(expected_val)
        z_scores.append(z)

    z_scores = np.array(z_scores)
    latest_z = float(z_scores[-1])

    # Persistence: consecutive abnormal months, counting back from the latest
    consec = 0
    for z in z_scores[::-1]:
        if z < z_threshold:
            consec += 1
        else:
            break

    # Worsening: is the deviation itself getting deeper across the run of
    # abnormal months, or is it a one-off that's already recovering?
    # Deliberately regress ONLY over the current abnormal run (not the
    # whole fixed 6-month window) — a sharp dip that's healing has a
    # trough in the middle of the window, and a naive whole-window
    # regression can misread that recovery as "worsening" just because the
    # window average sits below where it started. Looking at the abnormal
    # run itself asks the right question: each abnormal month vs the one
    # before it, is the gap growing or shrinking?
    if consec >= 2:
        run = z_scores[-consec:]
    else:
        run = z_scores
    z_slope, _ = _trailing_slope(run)

    if latest_z >= z_threshold:
        case = "A"
    elif z_slope <= worsening_slope_threshold and consec >= persistence_months:
        case = "C"
    else:
        case = "B"

    confidence = compute_confidence(len(baseline), resid_std, float(baseline.mean()), cold_start)

    return {
        "case": case,
        "latest_z": latest_z,
        "z_scores": z_scores,
        "z_slope": float(z_slope),
        "persistence_months_observed": consec,
        "confidence": confidence,
        "resid_std": resid_std,
        "seasonal_map": seasonal_map,
        "trend_slope": slope,
        "cold_start": cold_start,
        "holdout": holdout,
        "recent_dates": recent.index,
        "expected": expected,
        "baseline": baseline,
    }


CASE_LABELS = {
    "A": "Expected Seasonal Dip (Case A)",
    "B": "Temporary Shock (Case B)",
    "C": "Structural Deterioration (Case C)",
}


# ---------------------------------------------------------------------------
# 4. FORECASTING THE NEXT 6 MONTHS (uses ALL history, no holdout)
# ---------------------------------------------------------------------------

def forecast_next_months(series: pd.Series, n_ahead: int = 6, band_z: float = 1.28) -> pd.DataFrame:
    """
    Project cash flow forward n_ahead months using the trend + seasonal
    pattern fit on the FULL history (unlike classify_recent_period, there's
    no need to hold anything out here — we're not judging the recent past,
    we're projecting the future for the repayment schedule).

    band_z=1.28 gives a rough 80% confidence band under a normal-residual
    assumption (a classical, explainable choice — not a deep model).

    Anchoring note (bugfix): the centered moving average behind decompose()
    can't compute a trend value for the last `window/2` months of ANY
    series — there's no future data to center on. Anchoring the forecast at
    the last non-NaN trend point (the old approach) means that point can be
    up to 6 months stale relative to "today," so the forecast is blind to
    exactly the most recent 6 months — precisely where a sudden acceleration
    (e.g. a genuine structural decline) shows up first. That produced
    forecasts that reverted to a borrower's OLDER, healthier trajectory and
    ignored a recent collapse, which then got compounded by a seasonal
    swing at the forecast horizon — most visibly for Farmer borrowers with
    a large harvest-month seasonal spike, but the same mechanism affects
    any borrower type.

    The fix: keep using the longer-run trend only for its SLOPE (direction)
    — that's still a reasonable, classical estimate — but anchor the
    forecast's LEVEL at a season-adjusted average of the last few actual
    months (each with its own calendar month's seasonal index removed),
    anchored at "today" rather than at the stale trend point. This lets the
    forecast start from where the borrower actually is right now.
    classify_recent_period()'s own Case A/B/C decision is untouched by this
    — it already uses its own separate, holdout-based extrapolation.
    """
    trend, seasonal, residual, seasonal_map = decompose(series)
    valid_resid = residual.dropna()
    resid_std = float(np.std(valid_resid.values)) if len(valid_resid) > 0 else float("nan")
    if resid_std <= 1e-6 or np.isnan(resid_std):
        resid_std = max(float(series.std()) * 0.1, 1.0)

    valid_trend = trend.dropna()
    tail = valid_trend.iloc[-12:] if len(valid_trend) >= 2 else valid_trend
    slope, _ = _trailing_slope(tail.values)

    # Season-adjusted "current level": average of the last few ACTUAL
    # months with each month's own seasonal index subtracted out. This
    # reaches all the way to the last real data point, unlike the trend
    # series above (which stops `window/2` months early).
    recent_anchor_months = min(3, len(series))
    recent = series.iloc[-recent_anchor_months:]
    deseasonalized_recent = [float(recent.iloc[i]) - seasonal_map[recent.index[i].month]
                              for i in range(len(recent))]
    current_level = float(np.mean(deseasonalized_recent))
    anchor_date = series.index[-1]  # "today" — not the stale last-valid-trend date

    future_dates = pd.date_range(start=series.index[-1] + pd.DateOffset(months=1),
                                  periods=n_ahead, freq="MS")

    rows = []
    for date in future_dates:
        months_ahead = (date.year - anchor_date.year) * 12 + (date.month - anchor_date.month)
        expected_trend = current_level + slope * months_ahead
        forecast_val = expected_trend + seasonal_map[date.month]
        rows.append({
            "month": date,
            "forecast_cash_flow": forecast_val,
            "lower_80": forecast_val - band_z * resid_std,
            "upper_80": forecast_val + band_z * resid_std,
        })
    return pd.DataFrame(rows).set_index("month")


# ---------------------------------------------------------------------------
# 5. DYNAMIC REPAYMENT ENGINE
# ---------------------------------------------------------------------------

def standard_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """Standard reducing-balance amortized EMI formula."""
    if tenure_months <= 0:
        raise ValueError("tenure_months must be positive")
    r = (annual_rate_pct / 100.0) / 12.0
    if r == 0:
        return principal / tenure_months
    factor = (1 + r) ** tenure_months
    return principal * r * factor / (factor - 1)


def build_repayment_schedule(forecast_df: pd.DataFrame,
                              fixed_emi: float,
                              case: str,
                              essential_expense_ratio: float = 0.65,
                              relief_cap_per_year: int = 2,
                              principal: float | None = None,
                              max_deferred_pct_of_principal: float = 0.20,
                              borrower_type: str | None = None) -> pd.DataFrame:
    """
    Turn a 6-month cash-flow forecast into a month-by-month fixed-vs-dynamic
    repayment plan.

    Two numbers drive every decision (masterplan Phase 1.2):
      - DSCR (Debt Service Coverage Ratio) = (cash flow - essential
        expenses) / EMI — "for every rupee owed, how many rupees are on
        hand to pay it?" essential_expense_ratio is the configurable
        fraction of predicted cash flow assumed to go to non-negotiable
        living/business expenses.
      - Free Cash Buffer = cash flow - essential expenses - EMI — the same
        idea as a rupee amount instead of a ratio: what's left in the
        borrower's pocket after everything (including the EMI) is paid.

    Rule table (applied per month) — only Case A ever gets an automatic
    schedule change. Case B and Case C both stop short of that, for
    different reasons:
      - Case C (structural decline): EMI is NEVER auto-adjusted, regardless
        of DSCR. The month is flagged for loan officer review instead. This
        is deliberate — auto-relief for a genuine decline just delays the
        borrower's problem and grows unpayable arrears.
      - Case B (temporary shock): ALSO never auto-adjusted, but for a
        different reason — a shock is, by definition, unexplained by the
        borrower's own seasonal pattern, so auto-granting relief (or
        auto-disbursing a bridge loan) here has real moral-hazard risk: the
        system would be paying out on a pattern it cannot verify is a
        genuine emergency rather than, say, a gamed or coincidental dip.
        Instead, when DSCR drops below 1.5, the month is marked "Officer
        Review Recommended" with a rough bridge-loan ballpark (see
        suggested_bridge_loan_range()) attached for the officer's
        convenience — nothing is disbursed automatically, and the fixed
        EMI is unchanged pending that human review.
      - Case A (expected seasonal dip), 1.0 <= DSCR < 1.5: cash flow is
        tight but this is the borrower's own normal rhythm -> "Seasonal
        Light EMI" — halved this month, the other half deferred (tracked,
        not forgiven, capitalized onto the balance).
      - Case A, DSCR < 1.0: cash flow can't cover essentials + EMI ->
        "Interest-only / Skip" — near-interest-only EMI (~15%).
      - Case A's relief is capped at `relief_cap_per_year` such months per
        rolling 12-month window AND by a guardrail that the running
        deferred balance can never exceed `max_deferred_pct_of_principal`
        of the loan principal — whichever limit bites first, further
        low-DSCR months escalate to review instead of granting more relief.
      - Whenever a later month is a relative income peak (top ~35% of the
        6-month forecast) AND there's a deferred balance owed (only
        possible from Case A relief), a capped catch-up top-up is added on
        top of that month's EMI to pay the deferred balance down — capped
        so it never pushes that month's own DSCR below 1.0.
    """
    cash_flows = forecast_df["forecast_cash_flow"].values
    n = len(cash_flows)

    # Identify "peak" months: top ~35% of the 6-month forecast by cash flow.
    n_peak = max(1, round(0.35 * n))
    peak_positions = set(np.argsort(cash_flows)[-n_peak:])

    deferred_cap = (max_deferred_pct_of_principal * principal) if principal else float("inf")
    bridge_low, bridge_high = suggested_bridge_loan_range(borrower_type)

    deferred = 0.0
    relief_used = 0
    rows = []

    for i, (month, cf) in enumerate(zip(forecast_df.index, cash_flows)):
        essential = essential_expense_ratio * cf
        available = cf - essential  # cash left over to service debt
        dscr_fixed = available / fixed_emi if fixed_emi > 0 else np.nan

        # Snapshot the balance OWED COMING IN to this month, before this
        # month's own dispatch below can add to it. The catch-up top-up
        # further down must only ever recover a PRIOR month's deferred
        # balance — never claw back relief this exact month just granted,
        # which would silently erase the relief within the same iteration
        # (see build_repayment_schedule's bugfix note near the top-up).
        deferred_carried_in = deferred

        dynamic_emi = fixed_emi
        status = "Standard"
        note = "Cash flow comfortably covers the fixed EMI."
        officer_review_recommended = False
        bridge_loan_low = 0.0
        bridge_loan_high = 0.0

        if case == "C":
            status = "ESCALATE - flagged for loan officer review"
            note = ("Structural decline detected — SETU does not auto-adjust EMI in this "
                    "case. Escalated for a loan officer to review in person (options: "
                    "tenure extension, partial settlement, credit counseling).")
        elif case == "B":
            # Temporary shock: never auto-adjusted. Only flag for review
            # when the fixed EMI would actually be tight/severe this month
            # — a Case B month with healthy DSCR needs no intervention at all.
            if dscr_fixed >= 1.5:
                status = "Standard"
                note = "Cash flow comfortably covers the fixed EMI."
            else:
                severity = "tight" if dscr_fixed >= 1.0 else "severe"
                officer_review_recommended = True
                bridge_loan_low, bridge_loan_high = bridge_low, bridge_high
                status = "Officer Review Recommended"
                note = (f"Temporary shock — cash flow looks {severity} this month. SETU does not "
                        f"auto-adjust the EMI or disburse anything for a temporary shock; a rough "
                        f"bridge-loan range of Rs {bridge_low:,.0f}-{bridge_high:,.0f} (typical "
                        f"{borrower_type or 'borrower'} working-capital gap) is suggested for the "
                        f"officer to weigh, PENDING their confirmation of actual need.")
        elif dscr_fixed >= 1.5:
            status = "Standard"
            note = "Cash flow comfortably covers the fixed EMI."
        elif dscr_fixed >= 1.0:
            # Reached only for Case A — B and C are fully handled above.
            relief_amount = 0.5 * fixed_emi
            room_left = deferred_cap - deferred
            if relief_used < relief_cap_per_year and relief_amount <= room_left:
                dynamic_emi = fixed_emi - relief_amount
                deferred += relief_amount
                relief_used += 1
                status = "Seasonal Light EMI (50%)"
                note = "Cash flow is tight this month; EMI halved and the difference deferred (capitalized)."
            elif relief_used >= relief_cap_per_year:
                status = "ESCALATE - relief cap reached"
                note = "Cash flow is tight but the 2-relief-months/year cap is used up; routed to loan officer."
            else:
                status = "ESCALATE - deferred-balance guardrail reached"
                note = (f"Cash flow is tight but further relief would push deferred balance past "
                        f"{max_deferred_pct_of_principal:.0%} of principal; routed to loan officer.")
        else:  # dscr_fixed < 1.0, Case A only
            relief_amount = 0.85 * fixed_emi
            room_left = deferred_cap - deferred
            if relief_used < relief_cap_per_year and relief_amount <= room_left:
                dynamic_emi = fixed_emi - relief_amount
                deferred += relief_amount
                relief_used += 1
                status = "Interest-only / Skip (Capitalized)"
                note = "Severe shortfall this month; near interest-only EMI, balance deferred (capitalized)."
            elif relief_used >= relief_cap_per_year:
                status = "ESCALATE - relief cap reached"
                note = "Severe shortfall but the relief cap is used up; routed to loan officer."
            else:
                status = "ESCALATE - deferred-balance guardrail reached"
                note = (f"Severe shortfall but further relief would push deferred balance past "
                        f"{max_deferred_pct_of_principal:.0%} of principal; routed to loan officer.")

        # Post-peak catch-up top-up: deferred balance is now only ever
        # created by Case A relief (Case B/C never defer anything), so this
        # is effectively a Case-A-only step — the `case == "A"` guard just
        # makes that explicit rather than relying on deferred staying 0.
        #
        # BUGFIX: this must gate on `deferred_carried_in` (the balance owed
        # BEFORE this month), not the current `deferred` (which may already
        # include relief this SAME month just granted, above). Gating on
        # the live `deferred` meant that whenever a relief month was ALSO a
        # top-35%-by-cash-flow "peak" month — which happens often, since a
        # month with a DSCR of 1.0-1.5 already has real slack above the
        # halved EMI — the top-up fired in that identical month and
        # immediately clawed back the relief it had just granted, leaving
        # dynamic_emi == fixed_emi (a silent "Reduce EMI 0%" instead of the
        # intended ~50%). Recovering a balance is only meaningful for a
        # balance that was already owed coming into the month.
        topup = 0.0
        if case == "A" and deferred_carried_in > 0 and i in peak_positions:
            capacity = max(0.0, available - dynamic_emi)  # keeps this month's DSCR >= 1
            topup = min(deferred_carried_in, capacity)
            if topup > 0:
                dynamic_emi += topup
                deferred -= topup
                note += " EMI increased with a catch-up top-up this month (income peak) to pay down deferred balance."
                if "Standard" in status:
                    status = "Top-up Applied"

        dscr_dynamic = available / dynamic_emi if dynamic_emi > 0 else np.nan
        free_cash_buffer_fixed = available - fixed_emi
        free_cash_buffer_dynamic = available - dynamic_emi

        rows.append({
            "month": month,
            "predicted_cash_flow": cf,
            "fixed_emi": fixed_emi,
            "dynamic_emi": dynamic_emi,
            "dscr_fixed": dscr_fixed,
            "dscr_dynamic": dscr_dynamic,
            "free_cash_buffer_fixed": free_cash_buffer_fixed,
            "free_cash_buffer_dynamic": free_cash_buffer_dynamic,
            "status": status,
            "note": note,
            "deferred_balance": deferred,
            "topup_applied": topup,
            "officer_review_recommended": officer_review_recommended,
            "bridge_loan_low": bridge_loan_low,
            "bridge_loan_high": bridge_loan_high,
        })

    return pd.DataFrame(rows).set_index("month")


# ---------------------------------------------------------------------------
# 6. XAI EXPLANATION CARD
# ---------------------------------------------------------------------------

def build_explanation_card(borrower_name: str, classification: dict, series: pd.Series,
                            borrower_type: str | None = None) -> dict:
    """
    Build the plain-English explanation of the classification — written the
    way you'd explain it to a bank auditor, not a debug log. Returns a dict
    the UI can render directly (no raw internals leaking through).
    """
    case = classification["case"]
    latest_date = classification["recent_dates"][-1]
    latest_actual = float(series.loc[latest_date])
    expected_val = float(classification["expected"][-1])
    seasonal_val = classification["seasonal_map"].get(latest_date.month, 0.0)
    trend_component = expected_val - seasonal_val
    baseline_mean = float(classification["baseline"].mean()) if len(classification["baseline"]) else float(series.mean())
    one_off_component = latest_actual - expected_val

    headline = CASE_LABELS[case]

    if case == "A":
        action = "No action needed — continue with the standard EMI schedule (auto-adjusts if DSCR runs tight)."
    elif case == "B":
        b_low, b_high = suggested_bridge_loan_range(borrower_type)
        action = (f"Do NOT auto-adjust the EMI or auto-disburse anything — flag for officer review, with a "
                  f"rough bridge-loan range of Rs {b_low:,.0f}-{b_high:,.0f} for the officer to weigh, "
                  f"pending confirmation of the borrower's actual need.")
    else:
        action = "Do NOT auto-adjust the EMI — escalate to a loan officer for a manual review of the account."

    rule_triggers = [
        (f"1. Deviation test: {borrower_name}'s cash flow in "
         f"{latest_date.strftime('%b %Y')} was {classification['latest_z']:.2f} standard deviations "
         f"{'below' if classification['latest_z'] < 0 else 'above'} what their own history predicts for this time of year "
         f"({'within normal range' if classification['latest_z'] >= Z_THRESHOLD else 'outside normal range'})."),
        (f"2. Trend-slope test: the gap between actual and expected cash flow has been "
         f"{'widening (getting worse)' if classification.get('z_slope', 0) <= WORSENING_SLOPE_THRESHOLD else 'stable or improving'} "
         f"over the last {classification['holdout']} months."),
        (f"3. Persistence test: {classification.get('persistence_months_observed', 0)} consecutive month(s) of abnormal "
         f"deviation observed (a structural decline requires {PERSISTENCE_MONTHS}+)."),
    ]

    feature_attribution = [
        {"factor": "Seasonal pattern (expected for this month)", "rupees": round(seasonal_val, 0)},
        {"factor": "Underlying trend level (vs long-run average)", "rupees": round(trend_component - baseline_mean, 0)},
        {"factor": "One-off / unexplained deviation this month", "rupees": round(one_off_component, 0)},
    ]

    cold_start = classification.get("cold_start", False)
    confidence_note = (
        "Limited personal history — this borrower's seasonal pattern was blended with "
        "their peer cohort's known pattern (other borrowers of the same type) rather than "
        "estimated from their own thin data alone."
        if cold_start else
        f"Based on {len(classification['baseline'])} months of {borrower_name}'s own transaction history."
    )

    return {
        "borrower": borrower_name,
        "period": latest_date.strftime("%B %Y"),
        "headline": headline,
        "recommended_action": action,
        "rule_triggers": rule_triggers,
        "feature_attribution": feature_attribution,
        "confidence_pct": classification["confidence"],
        "confidence_note": confidence_note,
        "cold_start": cold_start,
    }
