"""
Cross-Source Entity Deduplication & Record Fusion Engine ('1 Row = 1 Distinct Cyber Incident').
"""
import re
from difflib import SequenceMatcher
import pandas as pd


GENERIC_OR_GEO_VICTIM_NAMES = {
    "", "unknown", "undetermined", "undisclosed", "public sector", "company",
    "town hall", "city administration", "municipal administration", "county administration",
    "district administration", "german companies", "not available", "law enforcement",
    "government", "government agencies of germany", "federal authority in germany",
    "politics", "technology", "schools", "hospital", "hospitals", "municipality",
    "energy supplier", "it service provider", "insurance provider", "automotive supplier",
    "baden wuerttemberg", "baden wurttemberg", "bayern", "bavaria", "berlin", "brandenburg",
    "bremen", "hamburg", "hessen", "hesse", "niedersachsen", "lower saxony",
    "mecklenburg vorpommern", "mecklenburg western pomerania",
    "nordrhein westfalen", "north rhine westphalia",
    "rheinland pfalz", "rhineland palatinate", "saarland", "sachsen", "saxony",
    "sachsen anhalt", "saxony anhalt", "schleswig holstein", "thueringen", "thuringen",
    "thuringia", "germany", "deutschland",
    "duesseldorf", "dusseldorf", "muenchen", "munchen", "munich", "stuttgart", "frankfurt",
    "koeln", "koln", "cologne", "hannover", "nuernberg", "nurnberg", "dortmund", "essen",
    "leipzig", "dresden", "karlsruhe", "mannheim", "augsburg", "wiesbaden", "muenster",
    "munster", "osnabrueck", "osnabruck", "goeppingen", "goppingen", "fuerth", "furth",
    "bad homburg vor der hoehe", "bad homburg vor der hohe", "money", "berlin germany",
    "berlin de",
}

NON_DISTINCTIVE_TOKENS = {
    "stadt", "stadtwerke", "landkreis", "gemeinde", "klinikum", "klinik",
    "krankenhaus", "universitaet", "universitat", "hochschule", "sparkasse",
    "volksbank", "polizei", "deutsche", "german", "federal", "verband", "stiftung",
    "schule", "rathaus", "verwaltung", "kreis", "nord", "sued", "west", "ost",
    "baden", "wuerttemberg", "wurttemberg", "bayern", "bavaria", "hessen", "hesse",
    "sachsen", "saxony", "anhalt", "berlin", "hamburg", "bremen", "nrw",
    "niedersachsen", "thueringen", "thuringen", "brandenburg", "saarland",
    "rheinland", "pfalz", "westfalen", "holstein", "vorpommern", "hospital",
    "medical", "health", "service", "services", "systems", "technik", "digital",
}

GENERIC_COMPOUND_PREFIXES = (
    "stadtwerke", "universita", "hochschule", "landkreis", "sparkasse", "volksbank",
    "gemeinde", "klinikum", "krankenhaus", "polizei", "landesamt", "bundesamt",
    "stadtverwaltung", "kreisverwaltung", "handwerkskammer",
)

LEGAL_SUFFIX_REGEX = re.compile(
    r"\b(gmbh|ggmbh|ag|se|kg|kgaa|mbh|ohg|gbr|ug|e\.?\s*v\.?|e\.?\s*g\.?|"
    r"co\.?|inc\.?|corp\.?|ltd\.?|plc|llc|group|gruppe|holding|deutschland|germany|"
    r"kdoer|kdor|aoer|aor)\b",
    flags=re.IGNORECASE,
)

SOURCE_RANK = {
    "EuRepoC": 1,
    "UMD": 2,
    "Ransomware.live": 3,
    "KonBriefing": 4,
}


def _clean_norm(s: str) -> str:
    s = re.sub(r"\.(de|com|org|net|eu|info)\b", " ", s)
    s = LEGAL_SUFFIX_REGEX.sub(" ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return "" if (len(s) < 3 or s in GENERIC_OR_GEO_VICTIM_NAMES) else s


def extract_victim_match_keys(victim_name_str: str) -> list[str]:
    """Generate both German-transliterated (ä->ae) and vowel-stripped (ä->a) keys
    so international OSINT spellings ('Eberspacher', 'Larssen', 'Sadwestfalen') match."""
    if pd.isna(victim_name_str):
        return []
    parts = [p.strip() for p in str(victim_name_str).split(";") if p.strip()]
    keys = []
    for raw_p in parts:
        variants_raw = [raw_p]
        if "(" in raw_p:
            variants_raw.append(raw_p.split("(")[0].strip())
        for vp in variants_raw:
            low = vp.lower().replace("&", " und ").replace("ß", "ss")
            k_ae = _clean_norm(low.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue"))
            k_ascii = _clean_norm(low.replace("ä", "a").replace("ö", "o").replace("ü", "u"))
            for k in (k_ae, k_ascii):
                if k and k not in keys:
                    keys.append(k)
    return keys


def names_match(keys_a: list[str], keys_b: list[str]) -> bool:
    """Member-wise fuzzy & token-safe comparison between two incident victim lists."""
    valid_a = [a for a in keys_a if a and a not in GENERIC_OR_GEO_VICTIM_NAMES]
    valid_b = [b for b in keys_b if b and b not in GENERIC_OR_GEO_VICTIM_NAMES]
    if not valid_a or not valid_b:
        return False

    for a in valid_a:
        tokens_a = set(a.split())
        for b in valid_b:
            if a == b:
                return True
            tokens_b = set(b.split())
            shared = tokens_a & tokens_b
            distinctive_shared = [t for t in shared if len(t) >= 5 and t not in NON_DISTINCTIVE_TOKENS]
            if (tokens_a <= tokens_b or tokens_b <= tokens_a) and distinctive_shared:
                return True
            # Compound brand prefix match (e.g., 'mediamarkt' <-> 'mediamarktsaturn'), excluding generic institution prefixes
            shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
            if len(shorter) >= 8 and " " not in shorter and longer.startswith(shorter) and not shorter.startswith(GENERIC_COMPOUND_PREFIXES):
                return True
            if SequenceMatcher(None, a, b).ratio() >= 0.84:
                return True
    return False


if __name__ == "__main__":
    tests = [
        ("Baden-Württemberg", "Polizei Baden-Württemberg", False),
        ("AOK Baden-Württemberg", "Sparkassenverband Baden-Württemberg", False),
        ("Sparkasse KölnBonn", "Sparkasse Aachen", False),
        ("Stadtwerke Karlsruhe", "Stadtwerke München", False),
        ("Telekom", "Deutsche Telekom", True),
        ("Südwestfalen-IT", "Sadwestfalen IT", True),
        ("Katholische Hospitalvereinigung Ostwestfalen; Mathilden Hospital Herford", "Mathilden Hospital", True),
        ("Eberspacher Group", "Eberspächer", True),
        ("Lürssen", "Larssen", True),
        ("MediaMarkt", "MediaMarktSaturn", True),
        ("CompuGroup Medical SE & Co. KGaA (CGM)", "CompuGroup Medical", True),
    ]
    for raw_a, raw_b, expected in tests:
        ka, kb = extract_victim_match_keys(raw_a), extract_victim_match_keys(raw_b)
        got = names_match(ka, kb)
        status = "PASS" if got == expected else "FAIL"
        print(f"  [{status}] '{raw_a}' <-> '{raw_b}' => {got} (expected {expected})")
