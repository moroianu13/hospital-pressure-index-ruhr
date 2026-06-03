"""
Suggest manual-review values for hospital acute-care classification.

This script is an assisted verification helper. It uses deterministic keyword
rules and city-level MAGS NRW planning pages to prepare suggested values, but it
does not set any row to verified and does not overwrite the manual review CSV.
Every suggestion still requires human verification before copying values into
the verified_* columns.

Input:
    data/manual/hospital_registry_review.csv

Output:
    data/manual/hospital_registry_review_suggestions.csv
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = PROJECT_ROOT / "data" / "manual" / "hospital_registry_review.csv"
OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "manual" / "hospital_registry_review_suggestions.csv"
)

REQUIRED_COLUMNS = {
    "hospital_id",
    "city",
    "hospital_name",
    "hospital_registry_type",
    "operator_name",
    "verification_status",
    "source_url",
    "review_notes",
}

SUGGESTION_COLUMNS = [
    "suggested_category",
    "suggested_acute_relevance_weight",
    "suggested_source_type",
    "suggested_source_url",
    "suggested_review_notes",
    "suggestion_confidence",
]

SOURCE_TYPE = "mags_nrw_krankenhausplanung"
MAGS_BASE_URL = (
    "https://www.mags.nrw/startseite/gesundheit/krankenhausplanung-nrw/"
    "planungsergebnisse/krankenhaeuser-und-angebote"
)

# Official MAGS index checked 2026-06-03. Some Ruhr pages use numeric paths;
# the plain Dortmund and Muelheim slug paths returned 404.
CITY_SOURCE_URLS = {
    "bochum": f"{MAGS_BASE_URL}/bochum",
    "bottrop": f"{MAGS_BASE_URL}/bottrop",
    "dortmund": f"{MAGS_BASE_URL}-3",
    "duisburg": f"{MAGS_BASE_URL}-8",
    "essen": f"{MAGS_BASE_URL}/essen",
    "gelsenkirchen": f"{MAGS_BASE_URL}-15",
    "hagen": f"{MAGS_BASE_URL}/hagen",
    "herne": f"{MAGS_BASE_URL}/herne",
    "mulheim an der ruhr": f"{MAGS_BASE_URL}-6",
    "oberhausen": f"{MAGS_BASE_URL}-7",
}


@dataclass(frozen=True)
class SuggestionRule:
    category: str
    weight: float
    source_label: str
    confidence: float
    terms: tuple[str, ...]


RULES = [
    SuggestionRule(
        category="psychiatric_psychosomatic",
        weight=0.0,
        source_label="psychiatric/psychosomatic keyword",
        confidence=0.95,
        terms=("lvr", "lwl", "psychiatr", "psychosom", "kjp", "valeara"),
    ),
    SuggestionRule(
        category="rehabilitation",
        weight=0.0,
        source_label="rehabilitation keyword",
        confidence=0.9,
        terms=("reha", "rehabilitation", "rehaklinik"),
    ),
    SuggestionRule(
        category="general_or_acute_care",
        weight=1.0,
        source_label="general/acute-care keyword",
        confidence=0.85,
        terms=(
            "universitatsklinikum",
            "klinikum",
            "krankenhaus",
            "marien hospital",
            "marienhospital",
            "st johannes",
            "sana",
            "kath kliniken",
            "kem",
            "bergmannsheil",
            "st anna",
            "augusta kranken anstalt",
            "helios st elisabeth klinik",
        ),
    ),
    SuggestionRule(
        category="specialized_or_partial_acute",
        weight=0.5,
        source_label="specialized/partial acute keyword",
        confidence=0.75,
        terms=(
            "rheumazentrum",
            "huttenhospital",
            "vamed hagen ambrock",
            "vamed klinik hagen ambrock",
            "fachklinik",
        ),
    ),
]


def normalize(value: object) -> str:
    """Normalize free text for deterministic keyword matching."""
    if pd.isna(value):
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


NORMALIZED_RULES = [
    SuggestionRule(
        category=rule.category,
        weight=rule.weight,
        source_label=rule.source_label,
        confidence=rule.confidence,
        terms=tuple(normalize(term) for term in rule.terms),
    )
    for rule in RULES
]


def validate_input(df: pd.DataFrame) -> None:
    missing_columns = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing_columns:
        raise ValueError(
            "Missing required columns in hospital registry review CSV: "
            + ", ".join(missing_columns)
        )

    duplicate_mask = df["hospital_id"].duplicated(keep=False)
    if duplicate_mask.any():
        duplicates = df.loc[duplicate_mask, "hospital_id"].astype(str).tolist()
        raise ValueError("Duplicate hospital_id values found: " + ", ".join(duplicates))

    verified_mask = df["verification_status"].fillna("").astype(str).eq("verified")
    missing_evidence = verified_mask & (
        df["source_url"].fillna("").astype(str).str.strip().eq("")
        | df["review_notes"].fillna("").astype(str).str.strip().eq("")
    )
    if missing_evidence.any():
        bad_ids = df.loc[missing_evidence, "hospital_id"].astype(str).tolist()
        raise ValueError(
            "Verified rows must already have source_url and review_notes. "
            "Missing evidence for hospital_id: "
            + ", ".join(bad_ids)
        )

    if INPUT_PATH.resolve() == OUTPUT_PATH.resolve():
        raise ValueError("Refusing to overwrite hospital_registry_review.csv")


def combined_search_text(row: pd.Series) -> str:
    fields = [
        row.get("hospital_name", ""),
        row.get("operator_name", ""),
    ]
    return normalize(" ".join(str(field) for field in fields if not pd.isna(field)))


def city_source_url(city: object) -> str:
    return CITY_SOURCE_URLS.get(normalize(city), "")


def suggest_row(row: pd.Series) -> dict[str, object]:
    source_url = city_source_url(row.get("city", ""))
    source_type = SOURCE_TYPE if source_url else ""
    text = combined_search_text(row)

    for rule in NORMALIZED_RULES:
        for term in rule.terms:
            if term and term in text:
                return {
                    "suggested_category": rule.category,
                    "suggested_acute_relevance_weight": rule.weight,
                    "suggested_source_type": source_type,
                    "suggested_source_url": source_url,
                    "suggested_review_notes": (
                        f"Suggested by deterministic {rule.source_label}: "
                        f"matched '{term}' in hospital/operator text. "
                        "Human verification required before copying into verified_* fields."
                    ),
                    "suggestion_confidence": rule.confidence,
                }

    note = (
        "No deterministic category rule matched. Keep verification_status as "
        "needs_verification until a human reviewer confirms the classification."
    )
    if not source_url:
        note += " No MAGS NRW city source URL was assigned."

    return {
        "suggested_category": "unknown_needs_review",
        "suggested_acute_relevance_weight": "",
        "suggested_source_type": source_type,
        "suggested_source_url": source_url,
        "suggested_review_notes": note,
        "suggestion_confidence": 0.0,
    }


def add_suggestions(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    for column in SUGGESTION_COLUMNS:
        output[column] = ""

    unverified_mask = (
        output["verification_status"].fillna("").astype(str).str.casefold().ne("verified")
    )
    suggestions = output.loc[unverified_mask].apply(suggest_row, axis=1)

    if not suggestions.empty:
        suggestion_df = pd.DataFrame(suggestions.tolist(), index=suggestions.index)
        for column in SUGGESTION_COLUMNS:
            output.loc[suggestion_df.index, column] = suggestion_df[column]

    return output


def print_summary(df: pd.DataFrame) -> None:
    unverified_mask = (
        df["verification_status"].fillna("").astype(str).str.casefold().ne("verified")
    )
    suggested = df.loc[unverified_mask]

    if suggested.empty:
        print("No unverified rows need suggestions.")
        print("\nRows still unclear: 0")
        print("\nRows where no source URL was assigned: 0")
        return

    unclear = suggested["suggested_category"].eq("unknown_needs_review")
    missing_url = suggested["suggested_source_url"].fillna("").astype(str).str.strip().eq("")

    print("Suggestions by suggested_category:")
    print(suggested["suggested_category"].value_counts(dropna=False).to_string())

    print(f"\nRows still unclear: {int(unclear.sum())}")
    if unclear.any():
        print(
            suggested.loc[unclear, ["hospital_id", "city", "hospital_name"]].to_string(
                index=False
            )
        )

    print(f"\nRows where no source URL was assigned: {int(missing_url.sum())}")
    if missing_url.any():
        print(
            suggested.loc[missing_url, ["hospital_id", "city", "hospital_name"]].to_string(
                index=False
            )
        )


def main() -> None:
    df = pd.read_csv(INPUT_PATH)
    validate_input(df)

    suggestions = add_suggestions(df)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    suggestions.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved suggestions to: {OUTPUT_PATH}")
    print(f"Shape: {suggestions.shape}")
    print()
    print_summary(suggestions)


if __name__ == "__main__":
    main()
