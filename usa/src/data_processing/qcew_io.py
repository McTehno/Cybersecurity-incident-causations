"""Selective loading of annual state-level BLS QCEW records."""

from pathlib import Path
from zipfile import ZipFile
import re

import pandas as pd


REQUIRED_COLUMNS = [
    "area_fips", "own_code", "industry_code", "agglvl_code", "year",
    "disclosure_code", "area_title", "own_title", "industry_title",
    "annual_avg_estabs_count", "annual_avg_emplvl", "total_annual_wages",
    "avg_annual_pay",
]

INDUSTRY_CODES = {
    "11", "21", "22", "23", "31-33", "42", "44-45", "48-49",
    "51", "52", "53", "54", "55", "56", "61", "62", "71", "72", "81",
}


def load_qcew_states(zip_path: str | Path, state_fips_codes: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read only 50 statewide CSVs and return totals and ownership-level NAICS sectors."""
    zip_path = Path(zip_path)
    year = int(zip_path.name[:4])
    state_rows = []
    sector_rows = []

    with ZipFile(zip_path) as archive:
        state_files = {}
        for name in archive.namelist():
            match = re.search(r"\.annual (\d{5}) .+ -- Statewide\.csv$", name)
            if match and match.group(1).endswith("000"):
                code = match.group(1)[:2]
                if code in state_fips_codes:
                    if code in state_files:
                        raise ValueError(f"Duplicate statewide files for {code}")
                    state_files[code] = name

        if set(state_files) != set(state_fips_codes):
            missing = set(state_fips_codes) - set(state_files)
            raise ValueError(f"Expected 50 state files for {year}; missing: {sorted(missing)}")

        for state_fips, name in sorted(state_files.items()):
            with archive.open(name) as stream:
                df = pd.read_csv(
                    stream,
                    usecols=REQUIRED_COLUMNS,
                    dtype={"area_fips": "string", "industry_code": "string"},
                    low_memory=False,
                )

            df["state_fips"] = state_fips
            df["year"] = year
            own = pd.to_numeric(df["own_code"], errors="coerce")
            agg = pd.to_numeric(df["agglvl_code"], errors="coerce")
            industry = df["industry_code"].str.strip()

            state_rows.append(df.loc[(own == 0) & (agg == 50) & (industry == "10")].copy())
            sector_rows.append(df.loc[
                own.isin([1, 2, 3, 5]) & (agg == 54) & industry.isin(INDUSTRY_CODES)
            ].copy())

    totals = pd.concat(state_rows, ignore_index=True)
    sectors = pd.concat(sector_rows, ignore_index=True)

    if len(totals) != 50 or totals.duplicated(["state_fips", "year"]).any():
        raise ValueError(f"Invalid statewide aggregate coverage in {year}")

    suppressed = sectors["disclosure_code"].astype("string").str.strip().eq("N").fillna(False)
    sectors.loc[suppressed, ["annual_avg_emplvl", "total_annual_wages", "avg_annual_pay"]] = float("nan")
    sectors["suppressed"] = suppressed

    return totals, sectors
