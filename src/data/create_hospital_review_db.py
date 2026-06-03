"""
Create SQLite review database from hospital_registry_review.csv.

Input:
    data/manual/hospital_registry_review.csv

Output:
    data/manual/hospital_registry_review.db
"""

from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CSV_PATH = PROJECT_ROOT / "data" / "manual" / "hospital_registry_review.csv"
DB_PATH = PROJECT_ROOT / "data" / "manual" / "hospital_registry_review.db"


def main() -> None:
    df = pd.read_csv(CSV_PATH)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql("hospital_review", conn, if_exists="replace", index=False)

    print(f"Saved review DB to: {DB_PATH}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
