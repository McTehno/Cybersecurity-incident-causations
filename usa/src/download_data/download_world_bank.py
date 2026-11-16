"""
Download World Bank WDI indicators.

Default: United States, 2014-2025.

Run from the usa/ project root:
    python src/download_data/download_world_bank.py

Uses only Python standard library.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "world_bank" / "api"

BASE_URL = "https://api.worldbank.org/v2"

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


def fetch_json(url: str, retries: int = 3):
    """Fetch and validate one JSON API response."""
    for attempt in range(1, retries + 1):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "MOS-Research/1.0",
                    "Accept": "application/json",
                },
            )

            with urlopen(request, timeout=30) as response:
                data = json.load(response)

            if isinstance(data, list) and len(data) == 1:
                if isinstance(data[0], dict) and "message" in data[0]:
                    raise ValueError(
                        f"World Bank API error: {data[0]['message']}"
                    )

            if not isinstance(data, list) or len(data) != 2:
                raise ValueError(
                    f"Unexpected API response: {str(data)[:300]}"
                )

            return data

        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if attempt == retries:
                raise RuntimeError(
                    f"API request failed: {url}"
                ) from exc

            print(f"  Retry {attempt}/{retries}: {exc}")
            time.sleep(2 * attempt)

    raise RuntimeError("API request failed")


def download_indicator(
    country: str,
    indicator_code: str,
    start_year: int,
    end_year: int,
):
    """Download all pages for one indicator."""
    all_records = []
    metadata = None
    page = 1

    while True:
        params = urlencode(
            {
                "format": "json",
                "date": f"{start_year}:{end_year}",
                "per_page": 1000,
                "page": page,
            }
        )

        url = (
            f"{BASE_URL}/country/{country}/"
            f"indicator/{indicator_code}?{params}"
        )

        response_metadata, records = fetch_json(url)

        if metadata is None:
            metadata = response_metadata

        if records:
            all_records.extend(records)

        total_pages = int(response_metadata.get("pages", 1))

        if page >= total_pages:
            break

        page += 1

    return {
        "country": country,
        "indicator_code": indicator_code,
        "start_year": start_year,
        "end_year": end_year,
        "retrieved_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "metadata": metadata,
        "records": all_records,
    }


def save_json(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def summarize_indicator(
    data: dict,
    start_year: int,
    end_year: int,
):
    """Return available and missing years."""
    records = data["records"]

    available_years = sorted(
        {
            int(record["date"])
            for record in records
            if record.get("value") is not None
        }
    )

    requested_years = set(range(start_year, end_year + 1))

    missing_years = sorted(
        requested_years - set(available_years)
    )

    return {
        "available_years": available_years,
        "missing_years": missing_years,
        "available_count": len(available_years),
        "requested_count": len(requested_years),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Download World Bank WDI indicators."
    )

    parser.add_argument(
        "--country",
        default="USA",
        help="World Bank country code, default USA",
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

    output_dir = RAW_DIR / country
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("WORLD BANK WDI DOWNLOAD")
    print(f"Country: {country}")
    print(f"Period: {args.start_year}-{args.end_year}")
    print(f"Indicators: {len(INDICATORS)}")
    print(f"Output: {output_dir}")
    print("=" * 65)

    summary = {}
    failed = {}

    for index, (name, code) in enumerate(
        INDICATORS.items(), start=1
    ):
        print(f"\n[{index}/{len(INDICATORS)}] {name}")
        print(f"  Code: {code}")

        try:
            data = download_indicator(
                country=country,
                indicator_code=code,
                start_year=args.start_year,
                end_year=args.end_year,
            )

            file_path = output_dir / f"{name}.json"
            save_json(data, file_path)

            result = summarize_indicator(
                data,
                args.start_year,
                args.end_year,
            )

            summary[name] = {
                "indicator_code": code,
                **result,
            }

            print(
                f"  Available: "
                f"{result['available_count']}/"
                f"{result['requested_count']} years"
            )

            if result["missing_years"]:
                print(
                    f"  Missing: {result['missing_years']}"
                )
            else:
                print("  Missing: none")

            print(f"  Saved: {file_path.name}")

        except (RuntimeError, ValueError) as exc:
            failed[name] = {
                "indicator_code": code,
                "error": str(exc),
            }

            print(f"  ERROR: {exc}")

    report = {
        "country": country,
        "start_year": args.start_year,
        "end_year": args.end_year,
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "indicators": summary,
        "failed_indicators": failed,
    }

    save_json(
        report,
        output_dir / "availability_report.json",
    )

    print("\n" + "=" * 65)
    print("AVAILABILITY SUMMARY")
    print("=" * 65)

    for name, result in summary.items():
        print(
            f"{name:30s} "
            f"{result['available_count']:2d}/"
            f"{result['requested_count']:2d}"
        )

    if failed:
        print("\nFAILED INDICATORS:")
        for name, details in failed.items():
            print(f"  {name}: {details['error']}")

    print("\nReport saved:")
    print(output_dir / "availability_report.json")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
