"""Extract 2025 FBI IC3 critical-infrastructure sector counts from Annual Report p.16.

The p.16 stacked chart is graphic-based: labels cannot reliably be associated
with the values by plain PDF text extraction. Values below are a verified,
manual transcription of the chart, not a reconstructed automated read.

From project root (Cybersecurity-incident-causations):
    python usa/src/data_processing/extract_ic3_national_sector_2025.py

Requires: pip install pymupdf
Input:  usa/docs/reports/2025_IC3Report.pdf
Output: usa/data/processed/ic3/annual/fbi_ic3_national_sector_2025.csv
"""
from __future__ import annotations
import csv
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / 'docs' / 'reports' / '2025_IC3Report.pdf'
OUTPUT = ROOT / 'data' / 'processed' / 'ic3' / 'annual' / 'fbi_ic3_national_sector_2025.csv'
PAGE = 16  # printed PDF page and 1-based page index

# sector, data_breach_count (green), ransomware_count (blue)
# Source: Annual Report 2025, p.16, "Cyber Threats to Critical Infrastructure".
SECTOR_COUNTS = [
    ('Dams', 1, 0),
    ('Nuclear', 1, 0),
    ('Emergency Services', 17, 24),
    ('Water/Wastewater', 11, 25),
    ('Defense Industrial Base', 9, 34),
    ('Communications', 28, 51),
    ('Energy', 31, 54),
    ('Chemical', 8, 59),
    ('Transportation', 82, 80),
    ('Food and Agriculture', 51, 89),
    ('Commercial Facilities', 84, 164),
    ('Information Technology', 199, 232),
    ('Government Facilities', 174, 233),
    ('Financial Services', 189, 258),
    ('Critical Manufacturing', 52, 355),
    ('Healthcare and Public Health', 182, 460),
]


def main() -> None:
    if not PDF.is_file():
        raise FileNotFoundError(f'Missing input PDF: {PDF}')

    with pymupdf.open(PDF) as doc:
        if len(doc) < PAGE:
            raise ValueError('PDF is missing printed page 16')
        page_text = doc[PAGE - 1].get_text()
        for anchor in ('Cyber Threats to Critical Infrastructure in 2025',
                       'Non-Critical Sector Ransomware Reporting'):
            if anchor not in page_text:
                raise ValueError(f'Unexpected PDF page 16: missing {anchor!r}')

    if len(SECTOR_COUNTS) != 16 or len({x[0] for x in SECTOR_COUNTS}) != 16:
        raise ValueError('Expected 16 unique critical infrastructure sectors')
    if not all(isinstance(a, int) and isinstance(b, int) and a >= 0 and b >= 0
               for _, a, b in SECTOR_COUNTS):
        raise ValueError('Invalid sector counts')

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {'year': 2025, 'sector': sector,
         'data_breach_complaints': breaches,
         'ransomware_complaints': ransomware,
         'source_report': '2025 IC3 Annual Report',
         'source_page': PAGE,
         'extraction_method': 'manually_transcribed_chart'}
        for sector, breaches, ransomware in SECTOR_COUNTS
    ]
    fields = list(rows[0])
    tmp = OUTPUT.with_name(OUTPUT.name + '.tmp')
    with tmp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(OUTPUT)
    print(f'[SUCCESS] {len(rows)} critical-infrastructure sectors saved to: {OUTPUT}')
    print(f'[CHECK] Data breach complaints: {sum(r["data_breach_complaints"] for r in rows):,}')
    print(f'[CHECK] Ransomware complaints: {sum(r["ransomware_complaints"] for r in rows):,}')
    print('[SOURCE] Annual Report 2025, page 16 (chart transcribed and checked visually)')
    print('[NOTE] Non-critical sector percentages are a different measurement and are not mixed in this dataset.')

if __name__ == '__main__':
    main()
