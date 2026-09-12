"""
Mandatory validation script for the SETU classifier (setu_core.py).

Runs all 9 combinations of borrower_type x scenario and checks that the
classifier lands on the expected Case:

    Normal Seasonal Rhythm  -> Case A
    Temporary Shock         -> Case B
    Structural Decline      -> Case C

Run with:  python validate_classifier.py
"""

import numpy as np

from setu_core import (
    BORROWER_PROFILES, SCENARIOS, generate_synthetic_history,
    classify_recent_period, CASE_LABELS,
)

EXPECTED = {
    "Normal Seasonal Rhythm": "A",
    "Temporary Shock": "B",
    "Structural Decline": "C",
}

SEEDS = [1, 2, 3, 4, 5]  # check robustness across several seeds, not just one


def main():
    borrower_types = list(BORROWER_PROFILES.keys())
    total = 0
    passed = 0
    rows = []

    for borrower_type in borrower_types:
        for scenario in SCENARIOS:
            expected_case = EXPECTED[scenario]
            case_counts = {"A": 0, "B": 0, "C": 0}
            details = []
            for seed in SEEDS:
                series = generate_synthetic_history(borrower_type, scenario, n_months=36, seed=seed)
                result = classify_recent_period(series)
                case_counts[result["case"]] += 1
                details.append((seed, result["case"], result["latest_z"], result.get("z_slope", 0),
                                 result.get("persistence_months_observed", 0)))

            majority_case = max(case_counts, key=case_counts.get)
            ok = majority_case == expected_case
            total += 1
            passed += int(ok)
            status = "PASS" if ok else "FAIL"

            print(f"[{status}] {borrower_type:14s} | {scenario:24s} | expected {expected_case} "
                  f"| got {case_counts} (majority={majority_case})")
            for seed, case, z, zslope, persist in details:
                print(f"         seed={seed}: case={case} latest_z={z:6.2f} z_slope={zslope:6.3f} "
                      f"persistence={persist}")
            rows.append((borrower_type, scenario, expected_case, majority_case, ok))

    print()
    print(f"{passed}/{total} combinations classified as expected (majority vote across {len(SEEDS)} seeds).")
    if passed < total:
        print("Some combinations did not match. Review the per-seed detail above and consider")
        print("retuning Z_THRESHOLD / WORSENING_SLOPE_THRESHOLD / PERSISTENCE_MONTHS in setu_core.py,")
        print("or the scenario perturbation strength in generate_synthetic_history().")
    else:
        print("All combinations classified as expected. Classifier is ready to wire into the UI.")


if __name__ == "__main__":
    main()
