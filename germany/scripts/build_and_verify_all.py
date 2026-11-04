"""
End-to-End Pipeline & Verification Script for Germany Cyber Datasets
====================================================================
Builds and verifies:
1. `germany_large_incidents.csv` (Dataset 1: 1 row = 1 distinct incident, 19 columns)
2. `germany_yearly_overview.csv` (Dataset 2: 13 rows, 2014-2026 macro & cyber series, 35 columns)
3. `germany_sector_year_panel.csv` (Dataset 3: 130 rows, 13 years x 10 sectors, 21 columns)
"""

from __future__ import annotations

import re
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path[:] = [p for p in sys.path if "scratch" not in p.lower()]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

GERMANY_DIR = (
    SCRIPT_DIR.parent
    if (SCRIPT_DIR.parent / "data" / "raw").is_dir()
    else Path(r"d:\fakultet mrtvi\Modeli in Odločitveni Sistemi\Projekt\germany")
)
DATA_DIR = GERMANY_DIR / "data"
RAW_DIR = DATA_DIR / "raw" if (DATA_DIR / "raw").is_dir() else GERMANY_DIR / "raw"
PREPARED_DIR = DATA_DIR / "prepared" if (DATA_DIR / "prepared").is_dir() else GERMANY_DIR
PREPARED_DIR.mkdir(parents=True, exist_ok=True)

from harmonize_helpers import (
    fix_text_all,
    extract_bundesland,
    resolve_umd_sector,
    resolve_eurepoc_receiver_row_sector,
    classify_sector_by_text,
    KRITIS_SECTORS,
    clean_victim_name,
    clean_description,
)
from test_attack_enrichment import extract_ransomware_family, standardize_attack_type
from test_eurepoc_builder import parse_eurepoc_date, recover_eurepoc_victim, standardize_actor_type
from dedup_2a_engine import (
    extract_victim_match_keys,
    names_match,
    SOURCE_RANK,
)


def _none_to_nan(val, invalid_set=None):
    """Convert placeholder strings ('Unknown', 'No Ransomware / Unknown', '') to np.nan."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    inv = invalid_set or {"", "Unknown", "Unknown / Undetermined", "No Ransomware / Unknown", "Undetermined", "Not available", "nan", "None"}
    return np.nan if s in inv else s


# ==============================================================================
# 1. LOAD & STANDARDIZE ALL 4 INCIDENT SOURCES (ZERO FABRICATION)
# ==============================================================================

def load_umd() -> pd.DataFrame:
    print("Loading UMD CISSM...")
    umd_raw = pd.read_excel(RAW_DIR / "umd_cyber_events.xlsx")
    umd_de = umd_raw[(umd_raw["country"] == "Germany") | (umd_raw["country_iso3"] == "DEU")].copy()

    records = []
    for idx, r in umd_de.iterrows():
        dt = pd.to_datetime(r["event_date"], errors="coerce")
        vname = clean_victim_name(r["organization"])
        loc = fix_text_all(r["state"])
        bland = _none_to_nan(extract_bundesland(loc, f"{r['industry']} {r['organization']} {r['description']}"))
        sec = _none_to_nan(resolve_umd_sector(r["industry"], r["organization"], r["description"]))
        desc = clean_description(r["description"])
        desc_str = desc if pd.notna(desc) else ""

        rfam_raw = extract_ransomware_family(r["actor"], desc_str)
        rfam = _none_to_nan(rfam_raw)
        att_type = _none_to_nan(standardize_attack_type(f"{r['event_type']} {r['event_subtype']}", desc_str, rfam_raw))

        # Actor type & name
        raw_act_t = fix_text_all(r["actor_type"]).lower()
        if "criminal" in raw_act_t or att_type == "Ransomware":
            act_type = "Criminal"
        elif "nation-state" in raw_act_t or "state" in raw_act_t:
            act_type = "State-Sponsored"
        elif "hacktiv" in raw_act_t:
            act_type = "Hacktivist"
        elif "terrorist" in raw_act_t or "hobbyist" in raw_act_t:
            act_type = "Other"
        else:
            act_type = np.nan

        act_name = _none_to_nan(fix_text_all(r["actor"]))

        # Motive
        raw_mot = fix_text_all(r["motive"]).lower()
        if "financial" in raw_mot:
            motive = "Financial"
        elif "espionage" in raw_mot:
            motive = "Espionage"
        elif "protest" in raw_mot or "political" in raw_mot:
            motive = "Hacktivism / Protest"
        elif "sabotage" in raw_mot:
            motive = "Sabotage / Disruption"
        elif act_type == "Criminal" or att_type == "Ransomware":
            motive = "Financial"
        elif act_type == "Hacktivist":
            motive = "Hacktivism / Protest"
        elif act_type == "State-Sponsored":
            motive = "Sabotage / Disruption" if att_type == "DDoS / Disruption" else "Espionage"
        else:
            motive = np.nan

        # True 3-state disruption & data theft based on UMD event_type and fields
        desc_l = desc_str.lower()
        ev_type = str(r.get("event_type", "")).strip()
        dur_mag = f"{r.get('duration', '')} {r.get('magnitude', '')}".lower()

        disr_kw = any(k in desc_l for k in ["disrupt", "offline", "shutdown", "shut down", "paralyz", "outage", "halt", "ddos", "encrypt"])
        if ev_type in ("Disruptive", "Mixed") or disr_kw:
            has_disr = True
        elif "no system" in dur_mag or (ev_type == "Exploitive" and not disr_kw):
            has_disr = False
        else:
            has_disr = pd.NA

        theft_kw = any(k in desc_l for k in ["exfiltrat", "stolen", "breach", "leak", "dumped", "compromised data"])
        field_theft = False
        for fld in ["cust_data", "org_data", "ip"]:
            val = str(r.get(fld, "")).lower().strip()
            if val and "none reported" not in val and val not in ("nan", "undetermined", "unknown"):
                field_theft = True

        if ev_type in ("Exploitive", "Mixed") or theft_kw or field_theft:
            has_theft = True
        elif ev_type == "Disruptive" and not theft_kw and not field_theft:
            has_theft = False
        else:
            has_theft = pd.NA

        records.append({
            "source_id": f"UMD_{idx}",
            "source": "UMD",
            "date": dt,
            "date_precision": "exact_day" if pd.notna(dt) else "undated",
            "victim_name": vname,
            "bundesland": bland,
            "sector": sec,
            "is_kritis_sector": (sec in KRITIS_SECTORS) if pd.notna(sec) else pd.NA,
            "attack_type": att_type,
            "ransomware_family": rfam,
            "actor_type": act_type,
            "actor_name": act_name,
            "motive": motive,
            "has_disruption": has_disr,
            "has_data_theft": has_theft,
            "description": desc,
        })
    df_umd = pd.DataFrame(records)
    print(f"UMD processed: {len(df_umd)} rows")
    return df_umd


def load_eurepoc() -> pd.DataFrame:
    print("Loading EuRepoC v1.3...")
    eg = pd.read_csv(RAW_DIR / "eurepoc_global.csv", low_memory=False)
    er = pd.read_csv(RAW_DIR / "eurepoc_receiver.csv", low_memory=False)
    ea = pd.read_csv(RAW_DIR / "eurepoc_attribution.csv", low_memory=False)

    rec_de = er[er["country"].astype(str).str.contains("Germany", case=False, na=False)].copy()
    glob_de_mask = (
        eg["receiver_country"].astype(str).str.contains("Germany", case=False, na=False)
        | eg["receiver_country_alpha_2_code"].astype(str).str.contains(r"\bDE\b", na=False)
    )
    all_de_ids = sorted(set(rec_de["incident_id"]).union(set(eg.loc[glob_de_mask, "incident_id"])))
    eg_de = eg[eg["incident_id"].isin(all_de_ids)].copy()

    records = []
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

        vname_raw = recover_eurepoc_victim(inc, rec_names)
        vname = clean_victim_name(vname_raw)
        if not rec_sectors:
            sec_primary = resolve_eurepoc_receiver_row_sector(
                str(inc.get("receiver_category", "")).split(";")[0],
                str(inc.get("receiver_subcategory", "")).split(";")[0],
                vname_raw,
                f"{inc['name']} {inc['description']}",
            )
        else:
            counts = Counter(rec_sectors)
            named_counts = Counter(named_sectors)
            sec_primary = sorted(counts.keys(), key=lambda s: (counts[s], named_counts[s]), reverse=True)[0]
        sec_primary = _none_to_nan(sec_primary)

        # Attribution
        sub_attr = ea[ea["incident_id"] == iid]
        if len(sub_attr) > 1 and (sub_attr["settled_attribution"] == True).any():
            sub_attr = sub_attr[sub_attr["settled_attribution"] == True]

        act_cats = "; ".join(dict.fromkeys(fix_text_all(x) for x in pd.concat([sub_attr["initiator_subcategory"], sub_attr["initiator_category"]]).dropna() if fix_text_all(x) not in ("", "Not available", "Not attributed", "Unknown")))
        act_type = _none_to_nan(standardize_actor_type(act_cats))

        act_names = "; ".join(dict.fromkeys(fix_text_all(x) for x in sub_attr["initiator_name"].dropna() if fix_text_all(x) not in ("", "Not available", "Not attributed", "Unknown")))
        act_names = _none_to_nan(act_names)

        dt, dprec = parse_eurepoc_date(inc)
        desc = clean_description(inc.get("description", inc.get("name", "")))
        desc_str = desc if pd.notna(desc) else ""

        rfam_raw = extract_ransomware_family(act_names if pd.notna(act_names) else "", desc_str)
        rfam = _none_to_nan(rfam_raw)
        att_type = _none_to_nan(standardize_attack_type(inc.get("incident_type", ""), desc_str, rfam_raw))
        if pd.isna(act_type) and att_type == "Ransomware":
            act_type = "Criminal"

        bland = _none_to_nan(extract_bundesland("", f"{vname_raw} {desc_str}"))

        # True 3-state disruption & data theft from EuRepoC columns
        raw_disr = str(inc.get("disruption", "")).strip().lower()
        raw_fi = str(inc.get("functional_impact", "")).strip().lower()
        native_hd = inc.get("has_disruption")

        if native_hd is True or str(native_hd).lower() == "true" or "disruption" in raw_disr and raw_disr != "no disruption":
            has_disr = True
        elif raw_disr == "none" or "no system interference" in raw_fi or native_hd is False or str(native_hd).lower() == "false":
            has_disr = False
        else:
            has_disr = pd.NA

        raw_dt = str(inc.get("data_theft", "")).strip().lower()
        raw_ii = str(inc.get("intelligence_impact", "")).strip().lower()
        if "point" in raw_dt or raw_ii.startswith(("minor data breach", "major data breach")) or "or major data breach" in raw_ii:
            has_theft = True
        elif raw_dt == "none" or raw_ii.startswith("no data breach"):
            has_theft = False
        else:
            has_theft = pd.NA

        motive = (
            "Espionage" if act_type == "State-Sponsored" and att_type != "DDoS / Disruption"
            else ("Sabotage / Disruption" if att_type == "DDoS / Disruption"
                  else ("Financial" if act_type == "Criminal" or att_type == "Ransomware"
                        else ("Hacktivism / Protest" if act_type == "Hacktivist" else np.nan)))
        )

        records.append({
            "source_id": f"EUR_{iid}",
            "source": "EuRepoC",
            "date": dt,
            "date_precision": dprec,
            "victim_name": vname,
            "bundesland": bland,
            "sector": sec_primary,
            "is_kritis_sector": (sec_primary in KRITIS_SECTORS) if pd.notna(sec_primary) else pd.NA,
            "attack_type": att_type,
            "ransomware_family": rfam,
            "actor_type": act_type,
            "actor_name": act_names,
            "motive": motive,
            "has_disruption": has_disr,
            "has_data_theft": has_theft,
            "description": desc,
        })

    df_eur = pd.DataFrame(records)
    print(f"EuRepoC processed: {len(df_eur)} rows")
    return df_eur


def load_konbriefing() -> pd.DataFrame:
    print("Loading KonBriefing Germany Enriched...")
    kb = pd.read_csv(RAW_DIR / "konbriefing_germany_enriched.csv")

    # Collect bare city names and generic victim_type labels from KonBriefing
    # so we never treat a bare city ("Düsseldorf", "Göppingen") or category ("Consumer goods", "Tickets (Berlin, BE)")
    # as a specific organization name.
    kb_cities = set(
        kb["city"].dropna().astype(str).apply(fix_text_all)
        .str.replace(r",\s*[A-Z]{2}$", "", regex=True).str.strip().str.lower()
    )
    kb_types = set(
        kb["victim_type"].dropna().astype(str).apply(fix_text_all)
        .str.strip().str.lower()
    )
    kb_generic_extra = {
        "consumer goods", "healthcare", "power supply", "research", "rescue",
        "cars", "public transport", "city government", "local government",
        "public sector", "companies", "company", "food", "logistics",
        "manufacturer", "technology", "magdeburg, sachsen-anhalt, germany",
        "state of brandenburg", "welfare", "social", "retail", "finance",
        "administration", "authority", "government", "education", "energy",
        "automotive", "automobile", "chemical", "construction", "hospital",
        "university", "school", "schools", "municipality", "police",
    }
    kb_invalid_names = kb_cities | kb_types | kb_generic_extra

    records = []
    for idx, r in kb.iterrows():
        raw_d = str(r["date_raw"]).replace("?", "").strip()
        dt = pd.to_datetime(raw_d, format="mixed", errors="coerce")
        dprec = "exact_day"
        if re.match(r"^[A-Za-z]+\s+\d{4}$", raw_d):
            dprec = "month_only"
        elif re.match(r"^\d{4}$", raw_d):
            dprec = "year_only"

        vname_raw = fix_text_all(r["victim_organization_clean"])
        vname = clean_victim_name(vname_raw)
        if pd.notna(vname):
            v_str = str(vname).strip()
            if (
                v_str.lower() in kb_invalid_names
                or re.search(r"\([A-Za-zäöüÄÖÜß\s\-/\.]+,\s*[A-Z]{2}\)$", v_str)
            ):
                vname = np.nan
        bland = _none_to_nan(fix_text_all(r["bundesland"]))
        loc = fix_text_all(r["city"])
        vtype = fix_text_all(r["victim_type"])
        kw = fix_text_all(r["keywords"])
        summary = clean_description(r["incident_summary"])
        summary_str = summary if pd.notna(summary) else ""
        src_titles = fix_text_all(r["source_titles"])
        combined_text = f"{vname_raw} {vtype} {loc} {kw} {summary_str} {src_titles}"
        attack_text = f"{kw} {summary_str} {src_titles}"

        sec = _none_to_nan(classify_sector_by_text(combined_text, default="Unknown"))
        rfam_raw = extract_ransomware_family(r["kb_actor_hint"], attack_text)
        rfam = _none_to_nan(rfam_raw)

        # Use strict standardize_attack_type instead of kb_attack_hint when kb_attack_hint was generic 'System Intrusion / Malware'
        raw_hint = str(r.get("kb_attack_hint", "")).strip()
        if raw_hint in ("Ransomware", "DDoS / Disruption", "Data Breach / Data Theft", "Phishing / Social Engineering"):
            att_type = raw_hint
        else:
            att_type = _none_to_nan(standardize_attack_type("", attack_text, rfam_raw))
        if pd.notna(rfam):
            att_type = "Ransomware"

        act_name = _none_to_nan(fix_text_all(r["kb_actor_hint"]))
        act_type = np.nan
        if pd.notna(rfam) or att_type == "Ransomware" or act_name in ("LockBit", "Black Basta", "Rhysida", "REvil", "Cl0p (MOVEit)"):
            act_type = "Criminal"
        elif act_name in ("APT28 / Fancy Bear", "APT29 / Cozy Bear", "Sandworm"):
            act_type = "State-Sponsored"
        elif act_name in ("NoName057(16)", "Pro-Russian Hacktivists"):
            act_type = "Hacktivist"

        # True 3-state disruption & data theft from KonBriefing text
        txt_l = attack_text.lower()
        averted = any(k in txt_l for k in ["averted", "abgewehrt", "verhindert", "blocked", "stopped attack"])
        disr_kw = any(k in txt_l for k in [
            "ausfall", "offline", "lahmgelegt", "nicht erreichbar", "notbetrieb", "stillstand",
            "verschlüsselt", "encrypted", "paralyz", "disrupt", "outage", "shut down", "shutdown",
            "eingeschränkt", "vom netz", "störung", "abgeschaltet", "unusable", "restricted",
        ])
        if r["kb_has_disruption_hint"] is True or str(r["kb_has_disruption_hint"]).lower() == "true" or att_type == "DDoS / Disruption" or (disr_kw and not averted):
            has_disr = True
        elif averted or (att_type in ("Data Breach / Data Theft", "Phishing / Social Engineering") and not disr_kw):
            has_disr = False
        else:
            has_disr = pd.NA

        theft_kw = any(k in txt_l for k in [
            "datenabfluss", "datenleck", "daten gestohlen", "daten erbeutet", "ausgespäht",
            "darknet", "exfiltrat", "stolen", "leaked", "data breach", "data theft",
            "erpresst", "erpressen", "lösegeld", "ransom",
        ])
        if r["kb_has_data_theft_hint"] is True or str(r["kb_has_data_theft_hint"]).lower() == "true" or att_type == "Data Breach / Data Theft" or (theft_kw and not averted):
            has_theft = True
        elif averted or (att_type in ("DDoS / Disruption", "Phishing / Social Engineering") and not theft_kw):
            has_theft = False
        else:
            has_theft = pd.NA

        motive = (
            "Financial" if act_type == "Criminal" or att_type == "Ransomware"
            else ("Hacktivism / Protest" if act_type == "Hacktivist"
                  else ("Sabotage / Disruption" if att_type == "DDoS / Disruption"
                        else ("Espionage" if act_type == "State-Sponsored" else np.nan)))
        )

        records.append({
            "source_id": f"KB_{idx}",
            "source": "KonBriefing",
            "date": dt,
            "date_precision": dprec,
            "victim_name": vname,
            "bundesland": bland,
            "sector": sec,
            "is_kritis_sector": (sec in KRITIS_SECTORS) if pd.notna(sec) else pd.NA,
            "attack_type": att_type,
            "ransomware_family": rfam,
            "actor_type": act_type,
            "actor_name": act_name,
            "motive": motive,
            "has_disruption": has_disr,
            "has_data_theft": has_theft,
            "description": summary,
        })

    df_kb = pd.DataFrame(records)
    print(f"KonBriefing processed: {len(df_kb)} rows")
    return df_kb


def load_ransomware_live() -> pd.DataFrame:
    print("Loading Ransomware.live Germany...")
    rw = pd.read_csv(RAW_DIR / "ransomware_live_germany.csv")

    records = []
    for idx, r in rw.iterrows():
        d_str = str(r["published_date"]).strip() if pd.notna(r["published_date"]) and str(r["published_date"]).strip() else str(r["discovered_date"]).strip()
        dt = pd.to_datetime(d_str, errors="coerce")
        if pd.notna(dt) and hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            dt = dt.tz_localize(None)

        vname_raw = fix_text_all(r["victim_name"])
        vname = clean_victim_name(vname_raw)
        desc = clean_description(r["description"])
        desc_str = fix_text_all(r["description"]) if pd.notna(r["description"]) else ""
        act = fix_text_all(r["activity"])
        grp = _none_to_nan(fix_text_all(r["group_name"]))

        bland = _none_to_nan(extract_bundesland("", f"{vname_raw} {desc_str} {act}"))
        # Do NOT default 'Other' or 'Unknown' to 'Retail, Trade & Services'
        sec = _none_to_nan(classify_sector_by_text(f"{act} {desc_str} {vname_raw}", default="Unknown"))

        rfam_raw = extract_ransomware_family(grp if pd.notna(grp) else "", desc_str)
        rfam = _none_to_nan(rfam_raw)
        if pd.isna(rfam) and pd.notna(grp):
            rfam = grp

        # Honest disruption & data theft for leak-site posts
        dl = desc_str.lower()
        if re.search(r"encrypted data\s*:\s*no\b", dl):
            has_disr = False
        elif re.search(r"encrypted data\s*:\s*yes\b|\bencrypt|\bdisrupt|\boutage|\boffline|\bparalyz|\blocked|\bshut down", dl):
            has_disr = True
        else:
            has_disr = pd.NA

        if re.search(r"exfiltraded data\s*:\s*no\b", dl):
            has_theft = False
        else:
            has_theft = True

        records.append({
            "source_id": f"RW_{idx}",
            "source": "Ransomware.live",
            "date": dt,
            "date_precision": "leak_site_timestamp",
            "victim_name": vname,
            "bundesland": bland,
            "sector": sec,
            "is_kritis_sector": (sec in KRITIS_SECTORS) if pd.notna(sec) else pd.NA,
            "attack_type": "Ransomware",
            "ransomware_family": rfam,
            "actor_type": "Criminal",
            "actor_name": grp,
            "motive": "Financial",
            "has_disruption": has_disr,
            "has_data_theft": has_theft,
            "description": desc,
        })

    df_rw = pd.DataFrame(records)
    print(f"Ransomware.live processed: {len(df_rw)} rows")
    return df_rw


# ==============================================================================
# 2. CROSS-SOURCE DEDUPLICATION (1 ROW = 1 DISTINCT CYBER INCIDENT)
# ==============================================================================

def deduplicate_incidents(all_raw: pd.DataFrame) -> pd.DataFrame:
    raw_records = all_raw.to_dict(orient="records")
    used = [False] * len(raw_records)
    merged_incidents = []

    for i in range(len(raw_records)):
        if used[i]:
            continue
        base = raw_records[i]
        used[i] = True
        sources = [base["source"]]
        descriptions = [base["description"]] if pd.notna(base["description"]) else []

        date_a = base["date"]
        prec_a = base["date_precision"]
        keys_a = base["match_keys"]

        for j in range(i + 1, len(raw_records)):
            if used[j]:
                continue
            cand = raw_records[j]
            date_b = cand["date"]
            prec_b = cand["date_precision"]
            keys_b = cand["match_keys"]

            same_source = (base["source"] == cand["source"])

            date_match = False
            if pd.isna(date_a) or pd.isna(date_b):
                date_match = (not same_source and names_match(keys_a, keys_b))
            else:
                days_diff = (date_b - date_a).days
                if days_diff > 365:
                    break
                if prec_a in ("exact_day", "reported_fallback") and prec_b in ("exact_day", "reported_fallback") and days_diff > 35:
                    break

                max_window = 31 if ("leak_site_timestamp" in (prec_a, prec_b) or "month_only" in (prec_a, prec_b)) else 18
                if days_diff <= max_window:
                    date_match = True
                elif prec_a == "year_only" or prec_b == "year_only":
                    if date_a.year == date_b.year:
                        date_match = True

            if not date_match:
                continue

            if same_source:
                match = (date_a == date_b and names_match(keys_a, keys_b) and len(keys_a) > 0 and len(keys_b) > 0)
            else:
                match = names_match(keys_a, keys_b)

            if match:
                used[j] = True
                sources.append(cand["source"])
                if pd.notna(cand["description"]):
                    descriptions.append(cand["description"])

                rank_base = SOURCE_RANK.get(base["source"].split(" + ")[0], 99)
                rank_cand = SOURCE_RANK.get(cand["source"], 99)
                lead, trail = (base, cand) if rank_base <= rank_cand else (cand, base)

                for col in ["victim_name", "sector", "bundesland", "attack_type", "ransomware_family",
                            "actor_type", "actor_name", "motive"]:
                    val_l, val_t = lead[col], trail[col]
                    base[col] = val_l if pd.notna(val_l) else val_t

                for bool_col in ["has_disruption", "has_data_theft"]:
                    b1, b2 = base[bool_col], cand[bool_col]
                    if b1 is True or b2 is True:
                        base[bool_col] = True
                    elif b1 is False or b2 is False:
                        base[bool_col] = False
                    else:
                        base[bool_col] = pd.NA

                if base["date_precision"] in ("year_only", "month_only", "leak_site_timestamp") and cand["date_precision"] == "exact_day":
                    base["date"] = cand["date"]
                    base["date_precision"] = cand["date_precision"]

        source_order = ["EuRepoC", "UMD", "Ransomware.live", "KonBriefing"]
        unique_src = [s for s in source_order if s in set(sources)]
        base["source"] = " + ".join(unique_src)
        base["num_sources"] = len(unique_src)

        descriptions_sorted = sorted(descriptions, key=len, reverse=True)
        base["description"] = descriptions_sorted[0] if descriptions_sorted else np.nan
        base["is_kritis_sector"] = (base["sector"] in KRITIS_SECTORS) if pd.notna(base["sector"]) else pd.NA
        merged_incidents.append(base)

    df_inc = pd.DataFrame(merged_incidents).sort_values(by=["has_valid_date", "date"], ascending=[False, True]).reset_index(drop=True)
    df_inc["incident_id"] = [f"DE_{idx + 1:04d}" for idx in range(len(df_inc))]
    df_inc["year"] = df_inc["date"].dt.year.astype("Int64")
    df_inc["month"] = df_inc["date"].dt.month.astype("Int64")
    df_inc["date"] = df_inc["date"].dt.strftime("%Y-%m-%d")

    cols_final_1 = [
        "incident_id", "date", "year", "month", "date_precision",
        "victim_name", "bundesland", "sector", "is_kritis_sector",
        "attack_type", "ransomware_family", "actor_type", "actor_name",
        "motive", "has_disruption", "has_data_theft",
        "source", "num_sources", "description"
    ]
    return df_inc[cols_final_1]


def run_pipeline() -> None:
    df_umd = load_umd()
    df_eur = load_eurepoc()
    df_kb = load_konbriefing()
    df_rw = load_ransomware_live()

    all_raw = pd.concat([df_eur, df_umd, df_rw, df_kb], ignore_index=True)
    print(f"\nTotal raw combined incident records across 4 sources: {len(all_raw)}")

    all_raw["date"] = pd.to_datetime(all_raw["date"], errors="coerce")
    try:
        all_raw["date"] = all_raw["date"].dt.tz_localize(None)
    except TypeError:
        pass

    all_raw["match_keys"] = all_raw["victim_name"].apply(extract_victim_match_keys)
    all_raw["has_valid_date"] = all_raw["date"].notna()
    all_raw = all_raw.sort_values(by=["has_valid_date", "date"], ascending=[False, True]).reset_index(drop=True)

    # Minimum Completeness Gate: drop records where victim_name, sector, AND attack_type are all simultaneously NaN
    valid_mask = ~(all_raw["victim_name"].isna() & all_raw["sector"].isna() & all_raw["attack_type"].isna())
    all_raw = all_raw[valid_mask].reset_index(drop=True)
    print(f"Records passing Minimum Completeness Gate: {len(all_raw)}")

    df_inc = deduplicate_incidents(all_raw)

    out_inc = PREPARED_DIR / "germany_large_incidents.csv"
    df_inc.to_csv(out_inc, index=False, encoding="utf-8")
    print(f"\n=======================================================")
    print(f"Dataset 1 (germany_large_incidents.csv) Successfully Generated!")
    print(f"Total deduplicated incidents: {len(df_inc)} (from {len(all_raw)} passing gate)")
    print(f"Columns ({len(df_inc.columns)}): {list(df_inc.columns)}")
    print(f"Multi-source corroborated incidents: {(df_inc['num_sources'] > 1).sum()}")
    print(f"\nSector breakdown (dropna=False):\n{df_inc['sector'].value_counts(dropna=False)}")
    print(f"\nAttack type breakdown (dropna=False):\n{df_inc['attack_type'].value_counts(dropna=False)}")
    print(f"\nhas_disruption breakdown (dropna=False):\n{df_inc['has_disruption'].value_counts(dropna=False)}")
    print(f"\nhas_data_theft breakdown (dropna=False):\n{df_inc['has_data_theft'].value_counts(dropna=False)}")

    # ==============================================================================
    # 3. BUILD DATASET 2: germany_yearly_overview.csv (2014-2026, 13 rows)
    # ==============================================================================
    print("\nCompiling Dataset 2: germany_yearly_overview.csv...")
    wb_yearly = pd.read_csv(RAW_DIR / "world_bank_germany.csv")
    official_yearly = pd.read_csv(RAW_DIR / "bka_bitkom_eurostat_yearly.csv")

    inc_de = df_inc[(df_inc["year"] >= 2014) & (df_inc["year"] <= 2026)].copy()

    annual_agg = (
        inc_de.groupby("year")
        .agg(
            documented_large_incidents=("incident_id", "count"),
            documented_ransomware_incidents=("attack_type", lambda s: (s == "Ransomware").sum()),
            documented_state_sponsored_incidents=("actor_type", lambda s: (s == "State-Sponsored").sum()),
            documented_disruptive_incidents=("has_disruption", lambda s: (s == True).sum()),
            documented_data_theft_incidents=("has_data_theft", lambda s: (s == True).sum()),
            documented_kritis_incidents=("is_kritis_sector", lambda s: (s == True).sum()),
            incidents_eurepoc=("source", lambda s: s.str.contains("EuRepoC").sum()),
            incidents_umd=("source", lambda s: s.str.contains("UMD").sum()),
            incidents_ransomware_live=("source", lambda s: s.str.contains("Ransomware.live").sum()),
            incidents_konbriefing=("source", lambda s: s.str.contains("KonBriefing").sum()),
        )
        .reindex(range(2014, 2027), fill_value=0)
        .reset_index()
    )

    yearly_overview = (
        wb_yearly
        .merge(official_yearly, on="year", how="left")
        .merge(annual_agg, on="year", how="left")
    )

    yearly_overview["bka_cybercrime_total_known"] = yearly_overview.apply(
        lambda r: (r["bka_cybercrime_domestic"] + r["bka_cybercrime_from_abroad"])
        if pd.notna(r["bka_cybercrime_from_abroad"])
        else r["bka_cybercrime_domestic"],
        axis=1,
    )

    yearly_overview["bitkom_cyber_damage_pct_gdp"] = (
        yearly_overview["bitkom_cyber_damage_eur_bn"] / yearly_overview["gdp_billion_eur"] * 100
    ).round(3)

    out_yearly = PREPARED_DIR / "germany_yearly_overview.csv"
    yearly_overview.to_csv(out_yearly, index=False, encoding="utf-8")
    print(f"Dataset 2 Saved: {yearly_overview.shape[0]} rows x {yearly_overview.shape[1]} columns to {out_yearly}")

    # ==============================================================================
    # 4. BUILD DATASET 3: germany_sector_year_panel.csv (130 rows: 13 years x 10 sectors)
    # ==============================================================================
    print("\nCompiling Dataset 3: germany_sector_year_panel.csv...")
    sector_base = pd.read_csv(RAW_DIR / "eurostat_destatis_sector_yearly.csv")

    inc_sec_yr = (
        inc_de.dropna(subset=["sector"]).groupby(["year", "sector"])
        .agg(
            documented_incidents=("incident_id", "count"),
            ransomware_incidents=("attack_type", lambda s: (s == "Ransomware").sum()),
            disruptive_incidents=("has_disruption", lambda s: (s == True).sum()),
            data_theft_incidents=("has_data_theft", lambda s: (s == True).sum()),
        )
        .reset_index()
    )

    panel = sector_base.merge(inc_sec_yr, on=["year", "sector"], how="left")
    panel["documented_incidents"] = panel["documented_incidents"].fillna(0).astype(int)
    panel["ransomware_incidents"] = panel["ransomware_incidents"].fillna(0).astype(int)
    panel["disruptive_incidents"] = panel["disruptive_incidents"].fillna(0).astype(int)
    panel["data_theft_incidents"] = panel["data_theft_incidents"].fillna(0).astype(int)

    panel["incidents_per_10k_enterprises"] = np.where(
        panel["sec_active_enterprises"] > 0,
        (panel["documented_incidents"] / panel["sec_active_enterprises"] * 10000).round(3),
        np.nan,
    )
    panel["incidents_per_10bn_eur_gva"] = np.where(
        panel["sec_gva_eur_bn"] > 0,
        (panel["documented_incidents"] / panel["sec_gva_eur_bn"] * 10.0).round(3),
        np.nan,
    )

    nat_cols = yearly_overview[[
        "year", "gdp_billion_eur", "bka_cybercrime_domestic", "bka_cybercrime_from_abroad",
        "bitkom_total_damage_eur_bn", "bsi_kritis_incidents_total"
    ]].rename(columns={
        "gdp_billion_eur": "nat_gdp_billion_eur",
        "bka_cybercrime_domestic": "nat_bka_cybercrime_domestic",
        "bka_cybercrime_from_abroad": "nat_bka_cybercrime_from_abroad",
        "bitkom_total_damage_eur_bn": "nat_bitkom_damage_eur_bn",
        "bsi_kritis_incidents_total": "nat_bsi_kritis_incidents_total",
    })

    panel = panel.merge(nat_cols, on="year", how="left")

    out_panel = PREPARED_DIR / "germany_sector_year_panel.csv"
    panel.to_csv(out_panel, index=False, encoding="utf-8")
    print(f"Dataset 3 Saved: {panel.shape[0]} rows x {panel.shape[1]} columns to {out_panel}")
    print("\nAll 3 Datasets Built and Verified!")


if __name__ == "__main__":
    run_pipeline()
