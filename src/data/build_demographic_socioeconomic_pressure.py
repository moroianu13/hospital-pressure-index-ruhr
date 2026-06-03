"""
Build demographic and socio-economic adjusted hospital pressure dataset.

Inputs:
    data/processed/ruhr_hospital_pressure_adjusted_2015_2024.csv
    data/processed/ruhr_demographics_2015_2024_clean.csv
    data/processed/ruhr_unemployment_2015_2024_clean.csv

Output:
    data/processed/ruhr_hospital_pressure_demographic_socioeconomic_2015_2024.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.features.pressure_index import min_max_scale


PROJECT_ROOT = Path(__file__).resolve().parents[2]

HOSPITAL_PRESSURE_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_pressure_adjusted_2015_2024.csv"
)

DEMOGRAPHICS_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_demographics_2015_2024_clean.csv"
)

UNEMPLOYMENT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_unemployment_2015_2024_clean.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ruhr_hospital_pressure_demographic_socioeconomic_2015_2024.csv"
)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hospital_df = pd.read_csv(HOSPITAL_PRESSURE_PATH)
    demographics_df = pd.read_csv(DEMOGRAPHICS_PATH)
    unemployment_df = pd.read_csv(UNEMPLOYMENT_PATH)

    return hospital_df, demographics_df, unemployment_df


def add_population_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["patients_per_1000_population"] = (
        df["stationary_patients"] / df["population_total"] * 1000
    )

    df["beds_per_1000_population"] = (
        df["beds"] / df["population_total"] * 1000
    )

    df["adjusted_beds_per_1000_population"] = (
        df["adjusted_beds"] / df["population_total"] * 1000
    )

    df["physician_fte_per_1000_population"] = (
        df["hospital_physicians"] / df["population_total"] * 1000
    )

    df["adjusted_physician_fte_per_1000_population"] = (
        df["adjusted_hospital_physicians"] / df["population_total"] * 1000
    )

    return df


def add_yearly_pressure_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    score_columns = [
        "patients_per_1000_population_score",
        "population_65_plus_score",
        "population_80_plus_score",
        "unemployment_pressure_score",
        "long_term_unemployment_pressure_score",
        "demographic_socioeconomic_pressure_score",
    ]

    for column in score_columns:
        df[column] = pd.NA

    for year in sorted(df["year"].dropna().unique()):
        year_mask = df["year"] == year
        year_df = df.loc[year_mask].copy()

        score_specs = [
            ("patients_per_1000_population", "patients_per_1000_population_score"),
            ("population_65_plus_pct", "population_65_plus_score"),
            ("population_80_plus_pct", "population_80_plus_score"),
            ("unemployment_rate_proxy", "unemployment_pressure_score"),
            ("long_term_unemployment_rate", "long_term_unemployment_pressure_score"),
        ]

        for source_column, score_column in score_specs:
            min_value = year_df[source_column].min()
            max_value = year_df[source_column].max()

            df.loc[year_mask, score_column] = year_df[source_column].apply(
                lambda value: min_max_scale(value, min_value, max_value)
            )

        df.loc[year_mask, "demographic_socioeconomic_pressure_score"] = (
            df.loc[year_mask, "patients_per_1000_population_score"] * 0.30
            + df.loc[year_mask, "population_65_plus_score"] * 0.20
            + df.loc[year_mask, "population_80_plus_score"] * 0.20
            + df.loc[year_mask, "unemployment_pressure_score"] * 0.20
            + df.loc[year_mask, "long_term_unemployment_pressure_score"] * 0.10
        )

    return df


def add_final_hpi_layers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Demographic and socioeconomic factors act as a risk amplifier
    # over acute-care-adjusted pressure, not as a replacement score.
    df["demographic_socioeconomic_hpi"] = (
        df["acute_care_adjusted_hpi"]
        + df["demographic_socioeconomic_pressure_score"] * 0.20
    )

    df["demographic_socioeconomic_hpi"] = df[
        "demographic_socioeconomic_hpi"
    ].clip(upper=100)

    df["hospital_type_corrected_hpi"] = df["acute_care_adjusted_hpi"]

    return df


def build_dataset() -> pd.DataFrame:
    hospital_df, demographics_df, unemployment_df = load_data()

    df = hospital_df.merge(
        demographics_df,
        on=["city", "year"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_demographics"),
    )

    df = df.merge(
        unemployment_df,
        on=["city", "year"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_unemployment"),
    )

    df = add_population_indicators(df)
    df = add_yearly_pressure_scores(df)
    df = add_final_hpi_layers(df)

    numeric_columns = [
        "patients_per_1000_population",
        "beds_per_1000_population",
        "adjusted_beds_per_1000_population",
        "physician_fte_per_1000_population",
        "adjusted_physician_fte_per_1000_population",
        "patients_per_1000_population_score",
        "population_65_plus_score",
        "population_80_plus_score",
        "unemployment_pressure_score",
        "long_term_unemployment_pressure_score",
        "demographic_socioeconomic_pressure_score",
        "demographic_socioeconomic_hpi",
        "hospital_type_corrected_hpi",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").round(2)

    df = df.sort_values(["city", "year"]).reset_index(drop=True)

    return df


def main() -> None:
    df = build_dataset()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved demographic-socioeconomic pressure dataset to: {OUTPUT_PATH}")
    print(f"Shape: {df.shape}")

    latest_year = int(df["year"].max())
    latest = df[df["year"] == latest_year].copy()

    print("\nLatest year comparison:")
    print(
        latest[
            [
                "city",
                "hospital_hpi",
                "acute_care_adjusted_hpi",
                "demographic_socioeconomic_hpi",
                "population_total",
                "population_65_plus_pct",
                "population_80_plus_pct",
                "unemployment_rate_proxy",
                "long_term_unemployment_rate",
            ]
        ]
        .sort_values("demographic_socioeconomic_hpi", ascending=False)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
