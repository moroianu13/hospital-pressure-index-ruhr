"""
Clean NRW unemployment rate data.

Input:
    data/raw/nrw_unemployment_rate_raw.csv

Output:
    data/processed/ruhr_unemployment_2015_2024_clean.csv

The raw Landesdatenbank file contains metadata rows first.
This script extracts Ruhr city rows for 2015–2024.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "nrw_unemployment_rate_raw.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_unemployment_2015_2024_clean.csv"


RUHR_CITIES = [
    "Bochum",
    "Bottrop",
    "Dortmund",
    "Duisburg",
    "Essen",
    "Gelsenkirchen",
    "Hagen",
    "Herne",
    "Mülheim an der Ruhr",
    "Oberhausen",
]


CITY_REPLACEMENTS = {
    "Bochum, krfr. Stadt": "Bochum",
    "Bottrop, krfr. Stadt": "Bottrop",
    "Dortmund, krfr. Stadt": "Dortmund",
    "Duisburg, krfr. Stadt": "Duisburg",
    "Essen, krfr. Stadt": "Essen",
    "Gelsenkirchen, krfr. Stadt": "Gelsenkirchen",
    "Hagen, krfr. Stadt": "Hagen",
    "Herne, krfr. Stadt": "Herne",
    "Mülheim an der Ruhr, krfr. Stadt": "Mülheim an der Ruhr",
    "Oberhausen, krfr. Stadt": "Oberhausen",
}


def normalize_city_name(value: str) -> str:
    value = str(value).strip()
    return CITY_REPLACEMENTS.get(value, value)


def to_number(value: str) -> float:
    if value is None:
        return pd.NA

    value = str(value).strip()

    if value in {"", ".", "-", "x"}:
        return pd.NA

    value = value.replace(".", "").replace(",", ".")

    return pd.to_numeric(value, errors="coerce")


def read_data_rows() -> list[list[str]]:
    rows = []

    with RAW_PATH.open("r", encoding="latin1", newline="") as file:
        reader = csv.reader(file, delimiter=";")

        for row in reader:
            if len(row) != 8:
                continue

            if row[0].strip().isdigit():
                rows.append(row)

    return rows


def clean_unemployment() -> pd.DataFrame:
    rows = read_data_rows()
    cleaned_rows = []

    for row in rows:
        year = int(row[0].strip())
        region_code = row[1].strip()
        city = normalize_city_name(row[2])

        if city not in RUHR_CITIES:
            continue

        if not 2015 <= year <= 2024:
            continue

        men_rate = to_number(row[3])
        women_rate = to_number(row[4])
        youth_rate = to_number(row[5])
        older_rate = to_number(row[6])
        long_term_rate = to_number(row[7])

        unemployment_rate_proxy = pd.Series([men_rate, women_rate]).mean(skipna=True)

        cleaned_rows.append(
            {
                "city": city,
                "region_code": region_code,
                "year": year,
                "unemployment_rate_proxy": unemployment_rate_proxy,
                "men_unemployment_rate": men_rate,
                "women_unemployment_rate": women_rate,
                "youth_unemployment_rate": youth_rate,
                "older_unemployment_rate": older_rate,
                "long_term_unemployment_rate": long_term_rate,
            }
        )

    df = pd.DataFrame(cleaned_rows)

    numeric_columns = [
        "unemployment_rate_proxy",
        "men_unemployment_rate",
        "women_unemployment_rate",
        "youth_unemployment_rate",
        "older_unemployment_rate",
        "long_term_unemployment_rate",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").round(2)

    df = df.sort_values(["city", "year"]).reset_index(drop=True)

    return df


def main() -> None:
    df = clean_unemployment()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved cleaned unemployment data to: {OUTPUT_PATH}")
    print(f"Shape: {df.shape}")

    print("\nRows by city:")
    print(df["city"].value_counts().sort_index())

    print("\nYear range:")
    print(df["year"].min(), "-", df["year"].max())

    print("\nPreview:")
    print(df.head(20))


if __name__ == "__main__":
    main()
