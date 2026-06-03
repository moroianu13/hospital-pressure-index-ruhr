"""
Forecast Ruhr hospital pressure indicators for 2025–2030.

Inputs:
    data/processed/ruhr_hospital_combined_2015_2024.csv
    data/processed/ruhr_hospital_type_correction.csv
    data/processed/ruhr_demographics_2015_2024_clean.csv
    data/processed/ruhr_unemployment_2015_2024_clean.csv
    data/processed/ruhr_hospital_pressure_demographic_socioeconomic_2015_2024.csv

Output:
    data/processed/ruhr_hospital_forecast_2025_2030.csv

Methodology:
- Each city uses its own historical trend.
- Scenarios modify the local city trend.
- Forecast HPI scores are scaled against fixed 2024 historical reference values.
- Demographic and socio-economic forecast indicators are projected from historical
  city trends and are scenario assumptions, not official future statistics.
- The output includes:
    hospital_hpi
    acute_care_adjusted_hpi
    demographic_socioeconomic_hpi
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.features.pressure_index import calculate_hospital_only_hpi


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_combined_2015_2024.csv"
CORRECTION_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_type_correction.csv"
DEMOGRAPHICS_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_demographics_2015_2024_clean.csv"
)
UNEMPLOYMENT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_unemployment_2015_2024_clean.csv"
)
DEMOGRAPHIC_SOCIOECONOMIC_REFERENCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ruhr_hospital_pressure_demographic_socioeconomic_2015_2024.csv"
)
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

DEMOGRAPHIC_GROWTH_RATE_LIMITS = {
    "population_total": (-0.015, 0.015),
}

DEMOGRAPHIC_POINT_CHANGE_LIMITS = {
    "population_65_plus_pct": (-0.50, 0.80),
    "population_80_plus_pct": (-0.40, 0.60),
    "unemployment_rate_proxy": (-0.70, 0.70),
    "long_term_unemployment_rate": (-0.50, 0.50),
}

DEMOGRAPHIC_VALUE_LIMITS = {
    "unemployment_rate_proxy": (0.0, 30.0),
    "long_term_unemployment_rate": (0.0, 20.0),
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


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hospital_df = pd.read_csv(INPUT_PATH)
    correction_df = pd.read_csv(CORRECTION_PATH)
    demographics_df = pd.read_csv(DEMOGRAPHICS_PATH)
    unemployment_df = pd.read_csv(UNEMPLOYMENT_PATH)
    demographic_reference_df = pd.read_csv(DEMOGRAPHIC_SOCIOECONOMIC_REFERENCE_PATH)
    return (
        hospital_df,
        correction_df,
        demographics_df,
        unemployment_df,
        demographic_reference_df,
    )


def get_complete_historical_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        df[REQUIRED_COLUMNS].notna().all(axis=1)
        & (df["beds"] > 0)
        & (df["stationary_patients"] > 0)
        & (df["hospital_physicians"] > 0)
        & (df["bed_occupancy_rate"] > 0)
        & (df["avg_length_of_stay"] > 0)
    ].copy()


def add_hospital_type_correction(
    df: pd.DataFrame,
    correction_df: pd.DataFrame,
) -> pd.DataFrame:
        if "acute_relevance_factor" in df.columns:
            return df.copy()
        
        df = df.merge(
        correction_df[
            [
                "city",
                "acute_relevance_factor",
                "total_hospital_sites",
                "general_or_acute_sites",
                "psychiatric_psychosomatic_sites",
                "specialized_partial_sites",
            ]
        ],
        on="city",
        how="left",
        validate="many_to_one",
    )

        df["acute_relevance_factor"] = df["acute_relevance_factor"].fillna(1.0)

        return df


def add_derived_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["patients_per_bed"] = df["stationary_patients"] / df["beds"]
    df["patients_per_physician"] = df["stationary_patients"] / df["hospital_physicians"]

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

    return df


def calculate_cagr(first_value: float, last_value: float, years: int) -> float:
    if pd.isna(first_value) or pd.isna(last_value):
        return 0.0

    if first_value <= 0 or last_value <= 0 or years <= 0:
        return 0.0

    return (last_value / first_value) ** (1 / years) - 1


def clip_growth_rate(column: str, rate: float) -> float:
    lower, upper = GROWTH_RATE_LIMITS[column]
    return max(lower, min(upper, rate))


def clip_value(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def clip_demographic_growth_rate(column: str, rate: float) -> float:
    lower, upper = DEMOGRAPHIC_GROWTH_RATE_LIMITS[column]
    return clip_value(rate, lower, upper)


def calculate_annual_point_change(
    first_value: float,
    last_value: float,
    years: int,
    lower: float,
    upper: float,
) -> float:
    if pd.isna(first_value) or pd.isna(last_value) or years <= 0:
        return 0.0

    annual_change = (last_value - first_value) / years
    return clip_value(annual_change, lower, upper)


def calculate_city_growth_rates(city_df: pd.DataFrame) -> dict:
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


def build_demographic_history(
    demographics_df: pd.DataFrame,
    unemployment_df: pd.DataFrame,
) -> pd.DataFrame:
    return demographics_df.merge(
        unemployment_df,
        on=["city", "year"],
        how="inner",
        validate="one_to_one",
        suffixes=("", "_unemployment"),
    )


def calculate_city_demographic_projection_rates(city_df: pd.DataFrame) -> dict:
    city_df = city_df.sort_values("year").copy()

    required_columns = [
        "population_total",
        "population_65_plus_pct",
        "population_80_plus_pct",
        "unemployment_rate_proxy",
        "long_term_unemployment_rate",
    ]
    complete_df = city_df.dropna(subset=required_columns).copy()

    if complete_df.empty:
        return {}

    first = complete_df.iloc[0]
    last = complete_df.iloc[-1]
    years = int(last["year"] - first["year"])

    population_growth = calculate_cagr(
        first_value=first["population_total"],
        last_value=last["population_total"],
        years=years,
    )

    rates = {
        "population_total": clip_demographic_growth_rate(
            "population_total",
            population_growth,
        )
    }

    for column, (lower, upper) in DEMOGRAPHIC_POINT_CHANGE_LIMITS.items():
        rates[column] = calculate_annual_point_change(
            first_value=first[column],
            last_value=last[column],
            years=years,
            lower=lower,
            upper=upper,
        )

    return rates


def project_city_demographic_indicators(city_df: pd.DataFrame) -> pd.DataFrame:
    city_df = city_df.sort_values("year").copy()

    required_columns = [
        "population_total",
        "population_65_plus_pct",
        "population_80_plus_pct",
        "unemployment_rate_proxy",
        "long_term_unemployment_rate",
    ]
    complete_df = city_df.dropna(subset=required_columns).copy()

    if complete_df.empty:
        return pd.DataFrame()

    latest = complete_df.iloc[-1]
    rates = calculate_city_demographic_projection_rates(complete_df)

    rows = []

    for year in FORECAST_YEARS:
        years_ahead = year - int(latest["year"])

        population_total = latest["population_total"] * (
            (1 + rates["population_total"]) ** years_ahead
        )
        population_65_plus_pct = (
            latest["population_65_plus_pct"]
            + rates["population_65_plus_pct"] * years_ahead
        )
        population_80_plus_pct = (
            latest["population_80_plus_pct"]
            + rates["population_80_plus_pct"] * years_ahead
        )
        unemployment_rate_proxy = (
            latest["unemployment_rate_proxy"]
            + rates["unemployment_rate_proxy"] * years_ahead
        )
        long_term_unemployment_rate = (
            latest["long_term_unemployment_rate"]
            + rates["long_term_unemployment_rate"] * years_ahead
        )

        unemployment_rate_proxy = clip_value(
            unemployment_rate_proxy,
            *DEMOGRAPHIC_VALUE_LIMITS["unemployment_rate_proxy"],
        )
        long_term_unemployment_rate = clip_value(
            long_term_unemployment_rate,
            *DEMOGRAPHIC_VALUE_LIMITS["long_term_unemployment_rate"],
        )

        rows.append(
            {
                "city": latest["city"],
                "year": year,
                "population_total": population_total,
                "population_65_plus": population_total
                * population_65_plus_pct
                / 100,
                "population_80_plus": population_total
                * population_80_plus_pct
                / 100,
                "population_65_plus_pct": population_65_plus_pct,
                "population_80_plus_pct": population_80_plus_pct,
                "unemployment_rate_proxy": unemployment_rate_proxy,
                "long_term_unemployment_rate": long_term_unemployment_rate,
            }
        )

    return pd.DataFrame(rows)


def build_demographic_projections(
    demographics_df: pd.DataFrame,
    unemployment_df: pd.DataFrame,
) -> pd.DataFrame:
    demographic_history = build_demographic_history(demographics_df, unemployment_df)
    projection_frames = []

    for city, city_df in demographic_history.groupby("city"):
        projected_city = project_city_demographic_indicators(city_df)

        if projected_city.empty:
            print(f"Skipping demographic projection for {city}: incomplete data.")
            continue

        projection_frames.append(projected_city)

    if not projection_frames:
        return pd.DataFrame()

    return pd.concat(projection_frames, ignore_index=True)


def get_forecast_confidence(city_df: pd.DataFrame) -> str:
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
            "acute_relevance_factor": latest["acute_relevance_factor"],
            "total_hospital_sites": latest["total_hospital_sites"],
            "general_or_acute_sites": latest["general_or_acute_sites"],
            "psychiatric_psychosomatic_sites": latest["psychiatric_psychosomatic_sites"],
            "specialized_partial_sites": latest["specialized_partial_sites"],
        }

        for column in REQUIRED_COLUMNS:
            row[column] = latest[column] * (
                (1 + scenario_growth_rates[column]) ** years_ahead
            )
            row[f"{column}_growth_rate"] = scenario_growth_rates[column]

        rows.append(row)

    return pd.DataFrame(rows)


def fixed_reference_scale(
    value: float,
    min_value: float,
    max_value: float,
    cap_score: bool = False,
) -> float:
    if pd.isna(value) or pd.isna(min_value) or pd.isna(max_value):
        return pd.NA

    if max_value == min_value:
        return 50.0

    score = (value - min_value) / (max_value - min_value) * 100

    if cap_score:
        return max(0.0, min(100.0, score))

    return max(0.0, score)


def build_reference_stats(
    complete_df: pd.DataFrame,
    correction_df: pd.DataFrame,
) -> dict:
    latest_year = int(complete_df["year"].max())

    reference_df = complete_df[complete_df["year"] == latest_year].copy()
    reference_df = add_hospital_type_correction(reference_df, correction_df)
    reference_df = add_derived_indicators(reference_df)

    reference_specs = {
        "hospital": [
            "patients_per_bed",
            "patients_per_physician",
            "bed_occupancy_rate",
            "avg_length_of_stay",
        ],
        "acute_adjusted": [
            "adjusted_patients_per_bed",
            "adjusted_patients_per_physician",
            "bed_occupancy_rate",
            "avg_length_of_stay",
        ],
    }

    reference_stats = {}

    for layer_name, columns in reference_specs.items():
        reference_stats[layer_name] = {}

        for column in columns:
            reference_stats[layer_name][column] = {
                "min": reference_df[column].min(),
                "max": reference_df[column].max(),
            }

    print(f"Using {latest_year} as fixed HPI reference year.")

    return reference_stats


def build_demographic_socioeconomic_reference_stats(
    demographic_reference_df: pd.DataFrame,
) -> dict:
    reference_columns = [
        "patients_per_1000_population",
        "population_65_plus_pct",
        "population_80_plus_pct",
        "unemployment_rate_proxy",
        "long_term_unemployment_rate",
    ]

    if "year" not in demographic_reference_df.columns:
        raise ValueError("Demographic reference data must include a year column.")

    reference_df = demographic_reference_df[
        demographic_reference_df["year"] == 2024
    ].copy()

    if reference_df.empty:
        latest_year = int(demographic_reference_df["year"].max())
        reference_df = demographic_reference_df[
            demographic_reference_df["year"] == latest_year
        ].copy()
        print(
            "2024 demographic reference rows were not found. "
            f"Using {latest_year} instead."
        )
    else:
        print("Using 2024 as fixed demographic/socioeconomic reference year.")

    reference_stats = {}

    for column in reference_columns:
        if column not in reference_df.columns:
            raise ValueError(f"Missing demographic reference column: {column}")

        reference_stats[column] = {
            "min": reference_df[column].min(),
            "max": reference_df[column].max(),
        }

    return reference_stats


def add_layer_hpi_scores(
    df: pd.DataFrame,
    reference_stats: dict,
    layer_name: str,
    score_specs: list[tuple[str, str]],
    output_hpi_column: str,
) -> pd.DataFrame:
    df = df.copy()

    for source_column, score_column in score_specs:
        min_value = reference_stats[layer_name][source_column]["min"]
        max_value = reference_stats[layer_name][source_column]["max"]

        df[score_column] = df[source_column].apply(
            lambda value: fixed_reference_scale(
                value=value,
                min_value=min_value,
                max_value=max_value,
                cap_score=False,
            )
        )

    score_columns = [score_column for _, score_column in score_specs]

    df[output_hpi_column] = df.apply(
        lambda row: calculate_hospital_only_hpi(
            patients_per_bed_score=row[score_columns[0]],
            patients_per_physician_score=row[score_columns[1]],
            occupancy_score=row[score_columns[2]],
            length_of_stay_score=row[score_columns[3]],
        ),
        axis=1,
    )

    return df


def add_demographic_socioeconomic_scores(
    forecast_df: pd.DataFrame,
    reference_stats: dict,
) -> pd.DataFrame:
    df = forecast_df.copy()

    df["patients_per_1000_population"] = (
        df["stationary_patients"] / df["population_total"] * 1000
    )

    score_specs = [
        ("patients_per_1000_population", "patients_per_1000_population_score"),
        ("population_65_plus_pct", "population_65_plus_score"),
        ("population_80_plus_pct", "population_80_plus_score"),
        ("unemployment_rate_proxy", "unemployment_pressure_score"),
        ("long_term_unemployment_rate", "long_term_unemployment_pressure_score"),
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

    df["demographic_socioeconomic_pressure_score"] = (
        df["patients_per_1000_population_score"] * 0.30
        + df["population_65_plus_score"] * 0.20
        + df["population_80_plus_score"] * 0.20
        + df["unemployment_pressure_score"] * 0.20
        + df["long_term_unemployment_pressure_score"] * 0.10
    )

    df["demographic_socioeconomic_pressure_score"] = (
        df["patients_per_1000_population_score"] * 0.30
        + df["population_65_plus_score"] * 0.20
        + df["population_80_plus_score"] * 0.20
        + df["unemployment_pressure_score"] * 0.20
        + df["long_term_unemployment_pressure_score"] * 0.10
)

# Demographic and socio-economic pressure is a risk amplifier.
# It should not replace or dilute acute-care pressure.
    # Demographic and socio-economic pressure acts as a risk amplifier,
# not as a replacement/dilution of acute-care pressure.
    df["demographic_socioeconomic_hpi"] = (
        df["acute_care_adjusted_hpi"]
        + df["demographic_socioeconomic_pressure_score"] * 0.20
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


def add_hpi_scores(
    forecast_df: pd.DataFrame,
    reference_stats: dict,
) -> pd.DataFrame:
    df = forecast_df.copy()

    hospital_score_specs = [
        ("patients_per_bed", "patients_per_bed_score"),
        ("patients_per_physician", "patients_per_physician_score"),
        ("bed_occupancy_rate", "occupancy_score"),
        ("avg_length_of_stay", "length_of_stay_score"),
    ]

    adjusted_score_specs = [
        ("adjusted_patients_per_bed", "adjusted_patients_per_bed_score"),
        ("adjusted_patients_per_physician", "adjusted_patients_per_physician_score"),
        ("bed_occupancy_rate", "adjusted_occupancy_score"),
        ("avg_length_of_stay", "adjusted_length_of_stay_score"),
    ]

    df = add_layer_hpi_scores(
        df=df,
        reference_stats=reference_stats,
        layer_name="hospital",
        score_specs=hospital_score_specs,
        output_hpi_column="hospital_hpi",
    )

    df = add_layer_hpi_scores(
        df=df,
        reference_stats=reference_stats,
        layer_name="acute_adjusted",
        score_specs=adjusted_score_specs,
        output_hpi_column="acute_care_adjusted_hpi",
    )

    # Preserve fully recalculated acute-care forecast HPI for audit/debugging.
    df["acute_care_recalculated_hpi"] = df["acute_care_adjusted_hpi"]

    # Acute-care forecast is a progressive correction over all-hospital forecast.
    df["acute_care_adjusted_hpi"] = df.apply(
        progressive_acute_hpi,
        axis=1,
    )

    if "demographic_socioeconomic_pressure_score" in df.columns:
        # Demographic and socio-economic pressure acts as a risk amplifier,
        # not as a replacement/dilution of acute-care pressure.
        df["demographic_socioeconomic_hpi"] = (
            df["acute_care_adjusted_hpi"]
            + df["demographic_socioeconomic_pressure_score"] * 0.20
        )

       

    # Backward compatibility for older dashboard code.
    df["hpi"] = df["hospital_hpi"]

    numeric_columns = [
        "beds",
        "stationary_patients",
        "hospital_physicians",
        "bed_occupancy_rate",
        "avg_length_of_stay",
        "patients_per_bed",
        "patients_per_physician",
        "adjusted_beds",
        "adjusted_hospital_physicians",
        "adjusted_patients_per_bed",
        "adjusted_patients_per_physician",
        "hospital_hpi",
        "acute_care_recalculated_hpi",
        "acute_care_adjusted_hpi",
        "hpi",
        "patients_per_bed_score",
        "patients_per_physician_score",
        "occupancy_score",
        "length_of_stay_score",
        "adjusted_patients_per_bed_score",
        "adjusted_patients_per_physician_score",
        "adjusted_occupancy_score",
        "adjusted_length_of_stay_score",
        "beds_growth_rate",
        "stationary_patients_growth_rate",
        "hospital_physicians_growth_rate",
        "bed_occupancy_rate_growth_rate",
        "avg_length_of_stay_growth_rate",
        "population_total",
        "population_65_plus",
        "population_80_plus",
        "population_65_plus_pct",
        "population_80_plus_pct",
        "unemployment_rate_proxy",
        "long_term_unemployment_rate",
        "patients_per_1000_population",
        "patients_per_1000_population_score",
        "population_65_plus_score",
        "population_80_plus_score",
        "unemployment_pressure_score",
        "long_term_unemployment_pressure_score",
        "demographic_socioeconomic_pressure_score",
        "demographic_socioeconomic_hpi",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").round(4)

    return df


def round_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    numeric_columns = [
        "population_total",
        "population_65_plus",
        "population_80_plus",
        "population_65_plus_pct",
        "population_80_plus_pct",
        "unemployment_rate_proxy",
        "long_term_unemployment_rate",
        "patients_per_1000_population",
        "patients_per_1000_population_score",
        "population_65_plus_score",
        "population_80_plus_score",
        "unemployment_pressure_score",
        "long_term_unemployment_pressure_score",
        "demographic_socioeconomic_pressure_score",
        "demographic_socioeconomic_hpi",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").round(4)

    return df


def build_forecasts() -> pd.DataFrame:
    (
        hospital_df,
        correction_df,
        demographics_df,
        unemployment_df,
        demographic_reference_df,
    ) = load_data()

    complete_df = get_complete_historical_rows(hospital_df)
    complete_df = add_hospital_type_correction(complete_df, correction_df)

    reference_stats = build_reference_stats(
        complete_df=complete_df,
        correction_df=correction_df,
    )
    demographic_reference_stats = build_demographic_socioeconomic_reference_stats(
        demographic_reference_df
    )
    demographic_projections = build_demographic_projections(
        demographics_df=demographics_df,
        unemployment_df=unemployment_df,
    )

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
    forecast_df = add_hpi_scores(
        forecast_df=forecast_df,
        reference_stats=reference_stats,
    )
    forecast_df = forecast_df.merge(
        demographic_projections,
        on=["city", "year"],
        how="left",
        validate="many_to_one",
    )
    forecast_df = add_demographic_socioeconomic_scores(
        forecast_df=forecast_df,
        reference_stats=demographic_reference_stats,
    )
    forecast_df = round_numeric_columns(forecast_df)

    forecast_df["data_type"] = "forecast"
    forecast_df["is_hpi_complete"] = True
    forecast_df["is_acute_adjusted_hpi_complete"] = True

    ordered_columns = [
        "city",
        "region_code",
        "year",
        "scenario",
        "data_type",
        "forecast_confidence",
        "acute_relevance_factor",
        "total_hospital_sites",
        "general_or_acute_sites",
        "psychiatric_psychosomatic_sites",
        "specialized_partial_sites",
        "beds",
        "adjusted_beds",
        "stationary_patients",
        "hospital_physicians",
        "adjusted_hospital_physicians",
        "population_total",
        "population_65_plus",
        "population_80_plus",
        "population_65_plus_pct",
        "population_80_plus_pct",
        "unemployment_rate_proxy",
        "long_term_unemployment_rate",
        "bed_occupancy_rate",
        "avg_length_of_stay",
        "patients_per_bed",
        "adjusted_patients_per_bed",
        "patients_per_physician",
        "adjusted_patients_per_physician",
        "patients_per_bed_score",
        "patients_per_physician_score",
        "occupancy_score",
        "length_of_stay_score",
        "adjusted_patients_per_bed_score",
        "adjusted_patients_per_physician_score",
        "adjusted_occupancy_score",
        "adjusted_length_of_stay_score",
        "patients_per_1000_population",
        "patients_per_1000_population_score",
        "population_65_plus_score",
        "population_80_plus_score",
        "unemployment_pressure_score",
        "long_term_unemployment_pressure_score",
        "demographic_socioeconomic_pressure_score",
        "hospital_hpi",
        "acute_care_adjusted_hpi",
        "demographic_socioeconomic_hpi",
        "hpi",
        "is_hpi_complete",
        "is_acute_adjusted_hpi_complete",
        "beds_growth_rate",
        "stationary_patients_growth_rate",
        "hospital_physicians_growth_rate",
        "bed_occupancy_rate_growth_rate",
        "avg_length_of_stay_growth_rate",
    ]

    forecast_df = forecast_df[ordered_columns].sort_values(
        ["scenario", "year", "hospital_hpi"],
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

    print("\nLatest forecast comparison:")
    latest_year = int(forecast_df["year"].max())
    print(
        forecast_df[forecast_df["year"] == latest_year][
            [
                "scenario",
                "city",
                "acute_relevance_factor",
                "hospital_hpi",
                "acute_care_adjusted_hpi",
                "demographic_socioeconomic_hpi",
                "population_total",
                "population_65_plus_pct",
                "population_80_plus_pct",
                "unemployment_rate_proxy",
                "long_term_unemployment_rate",
                "beds",
                "adjusted_beds",
                "hospital_physicians",
                "adjusted_hospital_physicians",
            ]
        ].head(40)
    )


if __name__ == "__main__":
    main()
