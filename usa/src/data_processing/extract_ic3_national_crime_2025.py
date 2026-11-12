"""Extract national crime-type data for 2025 from the FBI IC3 Annual PDF.

Run from the usa project root:
  pip install pymupdf
  python src/data_processing/extract_ic3_national_crime_2025.py

Input:  docs/reports/2025_IC3Report.pdf
Output: data/processed/ic3/annual/fbi_ic3_national_crime_2025.csv
Only uses the Annual Report; never accesses or merges State Reports.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'docs' / 'reports' / '2025_IC3Report.pdf'
OUTPUT = ROOT / 'data' / 'processed' / 'ic3' / 'annual' / 'fbi_ic3_national_crime_2025.csv'
YEAR = 2025

# Category spellings/order match the 2025 comparison tables, pp. 25–26.
CRIME_TYPES = [
    'Advanced Fee', 'BEC', 'Botnet', 'Charity', 'Confidence/Romance',
    'Credit Card/Check Fraud', 'Data Breach', 'Employment', 'Extortion',
    'Government Impersonation', 'Harassment/Stalking', 'Identity Theft',
    'Investment', 'IPR/Copyright and Counterfeit',
    'Lottery/Sweepstakes/Inheritance', 'Malware', 'Non-Payment/Non-Delivery',
    'Other', 'Overpayment', 'Personal Data Breach', 'Phishing/Spoofing',
    'Ransomware', 'Real Estate', 'SIM Swap', 'Tech/Customer Support',
    'Threats of Violence',
]
DESCRIPTORS = ['Cryptocurrency', 'AI Related', 'Crimes Against Children']


def first_2025_value(section: str, label: str, *, money: bool) -> int:
    # A category may wrap across PDF lines; normalize whitespace but retain
    # punctuation and use the category name as an exact boundary.
    normalized = section
    escaped = re.escape(label).replace(r"\ ", r"\s+")
    if money:
        pattern = rf'(?m)^[ \t]*{escaped}\s+\$([\d,]+)'
    else:
        pattern = rf'(?m)^[ \t]*{escaped}\s+([\d,]+)'
    hits = re.findall(pattern, normalized)
    if len(hits) != 1:
        raise ValueError(f'Expected one match for {label!r}; got {hits}')
    return int(hits[0].replace(',', ''))


def section_from_page(page_text: str, start: str, end: str) -> str:
    if start not in page_text or end not in page_text:
        raise ValueError(f'Missing table boundary {start!r} or {end!r}')
    return page_text.split(start, 1)[1].split(end, 1)[0]


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f'Put the 2025 FBI Annual Report at {SOURCE}')
    with fitz.open(SOURCE) as pdf:
        if len(pdf) < 26:
            raise ValueError('Unexpectedly short FBI Annual Report')
        count_text = section_from_page(pdf[24].get_text(), 'By Complaint Count', '* Crime Type')
        loss_text = section_from_page(pdf[25].get_text(), 'By Complaint Loss', '* Crime Type')
        desc_count_text = section_from_page(pdf[6].get_text(), 'Descriptors', 'Please see Appendix')
        desc_loss_text = section_from_page(pdf[7].get_text(), 'Descriptors', 'Please see Appendix')

    rows = []
    for category in CRIME_TYPES:
        rows.append({
            'year': YEAR, 'crime_type': category, 'category_kind': 'crime_type',
            'complaints': first_2025_value(count_text, category, money=False),
            'loss_usd': first_2025_value(loss_text, category, money=True),
            'count_source_page': 25, 'loss_source_page': 26,
            'source_report': '2025_IC3Report.pdf',
        })
    for category in DESCRIPTORS:
        rows.append({
            'year': YEAR, 'crime_type': category, 'category_kind': 'descriptor',
            'complaints': first_2025_value(desc_count_text, category, money=False),
            'loss_usd': first_2025_value(desc_loss_text, category, money=True),
            'count_source_page': 7, 'loss_source_page': 8,
            'source_report': '2025_IC3Report.pdf',
        })

    assert len(rows) == 29 and len({x['crime_type'] for x in rows}) == 29
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix('.csv.tmp')
    with tmp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(OUTPUT)
    print(f'[SUCCESS] {len(rows)} national crime categories saved to: {OUTPUT}')


if __name__ == '__main__':
    main()
