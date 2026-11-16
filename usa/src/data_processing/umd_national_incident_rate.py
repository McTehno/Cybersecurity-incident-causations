"""
Calculate the national US documented cyber incident rate.

Numerator:
    UMD deduplicated incident records for the USA.

Denominator:
    World Bank SP.POP.TOTL, total US population.

Run from usa/:
    python src/data_processing/umd_national_incident_rate.py
"""

from pathlib import Path
import json
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

UMD_PATH = (
    ROOT / "data/processed/umd_usa"
    / "umd_usa_deduplicated_consolidated.csv"
)

RAW_POPULATION_PATH = (
    ROOT / "data/raw/world_bank/api/USA"
    / "population_total.json"
)

OUTPUT_PATH = (
    ROOT / "data/processed/umd_usa"
    / "usa_national_incident_rate_2014_2025.csv"
)

START_YEAR = 2014
END_YEAR = 2025

POPULATION_API = (
    "https://api.worldbank.org/v2/country/USA/"
    "indicator/SP.POP.TOTL"
    "?format=json&date=2014:2025&per_page=100"
)


def load_umd_counts():
    df = pd.read_csv(UMD_PATH, low_memory=False)

    required = {"slug", "year", "country_iso3"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing UMD columns: {missing}")

    if df["slug"].isna().any():
        raise ValueError("UMD contains missing slugs.")

    if df["slug"].duplicated().any():
        raise ValueError("UMD contains duplicate slugs.")

    if not df["country_iso3"].eq("USA").all():
        raise ValueError("UMD contains non-USA records.")

    df["year"] = pd.to_numeric(
        df["year"], errors="raise"
    ).astype(int)

    df = df.loc[
        df["year"].between(START_YEAR, END_YEAR)
    ].copy()

    counts = (
        df.groupby("year")
        .size()
        .rename("incident_count")
        .reset_index()
    )

    return counts


def load_population():
    # Download once, then retain the original API response.
    if RAW_POPULATION_PATH.exists():
        with RAW_POPULATION_PATH.open(
            "r", encoding="utf-8"
        ) as file:
            payload = json.load(file)

        print("Population source: cached World Bank JSON")

    else:
        request = Request(
            POPULATION_API,
            headers={
                "User-Agent": "MOS-Research/1.0",
                "Accept": "application/json",
            },
        )

        with urlopen(request, timeout=30) as response:
            payload = json.load(response)

        RAW_POPULATION_PATH.parent.mkdir(
            parents=True, exist_ok=True
        )

        with RAW_POPULATION_PATH.open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(payload, file, indent=2)

        print("Population source: World Bank API")

    if not isinstance(payload, list) or len(payload) != 2:
        raise ValueError("Invalid World Bank API response.")

    metadata, records = payload

    if not isinstance(records, list):
        raise ValueError("Missing World Bank population records.")

    if int(metadata.get("pages", 1)) != 1:
        raise ValueError("Unexpected pagination.")

    rows = []

    for record in records:
        year = int(record["date"])
        value = record.get("value")

        if not START_YEAR <= year <= END_YEAR:
            continue

        if record["indicator"]["id"] != "SP.POP.TOTL":
            raise ValueError("Unexpected indicator.")

        if record["countryiso3code"] != "USA":
            raise ValueError("Unexpected country.")

        rows.append({
            "year": year,
            "population": value,
        })

    population = pd.DataFrame(rows)

    if population["year"].duplicated().any():
        raise ValueError("Duplicate population years.")

    return population


def main():
    counts = load_umd_counts()
    population = load_population()

    years = pd.DataFrame({
        "year": list(range(START_YEAR, END_YEAR + 1))
    })

    result = (
        years
        .merge(counts, on="year", how="left", validate="one_to_one")
        .merge(
            population,
            on="year",
            how="left",
            validate="one_to_one",
        )
    )

    if result[
        ["incident_count", "population"]
    ].isna().any().any():
        raise ValueError("Missing incidents or population.")

    if (result["population"] <= 0).any():
        raise ValueError("Invalid population.")

    result["incident_count"] = (
        result["incident_count"].astype(int)
    )
    result["population"] = (
        result["population"].astype(int)
    )

    result["incidents_per_100k"] = (
        result["incident_count"]
        / result["population"]
        * 100_000
    )

    result.insert(0, "country", "USA")

    result["incident_source"] = "UMD_deduplicated"
    result["population_source"] = "World_Bank_SP.POP.TOTL"

    OUTPUT_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )

    result.to_csv(OUTPUT_PATH, index=False)

    print("\nUSA NATIONAL INCIDENT RATE")
    print("=" * 75)

    print(
        result[
            [
                "year",
                "incident_count",
                "population",
                "incidents_per_100k",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )

    print("\nTotal incidents:", result["incident_count"].sum())

    print("\nMissing values:")
    print(result.isna().sum().to_string())

    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
