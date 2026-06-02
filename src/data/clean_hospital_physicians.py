"""
Clean Landesdatenbank NRW hospital physicians data.

Input:
    data/raw/hospital_physicians_2015_2024_raw.csv

Output:
    data/processed/ruhr_hospital_physicians_2015_2024_clean.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "hospital_physicians_2015_2024_raw.csv"
PROCESSED_PATH = (
    PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_physicians_2015_2024_clean.csv"
)

RUHR_CITY_NAMES = [
    "Duisburg",
    "Essen",
    "Mülheim an der Ruhr",
    "Oberhausen",
    "Bottrop",
    "Gelsenkirchen",
    "Bochum",
    "Dortmund",
    "Hagen",
    "Herne",
]

COLUMN_NAMES = [
    "date",
    "region_code",
    "city_raw",
    "hospital_physicians_total",
    "hospital_physicians_full_time",
    "hospital_physicians_part_time",
]


def read_physicians_csv(path: Path = RAW_PATH) -> pd.DataFrame:
    """Read Landesdatenbank physicians CSV and keep only real data rows."""
    rows = []

    with path.open("r", encoding="latin1") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            if line.startswith("31.12."):
                rows.append(line.split(";"))

    return pd.DataFrame(rows, columns=COLUMN_NAMES)


def clean_city_name(value: str) -> str:
    """Remove regional suffixes from city names."""
    city = value.strip()
    city = city.replace(", krfr. Stadt", "")
    return city.strip()


def convert_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Convert official missing marker '.' to pandas missing values."""
    return df.replace(".", pd.NA)


def clean_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert numeric columns."""
    df = df.copy()

    df["year"] = df["date"].str[-4:].astype(int)
    df["region_code"] = pd.to_numeric(df["region_code"], errors="coerce").astype("Int64")

    physician_columns = [
        "hospital_physicians_total",
        "hospital_physicians_full_time",
        "hospital_physicians_part_time",
    ]

    for column in physician_columns:
        df[column] = (
            df[column]
            .astype(str)
            .str.replace(" ", "", regex=False)
            .replace("<NA>", pd.NA)
        )
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    return df


def clean_dataset() -> pd.DataFrame:
    """Run full cleaning pipeline."""
    df = read_physicians_csv()
    df = convert_missing_values(df)

    df["city"] = df["city_raw"].apply(clean_city_name)
    df = clean_numeric_columns(df)

    df = df[df["city"].isin(RUHR_CITY_NAMES)].copy()

    columns = [
        "city",
        "year",
        "region_code",
        "hospital_physicians_total",
        "hospital_physicians_full_time",
        "hospital_physicians_part_time",
    ]

    df = df[columns].sort_values(["city", "year"]).reset_index(drop=True)

    return df


def main() -> None:
    df = clean_dataset()

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)

    print(f"Saved cleaned physicians dataset to: {PROCESSED_PATH}")
    print(f"Shape: {df.shape}")
    print(df.head())
    print(df.tail())
    print("Years:", df["year"].min(), "-", df["year"].max())
    print("Cities:", sorted(df["city"].unique()))

    print("\nRows with missing physician data:")
    print(
        df[df["hospital_physicians_total"].isna()][
            [
                "city",
                "year",
                "hospital_physicians_total",
                "hospital_physicians_full_time",
                "hospital_physicians_part_time",
            ]
        ]
    )


if __name__ == "__main__":
    main()
