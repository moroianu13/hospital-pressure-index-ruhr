"""
Apply manual hospital registry review.

Inputs:
    data/processed/ruhr_hospital_registry_classified.csv
    data/manual/hospital_registry_review.csv

Output:
    data/processed/ruhr_hospital_registry_verified.csv

Manual review overrides automatic classification only where
verification_status == 'verified'.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

AUTO_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_registry_classified.csv"
REVIEW_PATH = PROJECT_ROOT / "data" / "manual" / "hospital_registry_review.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_registry_verified.csv"


def main() -> None:
    auto_df = pd.read_csv(AUTO_PATH)
    review_df = pd.read_csv(REVIEW_PATH)

    review_columns = [
        "hospital_id",
        "verified_category",
        "verified_acute_relevance_weight",
        "verification_status",
        "source_type",
        "source_url",
        "review_notes",
    ]

    df = auto_df.merge(
        review_df[review_columns],
        on="hospital_id",
        how="left",
        validate="one_to_one",
    )

    df["final_care_category"] = df["hospital_care_category"]
    df["final_acute_relevance_weight"] = df["acute_relevance_weight"]
    df["final_classification_source"] = "automatic"

    verified_mask = (
        df["verification_status"].fillna("").eq("verified")
        & df["verified_category"].notna()
        & df["verified_acute_relevance_weight"].notna()
    )

    df.loc[verified_mask, "final_care_category"] = df.loc[
        verified_mask, "verified_category"
    ]

    df.loc[verified_mask, "final_acute_relevance_weight"] = pd.to_numeric(
        df.loc[verified_mask, "verified_acute_relevance_weight"],
        errors="coerce",
    )

    df.loc[verified_mask, "final_classification_source"] = "manual_verified"

    df["final_include_in_acute_pressure"] = df["final_acute_relevance_weight"] > 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved verified registry to: {OUTPUT_PATH}")
    print(f"Shape: {df.shape}")

    print("\nFinal category counts:")
    print(df["final_care_category"].value_counts(dropna=False))

    print("\nClassification source counts:")
    print(df["final_classification_source"].value_counts(dropna=False))

    print("\nStill needs verification:")
    print(
        df[df["final_classification_source"] == "automatic"][
            [
                "city",
                "hospital_name",
                "hospital_care_category",
                "acute_relevance_weight",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
