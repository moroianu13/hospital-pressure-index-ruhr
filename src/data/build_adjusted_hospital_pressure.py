"""
Build hospital pressure dataset with hospital type correction layer.

Inputs:
    data/processed/ruhr_hospital_combined_2015_2024.csv
    data/processed/ruhr_hospital_type_correction.csv

Output:
    data/processed/ruhr_hospital_pressure_adjusted_2015_2024.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.features.pressure_index import calculate_hospital_only_hpi, min_max_scale


PROJECT_ROOT = Path(__file__).resolve().parents[2]

HOSPITAL_DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_combined_2015_2024.csv"
)

CORRECTION_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_type_correction.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_pressure_adjusted_2015_2024.csv"
)


REQUIRED_BASE_COLUMNS = [
    "stationary_patients",
    "beds",
    "hospital_physicians",
    "bed_occupancy_rate",
    "avg_length_of_stay",
    "patients_per_bed",
    "patients_per_physician",
]

REQUIRED_ADJUSTED_COLUMNS = [
    "stationary_patients",
    "adjusted_beds",
    "adjusted_hospital_physicians",
    "bed_occupancy_rate",
    "avg_length_of_stay",
    "adjusted_patients_per_bed",
    "adjusted_patients_per_physician",
]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load base hospital dataset and city-level hospital type correction."""
    hospital_df = pd.read_csv(HOSPITAL_DATA_PATH)
    correction_df = pd.read_csv(CORRECTION_PATH)

    return hospital_df, correction_df


def add_completion_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add completeness flags for base and adjusted HPI."""
    df = df.copy()

    df["is_hpi_complete"] = (
        df[REQUIRED_BASE_COLUMNS].notna().all(axis=1)
        & (df["stationary_patients"] > 0)
        & (df["beds"] > 0)
        & (df["hospital_physicians"] > 0)
        & (df["bed_occupancy_rate"] > 0)
        & (df["avg_length_of_stay"] > 0)
    )

    df["is_acute_adjusted_hpi_complete"] = (
        df[REQUIRED_ADJUSTED_COLUMNS].notna().all(axis=1)
        & (df["stationary_patients"] > 0)
        & (df["adjusted_beds"] > 0)
        & (df["adjusted_hospital_physicians"] > 0)
        & (df["bed_occupancy_rate"] > 0)
        & (df["avg_length_of_stay"] > 0)
    )

    return df


def add_score_columns_by_year(
    df: pd.DataFrame,
    complete_flag: str,
    score_input_columns: dict[str, str],
    output_hpi_column: str,
) -> pd.DataFrame:
    """Calculate relative HPI scores year-by-year for a selected layer."""
    df = df.copy()

    for score_column in score_input_columns.values():
        df[score_column] = pd.NA

    df[output_hpi_column] = pd.NA

    for year in sorted(df["year"].dropna().unique()):
        year_mask = (df["year"] == year) & df[complete_flag]
        year_df = df.loc[year_mask].copy()

        if year_df.empty:
            continue

        for source_column, score_column in score_input_columns.items():
            min_value = year_df[source_column].min()
            max_value = year_df[source_column].max()

            df.loc[year_mask, score_column] = year_df[source_column].apply(
                lambda value: min_max_scale(value, min_value, max_value)
            )

        df.loc[year_mask, output_hpi_column] = df.loc[year_mask].apply(
            lambda row: calculate_hospital_only_hpi(
                patients_per_bed_score=row[list(score_input_columns.values())[0]],
                patients_per_physician_score=row[list(score_input_columns.values())[1]],
                occupancy_score=row[list(score_input_columns.values())[2]],
                length_of_stay_score=row[list(score_input_columns.values())[3]],
            ),
            axis=1,
        )

    return df


def progressive_acute_hpi(row: pd.Series) -> float:
    """Make acute-care HPI a progressive correction over hospital_hpi."""
    hospital_hpi = row["hospital_hpi"]
    recalculated_hpi = row["acute_care_recalculated_hpi"]
    acute_factor = row["acute_relevance_factor"]

    if pd.isna(hospital_hpi):
        return pd.NA

    if pd.isna(recalculated_hpi):
        return hospital_hpi

    if pd.isna(acute_factor) or acute_factor >= 0.999:
        return hospital_hpi

    return max(hospital_hpi, recalculated_hpi)



def build_adjusted_pressure_dataset() -> pd.DataFrame:
    """Build final historical pressure dataset with base and adjusted HPI."""
    hospital_df, correction_df = load_data()

    correction_columns = [
        "city",
        "total_hospital_sites",
        "acute_relevance_weight_sum",
        "general_or_acute_sites",
        "psychiatric_psychosomatic_sites",
        "specialized_partial_sites",
        "acute_relevance_factor",
    ]

    df = hospital_df.merge(
        correction_df[correction_columns],
        on="city",
        how="left",
        validate="many_to_one",
    )

    df["acute_relevance_factor"] = df["acute_relevance_factor"].fillna(1.0)

    df["hospital_hpi"] = pd.NA

    df["adjusted_beds"] = df["beds"] * df["acute_relevance_factor"]
    df["adjusted_hospital_physicians"] = (
        df["hospital_physicians"] * df["acute_relevance_factor"]
    )

    df["adjusted_patients_per_bed"] = (
        df["stationary_patients"] / df["adjusted_beds"]
    )
    df["adjusted_patients_per_physician"] = (
        df["stationary_patients"] / df["adjusted_hospital_physicians"]
    )

    df = add_completion_flags(df)

    base_score_columns = {
        "patients_per_bed": "patients_per_bed_score",
        "patients_per_physician": "patients_per_physician_score",
        "bed_occupancy_rate": "occupancy_score",
        "avg_length_of_stay": "length_of_stay_score",
    }

    adjusted_score_columns = {
        "adjusted_patients_per_bed": "adjusted_patients_per_bed_score",
        "adjusted_patients_per_physician": "adjusted_patients_per_physician_score",
        "bed_occupancy_rate": "adjusted_occupancy_score",
        "avg_length_of_stay": "adjusted_length_of_stay_score",
    }

    df = add_score_columns_by_year(
        df=df,
        complete_flag="is_hpi_complete",
        score_input_columns=base_score_columns,
        output_hpi_column="hospital_hpi",
    )

    df = add_score_columns_by_year(
        df=df,
        complete_flag="is_acute_adjusted_hpi_complete",
        score_input_columns=adjusted_score_columns,
        output_hpi_column="acute_care_adjusted_hpi",
    )


    # Preserve the fully recalculated acute-care HPI for audit/debugging.
    df["acute_care_recalculated_hpi"] = df["acute_care_adjusted_hpi"]

    # Product/clinical interpretation:
    # The acute-care layer is a progressive correction over the all-hospital layer.
    # It should not reduce pressure below the original all-hospital HPI.
    df["acute_care_adjusted_hpi"] = df.apply(
        progressive_acute_hpi,
        axis=1,
    )

    df["hpi"] = df["hospital_hpi"]

    numeric_columns = [
        "hospital_hpi",
        "acute_care_adjusted_hpi",
        "adjusted_beds",
        "adjusted_hospital_physicians",
        "adjusted_patients_per_bed",
        "adjusted_patients_per_physician",
        "patients_per_bed_score",
        "patients_per_physician_score",
        "occupancy_score",
        "length_of_stay_score",
        "adjusted_patients_per_bed_score",
        "adjusted_patients_per_physician_score",
        "adjusted_occupancy_score",
        "adjusted_length_of_stay_score",
        "acute_care_recalculated_hpi",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").round(2)

    df = df.sort_values(["city", "year"]).reset_index(drop=True)
   
    return df


def main() -> None:
    df = build_adjusted_pressure_dataset()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved adjusted pressure dataset to: {OUTPUT_PATH}")
    print(f"Shape: {df.shape}")

    print("\nLatest year comparison:")
    latest_year = int(df["year"].max())
    print(
        df[
            (df["year"] == latest_year)
            & (df["is_acute_adjusted_hpi_complete"])
        ][
            [
                "city",
                "acute_relevance_factor",
                "hospital_hpi",
                "acute_care_adjusted_hpi",
                "beds",
                "adjusted_beds",
                "hospital_physicians",
                "adjusted_hospital_physicians",
            ]
        ].sort_values("acute_care_adjusted_hpi", ascending=False)
    )


if __name__ == "__main__":
    main()
