
from pathlib import Path

import pandas as pd

from src.features.pressure_index import calculate_hpi, min_max_scale


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_cities_sample.csv"


def load_ruhr_city_sample_data() -> pd.DataFrame:
    """Load the current Ruhr city-level prototype dataset."""
    return pd.read_csv(SAMPLE_DATA_PATH)


def add_capacity_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add basic hospital capacity and demand indicators."""
    df = df.copy()

    df["patients_per_bed"] = df["stationary_patients"] / df["beds"]
    df["beds_per_1000_population"] = df["beds"] / df["population"] * 1000
    df["patients_per_1000_population"] = (
        df["stationary_patients"] / df["population"] * 1000
    )

    return df


def add_pressure_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized pressure component scores."""
    df = df.copy()

    df["patient_load_score"] = df["patients_per_1000_population"].apply(
        lambda x: min_max_scale(
            x,
            df["patients_per_1000_population"].min(),
            df["patients_per_1000_population"].max(),
        )
    )

    df["bed_capacity_score"] = df["beds_per_1000_population"].apply(
        lambda x: 100
        - min_max_scale(
            x,
            df["beds_per_1000_population"].min(),
            df["beds_per_1000_population"].max(),
        )
    )

    df["patients_per_bed_score"] = df["patients_per_bed"].apply(
        lambda x: min_max_scale(
            x,
            df["patients_per_bed"].min(),
            df["patients_per_bed"].max(),
        )
    )

    df["occupancy_score"] = df["bed_occupancy_rate"].apply(
        lambda x: min_max_scale(
            x,
            df["bed_occupancy_rate"].min(),
            df["bed_occupancy_rate"].max(),
        )
    )

    df["demographic_score"] = df["population_65_plus_pct"].apply(
        lambda x: min_max_scale(
            x,
            df["population_65_plus_pct"].min(),
            df["population_65_plus_pct"].max(),
        )
    )

    df["socioeconomic_score"] = df["unemployment_rate"].apply(
        lambda x: min_max_scale(
            x,
            df["unemployment_rate"].min(),
            df["unemployment_rate"].max(),
        )
    )

    return df


def add_hpi(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Hospital Pressure Index for each city."""
    df = df.copy()

    df["hpi"] = df.apply(
        lambda row: calculate_hpi(
            patient_load_score=row["patient_load_score"],
            bed_capacity_score=row["bed_capacity_score"],
            patients_per_bed_score=row["patients_per_bed_score"],
            occupancy_score=row["occupancy_score"],
            demographic_score=row["demographic_score"],
            socioeconomic_score=row["socioeconomic_score"],
        ),
        axis=1,
    )
    df["hpi"] = df["hpi"].round(2)
    
    return df


def load_prepared_ruhr_city_data() -> pd.DataFrame:
    """Load sample data and add all derived indicators and HPI scores."""
    df = load_ruhr_city_sample_data()
    df = add_capacity_indicators(df)
    df = add_pressure_scores(df)
    df = add_hpi(df)

    return df
