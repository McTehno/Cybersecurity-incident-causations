"""
Calculate US establishment density from BLS QCEW data
for the 50 states, 2014-2025.

Run from usa/:
    python src/data_processing/qcew_national_establishment_density.py
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

QCEW_PATH = (
    ROOT / "data/processed/economic/bls_qcew"
    / "qcew_state_2014_2025.csv"
)

ECONOMIC_PATH = (
    ROOT / "data/processed/economic/combined"
    / "usa_state_economic_factors_2014_2025.csv"
)

OUTPUT_PATH = (
    ROOT / "data/processed/economic/bls_qcew"
    / "usa_national_establishment_density_2014_2025.csv"
)

YEARS = list(range(2014, 2026))


def main():
    qcew = pd.read_csv(QCEW_PATH)
    economic = pd.read_csv(ECONOMIC_PATH)

    keys = ["state_fips", "year"]

    # Check unique state-year records.
    for name, df in [
        ("QCEW", qcew),
        ("Economic", economic),
    ]:
        if df.duplicated(keys).any():
            raise ValueError(
                f"Duplicate state-year records in {name}"
            )

    # Combine establishments and population.
    df = qcew[
        keys + ["establishments"]
    ].merge(
        economic[
            keys + ["population", "qcew_establishments"]
        ],
        on=keys,
        how="inner",
        validate="one_to_one",
    )

    if len(df) != 600:
        raise ValueError(
            f"Expected 600 state-year records, got {len(df)}"
        )

    if df[["establishments", "population"]].isna().any().any():
        raise ValueError("Missing establishments or population")

    if (df["population"] <= 0).any():
        raise ValueError("Population must be positive")

    if not (
        df["establishments"] == df["qcew_establishments"]
    ).all():
        raise ValueError(
            "QCEW establishment counts do not match"
        )

    # Validate coverage.
    years = sorted(df["year"].unique().tolist())
    if years != YEARS:
        raise ValueError(f"Unexpected years: {years}")

    counts = df.groupby("year")["state_fips"].nunique()
    if not counts.eq(50).all():
        raise ValueError(
            "Expected exactly 50 states for every year"
        )

    # Aggregate numerator and denominator separately.
    result = (
        df.groupby("year", as_index=False)
        .agg(
            establishments=("establishments", "sum"),
            population=("population", "sum"),
        )
    )

    result["country"] = "USA"

    result["establishments_per_10k"] = (
        result["establishments"]
        / result["population"]
        * 10_000
    )

    result["geographic_scope"] = "50_states_excluding_DC"

    result = result[
        [
            "country",
            "year",
            "establishments",
            "population",
            "establishments_per_10k",
            "geographic_scope",
        ]
    ]

    OUTPUT_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )

    result.to_csv(OUTPUT_PATH, index=False)

    print("\nUS ESTABLISHMENT DENSITY (50 STATES)")
    print("=" * 75)
    print(
        result.to_string(
            index=False,
            float_format=lambda x: f"{x:,.3f}",
        )
    )

    print("\nMissing values:")
    print(result.isna().sum().to_string())

    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
