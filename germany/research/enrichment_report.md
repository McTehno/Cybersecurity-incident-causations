# Enrichment report — `germany_large_incidents.csv` (rebuilt 19-column dataset)

**Input:** `data/prepared/germany_large_incidents.csv` — 2,323 incidents × 19 columns
**Output:** `data/prepared/germany_large_incidents_filled.csv` (same schema, same row order)
**Audit trail:** `data/prepared/germany_large_incidents_fill_log.csv` (one line per changed cell)

---

## 1. Result

**80 empty cells filled** across **71 of the 2,323 incidents**. Empty cells: 9,160 → 9,080.

| Field | Empty before | Filled | Empty after | Basis | Precision measured on this file* |
|---|---|---|---|---|---|
| `bundesland` | 1,169 | **48** | 1,121 | a German city named next to a locative cue ("in Lippstadt", "headquartered in Brilon, Germany", "25578 Dägeling") or inside the victim's own name ("Stadtwerke Schwerte") → federal state | 97.3 % (223 rows) |
| `sector` | 297 | **7** | 290 | sector keyword in the victim's own name (Verlag, Spedition, Medien…) | 88.1 % (202 rows) |
| `actor_type` | 760 | **6** | 754 | "state-sponsored / APT / espionage group", "hacktivist / Killnet / pro-Russian", "fraudsters" | 99.6 % (1,408 rows) |
| `motive` | 721 | **6** | 715 | espionage wording; DDoS/disruption wording | 98.0 % (1,429 rows) |
| `has_disruption` | 1,603 | **6** | 1,597 | explicit "was not affected" (False) / "systems were disconnected" (True) | 83.3 % (108 rows, all 6 reviewed by hand) |
| `is_kritis_sector` | 297 | **7** | 290 | derived: sector ∈ KRITIS list (3 True / 4 False) | pure function of `sector` (100 % on touched rows) |
| **Total** | | **80** | | | |

\* The same rule was applied to the rows where the field already has a value and compared with the recorded
value. Every one of the 80 fills was also read and confirmed by hand before being accepted.

---

## 2. Why this pass adds much less than the previous one

The previous enrichment (776 cells) was done on the **old 34-column build**, which carried `"Unknown"`
sentinels and had a description for every row. The rebuilt dataset is different in three ways:

1. **The build already extracts from the text.** `scripts/build_and_verify_all.py` classifies
   `sector` from `activity` + description + victim name, `attack_type` from keywords/summaries,
   `bundesland` from city names, `actor_type`/`motive` from hints, and `has_data_theft` /
   `has_disruption` from leak-site wording. My independent rules reproduce the build's own values on
   **97–99.6 %** of the rows where it has a value — i.e. both do the same job, so very little is left over.
2. **The build is deliberately conservative.** Its source code states, verbatim,
   *"Do NOT default 'Other' or 'Unknown' to 'Retail, Trade & Services'"*, and it sets
   `has_disruption` to `NA` unless the text mentions encryption/disruption. The old build filled such
   rows with defaults; those defaults are why the old file looked more complete.
3. **852 rows (37 %) have no description at all** in this build — mostly KonBriefing and short
   Ransomware.live entries where the source offers no summary. Without text there is nothing to extract.

Where the remaining 9,080 empty cells come from:

| Empty cells | Field(s) | Why they stay empty |
|---|---|---|
| 2,001 | `actor_name` (928), `ransomware_family` (1,073) | These are KonBriefing or non-ransomware incidents: no actor and no family is named anywhere in the record. |
| 1,597 | `has_disruption` | 1,122 are leak-site ransomware rows whose post never says whether systems were encrypted. |
| 1,121 | `bundesland` | The victim's city is simply not in the text (only a website/company description). |
| 1,230 | `attack_type` (615), `has_data_theft` (615) | 612 of them are KonBriefing rows with no source type and no text. |
| 1,469 | `actor_type` (754), `motive` (715) | Same KonBriefing rows — no actor, no intent stated. |
| 580 | `sector` (290), `is_kritis_sector` (290) | Leak-site rows whose industry is "Professional Services", "Technology", "Other" or "Unknown" — too ambiguous to map. |
| 852 | `description` | No text exists in the source for these rows (see §2.3). |
| 230 | `victim_name` | The build deliberately nulls names that are bare city names or generic labels ("City government", "Companies"). |

---

## 3. What could be filled but deliberately was not

| Candidate | Rows | Why rejected |
|---|---|---|
| `has_disruption = True` for ransomware leak-site rows | 1,122 | In this build only 187 of 205 ransomware rows with a known flag are `True` (91 %) — filling all blanks would inject ~100 wrong values into a variable that drives the yearly/severe-incident counts. |
| `attack_type = System Intrusion / Malware` for KonBriefing rows | 287 | The only evidence is the generic `kb_attack_hint` of the raw KonBriefing export, which is "System Intrusion / Malware" for 451 of 865 rows and "Unknown" for 297 — a default, not a finding, and the build code explicitly refuses to use it. |
| `sector` from the source's `activity` tag | ~243 | The tag is "Professional Services" (95), "Technology" (72), "Unknown" (38), "Other" (20); only ~18 rows (Transportation, Manufacturing) map unambiguously. |
| `bundesland` from the victim's domain | — | Domain names do not identify a federal state. |

If you want any of these as a separate "imputed" variant (e.g. `has_disruption` filled for modelling), say
so and I will generate it with the fill source flagged per cell.

---

## 4. Notes on the rebuild itself

* `is_kritis_sector` is a pure function of `sector` in the build script; it was recomputed for the 7 rows
  whose sector was filled (3 became `True`, 4 `False`).
* The rebuild keeps raw leak-site group names (`lockbit3`, `thegentlemen`, `cloak`) while UMD/EuRepoC rows
  use canonical names (`LockBit`, `Cloak`). The two spellings of the same family coexist in
  `ransomware_family` (e.g. `lockbit3` × 55 and `LockBit` × 8) — worth normalising before modelling.
* 852 rows lost their description relative to the previous build; several of the remaining empty cells
  (bundesland, sector, attack type) are a direct consequence.

---

## 5. Verification

* Output is byte-comparable to the input except for the 80 logged cells (same 2,323 rows, same 19 columns,
  same order, UTF-8, CRLF).
* `germany_large_incidents_fill_log.csv` lists every change with `incident_id`, field, old value,
  new value, the rule that fired and the text snippet that justified it.
* Rules were validated on the rows where the answer is already known (precision column above); the six
  `has_disruption` values, being the weakest rule, were each checked manually.
