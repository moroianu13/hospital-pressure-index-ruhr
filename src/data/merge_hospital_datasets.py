
"""
Merge Ruhr hospital capacity and workforce datasets.

Inputs:
    data/processed/ruhr_hospital_capacity_2015_2024_clean.csv
    data/processed/ruhr_hospital_regionalvergleich_clean.csv

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

REGIONALVERGLEICH_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_regionalvergleich_clean.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_combined_2015_2024.csv"
)


def load_capacity_data() -> pd.DataFrame:
    """Load official Landesdatenbank hospital capacity data."""
    return pd.read_csv(CAPACITY_PATH)


def load_workforce_data() -> pd.DataFrame:
    """Load Regionalvergleich data containing hospital physicians."""
    df = pd.read_csv(REGIONALVERGLEICH_PATH)

    return df[
        [
            "city",
            "year",
            "hospital_physicians",
        ]
    ].copy()


def merge_datasets() -> pd.DataFrame:
    """Merge capacity and workforce datasets by city and year."""
    capacity_df = load_capacity_data()
    workforce_df = load_workforce_data()

    df = capacity_df.merge(
        workforce_df,
        on=["city", "year"],
        how="left",
        validate="one_to_one",
    )

    df["patients_per_physician"] = (
        df["stationary_patients"] / df["hospital_physicians"]
    )

    df["has_physician_data"] = df["hospital_physicians"].notna()

    df["data_completeness_status"] = df["has_physician_data"].map(
        {
            True: "capacity_and_physicians",
            False: "capacity_only",
        }
    )

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

    print("\n2024 rows:")
    print(
        df[df["year"] == 2024][
            [
                "city",
                "hospitals",
                "beds",
                "stationary_patients",
                "hospital_physicians",
                "data_completeness_status",
            ]
        ]
    )


if __name__ == "__main__":
    main()
