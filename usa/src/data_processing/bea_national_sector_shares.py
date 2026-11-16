"""
Calculate national US GDP sector shares from BEA SAGDP2.

Run from the usa/ project root:
    python src/data_processing/bea_national_sector_shares.py
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "data/raw/bea/extracted/SAGDP"
    / "SAGDP2_US_1997_2025.csv"
)

OUTPUT = (
    ROOT / "data/processed/economic/bea"
    / "usa_national_sector_shares_2014_2025.csv"
)

YEARS = range(2014, 2026)

TOTAL = 1
AGRICULTURE = [3]
INDUSTRY = [6, 10, 11, 12]
SERVICES = [
    34, 35, 36, 45, 50,
    59, 68, 75, 82, 83
]


def main():
    df = pd.read_csv(INPUT)

    # Remove footer rows without LineCode.
    df = df.dropna(subset=["LineCode"]).copy()
    df["LineCode"] = df["LineCode"].astype(int)

    if df["LineCode"].duplicated().any():
        raise ValueError("Duplicate BEA LineCode detected.")

    df = df.set_index("LineCode")

    required = {TOTAL, *AGRICULTURE, *INDUSTRY, *SERVICES}
    missing = required - set(df.index)

    if missing:
        raise ValueError(f"Missing BEA LineCodes: {missing}")

    results = []

    for year in YEARS:
        column = str(year)

        if column not in df.columns:
            raise ValueError(f"Missing year: {year}")

        values = pd.to_numeric(
            df[column], errors="coerce"
        )

        total = values.loc[TOTAL]
        agriculture = values.loc[AGRICULTURE].sum(
            min_count=len(AGRICULTURE)
        )
        industry = values.loc[INDUSTRY].sum(
            min_count=len(INDUSTRY)
        )
        services = values.loc[SERVICES].sum(
            min_count=len(SERVICES)
        )

        if pd.isna(
            [total, agriculture, industry, services]
        ).any():
            raise ValueError(
                f"Missing sector GDP values for {year}"
            )

        if total <= 0:
            raise ValueError(f"Invalid total GDP for {year}")

        agriculture_pct = 100 * agriculture / total
        industry_pct = 100 * industry / total
        services_pct = 100 * services / total

        check = (
            agriculture_pct
            + industry_pct
            + services_pct
        )

        if abs(check - 100) > 0.05:
            raise ValueError(
                f"Sector shares do not add to 100 "
                f"in {year}: {check:.4f}"
            )

        results.append({
            "country": "USA",
            "year": year,
            "industry_gdp_pct_bea": industry_pct,
            "services_gdp_pct_bea": services_pct,
            "agriculture_gdp_pct_bea": agriculture_pct,
        })

    result = pd.DataFrame(results)

    OUTPUT.parent.mkdir(
        parents=True, exist_ok=True
    )
    result.to_csv(OUTPUT, index=False)

    print("\nBEA NATIONAL SECTOR SHARES")
    print("=" * 65)
    print(result.to_string(index=False, float_format="%.3f"))

    print("\nMissing values:")
    print(result.isna().sum().to_string())

    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
