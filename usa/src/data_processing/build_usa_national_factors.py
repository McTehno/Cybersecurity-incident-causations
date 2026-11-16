"""
Build the national USA dataset containing 10 research variables.

Period: 2014-2025
Unit of observation: USA x year

Sources:
    - World Bank WDI: economic and digital indicators
    - BEA: industry and services GDP shares
    - BLS QCEW: establishment density (50 states, excluding DC)
    - UMD + World Bank: documented incident rate

Run from usa/:
    python src/data_processing/build_usa_national_factors.py

Missing values are preserved (no interpolation or imputation).
"""

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data" / "processed"

WDI_PATH = (
    DATA / "world_bank"
    / "usa_wdi_2014_2025.csv"
)

BEA_PATH = (
    DATA / "economic" / "bea"
    / "usa_national_sector_shares_2014_2025.csv"
)

QCEW_PATH = (
    DATA / "economic" / "bls_qcew"
    / "usa_national_establishment_density_2014_2025.csv"
)

UMD_PATH = (
    DATA / "umd_usa"
    / "usa_national_incident_rate_2014_2025.csv"
)

OUTPUT_DIR = DATA / "factors"

OUTPUT_PATH = (
    OUTPUT_DIR / "usa_national_factors_2014_2025.csv"
)

AVAILABILITY_PATH = (
    OUTPUT_DIR / "usa_national_factors_availability_2014_2025.csv"
)

START_YEAR = 2014
END_YEAR = 2025

FEATURES = [
    "incident_rate",
    "gdp_per_capita",
    "gdp_growth",
    "industry_gdp_pct",
    "services_gdp_pct",
    "unemployment_rate",
    "labor_force_participation",
    "establishment_density",
    "internet_users_pct",
    "fixed_broadband_per_100",
]


def load_source(path: Path, columns: list[str]) -> pd.DataFrame:
    """Read and validate a source dataset."""

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    df = pd.read_csv(path)

    required = {"country", "year", *columns}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{path.name}: missing columns {sorted(missing)}"
        )

    df = df[["country", "year", *columns]].copy()

    if df[["country", "year"]].isna().any().any():
        raise ValueError(
            f"{path.name}: missing country or year"
        )

    if df.duplicated(["country", "year"]).any():
        raise ValueError(
            f"{path.name}: duplicate country-year records"
        )

    df["country"] = df["country"].astype(str).str.upper()

    if not df["country"].eq("USA").all():
        raise ValueError(
            f"{path.name}: contains non-USA records"
        )

    df["year"] = pd.to_numeric(
        df["year"], errors="raise"
    ).astype(int)

    expected_years = set(range(START_YEAR, END_YEAR + 1))

    if set(df["year"]) != expected_years:
        raise ValueError(
            f"{path.name}: unexpected year coverage"
        )

    if len(df) != len(expected_years):
        raise ValueError(
            f"{path.name}: unexpected number of rows"
        )

    for column in columns:
        df[column] = pd.to_numeric(
            df[column], errors="raise"
        )

    return df


def load_wdi() -> pd.DataFrame:
    """World Bank indicators with available annual observations."""

    columns = [
        "gdp_per_capita",
        "gdp_growth",
        "unemployment_rate",
        "labor_force_participation",
        "internet_users_pct",
        "fixed_broadband_per_100",
    ]

    return load_source(WDI_PATH, columns)


def load_bea() -> pd.DataFrame:
    """BEA national GDP sector shares."""

    df = load_source(
        BEA_PATH,
        [
            "industry_gdp_pct_bea",
            "services_gdp_pct_bea",
            "agriculture_gdp_pct_bea",
        ],
    )

    shares = (
        df["industry_gdp_pct_bea"]
        + df["services_gdp_pct_bea"]
        + df["agriculture_gdp_pct_bea"]
    )

    if not shares.between(99.95, 100.05).all():
        raise ValueError(
            "BEA sector shares do not sum to approximately 100%."
        )

    df = df.rename(
        columns={
            "industry_gdp_pct_bea": "industry_gdp_pct",
            "services_gdp_pct_bea": "services_gdp_pct",
        }
    )

    return df[
        [
            "country",
            "year",
            "industry_gdp_pct",
            "services_gdp_pct",
        ]
    ]


def load_qcew() -> pd.DataFrame:
    """Establishment density aggregated from 50 states."""

    if not QCEW_PATH.exists():
        raise FileNotFoundError(QCEW_PATH)

    raw = pd.read_csv(QCEW_PATH)

    if "geographic_scope" not in raw.columns:
        raise ValueError(
            "QCEW file lacks geographic_scope."
        )

    if not raw["geographic_scope"].eq(
        "50_states_excluding_DC"
    ).all():
        raise ValueError(
            "Unexpected QCEW geographic scope."
        )

    df = load_source(
        QCEW_PATH,
        [
            "establishments",
            "population",
            "establishments_per_10k",
        ],
    )

    expected = (
        df["establishments"]
        / df["population"]
        * 10_000
    )

    if not (
        (expected - df["establishments_per_10k"]).abs()
        < 1e-6
    ).all():
        raise ValueError(
            "Establishment density calculation mismatch."
        )

    return df[
        ["country", "year", "establishments_per_10k"]
    ].rename(
        columns={
            "establishments_per_10k": "establishment_density"
        }
    )


def load_umd() -> pd.DataFrame:
    """National UMD incident rate per 100,000 inhabitants."""

    df = load_source(
        UMD_PATH,
        [
            "incident_count",
            "population",
            "incidents_per_100k",
        ],
    )

    expected = (
        df["incident_count"]
        / df["population"]
        * 100_000
    )

    if not (
        (expected - df["incidents_per_100k"]).abs()
        < 1e-6
    ).all():
        raise ValueError(
            "Incident rate calculation mismatch."
        )

    if int(df["incident_count"].sum()) != 7791:
        raise ValueError(
            "Unexpected national UMD incident count."
        )

    return df[
        ["country", "year", "incidents_per_100k"]
    ].rename(
        columns={
            "incidents_per_100k": "incident_rate"
        }
    )


def build_dataset() -> pd.DataFrame:
    """Merge all sources into a single national dataset."""

    print("=" * 70)
    print("BUILD USA NATIONAL FACTORS DATASET")
    print(f"Period: {START_YEAR}-{END_YEAR}")
    print("=" * 70)

    sources = [
        ("World Bank", load_wdi()),
        ("BEA", load_bea()),
        ("BLS QCEW", load_qcew()),
        ("UMD", load_umd()),
    ]

    result = pd.DataFrame({
        "country": ["USA"] * (END_YEAR - START_YEAR + 1),
        "year": list(range(START_YEAR, END_YEAR + 1)),
    })

    for name, source in sources:
        print(f"\nMerging {name}: {len(source)} rows")

        result = result.merge(
            source,
            on=["country", "year"],
            how="left",
            validate="one_to_one",
        )

    result = result[
        ["country", "year", *FEATURES]
    ].sort_values("year").reset_index(drop=True)

    if len(result) != 12:
        raise ValueError("Expected exactly 12 rows.")

    # Check all indicators except the two known digital gaps.
    non_digital = [
        col for col in FEATURES
        if col not in [
            "internet_users_pct",
            "fixed_broadband_per_100",
        ]
    ]

    if result[non_digital].isna().any().any():
        raise ValueError(
            "Unexpected missing values in non-digital indicators."
        )

    for column in ["internet_users_pct", "fixed_broadband_per_100"]:
        missing_years = result.loc[
            result[column].isna(), "year"
        ].tolist()

        if missing_years != [2025]:
            raise ValueError(
                f"Unexpected missing years for {column}: "
                f"{missing_years}"
            )

    # Percentage and density sanity checks.
    percent_columns = [
        "industry_gdp_pct",
        "services_gdp_pct",
        "unemployment_rate",
        "labor_force_participation",
        "internet_users_pct",
    ]

    for column in percent_columns:
        if not result[column].dropna().between(0, 100).all():
            raise ValueError(
                f"Invalid percentage values in {column}"
            )

    positive_columns = [
        "gdp_per_capita",
        "establishment_density",
        "fixed_broadband_per_100",
    ]

    for column in positive_columns:
        if not result[column].dropna().gt(0).all():
            raise ValueError(
                f"Invalid positive values in {column}"
            )

    if not result["incident_rate"].ge(0).all():
        raise ValueError("Negative incident rate detected.")

    # GDP growth may legitimately be negative.
    return result


def build_availability(df: pd.DataFrame) -> pd.DataFrame:
    """Create a per-indicator coverage report."""

    records = []

    for column in FEATURES:
        missing_years = df.loc[
            df[column].isna(), "year"
        ].tolist()

        records.append({
            "indicator": column,
            "available_years": int(df[column].notna().sum()),
            "total_years": len(df),
            "missing_years": ",".join(
                str(year) for year in missing_years
            ),
        })

    return pd.DataFrame(records)


def main():
    result = build_dataset()
    availability = build_availability(result)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    availability.to_csv(
        AVAILABILITY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n" + "=" * 70)
    print("FINAL DATASET")
    print("=" * 70)

    print(
        result.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )

    print("\n" + "=" * 70)
    print("INDICATOR AVAILABILITY")
    print("=" * 70)

    print(availability.to_string(index=False))

    complete = result.dropna(subset=FEATURES)

    print("\nComplete years for all 10 indicators:")
    print(complete["year"].tolist())

    print(f"\nRows: {len(result)}")
    print(f"Research variables: {len(FEATURES)}")

    print("\nFiles saved:")
    print(OUTPUT_PATH)
    print(AVAILABILITY_PATH)

    print("\nNOTE:")
    print("- Establishment density covers 50 states, excluding DC.")
    print("- Industry/services use BEA definitions.")
    print("- Digital indicators for 2025 remain missing.")
    print("- Incident rate refers to documented UMD incidents.")


if __name__ == "__main__":
    main()
