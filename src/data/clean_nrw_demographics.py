"""
Clean NRW population by age and sex data.

Input:
    data/raw/nrw_population_age_sex_raw.csv

Output:
    data/processed/ruhr_demographics_2015_2024_clean.csv

The raw Landesdatenbank file has metadata/header rows before the actual data.
This script reads rows manually and extracts city-level "Insgesamt" rows
for Ruhr cities.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "nrw_population_age_sex_raw.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_demographics_2015_2024_clean.csv"


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
    """Clean city names from Landesdatenbank formatting."""
    value = str(value).strip()
    return CITY_REPLACEMENTS.get(value, value)


def to_number(value: str) -> float:
    """Convert German/CSV numeric value to number."""
    if value is None:
        return pd.NA

    value = str(value).strip()

    if value in {"", ".", "-", "x"}:
        return pd.NA

    value = value.replace(".", "").replace(",", ".")

    return pd.to_numeric(value, errors="coerce")


def read_data_rows() -> list[list[str]]:
    """Read only real data rows from the raw CSV."""
    data_rows = []

    with RAW_PATH.open("r", encoding="latin1", newline="") as file:
        reader = csv.reader(file, delimiter=";")

        for row in reader:
            if not row:
                continue

            first_cell = row[0].strip()

            # Real data rows start like 31.12.2024
            if len(row) >= 96 and first_cell.count(".") == 2:
                data_rows.append(row)

    return data_rows


def clean_demographics() -> pd.DataFrame:
    rows = read_data_rows()

    cleaned_rows = []

    for row in rows:
        date = row[0].strip()
        region_code = row[1].strip()
        city_raw = row[2].strip()
        sex = row[3].strip()

        year = int(date[-4:])
        city = normalize_city_name(city_raw)

        if city not in RUHR_CITIES:
            continue

        if sex != "Insgesamt":
            continue

        if not 2015 <= year <= 2024:
            continue

        population_total = to_number(row[4])

        # Column mapping:
        # 5 = under 1 year / age 0
        # 6 = age 1
        # ...
        # 70 = age 65
        # 85 = age 80
        # 95 = 90 years and more
        age_values = {}

        for age in range(0, 91):
            column_index = 5 + age
            age_values[age] = to_number(row[column_index])

        population_65_plus = sum(
            value for age, value in age_values.items()
            if age >= 65 and pd.notna(value)
        )

        population_80_plus = sum(
            value for age, value in age_values.items()
            if age >= 80 and pd.notna(value)
        )

        cleaned_rows.append(
            {
                "city": city,
                "region_code": region_code,
                "year": year,
                "population_total": population_total,
                "population_65_plus": population_65_plus,
                "population_80_plus": population_80_plus,
            }
        )

    df = pd.DataFrame(cleaned_rows)

    df["population_65_plus_pct"] = (
        df["population_65_plus"] / df["population_total"] * 100
    )

    df["population_80_plus_pct"] = (
        df["population_80_plus"] / df["population_total"] * 100
    )

    numeric_columns = [
        "population_total",
        "population_65_plus",
        "population_80_plus",
        "population_65_plus_pct",
        "population_80_plus_pct",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").round(2)

    df = df.sort_values(["city", "year"]).reset_index(drop=True)

    return df


def main() -> None:
    df = clean_demographics()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved cleaned demographics to: {OUTPUT_PATH}")
    print(f"Shape: {df.shape}")

    print("\nRows by city:")
    print(df["city"].value_counts().sort_index())

    print("\nYear range:")
    print(df["year"].min(), "-", df["year"].max())

    print("\nPreview:")
    print(df.head(20))


if __name__ == "__main__":
    main()
