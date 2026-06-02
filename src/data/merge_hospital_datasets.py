"""
Merge Ruhr hospital capacity and physician datasets.

Inputs:
    data/processed/ruhr_hospital_capacity_2015_2024_clean.csv
    data/processed/ruhr_hospital_physicians_2015_2024_clean.csv

Output:
    data/processed/ruhr_hospital_combined_2015_2024.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CAPACITY_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_capacity_2015_2024_clean.csv"
)

PHYSICIANS_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_physicians_2015_2024_clean.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_combined_2015_2024.csv"
)


def load_capacity_data() -> pd.DataFrame:
    """Load official Landesdatenbank hospital capacity data."""
    return pd.read_csv(CAPACITY_PATH)


def load_physicians_data() -> pd.DataFrame:
    """Load official Landesdatenbank hospital physicians data."""
    return pd.read_csv(PHYSICIANS_PATH)


def merge_datasets() -> pd.DataFrame:
    """Merge capacity and physician datasets by city and year."""
    capacity_df = load_capacity_data()
    physicians_df = load_physicians_data()

    df = capacity_df.merge(
        physicians_df,
        on=["city", "year", "region_code"],
        how="left",
        validate="one_to_one",
    )

    df["hospital_physicians"] = df["hospital_physicians_total"]

    df["patients_per_physician"] = (
        df["stationary_patients"] / df["hospital_physicians"]
    )

    df["has_patient_data"] = df["stationary_patients"].notna()
    df["has_physician_data"] = df["hospital_physicians"].notna()

    df["data_completeness_status"] = "complete"
    df.loc[~df["has_patient_data"], "data_completeness_status"] = "missing_patient_data"
    df.loc[~df["has_physician_data"], "data_completeness_status"] = "missing_physician_data"
    df.loc[
        ~df["has_patient_data"] & ~df["has_physician_data"],
        "data_completeness_status",
    ] = "missing_patient_and_physician_data"

    df = df.sort_values(["city", "year"]).reset_index(drop=True)

    return df


def main() -> None:
    df = merge_datasets()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved combined dataset to: {OUTPUT_PATH}")
    print(f"Shape: {df.shape}")
    print("Years:", df["year"].min(), "-", df["year"].max())
    print("Cities:", sorted(df["city"].dropna().unique()))

    print("\nCompleteness status:")
    print(df["data_completeness_status"].value_counts(dropna=False))

    print("\n2024 rows:")
    print(
        df[df["year"] == 2024][
            [
                "city",
                "hospitals",
                "beds",
                "stationary_patients",
                "hospital_physicians",
                "patients_per_physician",
                "data_completeness_status",
            ]
        ]
    )


if __name__ == "__main__":
    main()
