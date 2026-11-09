"""Create national cryptocurrency-nexus crime-type CSV from FBI IC3 Annual Report 2025.

Run from project root or elsewhere:
    python usa/src/data_processing/extract_ic3_national_crypto_2025.py

Source: docs/reports/2025_IC3Report.pdf, printed pages 54 (counts), 55 (losses).
The printed two-column PDF tables are transcribed below; the script verifies every
number against the selectable PDF text before exporting. No State Reports are used.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = ROOT / 'docs' / 'reports' / '2025_IC3Report.pdf'
OUTPUT = ROOT / 'data' / 'processed' / 'ic3' / 'annual' / 'fbi_ic3_national_crypto_2025.csv'

# Category, count (p.54), loss USD (p.55), kind
ROWS = [
    ('Investment', 61559, 7277868919, 'crime_type'),
    ('Extortion', 23797, 63195612, 'crime_type'),
    ('Tech/Customer Support', 17355, 1226298080, 'crime_type'),
    ('Personal Data Breach', 13486, 939398686, 'crime_type'),
    ('Employment', 10338, 288199807, 'crime_type'),
    ('Phishing/Spoofing', 7164, 111025191, 'crime_type'),
    ('Government Impersonation', 5955, 281146737, 'crime_type'),
    ('Confidence/Romance', 5925, 394787515, 'crime_type'),
    ('Non-Payment/Non-Delivery', 4761, 76196341, 'crime_type'),
    ('Other', 2332, 147700762, 'crime_type'),
    ('Advanced Fee', 2319, 67554554, 'crime_type'),
    ('Identity Theft', 1656, 16995129, 'crime_type'),
    ('Business Email Compromise', 1526, 83771329, 'crime_type'),
    ('Ransomware', 902, 17068810, 'crime_type'),
    ('Credit Card/Check Fraud', 901, 13423130, 'crime_type'),
    ('Data Breach', 866, 95861120, 'crime_type'),
    ('Lottery/Sweepstakes/Inheritance', 826, 29765165, 'crime_type'),
    ('Real Estate', 715, 25169423, 'crime_type'),
    ('Harassment/Stalking', 711, 4682411, 'crime_type'),
    ('Overpayment', 304, 6356416, 'crime_type'),
    ('Threats of Violence', 210, 7375785, 'crime_type'),
    ('Malware', 196, 15693486, 'crime_type'),
    ('IPR/Copyright and Counterfeit', 182, 4020461, 'crime_type'),
    ('SIM Swap', 121, 4405259, 'crime_type'),
    ('Charity', 65, 3221048, 'crime_type'),
    ('Botnet', 53, 60916, 'crime_type'),
    ('AI Related', 8712, 741639787, 'descriptor'),
    ('Crimes Against Children', 276, 596843, 'descriptor'),
]


def main() -> None:
    if not PDF_PATH.is_file():
        raise FileNotFoundError(f'Missing source PDF: {PDF_PATH}')

    doc = pymupdf.open(PDF_PATH)
    if len(doc) < 55:
        raise ValueError('Source PDF has fewer than 55 pages')
    count_text = doc[53].get_text(sort=True)
    loss_text = doc[54].get_text(sort=True)
    doc.close()

    if 'Crime Types with Cryptocurrency Nexus' not in count_text or 'Crime Types with Cryptocurrency Nexus' not in loss_text:
        raise ValueError('Wrong PDF or page numbering changed: expected crypto tables on pages 54–55')

    if len(ROWS) != 28 or len({name for name, *_ in ROWS}) != 28:
        raise ValueError('Expected 26 crime types + 2 descriptors, all unique')

    # Check amounts against the actual PDF pages, not against another dataset.
    # Word boundaries ensure, for instance, 65 does not match 165.
    for category, count, loss, kind in ROWS:
        for page_no, text, value in ((54, count_text, count), (55, loss_text, loss)):
            token = f'{value:,}'
            if not re.search(r'(?<!\d)' + re.escape(token) + r'(?!\d)', text):
                raise ValueError(f'{category}: value {token} missing on PDF page {page_no}; CSV not written')

    if sum(kind == 'crime_type' for _, _, _, kind in ROWS) != 26:
        raise ValueError('Expected 26 crime types')

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix('.csv.tmp')
    columns = ['year', 'crime_type', 'category_kind', 'complaints', 'loss_usd', 'source_page_counts', 'source_page_losses', 'source_report']
    with tmp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for name, count, loss, kind in ROWS:
            writer.writerow({
                'year': 2025, 'crime_type': name, 'category_kind': kind,
                'complaints': count, 'loss_usd': loss,
                'source_page_counts': 54, 'source_page_losses': 55,
                'source_report': '2025_IC3Report.pdf',
            })
    tmp.replace(OUTPUT)
    print(f'[SUCCESS] {len(ROWS)} crypto-nexus categories saved to: {OUTPUT}')
    print('[CHECK] 26 crime types + 2 overlapping descriptors; values checked against PDF pages 54-55')
    print('[NOTE] Source: Annual Report only. Descriptors must not be added to crime-type totals.')


if __name__ == '__main__':
    main()
