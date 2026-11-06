"""Extract 2025 FBI IC3 state-level tables from the supplied annual PDF.
Usage from project root: python src/data_processing/extract_ic3_2025.py
Requires pdftotext (Poppler). Optional args: PDF_PATH OUTPUT_CSV_PATH.
"""
import csv, re, subprocess, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2] if Path(__file__).parent.name == 'data_processing' else Path(__file__).resolve().parent
PDF = Path(sys.argv[1]) if len(sys.argv)>1 else PROJECT_ROOT / 'docs' / 'reports' / '2025_IC3Report.pdf'
OUT = Path(sys.argv[2]) if len(sys.argv)>2 else PROJECT_ROOT / 'data' / 'processed' / 'ic3' / 'fbi_ic3_state_2025.csv'
STATES = '''Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|District of Columbia'''.split('|')
STATE_RX = re.compile(r'(?<![A-Za-z])('+'|'.join(re.escape(s) for s in sorted(STATES,key=len,reverse=True))+r')(?![A-Za-z])')
NUM_RX = re.compile(r'\$?\d[\d,]*(?:\.\d+)?')
COLUMNS = {
 28: ('complaints',int),29:('loss_usd',int),
 30: ('complaints_per_100k',float),31:('loss_per_100k_usd',int),
 37: ('under17_complaints',int),38:('under17_loss_usd',int),
 49: ('over60_complaints',int),50:('over60_loss_usd',int),
 56: ('crypto_complaints',int),57:('crypto_loss_usd',int)
}

def parse_page(page_no, cast):
    txt=subprocess.check_output(['pdftotext','-f',str(page_no),'-l',str(page_no),'-layout',str(PDF),'-'],text=True)
    result={}
    for line in txt.splitlines():
        # The two printed ranking tables occupy separate halves of the page.
        # 58 is a separator before the right-hand rank in every 2025 table.
        for half in (line[:58],line[58:]):
            m=STATE_RX.search(half)
            if not m:continue
            tail=half[m.end():]
            numbers=NUM_RX.findall(tail)
            if not numbers:continue
            raw=numbers[-1].replace('$','').replace(',','')
            if '.' in raw and cast is int:continue
            result[m.group(1)]=cast(raw)
    return result

rows={s:{'state':s,'year':2025} for s in STATES}
for pg,(key,cast) in COLUMNS.items():
    values=parse_page(pg,cast)
    # Page 50 California loss is split across text lines in the PDF: $1,403,975,91 + 1
    # The rendered PDF shows $1,403,975,911.
    if pg==50:
        values['California']=1_403_975_911
        values['Florida']=709_823_172
    if pg==37: values['Oklahoma']=160  # displaced count in source PDF table
    missing=set(STATES)-set(values)
    if missing: print(f'Page {pg} {key}: missing {sorted(missing)}',file=sys.stderr)
    for s,v in values.items():
        if s in rows:rows[s][key]=v
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open('w',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['state','year']+[v[0] for v in COLUMNS.values()])
    writer.writeheader();writer.writerows(rows.values())
print('Written',OUT,'rows',len(rows),'metrics',len(COLUMNS))
for name in ['California','Texas','Florida','Alabama','District of Columbia','Wyoming']:
    print(name, rows[name])
