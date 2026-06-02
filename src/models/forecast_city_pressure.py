
"""
Forecast Ruhr hospital pressure indicators for 2025–2030.

Input:
    data/processed/ruhr_hospital_combined_2015_2024.csv

Output:
    data/processed/ruhr_hospital_forecast_2025_2030.csv

The script creates scenario-based forecasts for:
- beds
- stationary patients
- hospital physicians
- bed occupancy rate
- average length of stay

Then it calculates derived indicators and HPI scores per scenario/year.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression

from src.features.pressure_index import calculate_hospital_only_hpi, min_max_scale


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_combined_2015_2024.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_forecast_2025_2030.csv"

FORECAST_YEARS = list(range(2025, 2031))

MODEL_COLUMNS = [
    "beds",
    "stationary_patients",
    "hospital_physicians",
    "bed_occupancy_rate",
    "avg_length_of_stay",
]

REQUIRED_COLUMNS = [
    "beds",
    "stationary_patients",
    "hospital_physicians",
    "bed_occupancy_rate",
    "avg_length_of_stay",
]


SCENARIOS = {
    "stress": {
        "stationary_patients_growth": 0.020,
        "hospital_physicians_growth": 0.005,
        "beds_growth": -0.005,
        "bed_occupancy_rate_growth": 0.010,
        "avg_length_of_stay_growth": 0.000,
    },
    "recruitment_improvement": {
        "stationary_patients_growth": 0.010,
        "hospital_physicians_growth": 0.025,
        "beds_growth": 0.000,
        "bed_occupancy_rate_growth": 0.000,
        "avg_length_of_stay_growth": -0.005,
    },
    "capacity_decline": {
        "stationary_patients_growth": 0.015,
        "hospital_physicians_growth": 0.005,
        "beds_growth": -0.015,
        "bed_occupancy_rate_growth": 0.015,
        "avg_length_of_stay_growth": 0.000,
    },
}


def load_data() -> pd.DataFrame:
    """Load combined hospital dataset."""
    return pd.read_csv(INPUT_PATH)


def get_complete_historical_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep rows usable for forecasting."""
    complete = df[
        df[REQUIRED_COLUMNS].notna().all(axis=1)
        & (df["beds"] > 0)
        & (df["stationary_patients"] > 0)
        & (df["hospital_physicians"] > 0)
        & (df["bed_occupancy_rate"] > 0)
        & (df["avg_length_of_stay"] > 0)
    ].copy()

    return complete


def linear_forecast_city(city_df: pd.DataFrame) -> pd.DataFrame:
    """Create business-as-usual forecast using linear regression per indicator."""
    city = city_df["city"].iloc[0]
    region_code = city_df["region_code"].iloc[0]

    forecast = pd.DataFrame(
        {
            "city": city,
            "region_code": region_code,
            "year": FORECAST_YEARS,
            "scenario": "business_as_usual",
        }
    )

    x_train = city_df[["year"]]

    for column in MODEL_COLUMNS:
        model = LinearRegression()
        y_train = city_df[column]

        model.fit(x_train, y_train)

        predictions = model.predict(forecast[["year"]])
        predictions = pd.Series(predictions).clip(lower=0)

        forecast[column] = predictions.values

    return forecast


def scenario_forecast_city(city_df: pd.DataFrame, scenario_name: str, config: dict) -> pd.DataFrame:
    """Create scenario forecast from last complete historical value."""
    latest = city_df.sort_values("year").iloc[-1]

    rows = []

    for year in FORECAST_YEARS:
        years_ahead = year - int(latest["year"])

        rows.append(
            {
                "city": latest["city"],
                "region_code": latest["region_code"],
                "year": year,
                "scenario": scenario_name,
                "beds": latest["beds"] * ((1 + config["beds_growth"]) ** years_ahead),
                "stationary_patients": latest["stationary_patients"]
                * ((1 + config["stationary_patients_growth"]) ** years_ahead),
                "hospital_physicians": latest["hospital_physicians"]
                * ((1 + config["hospital_physicians_growth"]) ** years_ahead),
                "bed_occupancy_rate": latest["bed_occupancy_rate"]
                * ((1 + config["bed_occupancy_rate_growth"]) ** years_ahead),
                "avg_length_of_stay": latest["avg_length_of_stay"]
                * ((1 + config["avg_length_of_stay_growth"]) ** years_ahead),
            }
        )

    return pd.DataFrame(rows)


def add_derived_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived pressure indicators."""
    df = df.copy()

    df["patients_per_bed"] = df["stationary_patients"] / df["beds"]
    df["patients_per_physician"] = df["stationary_patients"] / df["hospital_physicians"]
    df["beds_per_hospital"] = pd.NA

    return df


def add_hpi_scores_by_scenario_year(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate relative HPI scores within each scenario and forecast year."""
    df = df.copy()

    score_columns = [
        "patients_per_bed_score",
        "patients_per_physician_score",
        "occupancy_score",
        "length_of_stay_score",
    ]

    for column in score_columns + ["hpi"]:
        df[column] = pd.NA

    for scenario in sorted(df["scenario"].unique()):
        for year in sorted(df["year"].unique()):
            mask = (df["scenario"] == scenario) & (df["year"] == year)
            year_df = df.loc[mask].copy()

            if year_df.empty:
                continue

            score_specs = [
                ("patients_per_bed", "patients_per_bed_score"),
                ("patients_per_physician", "patients_per_physician_score"),
                ("bed_occupancy_rate", "occupancy_score"),
                ("avg_length_of_stay", "length_of_stay_score"),
            ]

            for source_column, score_column in score_specs:
                min_value = year_df[source_column].min()
                max_value = year_df[source_column].max()

                df.loc[mask, score_column] = year_df[source_column].apply(
                    lambda value: min_max_scale(value, min_value, max_value)
                )

            df.loc[mask, "hpi"] = df.loc[mask].apply(
                lambda row: calculate_hospital_only_hpi(
                    patients_per_bed_score=row["patients_per_bed_score"],
                    patients_per_physician_score=row["patients_per_physician_score"],
                    occupancy_score=row["occupancy_score"],
                    length_of_stay_score=row["length_of_stay_score"],
                ),
                axis=1,
            )

    numeric_columns = [
        "beds",
        "stationary_patients",
        "hospital_physicians",
        "bed_occupancy_rate",
        "avg_length_of_stay",
        "patients_per_bed",
        "patients_per_physician",
        "hpi",
        "patients_per_bed_score",
        "patients_per_physician_score",
        "occupancy_score",
        "length_of_stay_score",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").round(2)

    return df


def build_forecasts() -> pd.DataFrame:
    """Build all city forecasts and scenarios."""
    df = load_data()
    complete_df = get_complete_historical_rows(df)

    forecast_frames = []

    for city, city_df in complete_df.groupby("city"):
        city_df = city_df.sort_values("year")

        if len(city_df) < 3:
            print(f"Skipping {city}: not enough complete historical data.")
            continue

        forecast_frames.append(linear_forecast_city(city_df))

        for scenario_name, config in SCENARIOS.items():
            forecast_frames.append(
                scenario_forecast_city(
                    city_df=city_df,
                    scenario_name=scenario_name,
                    config=config,
                )
            )

    forecast_df = pd.concat(forecast_frames, ignore_index=True)
    forecast_df = add_derived_indicators(forecast_df)
    forecast_df = add_hpi_scores_by_scenario_year(forecast_df)

    forecast_df["data_type"] = "forecast"

    ordered_columns = [
        "city",
        "region_code",
        "year",
        "scenario",
        "data_type",
        "beds",
        "stationary_patients",
        "hospital_physicians",
        "bed_occupancy_rate",
        "avg_length_of_stay",
        "patients_per_bed",
        "patients_per_physician",
        "patients_per_bed_score",
        "patients_per_physician_score",
        "occupancy_score",
        "length_of_stay_score",
        "hpi",
    ]

    forecast_df = forecast_df[ordered_columns].sort_values(
        ["scenario", "year", "hpi"],
        ascending=[True, True, False],
    )

    return forecast_df.reset_index(drop=True)


def main() -> None:
    forecast_df = build_forecasts()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    forecast_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved forecast dataset to: {OUTPUT_PATH}")
    print(f"Shape: {forecast_df.shape}")
    print("Years:", forecast_df["year"].min(), "-", forecast_df["year"].max())
    print("Scenarios:", sorted(forecast_df["scenario"].unique()))
    print("Cities:", sorted(forecast_df["city"].unique()))

    print("\nPreview:")
    print(
        forecast_df[
            [
                "scenario",
                "year",
                "city",
                "beds",
                "stationary_patients",
                "hospital_physicians",
                "patients_per_bed",
                "patients_per_physician",
                "hpi",
            ]
        ].head(20)
    )


if __name__ == "__main__":
    main()