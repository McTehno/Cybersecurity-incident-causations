import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import re
from collections import Counter
import numpy as np
import pandas as pd
from harmonize_helpers import (
    fix_text_all,
    extract_bundesland,
    classify_sector_by_text,
    resolve_eurepoc_receiver_row_sector,
)

# Helper to recover German victim name from EuRepoC global 'name' / 'description' when receiver table says 'Not available'
EUREPOC_NAME_EXTRACTION_PATTERNS = [
    r"(?:German\s+(?:pharmaceutical\s+wholesaler|thermotechnology\s+manufacturer|blockchain\s+identity\s+platform|Software\s+company|IT\s+Service\s+Provider|auto\s+spare\s+parts\s+manufacturer|creative\s+author's\s+society|party)\s+)([A-Z][A-Za-z0-9\-&\s]{1,35}?)(?:\s+(?:on|in|had|was|becomes|is)\b|$)",
    r'Pharmaceutical Company\s+"([^"]+)"',
    r"attacked German\s+([A-Za-z0-9\-&\s]{2,35}?)\s+with\b",
    r"targeted German\s+([A-Za-z0-9\-&\s]{2,35}?)\s+(?:in|on)\b",
    r"systems of\s+(German Fertility Center in Bielefeld)",
    r"account of German\s+(Berlinale)\s+festival",
    r"website of the\s+(Federal Election Commissioner)",
    r"server used by Germany's\s+(Federal Police)",
    r"hack into\s+(German Federal Police and Customs)",
    r"vs\.\s+(GEMA|Pirate Party)",
]


def recover_eurepoc_victim(inc_row, rec_names_list):
    """Recover the victim name for a German incident from receiver records or description."""
    if rec_names_list:
        return "; ".join(rec_names_list)
    # Check receiver_name in eurepoc_global paired with receiver_country
    r_names = [fix_text_all(x) for x in str(inc_row.get("receiver_name", "")).split(";")]
    r_countries = [fix_text_all(x) for x in str(inc_row.get("receiver_country", "")).split(";")]
    if len(r_names) == len(r_countries):
        de_specific = [n for n, c in zip(r_names, r_countries) if "germany" in c.lower() and n not in ("", "Not available", "Unknown", "nan")]
        if de_specific:
            return "; ".join(dict.fromkeys(de_specific))
    elif len(r_countries) == 1 and "germany" in r_countries[0].lower():
        valid_n = [n for n in r_names if n not in ("", "Not available", "Unknown", "nan")]
        if valid_n:
            return "; ".join(dict.fromkeys(valid_n))

    # Only extract from headline/description if Germany is the primary/sole target country
    non_empty_countries = [c for c in r_countries if c not in ("", "Not available", "Unknown", "nan")]
    if len(set(non_empty_countries)) <= 1:
        text_blob = f"{fix_text_all(inc_row.get('name', ''))} | {fix_text_all(inc_row.get('description', ''))}"
        for pat in EUREPOC_NAME_EXTRACTION_PATTERNS:
            m = re.search(pat, text_blob, flags=re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if cand.lower() == "pirate party":
                    return "Piratenpartei Deutschland"
                return cand
        if '"Bundeshack"' in text_blob:
            return "German Federal Government (IVBB)"
    return "Unknown"


def parse_eurepoc_date(inc_row):
    """Parse EuRepoC start_date and tag date precision level."""
    raw_d = str(inc_row.get("start_date", "")).strip()
    if raw_d and raw_d not in ("Not available", "Unknown", "nan"):
        dt = pd.to_datetime(raw_d, dayfirst=True, format="mixed", errors="coerce")
        if pd.notna(dt):
            # Fix known EuRepoC start_date typo on id=3576 ('01.06.2023' when headline & added_to_db say June 2024)
            if int(inc_row["incident_id"]) == 3576:
                dt = pd.Timestamp("2024-06-01")
            if raw_d.startswith("01.01."):
                return dt, "year_only"
            if raw_d.startswith("01."):
                return dt, "month_only"
            return dt, "exact_day"
    # Fallback for the 3 'Not available' German incidents: extract Month YYYY from headline/description, else added_to_db
    blob = f"{inc_row.get('name', '')} {inc_row.get('description', '')}"
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b", blob, re.I)
    if m:
        dt = pd.to_datetime(f"1 {m.group(1)} {m.group(2)}")
        return dt, "month_only"
    added = pd.to_datetime(inc_row.get("added_to_db"), errors="coerce")
    return added, "reported_fallback"


def standardize_actor_type(raw_actor: str) -> str:
    """Standardize EuRepoC initiator/actor taxonomy into canonical 4 classes."""
    t = fix_text_all(raw_actor).lower()
    if not t or t in {"undetermined", "unknown", "not attributed", "not available"}:
        return "Unknown"
    if "criminal" in t:
        return "Criminal"
    if "hacktiv" in t:
        return "Hacktivist"
    t_no_nonstate = re.sub(r"non[- ]state[- ]?(group|actor)?s?", "", t)
    if "state-affiliation suggested" in t or re.search(r"\b(nation[- ]state|state[- ]affiliated|state)\b", t_no_nonstate) or re.search(r"\bapt\s*\d*\b", t):
        return "State-Sponsored"
    if any(k in t for k in ["non-state", "individual hacker", "terrorist", "hobbyist", "private technology"]):
        return "Other"
    return "Unknown"


def run_eurepoc_test():
    """Isolated test harness for validating EuRepoC entity recovery."""
    RAW = SCRIPT_DIR.parent / "data" / "raw" if (SCRIPT_DIR.parent / "data" / "raw").is_dir() else (SCRIPT_DIR / "raw" if (SCRIPT_DIR / "raw").is_dir() else SCRIPT_DIR.parent / "raw")
    eg = pd.read_csv(RAW / "eurepoc_global.csv", low_memory=False)
    er = pd.read_csv(RAW / "eurepoc_receiver.csv", low_memory=False)
    ea = pd.read_csv(RAW / "eurepoc_attribution.csv", low_memory=False)

    # 1. Isolate ALL 171 German incidents (168 in receiver + 3 in global only)
    rec_de = er[er["country"].astype(str).str.contains("Germany", case=False, na=False)].copy()
    glob_de_mask = (
        eg["receiver_country"].astype(str).str.contains("Germany", case=False, na=False)
        | eg["receiver_country_alpha_2_code"].astype(str).str.contains(r"\bDE\b", na=False)
    )
    all_de_ids = sorted(set(rec_de["incident_id"]).union(set(eg.loc[glob_de_mask, "incident_id"])))
    print(f"Total EuRepoC German incidents: {len(all_de_ids)}")

    # Count total countries per incident for is_global_campaign
    countries_per_inc = er.groupby("incident_id")["country"].nunique().to_dict()

    eg_de = eg[eg["incident_id"].isin(all_de_ids)].copy()
    rows_test = []
    for _, inc in eg_de.iterrows():
        iid = inc["incident_id"]
        sub_recs = rec_de[rec_de["incident_id"] == iid]
        rec_names = []
        rec_sectors = []
        named_sectors = []
        for _, rr in sub_recs.iterrows():
            nm = fix_text_all(rr["name"])
            valid_nm = nm not in ("", "Not available", "Unknown", "nan")
            if valid_nm and nm not in rec_names:
                rec_names.append(nm)
            sec = resolve_eurepoc_receiver_row_sector(rr["category"], rr["subcategory"], nm if valid_nm else "", f"{inc['name']} {inc['description']}")
            if sec != "Unknown":
                rec_sectors.append(sec)
                if valid_nm:
                    named_sectors.append(sec)

        victim_str = recover_eurepoc_victim(inc, rec_names)
        if not rec_sectors:
            sec_primary = resolve_eurepoc_receiver_row_sector(
                str(inc.get("receiver_category", "")).split(";")[0],
                str(inc.get("receiver_subcategory", "")).split(";")[0],
                victim_str,
                f"{inc['name']} {inc['description']}",
            )
            all_secs = [sec_primary] if sec_primary != "Unknown" else []
        else:
            # Majority vote; tie-break using named German victims first!
            counts = Counter(rec_sectors)
            named_counts = Counter(named_sectors)
            sec_primary = sorted(counts.keys(), key=lambda s: (counts[s], named_counts[s]), reverse=True)[0]
            all_secs = list(dict.fromkeys([sec_primary] + [s for s in rec_sectors if s != sec_primary]))

        # Attribution (prefer settled_attribution == True if multiple exist)
        sub_attr = ea[ea["incident_id"] == iid]
        if len(sub_attr) > 1 and (sub_attr["settled_attribution"] == True).any():
            sub_attr = sub_attr[sub_attr["settled_attribution"] == True]
        act_cats = "; ".join(dict.fromkeys(fix_text_all(x) for x in pd.concat([sub_attr["initiator_subcategory"], sub_attr["initiator_category"]]).dropna() if fix_text_all(x) not in ("", "Not available", "Not attributed", "Unknown")))
        actor_t = standardize_actor_type(act_cats)
        dt, dprec = parse_eurepoc_date(inc)
        rows_test.append({
            "incident_id": iid,
            "date": dt,
            "date_precision": dprec,
            "victim_name": victim_str,
            "sector": sec_primary,
            "all_sectors_hit": "; ".join(all_secs) if all_secs else "Unknown",
            "actor_type": actor_t,
            "de_victim_count": max(1, len(rec_names) if rec_names else len(sub_recs)),
            "is_global_campaign": countries_per_inc.get(iid, 1) >= 3,
        })

    df_t = pd.DataFrame(rows_test)
    print("\nNew EuRepoC Actor Type Distribution:")
    print(df_t["actor_type"].value_counts())
    print("\nNew EuRepoC Sector Distribution:")
    print(df_t["sector"].value_counts())
    print("\nNew EuRepoC Date Precision:")
    print(df_t["date_precision"].value_counts())
    print(f"\nNamed victims in EuRepoC: {(df_t['victim_name'] != 'Unknown').sum()} / {len(df_t)} (was 83 / 168 before!)")
    print("Check ThyssenKrupp rows in EuRepoC:")
    print(df_t[df_t["victim_name"].str.contains("Thyssen", case=False)])


if __name__ == "__main__":
    run_eurepoc_test()
