"""
Build city-level hospital type correction factors.

Input:
    data/processed/ruhr_hospital_registry_verified.csv

Output:
    data/processed/ruhr_hospital_type_correction.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_registry_verified.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_type_correction.csv"


def main() -> None:
    df = pd.read_csv(INPUT_PATH)

    correction = (
        df.groupby("city")
        .agg(
            total_hospital_sites=("hospital_id", "count"),
            acute_relevance_weight_sum=("final_acute_relevance_weight", "sum"),
            included_hospital_sites=("final_include_in_acute_pressure", "sum"),
            general_or_acute_sites=(
                "final_care_category",
                lambda x: (x == "general_or_acute_care").sum(),
            ),
            psychiatric_psychosomatic_sites=(
                "final_care_category",
                lambda x: (x == "psychiatric_psychosomatic").sum(),
            ),
            rehabilitation_sites=(
                "final_care_category",
                lambda x: (x == "rehabilitation").sum(),
            ),
            specialized_partial_sites=(
                "final_care_category",
                lambda x: (x == "specialized_or_partial_acute").sum(),
            ),
            unknown_needs_review_sites=(
                "final_care_category",
                lambda x: (x == "unknown_needs_review").sum(),
            ),
        )
        .reset_index()
    )

    correction["acute_relevance_factor"] = (
        correction["acute_relevance_weight_sum"]
        / correction["total_hospital_sites"]
    ).round(3)

    correction = correction.sort_values("city").reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    correction.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved hospital type correction to: {OUTPUT_PATH}")
    print(correction.sort_values("acute_relevance_factor"))


if __name__ == "__main__":
    main()