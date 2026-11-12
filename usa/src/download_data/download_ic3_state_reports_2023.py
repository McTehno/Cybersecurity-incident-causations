
"""Extract FBI IC3 2023 State Reports into state crime and age datasets."""

from __future__ import annotations

import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data/raw/ic3/2023/state_reports"
OUT_DIR = ROOT / "data/processed/ic3/state_reports"

BASE = "https://www.ic3.gov/AnnualReport/Reports/2023State/StateReport.aspx?s={}"
YEAR = 2023

STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming"
}

OTHER_AREAS = {
    "American Samoa",
    "Guam",
    "Northern Mariana Islands",
    "Puerto Rico",
    "United States Minor Outlying Islands",
    "Virgin Islands, U.S.",
}

CRIME_SECTIONS = [
    ("Crime Type by Victim Count", "victim_count"),
    ("Crime Type by Victim Loss", "victim_loss_usd"),
    ("Crime Type by Subject Count", "subject_count"),
    ("Crime Type by Subject Loss", "subject_loss_usd"),
]

AGE_SECTION = "Victims by Age Group"


def clean(value):
    return re.sub(
        r"\s+", " ", str(value).replace("\xa0", " ")
    ).strip()


def number(value):
    value = clean(value).replace("$", "").replace(",", "").replace(" ", "")

    if not re.fullmatch(r"\d+", value):
        raise ValueError(f"Invalid numeric value: {value!r}")

    return int(value)


def report_state(soup):
    title = (
        clean(soup.title.get_text(" ", strip=True))
        if soup.title else ""
    )

    match = re.search(
        r"\b2023\s+(.+?)\s+IC3\s+(?:Annual\s+)?Report\b",
        title,
        re.I,
    )

    if not match:
        raise ValueError(f"Unrecognized report title: {title!r}")

    state = match.group(1).strip()

    aliases = {
        "U.S. Virgin Islands": "Virgin Islands, U.S.",
        "US Virgin Islands": "Virgin Islands, U.S.",
        "Virgin Islands": "Virgin Islands, U.S.",
        "U.S. Minor Outlying Islands": "United States Minor Outlying Islands",
        "Northern Mariana": "Northern Mariana Islands",
    }

    state = aliases.get(state, state)

    if state not in STATES | OTHER_AREAS:
        raise ValueError(
            f"Unexpected state or territory: {state!r}; title={title!r}"
        )

    return state


def direct_cells(row):
    return [
        clean(cell.get_text(" ", strip=True))
        for cell in row.find_all(["td", "th"], recursive=False)
    ]


def parse_crime_table(table):
    rows = {}
    descriptor = False

    for tr in table.find_all("tr"):
        cells = direct_cells(tr)

        if not cells:
            continue

        if any(
            re.fullmatch(r"Descriptors?\s*\*?", value, re.I)
            for value in cells
        ):
            descriptor = True
            continue

        for i in range(0, len(cells) - 1, 2):
            category, raw_value = cells[i], cells[i + 1]

            if not category or category.lower() in {
                "crime type",
                "victim count",
                "subject count",
                "loss amount",
            }:
                continue

            if not re.fullmatch(r"\$?\s*[\d,]+", raw_value):
                continue

            key = (
                category,
                "descriptor" if descriptor else "crime_type",
            )

            value = number(raw_value)

            if key in rows and rows[key] != value:
                raise ValueError(
                    f"Conflicting values for category: {key}"
                )

            rows[key] = value

    return rows


def parse_age_table(table):
    rows = {}

    for tr in table.find_all("tr"):
        cells = direct_cells(tr)

        if len(cells) < 3:
            continue

        age_group = cells[0]

        if not re.search(
            r"under\s*20|over\s*60|60\+|"
            r"20\s*[-–]\s*29|30\s*[-–]\s*39|"
            r"40\s*[-–]\s*49|50\s*[-–]\s*59",
            age_group,
            re.I,
        ):
            continue

        try:
            victim_count = number(cells[1])
            victim_loss = number(cells[2])
        except ValueError:
            continue

        values = (victim_count, victim_loss)

        if age_group in rows and rows[age_group] != values:
            raise ValueError(
                f"Conflicting values for age group: {age_group}"
            )

        rows[age_group] = values

    return rows


def best_table(soup, heading, kind):
    """Find the correct table without crossing into another section."""

    heading_node = next(
        (
            node
            for node in soup.find_all(string=True)
            if clean(str(node)).casefold() == heading.casefold()
        ),
        None,
    )

    if heading_node is None:
        raise ValueError(f"Section heading not found: {heading}")

    expected_min = 6 if kind == "age" else 25
    parser = parse_age_table if kind == "age" else parse_crime_table

    section_names = [
        *(name for name, _ in CRIME_SECTIONS),
        AGE_SECTION,
    ]

    # First inspect tables containing the heading itself.
    node = heading_node.parent

    while node is not None:
        if getattr(node, "name", None) == "table":
            table_text = clean(
                node.get_text(" ", strip=True)
            ).casefold()

            contains_other_sections = any(
                name != heading and name.casefold() in table_text
                for name in section_names
            )

            if not contains_other_sections:
                try:
                    values = parser(node)

                    if len(values) >= expected_min:
                        return values
                except ValueError:
                    pass

        node = node.parent

    # Alternatively, inspect tables following the heading.
    # Stop as soon as another section begins.
    node = heading_node.parent
    inspected = 0

    for item in node.next_elements:
        if getattr(item, "name", None) == "table":
            inspected += 1

            if inspected > 12:
                break

            try:
                values = parser(item)
            except ValueError:
                continue

            if len(values) >= expected_min:
                return values

        elif isinstance(item, str):
            label = clean(item).casefold()

            if (
                label != heading.casefold()
                and label in {
                    name.casefold()
                    for name in section_names
                }
            ):
                break

    raise ValueError(
        f"No matching table (>={expected_min} rows): {heading}"
    )


def extract(html, url):
    soup = BeautifulSoup(html, "html.parser")
    state = report_state(soup)

    if state not in STATES:
        return state, [], []

    values_by_category = defaultdict(dict)

    for heading, metric in CRIME_SECTIONS:
        table_values = best_table(soup, heading, "crime")

        for (category, category_kind), value in table_values.items():
            values_by_category[
                (category, category_kind)
            ][metric] = value

    expected_metrics = {
        metric for _, metric in CRIME_SECTIONS
    }

    if len(values_by_category) < 25:
        raise ValueError(
            f"Only {len(values_by_category)} crime categories in {state}"
        )

    crimes = []

    for (category, category_kind), metrics in sorted(
        values_by_category.items()
    ):
        if set(metrics) != expected_metrics:
            raise ValueError(
                f"Missing crime metrics: {state}, {category}"
            )

        crimes.append({
            "state": state,
            "year": YEAR,
            "category": category,
            "category_kind": category_kind,
            **metrics,
            "source_url": url,
        })

    age_values = best_table(soup, AGE_SECTION, "age")

    ages = [
        {
            "state": state,
            "year": YEAR,
            "age_group": age_group,
            "victim_count": count,
            "victim_loss_usd": loss,
            "source_url": url,
        }
        for age_group, (count, loss) in sorted(age_values.items())
    ]

    if len(ages) != 6:
        raise ValueError(
            f"Expected 6 age groups, found {len(ages)} in {state}"
        )

    return state, crimes, ages


def atomic_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_name(path.name + ".tmp")

    with temp_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    temp_path.replace(path)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (educational research; IC3 public aggregate data)"
    )

    seen = set()
    all_crimes = []
    all_ages = []
    failures = []
    skipped = []

    for report_id in range(1, 58):
        url = BASE.format(report_id)
        cached = RAW_DIR / f"report_{report_id:02d}.html"

        try:
            if cached.exists():
                html = cached.read_text(encoding="utf-8")
            else:
                response = session.get(url, timeout=40)
                response.raise_for_status()

                response.encoding = (
                    response.apparent_encoding or "utf-8"
                )

                html = response.text
                cached.write_text(html, encoding="utf-8")

            state, crimes, ages = extract(html, url)

            if state not in STATES:
                skipped.append(state)
                print(
                    f"[SKIP] {report_id:02d} {state} (territory)"
                )
                continue

            if state in seen:
                raise ValueError(
                    f"Duplicate report for {state}"
                )

            seen.add(state)
            all_crimes.extend(crimes)
            all_ages.extend(ages)

            print(
                f"[OK] {report_id:02d} {state}: "
                f"{len(crimes)} categories, "
                f"{len(ages)} age groups"
            )

        except Exception as exc:
            failures.append((report_id, str(exc)))
            print(
                f"[ERROR] s={report_id}: {exc}",
                file=sys.stderr,
            )

        time.sleep(0.5)

    missing_states = STATES - seen

    if (
        failures
        or missing_states
        or len(seen) != 51
        or len(all_ages) != 51 * 6
    ):
        print(
            f"FAILED: {len(failures)} pages, "
            f"{len(missing_states)} missing states, "
            f"{len(all_ages)} age rows. "
            "CSVs were NOT modified.",
            file=sys.stderr,
        )

        if missing_states:
            print(
                "Missing states: "
                + ", ".join(sorted(missing_states)),
                file=sys.stderr,
            )

        return 1

    atomic_csv(
        OUT_DIR / "fbi_ic3_state_crime_2023.csv",
        all_crimes,
        [
            "state",
            "year",
            "category",
            "category_kind",
            "victim_count",
            "victim_loss_usd",
            "subject_count",
            "subject_loss_usd",
            "source_url",
        ],
    )

    atomic_csv(
        OUT_DIR / "fbi_ic3_state_age_2023.csv",
        all_ages,
        [
            "state",
            "year",
            "age_group",
            "victim_count",
            "victim_loss_usd",
            "source_url",
        ],
    )

    print(
        f"DONE: {len(seen)} states/DC, "
        f"{len(all_crimes)} crime rows, "
        f"{len(all_ages)} age rows; "
        f"skipped {len(skipped)} territories"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
