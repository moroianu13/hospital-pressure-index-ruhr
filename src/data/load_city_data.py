
from pathlib import Path

import pandas as pd

from src.features.pressure_index import (
    calculate_hpi,
    calculate_hospital_only_hpi,
    min_max_scale,
)


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


OFFICIAL_HOSPITAL_DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_regionalvergleich_clean.csv"
)


def load_official_ruhr_hospital_data() -> pd.DataFrame:
    """Load cleaned official Ruhr hospital dataset."""
    return pd.read_csv(OFFICIAL_HOSPITAL_DATA_PATH)


def load_latest_official_ruhr_hospital_data() -> pd.DataFrame:
    """Load the latest available year from the official Ruhr hospital dataset."""
    df = load_official_ruhr_hospital_data()
    latest_year = df["year"].max()

    return df[df["year"] == latest_year].copy()

def add_official_hospital_pressure_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add pressure component scores for official hospital-only data."""
    df = df.copy()

    df["patients_per_bed_score"] = df["patients_per_bed"].apply(
        lambda x: min_max_scale(
            x,
            df["patients_per_bed"].min(),
            df["patients_per_bed"].max(),
        )
    )

    df["patients_per_physician_score"] = df["patients_per_physician"].apply(
        lambda x: min_max_scale(
            x,
            df["patients_per_physician"].min(),
            df["patients_per_physician"].max(),
        )
    )

    df["occupancy_score"] = df["bed_occupancy_rate"].apply(
        lambda x: min_max_scale(
            x,
            df["bed_occupancy_rate"].min(),
            df["bed_occupancy_rate"].max(),
        )
    )

    df["length_of_stay_score"] = df["avg_length_of_stay"].apply(
        lambda x: min_max_scale(
            x,
            df["avg_length_of_stay"].min(),
            df["avg_length_of_stay"].max(),
        )
    )

    return df


def add_official_hospital_hpi(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate hospital-only HPI for official data."""
    df = df.copy()

    required_score_columns = [
        "patients_per_bed_score",
        "patients_per_physician_score",
        "occupancy_score",
        "length_of_stay_score",
    ]

    df["hpi"] = pd.NA

    complete_rows = df[required_score_columns].notna().all(axis=1)

    df.loc[complete_rows, "hpi"] = df.loc[complete_rows].apply(
        lambda row: calculate_hospital_only_hpi(
            patients_per_bed_score=row["patients_per_bed_score"],
            patients_per_physician_score=row["patients_per_physician_score"],
            occupancy_score=row["occupancy_score"],
            length_of_stay_score=row["length_of_stay_score"],
        ),
        axis=1,
    )

    df["hpi"] = pd.to_numeric(df["hpi"], errors="coerce").round(2)

    return df


def load_latest_official_ruhr_hospital_pressure_data() -> pd.DataFrame:
    """Load latest official hospital data and calculate hospital-only HPI."""
    df = load_latest_official_ruhr_hospital_data()
    df = add_official_hospital_pressure_scores(df)
    df = add_official_hospital_hpi(df)

    return df

def load_official_ruhr_hospital_pressure_data() -> pd.DataFrame:
    """Load official hospital data and calculate hospital-only HPI for all years."""
    df = load_official_ruhr_hospital_data()
    df = add_official_hospital_pressure_scores(df)
    df = add_official_hospital_hpi(df)

    return df

COMBINED_HOSPITAL_DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_combined_2015_2024.csv"
)


def load_combined_ruhr_hospital_data() -> pd.DataFrame:
    """Load combined Ruhr hospital capacity and physician dataset."""
    return pd.read_csv(COMBINED_HOSPITAL_DATA_PATH)


from src.features.pressure_index import calculate_hospital_only_hpi, min_max_scale


def add_hpi_scores_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate HPI scores year-by-year.

    Scores are normalized within each selected year, so the HPI shows
    relative pressure compared with other Ruhr cities in the same year.
    """
    df = df.copy()

    required_columns = [
        "stationary_patients",
        "beds",
        "hospital_physicians",
        "bed_occupancy_rate",
        "avg_length_of_stay",
        "patients_per_bed",
        "patients_per_physician",
    ]

    df["is_hpi_complete"] = (
        df[required_columns].notna().all(axis=1)
        & (df["stationary_patients"] > 0)
        & (df["beds"] > 0)
        & (df["hospital_physicians"] > 0)
        & (df["bed_occupancy_rate"] > 0)
        & (df["avg_length_of_stay"] > 0)
    )

    df["hpi"] = pd.NA
    df["patients_per_bed_score"] = pd.NA
    df["patients_per_physician_score"] = pd.NA
    df["occupancy_score"] = pd.NA
    df["length_of_stay_score"] = pd.NA

    for year in sorted(df["year"].dropna().unique()):
        year_mask = (df["year"] == year) & df["is_hpi_complete"]
        year_df = df.loc[year_mask].copy()

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

            df.loc[year_mask, score_column] = year_df[source_column].apply(
                lambda x: min_max_scale(x, min_value, max_value)
            )

        df.loc[year_mask, "hpi"] = df.loc[year_mask].apply(
            lambda row: calculate_hospital_only_hpi(
                patients_per_bed_score=row["patients_per_bed_score"],
                patients_per_physician_score=row["patients_per_physician_score"],
                occupancy_score=row["occupancy_score"],
                length_of_stay_score=row["length_of_stay_score"],
            ),
            axis=1,
        )

    numeric_columns = [
        "hpi",
        "patients_per_bed_score",
        "patients_per_physician_score",
        "occupancy_score",
        "length_of_stay_score",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").round(2)

    return df


def load_combined_ruhr_hospital_pressure_data() -> pd.DataFrame:
    """Load combined Ruhr hospital dataset and calculate HPI for all years."""
    df = load_combined_ruhr_hospital_data()
    df = add_hpi_scores_by_year(df)

    return df


FORECAST_HOSPITAL_DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_forecast_2025_2030.csv"
)


def load_ruhr_hospital_forecast_data() -> pd.DataFrame:
    """Load Ruhr hospital forecast dataset."""
    return pd.read_csv(FORECAST_HOSPITAL_DATA_PATH)