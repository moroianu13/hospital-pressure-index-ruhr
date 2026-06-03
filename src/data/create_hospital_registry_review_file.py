"""
Create manual review file for hospital registry classification.

Input:
    data/processed/ruhr_hospital_registry_classified.csv

Output:
    data/manual/hospital_registry_review.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_registry_classified.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "manual" / "hospital_registry_review.csv"


def main() -> None:
    df = pd.read_csv(INPUT_PATH)

    review = df[
        [
            "hospital_id",
            "city",
            "hospital_name",
            "hospital_registry_type",
            "operator_name",
            "street",
            "hospital_care_category",
            "acute_relevance_weight",
            "classification_reason",
        ]
    ].copy()

    review = review.rename(
        columns={
            "hospital_care_category": "automatic_category",
            "acute_relevance_weight": "automatic_acute_relevance_weight",
            "classification_reason": "automatic_classification_reason",
        }
    )

    review["verified_category"] = ""
    review["verified_acute_relevance_weight"] = ""
    review["verification_status"] = "needs_verification"
    review["source_type"] = ""
    review["source_url"] = ""
    review["review_notes"] = ""

    review = review.sort_values(["city", "hospital_name"]).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved review file to: {OUTPUT_PATH}")
    print(f"Shape: {review.shape}")
    print(review.head(20))


if __name__ == "__main__":
    main()
