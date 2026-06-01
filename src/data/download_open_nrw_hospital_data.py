"""
Download official NRW hospital statistics data.

This script downloads the raw hospital statistics file from a direct URL
and stores it in data/raw/.

Usage:
    python src/data/download_open_nrw_hospital_data.py --url "DIRECT_FILE_URL"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def download_file(url: str, output_path: Path) -> None:
    """Download a file from a URL and save it locally."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    output_path.write_bytes(response.content)

    print(f"Downloaded file to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.2f} KB")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download NRW hospital statistics raw data."
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Direct URL to CSV/XLSX file from Open.NRW or Landesdatenbank NRW.",
    )

    parser.add_argument(
        "--output",
        default="open_nrw_hospital_statistics_raw.csv",
        help="Output filename inside data/raw/.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = RAW_DATA_DIR / args.output

    download_file(url=args.url, output_path=output_path)


if __name__ == "__main__":
    main()
