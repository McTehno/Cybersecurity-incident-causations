"""Extract comparable 2023 FBI IC3 annual tables (states, crimes, sectors).

Usage from repository root:
    python usa/src/data_processing/extract_ic3_annual_2023.py
The file is expected at usa/docs/reports/2023_IC3Report.pdf.
"""
from __future__ import annotations
import re
from pathlib import Path
import pymupdf
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / 'docs/reports/2023_IC3Report.pdf'
OUT = ROOT / 'data/processed/ic3/annual'
YEAR = 2023
STATES = '''Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|District of Columbia|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming'''.split('|')
STATE_SET = set(STATES)

CRIMES = '''Phishing/Spoofing|Personal Data Breach|Non-payment/Non-Delivery|Extortion|Investment|Tech Support|BEC|Identity Theft|Confidence/Romance|Employment|Government Impersonation|Credit Card/Check Fraud|Harassment/Stalking|Real Estate|Other|Advanced Fee|Lottery/Sweepstakes/Inheritance|Overpayment|Data Breach|Ransomware|Crimes Against Children|Threats of Violence|IPR/Copyright and Counterfeit|SIM Swap|Malware|Botnet|Cryptocurrency|Cryptocurrency Wallet'''.split('|')
CRIME_SET = set(CRIMES)
DESCRIPTORS = {'Cryptocurrency', 'Cryptocurrency Wallet'}


def clean_num(raw: str) -> int:
    v = raw.replace(',', '').replace('$', '').replace(' ', '').strip()
    if not re.fullmatch(r'\d+', v):
        raise ValueError(f'Invalid numeric text: {raw!r}')
    return int(v)


def state_values(page: pymupdf.Page, kind: str) -> dict[str, int | float]:
    lines = [x.strip() for x in page.get_text(sort=False).splitlines() if x.strip()]
    result = {}
    for i, item in enumerate(lines[:-1]):
        # On PDF page 25 the right-hand table prints rank and state on one line.
        state = re.sub(r'^\d+\s+', '', item)
        if state not in STATE_SET:
            continue
        raw = lines[i+1].strip()
        if kind == 'rate':
            match = re.fullmatch(r'\$?\s*([\d,]+(?:\.\d+)?)', raw)
            if not match:
                continue
            value = float(match.group(1).replace(',', ''))
        else:
            if not re.fullmatch(r'\$?\s*[\d,]+', raw):
                continue
            value = clean_num(raw)
        if state in result and result[state] != value:
            raise ValueError(f'Conflicting state values on page {page.number+1}: {state}')
        result[state] = value
    if set(result) != STATE_SET:
        raise ValueError(f'Page {page.number+1}: expected 51 states, got {len(result)}; missing {sorted(STATE_SET-set(result))}')
    return result


def crime_values(page: pymupdf.Page) -> dict[str, int]:
    lines = [x.strip() for x in page.get_text(sort=False).splitlines() if x.strip()]
    result = {}
    for i, line in enumerate(lines[:-1]):
        name = line.rstrip('*').strip()
        if name not in CRIME_SET:
            continue
        candidate = lines[i+1]
        if not re.fullmatch(r'\$?\s*[\d,]+', candidate):
            continue
        value = clean_num(candidate)
        if name in result and result[name] != value:
            raise ValueError(f'Conflicting crime {name} on p.{page.number+1}')
        result[name] = value
    if set(result) != CRIME_SET:
        raise ValueError(f'Page {page.number+1}: crime categories {len(result)}/{len(CRIME_SET)}; missing {sorted(CRIME_SET-set(result))}')
    return result


def sector_values(page: pymupdf.Page) -> dict[str, int]:
    text = page.get_text()
    # The sector graphic is accompanied by an accessibility text extract and distinct labels.
    sectors = [
        'Healthcare and Public Health', 'Critical Manufacturing',
        'Government Facilities', 'Information Technology',
        'Financial Services', 'Commercial Facilities',
        'Food and Agriculture', 'Transportation',
        'Communications', 'Energy', 'Chemical',
        'Emergency Services', 'Water and Wastewater Systems',
        'Defense Industrial Base',
    ]
    expected = [249,218,156,137,122,87,75,44,32,30,24,9,8,2]
    # Confirm every manually transcribed graph value against the PDF's text layer.
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    for name, count in zip(sectors, expected):
        if name not in text:
            raise ValueError(f'Sector label missing from p.13: {name}')
        if str(count) not in lines:
            raise ValueError(f'Sector count not found on p.13: {name}, {count}')
    if sum(expected) != 1193:
        raise ValueError('Critical-sector ransomware totals do not match 1,193.')
    return dict(zip(sectors, expected))


def main():
    if not PDF.is_file():
        raise FileNotFoundError(f'Annual PDF not found: {PDF}')
    doc = pymupdf.open(PDF)
    if len(doc) != 34:
        raise ValueError(f'Unexpected PDF length: {len(doc)}')
    # The page indices are zero-based; source_page below is one-based.
    pages = {
        'complaints': 23,
        'loss_usd': 24,
        'subject_count': 25,
        'subject_loss_usd': 26,
        'complaints_per_100k': 27,
        'loss_per_100k_usd': 28,
    }
    mapped = {
        name: state_values(doc[idx], 'rate' if 'per_100k' in name else 'integer')
        for name, idx in pages.items()
    }
    states = pd.DataFrame([
        {'state': name, 'year': YEAR, **{field: vals[name] for field, vals in mapped.items()}}
        for name in STATES
    ])
    assert len(states) == 51
    assert states.loc[states.state.eq('California'), 'complaints'].iloc[0] == 77271
    assert states.loc[states.state.eq('District of Columbia'), 'complaints_per_100k'].iloc[0] == 555.1

    counts = crime_values(doc[19])
    losses = crime_values(doc[20])
    crimes = pd.DataFrame([
        {'year': YEAR, 'crime_type': name,
         'category_kind': 'descriptor' if name in DESCRIPTORS else 'crime_type',
         'complaints': counts[name], 'loss_usd': losses[name],
         'count_source_page': 20, 'loss_source_page': 21,
         'source_report': PDF.name}
        for name in sorted(CRIMES)
    ])
    assert len(crimes) == 28
    assert crimes.loc[crimes.crime_type.eq('Investment'), 'loss_usd'].iloc[0] == 4570275683

    sector_map = sector_values(doc[12])
    sectors = pd.DataFrame([
        {'year': YEAR, 'sector': sector,
         'data_breach_complaints': pd.NA,  # Not reported by sector in 2023 annual report
         'ransomware_complaints': count,
         'source_report': '2023 IC3 Annual Report', 'source_page': 13,
         'extraction_method': 'manually_transcribed_chart_verified_text'}
        for sector, count in sector_map.items()
    ])

    OUT.mkdir(parents=True, exist_ok=True)
    destinations = [
        ('fbi_ic3_state_2023.csv', states),
        ('fbi_ic3_national_crime_2023.csv', crimes),
        ('fbi_ic3_national_sector_2023.csv', sectors),
    ]
    for name, frame in destinations:
        frame.to_csv(OUT/name, index=False, encoding='utf-8-sig')
        print(f'[SUCCESS] {name}: {len(frame)} records')
    print('[CHECK] 51 states/DC, 26 crime types + 2 descriptors, 14 ransomware sectors (total 1,193).')
    print('[NOTE] 2023 has no state-level Under-17, Over-60 or crypto columns in this PDF.')
    print('[NOTE] Sector data breach counts are unavailable, not zero.')
    print(f'[OUTPUT] {OUT}')


if __name__ == '__main__':
    main()
