"""
Clean NRW hospital registry from OpenGeodata NRW.

Input:
    data/raw/nrw_hospital_registry_raw.csv

Output:
    data/processed/ruhr_hospital_registry_clean.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "nrw_hospital_registry_raw.csv"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "ruhr_hospital_registry_clean.csv"


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


COLUMN_MAPPING = {
    "kh_id": "hospital_id",
    "kh_bez": "hospital_name",
    "kh_art": "hospital_registry_type",
    "tr_bez": "operator_name",
    "tr_rechtsform": "operator_legal_form",
    "bs_bez": "site_name",
    "bs_plz": "postal_code",
    "bs_strasse": "street",
    "bs_gemeinde": "city",
}


def load_raw_registry() -> pd.DataFrame:
    """Load raw OpenGeodata NRW hospital registry."""
    return pd.read_csv(RAW_PATH, sep=";", encoding="utf-8")


def clean_registry() -> pd.DataFrame:
    """Clean and filter registry to Ruhr cities."""
    df = load_raw_registry()

    df = df.rename(columns=COLUMN_MAPPING)
    df = df[list(COLUMN_MAPPING.values())].copy()

    text_columns = [
        "hospital_name",
        "hospital_registry_type",
        "operator_name",
        "operator_legal_form",
        "site_name",
        "street",
        "city",
    ]

    for column in text_columns:
        df[column] = df[column].fillna("").astype(str).str.strip()

    df["postal_code"] = df["postal_code"].astype(str).str.strip()

    df = df[df["city"].isin(RUHR_CITIES)].copy()

    df["is_psychiatric_or_psychosomatic"] = df["hospital_name"].str.contains(
        "psychiatr|psychosom|lvr|lwl",
        case=False,
        regex=True,
    )

    df["is_rehabilitation_like"] = df["hospital_name"].str.contains(
        "rehabilitation|reha|rehaklinik",
        case=False,
        regex=True,
    )

    df["acute_relevance_initial"] = "unknown"

    df.loc[
        df["is_psychiatric_or_psychosomatic"],
        "acute_relevance_initial",
    ] = "likely_exclude_or_separate"

    df.loc[
        df["is_rehabilitation_like"],
        "acute_relevance_initial",
    ] = "likely_exclude"

    df.loc[
        ~df["is_psychiatric_or_psychosomatic"]
        & ~df["is_rehabilitation_like"],
        "acute_relevance_initial",
    ] = "needs_classification"

    df = df.sort_values(["city", "hospital_name"]).reset_index(drop=True)

    return df


def main() -> None:
    df = clean_registry()

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)

    print(f"Saved cleaned hospital registry to: {PROCESSED_PATH}")
    print(f"Shape: {df.shape}")

    print("\nHospitals by city:")
    print(df["city"].value_counts().sort_index())

    print("\nInitial acute relevance classification:")
    print(df["acute_relevance_initial"].value_counts())

    print("\nPreview:")
    print(
        df[
            [
                "city",
                "hospital_name",
                "hospital_registry_type",
                "operator_name",
                "acute_relevance_initial",
            ]
        ].head(30)
    )


if __name__ == "__main__":
    main()
