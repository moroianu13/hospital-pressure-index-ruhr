"""
Download NRW population by age and sex.

Input:
    Landesdatenbank NRW CSV table 12411-10i_00

Output:
    data/raw/nrw_population_age_sex_raw.csv
"""

from __future__ import annotations

from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "nrw_population_age_sex_raw.csv"

URL = (
    "https://www.landesdatenbank.nrw.de/ldbnrwws/downloader/00/tables/"
    "12411-10i_00.csv"
)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(URL, timeout=60)
    response.raise_for_status()

    OUTPUT_PATH.write_bytes(response.content)

    print(f"Saved demographics raw data to: {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    main()
