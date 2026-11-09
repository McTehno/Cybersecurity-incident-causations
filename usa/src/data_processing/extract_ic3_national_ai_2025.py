"""Extract AI-related complaint counts and losses from FBI IC3 Annual Report 2025.

Run from any directory:
    python usa/src/data_processing/extract_ic3_national_ai_2025.py

Input:  usa/docs/reports/2025_IC3Report.pdf
Output: usa/data/processed/ic3/annual/fbi_ic3_national_ai_2025.csv

One row = one national crime type or descriptor (NOT a state).
The descriptor counts can overlap with crime types; do not sum them together.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = ROOT / 'docs' / 'reports' / '2025_IC3Report.pdf'
OUTPUT_PATH = ROOT / 'data' / 'processed' / 'ic3' / 'annual' / 'fbi_ic3_national_ai_2025.csv'

PAGE_COUNT = 41  # PDF page number (1-indexed)
PAGE_LOSS = 42
EXPECTED_CRIME_TYPES = 26
EXPECTED_DESCRIPTORS = 2


def extract_column_pairs(page: pymupdf.Page, value_kind: str) -> dict[tuple[str, str], int]:
    """Read text blocks in both columns of the PDF table; wrapped labels are joined."""
    result = {}
    in_descriptor_section = False

    # Document's text blocks here contain complete (label, value) pairs.
    blocks = sorted(page.get_text('blocks'), key=lambda b: (b[1], b[0]))
    for block in blocks:
        x0, y0, x1, y1, text, *_ = block
        if y0 < 120 or y0 >= 530:
            continue
        if not (70 <= x0 <= 540):
            continue

        pending = []
        for raw_line in text.splitlines():
            line = ' '.join(raw_line.strip().split())
            if not line:
                continue
            if line.lower().startswith('descriptors'):
                in_descriptor_section = True
                continue
            if line in ('Crime Type', 'Complaint', 'Loss'):
                continue

            # A PDF line can contain both column entries, e.g.
            # "Investment $632,041,188 Extortion $2,940,642".
            # Split at EVERY amount, not only at the last amount.
            cursor = 0
            for match in re.finditer(r'\$?\d[\d,]*', line):
                leading = line[cursor:match.start()].strip()
                if leading:
                    pending.append(leading)
                if not pending:
                    raise ValueError(
                        f'Value without category on p.{page.number + 1}: {line!r}'
                    )
                label = ' '.join(pending)
                label = re.sub(r'\s*/\s*', '/', label)
                label = re.sub(r'(?<=/)\s+', '', label)
                label = re.sub(r'-\s+', '-', label)
                val = int(match.group().replace('$', '').replace(',', ''))
                kind = 'descriptor' if in_descriptor_section else 'crime_type'
                key = (label, kind)
                if key in result:
                    raise ValueError(f'Duplicate category on p.{page.number + 1}: {key}')
                result[key] = val
                pending.clear()
                cursor = match.end()
            trailing = line[cursor:].strip()
            if trailing:
                pending.append(trailing)

        if pending:
            raise ValueError(f'Unpaired label in PDF block p.{page.number + 1}: {pending}')

    return result


def main():
    if not PDF_PATH.is_file():
        raise FileNotFoundError(f'PDF not found: {PDF_PATH}')

    with pymupdf.open(PDF_PATH) as pdf:
        counts = extract_column_pairs(pdf[PAGE_COUNT - 1], 'count')
        losses = extract_column_pairs(pdf[PAGE_LOSS - 1], 'loss')

    # On the first page the text extractor may order blocks in a slightly different
    # way from the visual layout; all descriptors occur below the separator.
    if counts.keys() != losses.keys():
        only_counts = counts.keys() - losses.keys()
        only_losses = losses.keys() - counts.keys()
        raise ValueError(f'Category mismatch: count-only={only_counts}, loss-only={only_losses}')

    n_crimes = sum(kind == 'crime_type' for _, kind in counts)
    n_descriptors = sum(kind == 'descriptor' for _, kind in counts)
    if (n_crimes, n_descriptors) != (EXPECTED_CRIME_TYPES, EXPECTED_DESCRIPTORS):
        raise ValueError(
            f'Unexpected categories: {n_crimes} crime types, {n_descriptors} descriptors '
            f'(expected {EXPECTED_CRIME_TYPES} and {EXPECTED_DESCRIPTORS})'
        )

    records = [
        {
            'year': 2025,
            'crime_type': category,
            'category_kind': kind,
            'complaints': counts[(category, kind)],
            'loss_usd': losses[(category, kind)],
            'source_report': 'FBI IC3 Annual Report 2025',
            'source_page_complaints': PAGE_COUNT,
            'source_page_loss': PAGE_LOSS,
        }
        for category, kind in sorted(counts)
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = OUTPUT_PATH.with_suffix('.csv.tmp')
    with temp_path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    temp_path.replace(OUTPUT_PATH)

    print(f'[SUCCESS] {len(records)} AI-related categories saved to: {OUTPUT_PATH}')
    print(f'[CHECK] {n_crimes} crime types + {n_descriptors} overlapping descriptors')
    print(f'[SOURCE] Annual Report 2025, pages {PAGE_COUNT}-{PAGE_LOSS}')


if __name__ == '__main__':
    main()
