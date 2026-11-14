"""Download World Bank WDI country-level indicators (2014-2025) and merge with UMD incidents.

Saves:
- germany/data/raw/world_bank_global_2014_2025.csv
- germany/data/prepared/global_country_year_wb_umd.csv
"""

from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PREP_DIR = ROOT / "data" / "prepared"
CACHE_DIR = RAW_DIR / "_wb_zip_cache"

INDICATORS = {
    "SP.POP.TOTL": "population",
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
    "NV.IND.TOTL.ZS": "industry_gdp_pct",
    "NV.SRV.TOTL.ZS": "services_gdp_pct",
    "SL.UEM.TOTL.ZS": "unemployment_rate_pct",
    "SL.TLF.CACT.ZS": "labor_participation_pct",
    "IC.BUS.NDNS.ZS": "new_business_density",
    "IT.NET.USER.ZS": "internet_users_pct",
    "IT.NET.BBND.P2": "broadband_per_100",
}

YEARS = list(range(2014, 2026))
YEAR_STRS = [str(y) for y in YEARS]


def fetch_indicator_zip(code: str) -> bytes:
    """Download World Bank CSV ZIP with local caching and retries."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{code}.zip"
    if cache_path.exists() and cache_path.stat().st_size > 1000:
        return cache_path.read_bytes()

    urls = [
        f"https://api.worldbank.org/v2/en/indicator/{code}?downloadformat=csv",
        f"http://api.worldbank.org/v2/en/indicator/{code}?downloadformat=csv",
    ]
    headers = {"User-Agent": "Mozilla/5.0", "Connection": "close"}

    last_err: Exception | None = None
    for attempt in range(8):
        url = urls[attempt % len(urls)]
        try:
            resp = requests.get(url, headers=headers, timeout=35)
            resp.raise_for_status()
            if resp.content[:2] == b"PK":
                cache_path.write_bytes(resp.content)
                return resp.content
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        time.sleep(2 + attempt)

    raise RuntimeError(f"Failed to download {code}: {last_err}")


def parse_wb_zip(raw_bytes: bytes, col_name: str) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Parse World Bank CSV ZIP into long country-year dataframe and optional country metadata."""
    zf = zipfile.ZipFile(io.BytesIO(raw_bytes))
    data_name = [n for n in zf.namelist() if n.startswith("API_")][0]
    meta_names = [n for n in zf.namelist() if "Metadata_Country" in n]

    df = pd.read_csv(zf.open(data_name), skiprows=4)
    keep_cols = ["Country Name", "Country Code"] + [y for y in YEAR_STRS if y in df.columns]
    long_df = df[keep_cols].melt(
        id_vars=["Country Name", "Country Code"],
        var_name="year",
        value_name=col_name,
    )
    long_df["year"] = long_df["year"].astype(int)
    long_df = long_df.rename(
        columns={"Country Code": "country_iso3", "Country Name": "country_name"}
    )

    meta_df = pd.read_csv(zf.open(meta_names[0])) if meta_names else None
    return long_df, meta_df


def build_global_datasets() -> None:
    """Build world_bank_global_2014_2025.csv and global_country_year_wb_umd.csv."""
    merged: pd.DataFrame | None = None
    meta_df: pd.DataFrame | None = None

    for code, col in INDICATORS.items():
        print(f"Fetching {code} ({col})...", flush=True)
        raw_bytes = fetch_indicator_zip(code)
        long_df, meta = parse_wb_zip(raw_bytes, col)
        if meta_df is None and meta is not None:
            meta_df = meta[["Country Code", "Region", "IncomeGroup"]].rename(
                columns={
                    "Country Code": "country_iso3",
                    "Region": "wb_region",
                    "IncomeGroup": "wb_income_group",
                }
            )
        if merged is None:
            merged = long_df
        else:
            merged = merged.merge(
                long_df.drop(columns=["country_name"]),
                on=["country_iso3", "year"],
                how="outer",
                validate="one_to_one",
            )
        time.sleep(0.5)

    assert merged is not None and meta_df is not None
    wb_df = merged.merge(meta_df, on="country_iso3", how="left", validate="many_to_one")
    wb_df["is_sovereign_country"] = wb_df["wb_region"].notna()
    wb_df = wb_df.sort_values(["country_iso3", "year"]).reset_index(drop=True)

    wb_out = RAW_DIR / "world_bank_global_2014_2025.csv"
    wb_df.to_csv(wb_out, index=False)
    print(f"Saved {wb_out} ({len(wb_df)} rows)")

    # Load UMD incidents (2014-2025) by country_iso3 and year
    umd = pd.read_excel(RAW_DIR / "umd_cyber_events.xlsx")
    umd = umd[umd["year"].between(2014, 2025)].copy()
    umd["country_iso3"] = umd["country_iso3"].astype(str).str.strip()
    valid_umd = umd[umd["country_iso3"].str.len().eq(3) & (umd["country_iso3"] != "Undetermined")]

    inc_counts = (
        valid_umd.groupby(["country_iso3", "year"])
        .size()
        .reset_index(name="incident_count")
    )

    # Keep the 217 sovereign World Bank countries (exclude aggregate regions like WLD/EUU)
    countries = wb_df[wb_df["is_sovereign_country"]].copy()
    panel = countries.merge(inc_counts, on=["country_iso3", "year"], how="left", validate="one_to_one")
    panel["incident_count"] = panel["incident_count"].fillna(0).astype(int)
    panel["incidents_per_100k"] = panel["incident_count"] / panel["population"] * 100_000

    # Keep only sovereign rows with valid population
    panel = panel[panel["population"].notna() & (panel["population"] > 0)].reset_index(drop=True)
    panel_out = PREP_DIR / "global_country_year_wb_umd.csv"
    panel.to_csv(panel_out, index=False)
    print(
        f"Saved {panel_out} ({len(panel)} rows, {panel['country_iso3'].nunique()} countries, "
        f"{int(panel['incident_count'].sum())} matched incidents)"
    )


if __name__ == "__main__":
    build_global_datasets()
