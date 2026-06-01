"""
Clean Ruhr / NRW hospital regional comparison data.

Input:
    data/raw/ruhr_hospital_regionalvergleich_raw.csv

Output:
    data/processed/ruhr_hospital_regionalvergleich_clean.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "ruhr_hospital_regionalvergleich_raw.csv"
PROCESSED_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_regionalvergleich_clean.csv"
)


RUHR_CITIES = [
    "Duisburg",
    "Oberhausen",
    "Mülheim an der Ruhr",
    "Essen",
    "Bochum",
    "Dortmund",
    "Gelsenkirchen",
    "Herne",
    "Hagen",
    "Bottrop",
]


COLUMN_MAPPING = {
    "Kreisfreie Städte und NRW": "city",
    "Jahr": "year",
    "Anzahl der Krankenhäuser": "hospitals",
    "Ärztinnen und Ärzte in Krankenhäusern": "hospital_physicians",
    "Aufgestellte Krankenbetten im Jahredurchschnitt": "beds",
    "Stationär behandelte Kranke": "stationary_patients",
    "Berechnungs-/Belegungstage": "occupancy_days",
    "Verweildauer in Tagen": "avg_length_of_stay",
    "Bettennutzung in Prozent": "bed_occupancy_rate",
}


def read_raw_data(path: Path = RAW_PATH) -> pd.DataFrame:
    """Read raw semicolon-separated German CSV."""
    return pd.read_csv(path, sep=";", encoding="utf-8")


def clean_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert German decimal comma columns and numeric fields."""
    df = df.copy()

    decimal_columns = ["avg_length_of_stay", "bed_occupancy_rate"]

    for column in decimal_columns:
        df[column] = (
            df[column]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .replace("nan", pd.NA)
            .astype(float)
        )

    integer_columns = [
        "year",
        "hospitals",
        "hospital_physicians",
        "beds",
        "stationary_patients",
        "occupancy_days",
    ]

    for column in integer_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    return df


def add_derived_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add hospital pressure-related indicators."""
    df = df.copy()

    df["patients_per_bed"] = df["stationary_patients"] / df["beds"]
    df["patients_per_physician"] = (
        df["stationary_patients"] / df["hospital_physicians"]
    )
    df["beds_per_hospital"] = df["beds"] / df["hospitals"]

    return df


def filter_ruhr_cities(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only selected Ruhrgebiet cities."""
    return df[df["city"].isin(RUHR_CITIES)].copy()


def replace_structural_zeros_with_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Replace structural zeros (0) with missing (pd.NA) for relevant numeric cols.

    Some datasets use 0 to indicate missing / not applicable values (structural
    zeros). Replace these with pd.NA so downstream numeric conversions and
    indicators behave correctly.
    """
    df = df.copy()

    # Columns where a value of 0 is more likely to indicate missing / not
    # applicable rather than a true count. Do not include 'year' here.
    structural_cols = [
        "hospitals",
        "hospital_physicians",
        "beds",
        "stationary_patients",
        "occupancy_days",
    ]

    for col in structural_cols:
        if col in df.columns:
            # preserve nullable integer dtype where possible
            mask = df[col].astype(object).isin([0, "0"])  # catch string zeros
            df.loc[mask, col] = pd.NA

    return df


def clean_dataset() -> pd.DataFrame:
    """Run full cleaning pipeline."""
    df = read_raw_data()

    df = df.rename(columns=COLUMN_MAPPING)

    columns_to_keep = list(COLUMN_MAPPING.values())
    df = df[columns_to_keep]

    df = clean_numeric_columns(df)
    df = replace_structural_zeros_with_missing(df)
    df = filter_ruhr_cities(df)
    df = add_derived_indicators(df)

    df = df.sort_values(["city", "year"]).reset_index(drop=True)

    return df


def main() -> None:
    df = clean_dataset()

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)

    print(f"Saved cleaned dataset to: {PROCESSED_PATH}")
    print(f"Shape: {df.shape}")
    print(df.head())


if __name__ == "__main__":
    main()
