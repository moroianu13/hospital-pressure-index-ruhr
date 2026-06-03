"""
Forecast Ruhr hospital pressure indicators for 2025–2030.

Input:
    data/processed/ruhr_hospital_combined_2015_2024.csv

Output:
    data/processed/ruhr_hospital_forecast_2025_2030.csv

Methodology:
- Each city gets its own local historical growth rates.
- Scenario forecasts modify the local city trend instead of applying the same
  fixed growth rate to all cities.
- Forecast HPI scores are scaled against a fixed 2024 historical reference.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.features.pressure_index import calculate_hospital_only_hpi


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_combined_2015_2024.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_forecast_2025_2030.csv"

FORECAST_YEARS = list(range(2025, 2031))

REQUIRED_COLUMNS = [
    "beds",
    "stationary_patients",
    "hospital_physicians",
    "bed_occupancy_rate",
    "avg_length_of_stay",
]

GROWTH_RATE_LIMITS = {
    "beds": (-0.05, 0.05),
    "stationary_patients": (-0.08, 0.08),
    "hospital_physicians": (-0.08, 0.08),
    "bed_occupancy_rate": (-0.05, 0.05),
    "avg_length_of_stay": (-0.05, 0.05),
}

SCENARIO_MODIFIERS = {
    "business_as_usual": {
        "beds": 0.000,
        "stationary_patients": 0.000,
        "hospital_physicians": 0.000,
        "bed_occupancy_rate": 0.000,
        "avg_length_of_stay": 0.000,
    },
    "stress": {
        "beds": -0.005,
        "stationary_patients": 0.010,
        "hospital_physicians": -0.005,
        "bed_occupancy_rate": 0.005,
        "avg_length_of_stay": 0.000,
    },
    "recruitment_improvement": {
        "beds": 0.000,
        "stationary_patients": 0.000,
        "hospital_physicians": 0.020,
        "bed_occupancy_rate": -0.003,
        "avg_length_of_stay": -0.005,
    },
    "capacity_decline": {
        "beds": -0.015,
        "stationary_patients": 0.000,
        "hospital_physicians": 0.000,
        "bed_occupancy_rate": 0.007,
        "avg_length_of_stay": 0.000,
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


def add_derived_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived pressure indicators."""
    df = df.copy()

    df["patients_per_bed"] = df["stationary_patients"] / df["beds"]
    df["patients_per_physician"] = df["stationary_patients"] / df["hospital_physicians"]
    df["beds_per_hospital"] = pd.NA

    return df


def calculate_cagr(first_value: float, last_value: float, years: int) -> float:
    """Calculate compound annual growth rate."""
    if pd.isna(first_value) or pd.isna(last_value):
        return 0.0

    if first_value <= 0 or last_value <= 0 or years <= 0:
        return 0.0

    return (last_value / first_value) ** (1 / years) - 1


def clip_growth_rate(column: str, rate: float) -> float:
    """Limit extreme rates so short historical windows do not explode."""
    lower, upper = GROWTH_RATE_LIMITS[column]
    return max(lower, min(upper, rate))


def calculate_city_growth_rates(city_df: pd.DataFrame) -> dict:
    """
    Calculate local historical growth rates per city.

    Uses first and last complete year for that city.
    """
    city_df = city_df.sort_values("year").copy()

    first = city_df.iloc[0]
    last = city_df.iloc[-1]
    years = int(last["year"] - first["year"])

    growth_rates = {}

    for column in REQUIRED_COLUMNS:
        rate = calculate_cagr(
            first_value=first[column],
            last_value=last[column],
            years=years,
        )
        growth_rates[column] = clip_growth_rate(column, rate)

    return growth_rates


def get_forecast_confidence(city_df: pd.DataFrame) -> str:
    """Assign simple confidence level based on number of complete historical years."""
    n_years = city_df["year"].nunique()

    if n_years >= 8:
        return "high"
    if n_years >= 5:
        return "medium"

    return "low"


def apply_scenario_growth(
    base_growth_rates: dict,
    scenario_modifiers: dict,
) -> dict:
    """Combine local city growth rates with scenario modifiers."""
    scenario_growth = {}

    for column in REQUIRED_COLUMNS:
        combined_rate = base_growth_rates[column] + scenario_modifiers[column]
        scenario_growth[column] = clip_growth_rate(column, combined_rate)

    return scenario_growth


def scenario_forecast_city(
    city_df: pd.DataFrame,
    scenario_name: str,
    scenario_modifiers: dict,
) -> pd.DataFrame:
    """Create forecast from local city trend plus scenario modifiers."""
    city_df = city_df.sort_values("year").copy()

    latest = city_df.iloc[-1]
    base_growth_rates = calculate_city_growth_rates(city_df)
    scenario_growth_rates = apply_scenario_growth(
        base_growth_rates=base_growth_rates,
        scenario_modifiers=scenario_modifiers,
    )

    confidence = get_forecast_confidence(city_df)

    rows = []

    for year in FORECAST_YEARS:
        years_ahead = year - int(latest["year"])

        row = {
            "city": latest["city"],
            "region_code": latest["region_code"],
            "year": year,
            "scenario": scenario_name,
            "forecast_confidence": confidence,
        }

        for column in REQUIRED_COLUMNS:
            row[column] = latest[column] * ((1 + scenario_growth_rates[column]) ** years_ahead)
            row[f"{column}_growth_rate"] = scenario_growth_rates[column]

        rows.append(row)

    return pd.DataFrame(rows)


def fixed_reference_scale(
    value: float,
    min_value: float,
    max_value: float,
    cap_score: bool = False,
) -> float:
    """
    Scale value against fixed reference min/max.

    For forecast, scores are not capped by default, so values can exceed 100.
    This makes pressure above the 2024 reference visible.
    """
    if pd.isna(value) or pd.isna(min_value) or pd.isna(max_value):
        return pd.NA

    if max_value == min_value:
        return 50.0

    score = (value - min_value) / (max_value - min_value) * 100

    if cap_score:
        return max(0.0, min(100.0, score))

    return max(0.0, score)


def build_2024_reference_stats(complete_df: pd.DataFrame) -> dict:
    """Build fixed scaling reference from latest official complete year."""
    latest_year = int(complete_df["year"].max())

    reference_df = complete_df[complete_df["year"] == latest_year].copy()
    reference_df = add_derived_indicators(reference_df)

    reference_columns = [
        "patients_per_bed",
        "patients_per_physician",
        "bed_occupancy_rate",
        "avg_length_of_stay",
    ]

    reference_stats = {}

    for column in reference_columns:
        reference_stats[column] = {
            "min": reference_df[column].min(),
            "max": reference_df[column].max(),
        }

    print(f"Using {latest_year} as fixed HPI reference year.")

    return reference_stats


def add_hpi_scores_against_fixed_reference(
    forecast_df: pd.DataFrame,
    reference_stats: dict,
) -> pd.DataFrame:
    """Calculate forecast HPI using fixed historical reference scaling."""
    df = forecast_df.copy()

    score_specs = [
        ("patients_per_bed", "patients_per_bed_score"),
        ("patients_per_physician", "patients_per_physician_score"),
        ("bed_occupancy_rate", "occupancy_score"),
        ("avg_length_of_stay", "length_of_stay_score"),
    ]

    for source_column, score_column in score_specs:
        min_value = reference_stats[source_column]["min"]
        max_value = reference_stats[source_column]["max"]

        df[score_column] = df[source_column].apply(
            lambda value: fixed_reference_scale(
                value=value,
                min_value=min_value,
                max_value=max_value,
                cap_score=False,
            )
        )

    df["hpi"] = df.apply(
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
        "beds_growth_rate",
        "stationary_patients_growth_rate",
        "hospital_physicians_growth_rate",
        "bed_occupancy_rate_growth_rate",
        "avg_length_of_stay_growth_rate",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").round(4)

    return df


def build_forecasts() -> pd.DataFrame:
    """Build all city forecasts and scenarios."""
    df = load_data()
    complete_df = get_complete_historical_rows(df)

    reference_stats = build_2024_reference_stats(complete_df)

    forecast_frames = []

    for city, city_df in complete_df.groupby("city"):
        city_df = city_df.sort_values("year")

        if len(city_df) < 3:
            print(f"Skipping {city}: not enough complete historical data.")
            continue

        for scenario_name, scenario_modifiers in SCENARIO_MODIFIERS.items():
            forecast_frames.append(
                scenario_forecast_city(
                    city_df=city_df,
                    scenario_name=scenario_name,
                    scenario_modifiers=scenario_modifiers,
                )
            )

    forecast_df = pd.concat(forecast_frames, ignore_index=True)
    forecast_df = add_derived_indicators(forecast_df)
    forecast_df = add_hpi_scores_against_fixed_reference(
        forecast_df=forecast_df,
        reference_stats=reference_stats,
    )

    forecast_df["data_type"] = "forecast"

    ordered_columns = [
        "city",
        "region_code",
        "year",
        "scenario",
        "data_type",
        "forecast_confidence",
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
        "beds_growth_rate",
        "stationary_patients_growth_rate",
        "hospital_physicians_growth_rate",
        "bed_occupancy_rate_growth_rate",
        "avg_length_of_stay_growth_rate",
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

    print("\nScenario comparison preview:")
    print(
        forecast_df[
            [
                "scenario",
                "year",
                "city",
                "forecast_confidence",
                "stationary_patients_growth_rate",
                "hospital_physicians_growth_rate",
                "beds_growth_rate",
                "patients_per_bed",
                "patients_per_physician",
                "hpi",
            ]
        ].head(40)
    )


if __name__ == "__main__":
    main()
