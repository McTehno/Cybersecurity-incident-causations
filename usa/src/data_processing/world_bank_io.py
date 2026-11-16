"""
Process World Bank WDI data downloaded by download_world_bank.py.

Run from the usa/ project root:
    python src/data_processing/world_bank_io.py

Input:
    data/raw/world_bank/api/USA/*.json

Output:
    data/processed/world_bank/usa_wdi_2014_2025.csv

Uses only Python standard library.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "world_bank" / "api"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "world_bank"

INDICATORS = {
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "industry_gdp_pct": "NV.IND.TOTL.ZS",
    "services_gdp_pct": "NV.SRV.TOTL.ZS",
    "unemployment_rate": "SL.UEM.TOTL.ZS",
    "labor_force_participation": "SL.TLF.CACT.ZS",
    "new_business_density": "IC.BUS.NDNS.ZS",
    "internet_users_pct": "IT.NET.USER.ZS",
    "fixed_broadband_per_100": "IT.NET.BBND.P2",
}


def load_indicator(path: Path, expected_code: str) -> dict[int, float]:
    """Load one indicator and return {year: value}."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    actual_code = data.get("indicator_code")

    if actual_code != expected_code:
        raise ValueError(
            f"Indicator mismatch in {path.name}: "
            f"expected {expected_code}, got {actual_code}"
        )

    values = {}

    for record in data.get("records", []):
        year = int(record["date"])
        value = record.get("value")

        if year in values:
            raise ValueError(
                f"Duplicate year {year} in {path.name}"
            )

        values[year] = float(value) if value is not None else None

    return values


def build_dataset(
    country: str,
    start_year: int,
    end_year: int,
):
    input_dir = RAW_DIR / country

    if not input_dir.exists():
        raise FileNotFoundError(
            f"Directory does not exist: {input_dir}"
        )

    dataset = {
        year: {
            "country": country,
            "year": year,
        }
        for year in range(start_year, end_year + 1)
    }

    print("=" * 65)
    print("WORLD BANK WDI DATA PROCESSING")
    print(f"Country: {country}")
    print(f"Period: {start_year}-{end_year}")
    print("=" * 65)

    for name, code in INDICATORS.items():
        path = input_dir / f"{name}.json"

        if not path.exists():
            raise FileNotFoundError(
                f"Missing input: {path}\n"
                "Run download_world_bank.py first."
            )

        values = load_indicator(path, code)

        for year in dataset:
            dataset[year][name] = values.get(year)

    rows = list(dataset.values())

    return rows


def print_availability(rows: list[dict]):
    print("\nAVAILABILITY BY INDICATOR")
    print("-" * 65)

    for name in INDICATORS:
        available = [
            row["year"]
            for row in rows
            if row[name] is not None
        ]

        missing = [
            row["year"]
            for row in rows
            if row[name] is None
        ]

        print(
            f"{name:30s} "
            f"{len(available):2d}/{len(rows):2d}"
        )

        if missing:
            print(f"  Missing years: {missing}")

    complete_years = [
        row["year"]
        for row in rows
        if all(row[name] is not None for name in INDICATORS)
    ]

    print("\nYears complete for all nine indicators:")
    print(complete_years if complete_years else "None")


def save_csv(rows: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "country",
        "year",
        *INDICATORS.keys(),
    ]

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
        )

        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--country",
        default="USA",
    )

    parser.add_argument(
        "--start-year",
        type=int,
        default=2014,
    )

    parser.add_argument(
        "--end-year",
        type=int,
        default=2025,
    )

    args = parser.parse_args()

    if args.start_year > args.end_year:
        parser.error("Start year must not exceed end year.")

    country = args.country.upper()

    rows = build_dataset(
        country=country,
        start_year=args.start_year,
        end_year=args.end_year,
    )

    print_availability(rows)

    output_path = (
        PROCESSED_DIR
        / f"{country.lower()}_wdi_{args.start_year}_{args.end_year}.csv"
    )

    save_csv(rows, output_path)

    print("\nSaved:")
    print(output_path)

    print("\nFirst three rows:")
    for row in rows[:3]:
        print(row)


if __name__ == "__main__":
    main()
