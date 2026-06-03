"""
Download NRW hospital registry from OpenGeodata NRW.

Input:
    OpenGeodata NRW direct CSV URL

Output:
    data/raw/nrw_hospital_registry_raw.csv
"""

from __future__ import annotations

from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "nrw_hospital_registry_raw.csv"

URL = (
    "https://www.opengeodata.nrw.de/produkte/gesundheit/krankenhaeuser/"
    "krankenhaeuser_EPSG25832_CSV.csv"
)


def main() -> None:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(URL, timeout=60)
    response.raise_for_status()

    RAW_PATH.write_bytes(response.content)

    print(f"Saved NRW hospital registry to: {RAW_PATH}")
    print(f"File size: {RAW_PATH.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    main()
