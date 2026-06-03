"""
Classify Ruhr hospitals by acute-care relevance.

Input:
    data/processed/ruhr_hospital_registry_clean.csv

Output:
    data/processed/ruhr_hospital_registry_classified.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_registry_clean.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_registry_classified.csv"


def classify_hospital(row: pd.Series) -> pd.Series:
    """Classify hospital by name/operator keywords."""
    name = str(row["hospital_name"]).lower()
    operator = str(row["operator_name"]).lower()
    combined = f"{name} {operator}"

    row["hospital_care_category"] = "unknown_needs_review"
    row["include_in_acute_pressure"] = True
    row["acute_relevance_weight"] = 0.5
    row["classification_reason"] = "No clear automatic rule matched."

    psychiatric_terms = [
        "psychiatr",
        "psychosom",
        "lvr",
        "lwl",
        "elisabeth-klinik",
    ]

    rehab_terms = [
        "reha",
        "rehabilitation",
        "rehaklinik",
        "klinik für rehabilitation",
    ]

    acute_terms = [
        "universitätsklinikum",
        "klinikum",
        "krankenhaus",
        "knappschaftskrankenhaus",
        "marien hospital",
        "marienhospital",
        "st. josef",
        "st.-josef",
        "elisabeth-krankenhaus",
        "evangelisches krankenhaus",
        "katholisches klinikum",
    ]

    specialized_terms = [
        "tagesklinik",
        "augenklinik",
        "orthopädie",
        "orthopädisch",
        "fachklinik",
    ]

    if any(term in combined for term in psychiatric_terms):
        row["hospital_care_category"] = "psychiatric_psychosomatic"
        row["include_in_acute_pressure"] = False
        row["acute_relevance_weight"] = 0.0
        row["classification_reason"] = "Psychiatric/psychosomatic or LVR/LWL provider detected."

    elif any(term in combined for term in rehab_terms):
        row["hospital_care_category"] = "rehabilitation"
        row["include_in_acute_pressure"] = False
        row["acute_relevance_weight"] = 0.0
        row["classification_reason"] = "Rehabilitation-related term detected."

    elif any(term in combined for term in specialized_terms):
        row["hospital_care_category"] = "specialized_or_elective"
        row["include_in_acute_pressure"] = True
        row["acute_relevance_weight"] = 0.3
        row["classification_reason"] = "Specialized/elective-care term detected."

    elif any(term in combined for term in acute_terms):
        row["hospital_care_category"] = "general_or_acute_care"
        row["include_in_acute_pressure"] = True
        row["acute_relevance_weight"] = 1.0
        row["classification_reason"] = "General hospital / acute-care term detected."

    return row


def main() -> None:
    df = pd.read_csv(INPUT_PATH)

    df = df.apply(classify_hospital, axis=1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved classified registry to: {OUTPUT_PATH}")
    print(f"Shape: {df.shape}")

    print("\nCare category counts:")
    print(df["hospital_care_category"].value_counts())

    print("\nAcute relevance by city:")
    print(
        df.groupby("city")
        .agg(
            total_hospitals=("hospital_id", "count"),
            acute_weight_sum=("acute_relevance_weight", "sum"),
            included_sites=("include_in_acute_pressure", "sum"),
        )
        .sort_index()
    )

    print("\nNeeds review:")
    print(
        df[df["hospital_care_category"] == "unknown_needs_review"][
            [
                "city",
                "hospital_name",
                "operator_name",
                "classification_reason",
            ]
        ]
    )


if __name__ == "__main__":
    main()
