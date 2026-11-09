"""Extract 2025 US national IC3 crime type x age group table from ANNUAL PDF only.

Install: pip install pymupdf
Run from anywhere: python src/data_processing/extract_ic3_national_crime_age_2025.py
Input:  usa/docs/reports/2025_IC3Report.pdf
Output: usa/data/processed/ic3/annual/fbi_ic3_national_crime_age_2025.csv

The PDF itself visibly truncates three monetary figures on p.33. They are
left blank (not guessed); see 'quality_note' and the console warning.
For age 60+, uses the 2025 column of the Elder Fraud comparison on pp.47-48.
The report's pp.45-46 contain inconsistent values for a few entries;
this script chooses one clearly documented set rather than mixing sources.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = ROOT / 'docs' / 'reports' / '2025_IC3Report.pdf'
CSV_PATH = ROOT / 'data' / 'processed' / 'ic3' / 'annual' / 'fbi_ic3_national_crime_age_2025.csv'

# Ordered exactly as the 26 crime types printed on pp.32-33 and pp.47-48.
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
AGE_GROUPS = ['Under 20', '20 - 29', '30 - 39', '40 - 49', '50 - 59', '60+']


def collect_numeric_rows(page, y_min, y_max, x_min, x_max, pattern, *, max_gap=2.0):
    """Group table cells by their baseline y coordinate; sort each row left-to-right."""
    matched = []
    for x0, y0, x1, y1, value, *_ in page.get_text('words'):
        if y_min <= y0 <= y_max and x_min <= x0 < x_max and re.fullmatch(pattern, value):
            matched.append((y0, x0, value))
    matched.sort()
    groups = []
    for y, x, val in matched:
        if not groups or y - groups[-1][0][0] > max_gap:
            groups.append([])
        groups[-1].append((y, x, val))
    return [[v for _, _, v in sorted(group, key=lambda item: item[1])] for group in groups]


def strict_number(text, *, money=False):
    expr = r'\$?\d{1,3}(?:,\d{3})*' if money else r'\d{1,3}(?:,\d{3})*'
    if not re.fullmatch(expr, text):
        return None
    return int(text.replace('$', '').replace(',', ''))


def five_age_table(page, *, money):
    rows = collect_numeric_rows(
        page,
        y_min=79 if money else 115,
        y_max=690 if money else 650,
        x_min=140 if money else 230,
        x_max=570,
        pattern=r'\$[\d,]+' if money else r'[\d,]+',
    )
    if len(rows) != 26 or any(len(r) != 5 for r in rows):
        raise ValueError('Expected 26 rows of 5 values, got ' + str([len(r) for r in rows]))
    return rows


def over60_table(page, *, money):
    # p47 count and p48 loss: numeric 2025 column, before the 2024 column.
    rows = collect_numeric_rows(
        page,
        y_min=148,
        y_max=620,
        x_min=280,
        x_max=375 if money else 390,
        pattern=r'\$[\d,]+' if money else r'[\d,]+',
    )
    if len(rows) != 26 or any(len(r) != 1 for r in rows):
        raise ValueError('Expected 26 values in 2025 column, got ' + str([len(r) for r in rows]))
    return [r[0] for r in rows]


def main():
    if not PDF_PATH.is_file():
        raise FileNotFoundError(f'Missing source PDF: {PDF_PATH}')
    with pymupdf.open(PDF_PATH) as pdf:
        if len(pdf) < 48:
            raise ValueError('Source PDF is too short')
        if 'Crime Types by Age Groups' not in pdf[31].get_text():
            raise ValueError('Unexpected source table on p32')
        if 'Losses' not in pdf[32].get_text():
            raise ValueError('Unexpected source table on p33')
        if 'Three Year Comparison' not in pdf[46].get_text():
            raise ValueError('Unexpected source table on p47')
        counts = five_age_table(pdf[31], money=False)
        losses = five_age_table(pdf[32], money=True)
        counts60 = over60_table(pdf[46], money=False)
        losses60 = over60_table(pdf[47], money=True)

    # Defend against accidental row-order changes or extraction drift.
    assert counts[0] == ['288', '991', '1,170', '1,120', '1,169']
    assert counts[8] == ['13,110', '26,963', '15,866', '11,279', '7,841']
    assert losses[0] == ['$327,823', '$7,081,874', '$13,311,458', '$18,801,337', '$25,811,979']
    assert counts60[0] == '2,020' and counts60[-1] == '348'
    assert losses60[0] == '$65,877,660' and losses60[-1] == '$244,840'

    output_rows = []
    unclear = []
    for i, crime in enumerate(CRIME_TYPES):
        for j, age in enumerate(AGE_GROUPS):
            if j < 5:
                count_raw = counts[i][j]
                loss_raw = losses[i][j]
                source_count, source_loss = 32, 33
            else:
                count_raw, loss_raw = counts60[i], losses60[i]
                source_count, source_loss = 47, 48
            count = strict_number(count_raw)
            loss = strict_number(loss_raw, money=True)
            if count is None:
                raise ValueError(f'Invalid count: {crime} / {age}: {count_raw}')
            note = ''
            if loss is None:
                note = f'Truncated/invalid monetary amount in source PDF: {loss_raw}; not imputed'
                unclear.append((crime, age, loss_raw))
            if j == 5:
                note = (note + '; ' if note else '') + '60+ data from Annual Report 2025 three-year comparison (2025 column), pp.47-48'
            output_rows.append({
                'year': 2025,
                'crime_type': crime,
                'age_group': age,
                'complaints': count,
                'loss_usd': '' if loss is None else loss,
                'count_source_page': source_count,
                'loss_source_page': source_loss,
                'quality_note': note,
                'source_report': '2025_IC3Report.pdf',
            })

    if len(output_rows) != 156 or len({(r['crime_type'], r['age_group']) for r in output_rows}) != 156:
        raise ValueError('Missing or duplicate keys')

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = CSV_PATH.with_suffix('.csv.tmp')
    with temp.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)
    temp.replace(CSV_PATH)
    print(f'[SUCCESS] {len(output_rows)} crime × age records saved to: {CSV_PATH}')
    print(f'[QUALITY] {len(unclear)} truncated monetary figures left blank (not zero):')
    for crime, age, raw in unclear:
        print(f'  - {crime} / {age}: {raw}')
    print('[NOTE] 60+ figures taken from Annual Report pp.47-48 (2025 column).')


if __name__ == '__main__':
    main()
