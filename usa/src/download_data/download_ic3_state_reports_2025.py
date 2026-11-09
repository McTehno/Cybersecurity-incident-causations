
from pathlib import Path
from collections import defaultdict
import csv
import re
import time

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT / "data" / "raw" / "ic3" / "2025" / "state_reports"
OUT_DIR = ROOT / "data" / "processed" / "ic3"

BASE_URL = (
    "https://www.ic3.gov/AnnualReport/Reports/"
    "2025State/StateReport.aspx?s={}"
)

YEAR = 2025

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; AcademicResearch/1.0)"
})

US_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas",
    "California", "Colorado", "Connecticut", "Delaware",
    "District of Columbia", "Florida", "Georgia", "Hawaii",
    "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
    "Kentucky", "Louisiana", "Maine", "Maryland",
    "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming"
}

TERRITORIES = {
    "American Samoa",
    "Guam",
    "Northern Mariana Islands",
    "Puerto Rico",
    "United States Minor Outlying Islands",
    "Virgin Islands, U.S.",
}

METRICS = {
    "Crime Type by Victim Count": "victim_count",
    "Crime Type by Victim Loss": "victim_loss_usd",
    "Crime Type by Subject Count": "subject_count",
    "Crime Type by Subject Loss": "subject_loss_usd",
}


# ============================================================
# HELPERS
# ============================================================

def clean(text):
    return re.sub(
        r"\s+", " ", text.replace("\xa0", " ")
    ).strip()


def parse_number(text):
    value = clean(text).replace("$", "").replace(",", "")

    if not re.fullmatch(r"\d+", value):
        raise ValueError(f"Invalid numeric value: {text!r}")

    return int(value)


def get_state(soup):
    if soup.title is None:
        raise ValueError("Missing HTML title")

    title = clean(soup.title.get_text(" ", strip=True))

    match = re.fullmatch(
        r"2025 (.+?) IC3 Annual Report",
        title,
        flags=re.IGNORECASE
    )

    if not match:
        raise ValueError(f"Unexpected page title: {title}")

    state = match.group(1)

    if state not in US_STATES | TERRITORIES:
        raise ValueError(f"Unknown state or territory: {state}")

    return state


def find_table(soup, caption_text):
    """
    Find a table using the exact <caption> text.
    """

    for table in soup.find_all("table"):
        caption = table.find("caption", recursive=False)

        if caption is None:
            continue

        title = clean(caption.get_text(" ", strip=True))

        if title.casefold() == caption_text.casefold():
            return table

    raise ValueError(
        f"Table not found: {caption_text}"
    )


# ============================================================
# CRIME TABLES
# ============================================================

def parse_crime_table(table):
    """
    HTML example:

    <tr>
        <td>BEC</td><td>301</td>
        <td>Malware</td><td>13</td>
    </tr>

    Returns:
        {
          ("BEC", "crime_type"): 301,
          ("Malware", "crime_type"): 13
        }
    """

    tbody = table.find("tbody", recursive=False)

    if tbody is None:
        raise ValueError("Crime table has no tbody")

    results = {}
    category_kind = "crime_type"

    for tr in tbody.find_all("tr", recursive=False):
        cells = tr.find_all(
            ["td", "th"], recursive=False
        )

        if not cells:
            continue

        # Handle rows such as <td colspan="4">Descriptors*</td>
        if len(cells) == 1:
            label = clean(
                cells[0].get_text(" ", strip=True)
            )

            if re.fullmatch(
                r"Descriptors?\*?", label, flags=re.I
            ):
                category_kind = "descriptor"

            continue

        # Normal data rows contain four cells (two pairs).
        if len(cells) != 4:
            raise ValueError(
                f"Unexpected crime table row: "
                f"{[c.get_text(' ', strip=True) for c in cells]}"
            )

        for index in (0, 2):
            name = clean(
                cells[index].get_text(" ", strip=True)
            )

            value_text = clean(
                cells[index + 1].get_text(" ", strip=True)
            )

            # Ignore empty spacer cells.
            if not name or not value_text:
                continue

            key = (name, category_kind)

            if key in results:
                raise ValueError(
                    f"Duplicate crime category: {key}"
                )

            results[key] = parse_number(value_text)

    return results


# ============================================================
# AGE TABLE
# ============================================================

def parse_age_table(table):
    """
    HTML example:

    <tr>
      <th scope="row">Under 20</th>
      <td>394</td>
      <td>$95,213</td>
    </tr>
    """

    tbody = table.find("tbody", recursive=False)

    if tbody is None:
        raise ValueError("Age table has no tbody")

    results = []

    for tr in tbody.find_all("tr", recursive=False):
        cells = tr.find_all(
            ["th", "td"], recursive=False
        )

        if len(cells) != 3:
            raise ValueError(
                "Expected 3 cells in age table row"
            )

        age_group = clean(
            cells[0].get_text(" ", strip=True)
        )

        count = parse_number(
            cells[1].get_text(" ", strip=True)
        )

        loss = parse_number(
            cells[2].get_text(" ", strip=True)
        )

        results.append({
            "age_group": age_group,
            "victim_count": count,
            "victim_loss_usd": loss
        })

    expected = {
        "Under 20", "20 - 29", "30 - 39",
        "40 - 49", "50 - 59", "Over 60"
    }

    found = {r["age_group"] for r in results}

    if found != expected or len(results) != 6:
        raise ValueError(
            f"Unexpected age groups: {sorted(found)}"
        )

    return results


# ============================================================
# EXTRACT ONE REPORT
# ============================================================

def extract_report(html, url):
    soup = BeautifulSoup(html, "html.parser")
    state = get_state(soup)

    if state in TERRITORIES:
        return state, [], []

    crime_data = defaultdict(dict)

    for caption, metric in METRICS.items():
        table = find_table(soup, caption)
        values = parse_crime_table(table)

        for key, value in values.items():
            crime_data[key][metric] = value

    required_metrics = set(METRICS.values())

    crime_rows = []

    for (category, kind), metrics in sorted(
        crime_data.items()
    ):
        if set(metrics) != required_metrics:
            raise ValueError(
                f"Missing metrics: {state}, {category}, "
                f"{required_metrics - set(metrics)}"
            )

        crime_rows.append({
            "state": state,
            "year": YEAR,
            "category": category,
            "category_kind": kind,
            **metrics,
            "source_url": url,
        })

    # Validate complete category structure.
    crime_types = [
        r for r in crime_rows
        if r["category_kind"] == "crime_type"
    ]

    descriptors = [
        r for r in crime_rows
        if r["category_kind"] == "descriptor"
    ]

    if len(crime_types) != 27:
        raise ValueError(
            f"{state}: expected 27 crime types, "
            f"found {len(crime_types)}"
        )

    if len(descriptors) != 4:
        raise ValueError(
            f"{state}: expected 4 descriptors, "
            f"found {len(descriptors)}"
        )

    age_table = find_table(
        soup, "Victims by Age Group"
    )

    age_rows = parse_age_table(age_table)

    for row in age_rows:
        row["state"] = state
        row["year"] = YEAR
        row["source_url"] = url

    return state, crime_rows, age_rows


# ============================================================
# SAVE CSV SAFELY
# ============================================================

def save_csv(path, rows, columns):
    tmp = path.with_name(path.name + ".tmp")

    with tmp.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(rows)

    tmp.replace(path)


# ============================================================
# MAIN
# ============================================================

def main():
    all_crimes = []
    all_ages = []

    collected_states = set()
    collected_territories = set()
    errors = []

    for report_id in range(1, 58):
        url = BASE_URL.format(report_id)

        cache_path = (
            RAW_DIR / f"report_{report_id:02d}.html"
        )

        try:
            if cache_path.exists():
                html = cache_path.read_text(
                    encoding="utf-8"
                )
            else:
                response = session.get(
                    url, timeout=40
                )
                response.raise_for_status()

                # Preserve the response encoding.
                response.encoding = (
                    response.apparent_encoding or "utf-8"
                )

                html = response.text

                cache_path.write_text(
                    html, encoding="utf-8"
                )

                time.sleep(0.5)

            state, crimes, ages = extract_report(
                html, url
            )

            if state in TERRITORIES:
                if state in collected_territories:
                    raise ValueError(
                        f"Duplicate territory: {state}"
                    )

                collected_territories.add(state)

                print(
                    f"[SKIP] s={report_id}: {state}"
                )
                continue

            if state in collected_states:
                raise ValueError(
                    f"Duplicate state: {state}"
                )

            collected_states.add(state)

            all_crimes.extend(crimes)
            all_ages.extend(ages)

            print(
                f"[OK] s={report_id}: {state} | "
                f"{len(crimes)} categories | "
                f"{len(ages)} age groups"
            )

        except Exception as exc:
            errors.append((report_id, str(exc)))

            print(
                f"[ERROR] s={report_id}: {exc}"
            )

    missing_states = US_STATES - collected_states
    missing_territories = TERRITORIES - collected_territories

    expected_crimes = 51 * 31
    expected_ages = 51 * 6

    if (
        errors
        or missing_states
        or missing_territories
        or len(all_crimes) != expected_crimes
        or len(all_ages) != expected_ages
    ):
        print("\n[FAILED] Incomplete extraction.")
        print(f"Errors: {errors}")
        print(f"Missing states: {sorted(missing_states)}")
        print(
            f"Missing territories: "
            f"{sorted(missing_territories)}"
        )
        print(
            f"Crime rows: {len(all_crimes)}/{expected_crimes}"
        )
        print(
            f"Age rows: {len(all_ages)}/{expected_ages}"
        )
        print("Final CSV files were not overwritten.")
        return

    # Sort for reproducibility.
    all_crimes.sort(
        key=lambda r: (
            r["state"],
            r["category_kind"],
            r["category"]
        )
    )

    all_ages.sort(
        key=lambda r: (
            r["state"],
            r["age_group"]
        )
    )

    save_csv(
        OUT_DIR / "fbi_ic3_state_crime_2025.csv",
        all_crimes,
        [
            "state", "year", "category",
            "category_kind", "victim_count",
            "victim_loss_usd", "subject_count",
            "subject_loss_usd", "source_url"
        ]
    )

    save_csv(
        OUT_DIR / "fbi_ic3_state_age_2025.csv",
        all_ages,
        [
            "state", "year", "age_group",
            "victim_count", "victim_loss_usd",
            "source_url"
        ]
    )

    print("\n[SUCCESS] Extraction complete.")
    print(f"States and DC: {len(collected_states)}")
    print(f"Territories skipped: {len(collected_territories)}")
    print(f"Crime rows: {len(all_crimes)}")
    print(f"Age rows: {len(all_ages)}")
    print(f"Files saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
