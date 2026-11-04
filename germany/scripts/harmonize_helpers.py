"""
Core harmonization, entity recovery, geocoding, and enrichment helpers
for the Germany Cyber Incidents Data Preparation Pipeline.
"""
import re
from collections import Counter
import numpy as np
import pandas as pd


# ==============================================================================
# 1. TEXT & ENCODING REPAIR (Multi-pass Hybrid CP1252/Latin-1 + German Umlauts)
# ==============================================================================
FFFD_REPLACEMENTS = {
    "Baden-W\ufffdrttemberg": "Baden-Württemberg",
    "Th\ufffdringen": "Thüringen",
    "M\ufffdnchen": "München",
    "N\ufffdrnberg": "Nürnberg",
    "F\ufffdrth": "Fürth",
    "W\ufffdrzburg": "Würzburg",
    "D\ufffdsseldorf": "Düsseldorf",
    "K\ufffdln": "Köln",
    "M\ufffdnster": "Münster",
    "Osnabr\ufffdck": "Osnabrück",
    "G\ufffdppingen": "Göppingen",
    "G\ufffdttingen": "Göttingen",
    "L\ufffdbeck": "Lübeck",
    "Saarbr\ufffdcken": "Saarbrücken",
    "S\ufffddwestfalen": "Südwestfalen",
    "Stra\ufffdenbahn": "Straßenbahn",
    "Universit\ufffdts": "Universitäts",
    "Universit\ufffdt": "Universität",
    "Wirtschaftlichkeitspr\ufffdfung": "Wirtschaftlichkeitsprüfung",
    "St\ufffdrung": "Störung",
    "Gr\ufffdbener": "Gräbener",
    "Wiedenbr\ufffdck": "Wiedenbrück",
    "Fr\ufffdre": "Frère",
    "K\ufffdstner": "Kästner",
    "Kellm\ufffdnz": "Kellmünz",
    "K\ufffdhlanlagenbau": "Kühlanlagenbau",
    "f\ufffdr": "für",
    "\ufffd": "",
}


def _char_to_single_byte(ch: str):
    """Convert a mojibaked character back to its underlying 0x00-0xFF byte,
    supporting mixed Windows-1252 printable glyphs and ISO-8859-1 C1 controls."""
    try:
        return ch.encode("cp1252")
    except UnicodeEncodeError:
        code = ord(ch)
        return bytes([code]) if code < 256 else None


def _unwind_utf8_chunk(chunk: str) -> str:
    """Iteratively reverse up to 10 layers of UTF-8 decoded as CP1252/Latin-1."""
    for _ in range(10):
        if not any(ord(c) >= 0x80 for c in chunk):
            break
        buf = bytearray()
        valid = True
        for c in chunk:
            b = _char_to_single_byte(c)
            if b is None:
                valid = False
                break
            buf.extend(b)
        if not valid:
            break
        try:
            decoded = buf.decode("utf-8")
            if decoded == chunk:
                break
            chunk = decoded
        except UnicodeDecodeError:
            break
    return chunk


def fix_text_all(text) -> str:
    """Repair multi-encoded UTF-8 mojibake, Excel-corrupted quote chains,
    Unicode replacement characters, and KonBriefing mid-word A/O/U umlauts."""
    if pd.isna(text):
        return ""
    s = str(text).strip()
    if not s:
        return ""

    # Step 1: Unwind whole string and individual non-ASCII runs
    s = _unwind_utf8_chunk(s)
    s = re.sub(r"[^\x00-\x7f]+", lambda m: _unwind_utf8_chunk(m.group(0)), s)

    # Step 2: Clean residual Excel quote-broken multi-encoding artifacts in UMD
    if "Ã" in s:
        s = re.sub(r"S(?:Ã[ƒ‚†”•€¢Â\s'\"¬šžŒŽŸ¡-ÿ\x80-\x9f]+)+¼ddeutsche", "Süddeutsche", s)
        s = re.sub(r"Baden-W(?:Ã[ƒ‚†”•€¢Â\s'\"¬šžŒŽŸ¡-ÿ\x80-\x9f]+)+rttemberg", "Baden-Württemberg", s)
        s = re.sub(r"Universit(?:Ã[ƒ‚†”•€¢Â\s'\"¬šžŒŽŸ¡-ÿ\x80-\x9f]+)+t", "Universität", s)
        s = re.sub(r"L(?:Ã[ƒ‚†”•€¢Â\s'\"¬šžŒŽŸ¡-ÿ\x80-\x9f]+)+rssen", "Lürssen", s)
        s = re.sub(r"(?:Ã[ƒ‚†”•€¢Â\s'\"¬šžŒŽŸ¡-ÿ\x80-\x9f]+)+", " ", s)

    # Step 3: Repair known Unicode replacement char (\ufffd) words
    for bad, good in FFFD_REPLACEMENTS.items():
        if bad in s:
            s = s.replace(bad, good)

    # Step 4: Repair KonBriefing mid-word uppercase A/O/U German umlaut substitutions
    # (e.g. Baden-WUrttemberg -> Baden-Württemberg, fUr -> für, StAdtisches -> Städtisches)
    s = re.sub(r"(?<=[A-Za-zäöüßÄÖÜ])A(?=[a-zß])", "ä", s)
    s = re.sub(r"(?<=[A-Za-zäöüßÄÖÜ])O(?=[a-zß])", "ö", s)
    s = re.sub(r"(?<=[A-Za-zäöüßÄÖÜ])U(?=[a-zß])", "ü", s)

    return re.sub(r"\s+", " ", s).strip()


# ==============================================================================
# 2. GERMAN GEOGRAPHY (16 Bundesländer Geocoder)
# ==============================================================================
STATE_CODE_TO_BUNDESLAND = {
    "BW": "Baden-Württemberg",
    "BY": "Bavaria",
    "BE": "Berlin",
    "BB": "Brandenburg",
    "HB": "Bremen",
    "HH": "Hamburg",
    "HE": "Hesse",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Lower Saxony",
    "NW": "North Rhine-Westphalia",
    "RP": "Rhineland-Palatinate",
    "SL": "Saarland",
    "SN": "Saxony",
    "ST": "Saxony-Anhalt",
    "SH": "Schleswig-Holstein",
    "TH": "Thuringia",
}

BUNDESLAND_KEYWORDS = [
    ("Baden-Württemberg", ["baden-württemberg", "baden-wuerttemberg", "stuttgart", "karlsruhe", "mannheim", "freiburg", "heidelberg", "ulm", "heilbronn", "pforzheim", "reutlingen", "esslingen", "ludwigsburg", "tübingen", "konstanz", "offenburg", "friedrichshafen", "ravensburg", "böblingen", "göppingen", "baden-baden"]),
    ("Bavaria", ["bavaria", "bayern", "munich", "münchen", "nuremberg", "nürnberg", "augsburg", "regensburg", "ingolstadt", "würzburg", "fürth", "erlangen", "bamberg", "bayreuth", "passau", "landshut", "rosenheim", "kempten", "aschaffenburg", "schweinfurt", "coburg", "franconia", "schwaben", "allgäu"]),
    ("North Rhine-Westphalia", ["north rhine-westphalia", "nordrhein-westfalen", "cologne", "köln", "düsseldorf", "dortmund", "essen", "duisburg", "bochum", "wuppertal", "bielefeld", "bonn", "münster", "aachen", "gelsenkirchen", "mönchengladbach", "krefeld", "oberhausen", "hagen", "hamm", "leverkusen", "paderborn", "solingen", "herne", "neuss", "siegen", "gütersloh", "detmold", "südwestfalen", "ostwestfalen", "rhein-ruhr", "hemer"]),
    ("Hesse", ["hesse", "hessen", "frankfurt", "wiesbaden", "kassel", "darmstadt", "offenbach", "hanau", "giessen", "gießen", "marburg", "fulda", "rüsselsheim", "bad homburg", "wetzlar", "limburg"]),
    ("Lower Saxony", ["lower saxony", "niedersachsen", "hannover", "hanover", "braunschweig", "osnabrück", "oldenburg", "wolfsburg", "göttingen", "salzgitter", "hildesheim", "delmenhorst", "lüneburg", "celle", "emden", "wilhelmshaven", "hameln", "cuxhaven"]),
    ("Rhineland-Palatinate", ["rhineland-palatinate", "rheinland-pfalz", "mainz", "ludwigshafen", "koblenz", "trier", "kaiserslautern", "worms", "neuwied", "speyer", "bad kreuznach", "frankenthal", "landau"]),
    ("Saxony", ["saxony-anhalt", "sachsen-anhalt"]),  # Placeholder guard handled below
    ("Saxony-Anhalt", ["saxony-anhalt", "sachsen-anhalt", "magdeburg", "halle (saale)", "halle", "dessau", "bitterfeld", "anhalt-bitterfeld", "wittenberg", "stendal", "halberstadt", "harz"]),
    ("Saxony", ["saxony", "sachsen", "leipzig", "dresden", "chemnitz", "zwickau", "plauen", "görlitz", "freiberg", "bautzen", "pirna"]),
    ("Schleswig-Holstein", ["schleswig-holstein", "kiel", "lübeck", "flensburg", "neumünster", "norderstedt", "elmshorn", "pinneberg", "itzehoe", "husum"]),
    ("Brandenburg", ["brandenburg", "potsdam", "cottbus", "frankfurt (oder)", "oranienburg", "falkensee", "eberswalde", "senftenberg", "lausitz"]),
    ("Thuringia", ["thuringia", "thüringen", "erfurt", "jena", "gera", "weimar", "gotha", "eisenach", "nordhausen", "suhl", "ilmenau"]),
    ("Mecklenburg-Vorpommern", ["mecklenburg-vorpommern", "mecklenburg-western pomerania", "rostock", "schwerin", "neubrandenburg", "stralsund", "greifswald", "wismar", "rügen"]),
    ("Saarland", ["saarland", "saarbrücken", "neunkirchen", "homburg", "völklingen", "saarlouis", "merzig", "wadern"]),
    ("Berlin", ["berlin"]),
    ("Hamburg", ["hamburg"]),
    ("Bremen", ["bremen", "bremerhaven"]),
]


def extract_bundesland(location_str: str = "", extra_text: str = "") -> str:
    """Resolve German federal state (Bundesland) from state code, location, or description."""
    loc_clean = fix_text_all(location_str)
    m = re.search(r",\s*([A-Z]{2})\b", loc_clean)
    if m and m.group(1) in STATE_CODE_TO_BUNDESLAND:
        return STATE_CODE_TO_BUNDESLAND[m.group(1)]

    combined = f"{loc_clean} {fix_text_all(extra_text)}".lower()
    # Check Saxony-Anhalt and Lower Saxony BEFORE Saxony!
    ordered = [b for b in BUNDESLAND_KEYWORDS if b[0] != "Saxony"] + [b for b in BUNDESLAND_KEYWORDS if b[0] == "Saxony"]
    # Deduplicate ordered list properly
    seen = set()
    final_ordered = []
    for name, kws in ordered:
        if name not in seen and not (name == "Saxony" and kws == ["saxony-anhalt", "sachsen-anhalt"]):
            seen.add(name)
            final_ordered.append((name, kws))

    for state_name, kws in final_ordered:
        for kw in kws:
            if re.search(r"\b" + re.escape(kw) + r"\b", combined):
                return state_name

    if any(k in combined for k in ["bundestag", "bundeswehr", "bundespolizei", "federal ", "chancellery", "bundeskanzler", "bafin"]):
        return "Federal / Nationwide"
    return "Unknown"


# ==============================================================================
# 3. HARMONIZED 10-SECTOR TAXONOMY (Structured Maps First + Word-Bounded Regex)
# ==============================================================================
UMD_NAICS_DIRECT_MAP = {
    "Utilities": "Energy & Utilities",
    "Mining, Quarrying, and Oil and Gas Extraction": "Energy & Utilities",
    "Manufacturing": "Manufacturing & Industry",
    "Finance and Insurance": "Finance & Insurance",
    "Finance And Insurance": "Finance & Insurance",
    "Finance and insurance": "Finance & Insurance",
    "Information": "IT & Telecommunications",
    "Transportation and Warehousing": "Transportation & Logistics",
    "Educational Services": "Education & Research",
    "Health Care and Social Assistance": "Healthcare",
    "Health Care And Social Assistance": "Healthcare",
    "Public Administration": "Public Administration & Government",
    "Retail Trade": "Retail, Trade & Services",
    "Wholesale Trade": "Retail, Trade & Services",
    "Accommodation and Food Services": "Retail, Trade & Services",
    "Construction": "Retail, Trade & Services",
    "Real Estate and Rental and Leasing": "Retail, Trade & Services",
    "Management of Companies and Enterprises": "Retail, Trade & Services",
    "Arts, Entertainment, and Recreation": "Media, NGOs & Other",
}

EUREPOC_SUBCAT_MAP = {
    "Civil service / administration": "Public Administration & Government",
    "Government / ministries": "Public Administration & Government",
    "Police": "Public Administration & Government",
    "Military": "Public Administration & Government",
    "Legislative": "Public Administration & Government",
    "Intelligence agencies": "Public Administration & Government",
    "Judiciary": "Public Administration & Government",
    "Election infrastructure / related systems": "Public Administration & Government",
    "Political parties": "Media, NGOs & Other",
    "Health": "Healthcare",
    "Research": "Education & Research",
    "Critical Manufacturing": "Manufacturing & Industry",
    "Defence industry": "Manufacturing & Industry",
    "Chemicals": "Manufacturing & Industry",
    "Space": "Manufacturing & Industry",
    "Energy": "Energy & Utilities",
    "Water": "Energy & Utilities",
    "Waste Water Management": "Energy & Utilities",
    "Telecommunications": "IT & Telecommunications",
    "Digital Provider": "IT & Telecommunications",
    "Finance": "Finance & Insurance",
    "Transportation": "Transportation & Logistics",
    "Food": "Retail, Trade & Services",
    "Religious": "Media, NGOs & Other",
    "Advocacy / activists (e.g. human rights organizations)": "Media, NGOs & Other",
    "Political opposition / dissidents / expats": "Media, NGOs & Other",
    "Other social groups": "Media, NGOs & Other",
}

EUREPOC_CAT_MAP = {
    "State institutions / political system": "Public Administration & Government",
    "Education": "Education & Research",
    "Science": "Education & Research",
    "Media": "Media, NGOs & Other",
    "Social groups": "Media, NGOs & Other",
    "International / supranational organization": "Public Administration & Government",
}

SECTOR_PATTERNS = [
    ("Energy & Utilities", r"\b(stadtwerke|utilit\w*|energ\w*|power plant\w*|power grid|electricity|wind turbine\w*|solar\w*|water supply|wastewater|abwasser|entsorgung|waste disposal|gasnetz|fernwärme|oil refinery|pipelines?)\b"),
    ("Healthcare", r"\b(health\s*care|healthcare|hospitals?|clinics?|klinik\w*|krankenhaus\w*|universitätsklinik\w*|universitätsmedizin|medical|pharma\w*|biotech\w*|apotheke\w*|zahnärzt\w*|ärztekammer|red cross|rotes kreuz|pflege\w*|sanitätshaus|fertility center|drk)\b"),
    ("Education & Research", r"\b(universit\w*|hochschul\w*|volkshochschul\w*|schools?|schul\w*|gymnasium|realschule|education\w*|college\w*|fraunhofer|max[- ]planck|helmholtz|leibniz|research center|research institute\w*|forschungs\w*|akademie|boarding school)\b"),
    ("Finance & Insurance", r"\b(banks?|banking|sparkasse\w*|volksbank\w*|raiffeisenbank\w*|landesbank|dz bank|deutsche bank|targobank|commerzbank|bafin|insur\w*|versicherung\w*|krankenkasse\w*|aok|unfallkasse|vbg|leasing|financial|asset management|credit|payment|wallet)\b"),
    ("IT & Telecommunications", r"\b(it service\w*|it provider\w*|it[- ]dienstleist\w*|software\w*|telekom\w*|telecom\w*|telefonica|vodafone|hosting|cloud|datacenter|rechenzentrum|datenverarbeitung|südwestfalen[- ]it|teamviewer|anydesk|tutanota|opensuse|mastodon|telegram|cyber\s*security|blockchain|web3|internet provider|domain)\b"),
    ("Transportation & Logistics", r"\b(airports?|flughafen|airlines?|lufthansa|aviation|railways?|deutsche bahn|straßenbahn|verkehrsbetrieb\w*|public transit|mass transit|logistics|logistik\w*|spedition|shipping|maritime|harbor|ports?|warehous\w*|car rental|sixt|cab service)\b"),
    ("Manufacturing & Industry", r"\b(manufactur\w*|automotive|automobil\w*|industrial|machinery|maschinenbau\w*|metall\w*|steel\w*|thyssenkrupp|rheinmetall|continental|siemens|basf|covestro|henkel|symrise|eberspächer|lürssen|bilstein|mahle|zeiss|trumpf|chemical\w*|electronics|aerospace|factory|plant engineering|packaging|verpackung\w*|shipyard|werft|thermotechnolog\w*|semiconductor\w*|tire\w*|plastics?|glas\w*|textil\w*|holz\w*|heating|heizung\w*)\b"),
    ("Public Administration & Government", r"\b(public administration|municipal\w*|municipality|town hall|rathaus|stadtverwaltung|gemeindeverwaltung|kreisverwaltung|landkreis|landratsamt|bezirksamt|bürgeramt|city administration|city government|district administration|county administration|ministr\w+|bundestag|bundesrat|bundeswehr|bundeskanzler\w*|chancellery|parliaments?|police|polizei|law enforcement|customs|zoll|courts?|amtsgericht|landesamt|bundesamt|behörde|state portal|government|mayor|election)\b"),
    ("Retail, Trade & Services", r"\b(retail\w*|wholesal\w*|e-commerce|online shop|online marketplace|department store|kadewe|mediamarkt\w*|supermarket\w*|grocer\w*|food|beverage|brauerei|hotels?|hospitality|gastronomie|real estate|immobilien\w*|wohnungsbau\w*|housing|construction|bau\w*|law firms?|legal|rechtsanw\w*|bar association|brak|consulting|berat\w*|accounting|wirtschaftsprüf\w*|steuerberat\w*|architect\w*|engineering office|ingenieurbüro|chambers? of commerce|handwerkskammer\w*|ihk|dihk|tourism|tourist)\b"),
    ("Media, NGOs & Other", r"\b(media|newspapers?|zeitung\w*|verlag\w*|publish\w*|broadcast\w*|radio|rundfunk|television|film festival|berlinale|museums?|landes?museum|concert hall|theater|theatre|church\w*|kirch\w*|evangelisch\w*|katholisch\w*|diakonie|caritas|paritätisch\w*|welfare|wohlfahrt\w*|social service\w*|humanitarian|associations?|verband|verein|stiftung|foundation|political part\w*|cdu|spd|grüne|fdp|linke|piratenpartei|unions?|gewerkschaft\w*|sports?|olympic|luge|football|bundesliga|gema)\b"),
]


def classify_sector_by_text(text: str, default: str = "Unknown") -> str:
    """Classify sector using strict word-bounded regexes ordered by specificity."""
    t = fix_text_all(text).lower()
    if not t or t in {"unknown", "undetermined", "not available", "not found", "nan"}:
        return default
    for sector_name, pattern in SECTOR_PATTERNS:
        if re.search(pattern, t):
            return sector_name
    return default


def resolve_umd_sector(industry: str, org: str, desc: str) -> str:
    """Map UMD sector using NAICS industry first, except for broad catch-all NAICS 54, 56, 81, and 99."""
    ind = fix_text_all(industry)
    org_desc = f"{fix_text_all(org)} {fix_text_all(desc)}"
    if ind in {"Professional, Scientific, and Technical Services",
               "Other Services (except Public Administration)",
               "Administrative and Support and Waste Management and Remediation Services",
               "Undetermined", ""}:
        by_text = classify_sector_by_text(org_desc, default="")
        if by_text:
            return by_text
        if ind == "Professional, Scientific, and Technical Services":
            return "Retail, Trade & Services"
        if ind == "Other Services (except Public Administration)":
            return "Media, NGOs & Other"
        if ind == "Administrative and Support and Waste Management and Remediation Services":
            return "Retail, Trade & Services"
        return "Unknown"
    # Even for direct NAICS, check obvious IT software providers miscoded under Wholesale (e.g. Medatixx, Kisters AG)
    if ind in {"Wholesale Trade"} and re.search(r"\b(medatixx|kisters|software)\b", org_desc.lower()):
        return "IT & Telecommunications"
    return UMD_NAICS_DIRECT_MAP.get(ind, classify_sector_by_text(f"{ind} {org_desc}", default="Unknown"))


def resolve_eurepoc_receiver_row_sector(cat: str, subcat: str, rec_name: str, fallback_text: str = "") -> str:
    """Map a single EuRepoC German receiver slot to one of the 10 harmonized sectors."""
    sub_c = fix_text_all(subcat)
    cat_c = fix_text_all(cat)
    name_c = fix_text_all(rec_name)

    if sub_c in EUREPOC_SUBCAT_MAP:
        return EUREPOC_SUBCAT_MAP[sub_c]
    if cat_c in EUREPOC_CAT_MAP:
        return EUREPOC_CAT_MAP[cat_c]
    # Corporate Targets or Unknown -> inspect receiver name first, then incident description
    by_name = classify_sector_by_text(name_c, default="")
    if by_name:
        return by_name
    by_fb = classify_sector_by_text(fallback_text, default="")
    if by_fb:
        return by_fb
    return "Retail, Trade & Services" if "Corporate Targets" in cat_c else "Unknown"


# ==============================================================================
# 5. SEVERITY SCORING & THREAT VECTOR ENRICHMENT HELPERS
# ==============================================================================

KRITIS_SECTORS = {
    "Energy & Utilities",
    "Healthcare",
    "IT & Telecommunications",
    "Transportation & Logistics",
    "Finance & Insurance",
    "Public Administration & Government",
}

CASCADE_KEYWORDS = [
    r"\bsüdwestfalen[- ]it\b", r"\bkaseya\b", r"\bmoveit\b", r"\bmedatixx\b",
    r"\bitzbund\b", r"\bsupply chain\b", r"\bthird[- ]party\b", r"\bit[- ]dienstleist\w*\b",
    r"\bsoftware update\b", r"\bviasat\b", r"\bverwaltungsportal\b", r"\bcloud provider\b",
]

ZERO_DAY_REGEX = re.compile(
    r"\b(zero[- ]day|0[- ]day|zero[- ]click|cve-20\d{2}-\d{4,5}\s+exploited as a zero[- ]day)\b",
    flags=re.IGNORECASE,
)


def is_cascade(text: str) -> bool:
    """Check if the incident text indicates a cascading / supply-chain attack."""
    t = fix_text_all(text).lower()
    return any(re.search(pat, t) for pat in CASCADE_KEYWORDS)


def is_zero_day(text: str) -> bool:
    """Check if the incident exploited an unpatched zero-day vulnerability."""
    t = fix_text_all(text).lower()
    return bool(ZERO_DAY_REGEX.search(t))


def calc_severity_score(
    attack_type: str,
    functional_impact: str,
    has_disruption: any,
    has_data_theft: any,
    is_kritis: bool,
    native_eurepoc_intensity: float = None,
) -> int:
    """
    Standardize incident severity onto an objective 1-5 integer scale:
    1: Minor probe / non-disruptive reconnaissance / unsuccessful attempt
    2: Short disruption (<24h) or non-critical minor breach (baseline targeted incident)
    3: Multi-day disruption (<7d) OR significant confidential data exfiltration
    4: Multi-week downtime (Weeks+) OR KRITIS disruption OR double-extortion ransomware
    5: Complete paralyzed organizational loss / national critical service outage
    """
    if pd.notna(native_eurepoc_intensity):
        raw_int = float(native_eurepoc_intensity)
        if raw_int >= 9.0:
            return 5
        elif raw_int >= 6.0:
            return 4
        elif raw_int >= 4.0:
            return 3
        elif raw_int >= 2.0:
            return 2
        else:
            return 1

    score = 2  # Baseline for any verified targeted cyber incident
    if functional_impact == "Weeks+":
        score = 4
    elif functional_impact == "Days (< 7d)":
        score = 3
    elif functional_impact == "Hours (< 24h)":
        score = 2

    # Double extortion elevates severity
    if has_disruption is True and has_data_theft is True:
        score = max(score, 3)

    # KRITIS sector target experiencing downtime
    if is_kritis and has_disruption is True:
        score = max(score, 4 if functional_impact in ("Days (< 7d)", "Weeks+") else 3)

    if attack_type == "Ransomware":
        score = max(score, 3)

    return min(5, max(1, score))


# ==============================================================================
# 6. STRICT NON-FABRICATION FILTERS FOR VICTIM NAMES & DESCRIPTIONS
# ==============================================================================

_GENERIC_VICTIM_SET = {
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
    "berlin de", "unternehmen",
}


def clean_victim_name(raw_name: any):
    """Return a clean specific organization name, or np.nan if the raw value is
    missing, a generic category label ('town hall', 'law enforcement'), or a bare city/state name."""
    if pd.isna(raw_name):
        return np.nan
    v = fix_text_all(str(raw_name)).strip()
    if not v:
        return np.nan
    low = v.lower().replace("ß", "ss")
    low_ae = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", low.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue"))).strip()
    low_ascii = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", low.replace("ä", "a").replace("ö", "o").replace("ü", "u"))).strip()
    if low in _GENERIC_VICTIM_SET or low_ae in _GENERIC_VICTIM_SET or low_ascii in _GENERIC_VICTIM_SET:
        return np.nan
    return v


_JUNK_DESCRIPTION_PATTERNS = re.compile(
    r"^(?:\[ai generated\]\s*\"?n/a\"?|data is not available now\.?|description not available\.?|"
    r"\[unpublished\]|germany|country\s*:\s*germany|united states|south korea|berlin,\s*germany|"
    r"baden-w[uü]e?rttemberg,\s*germany|nordrhein[- ]westfalen,\s*germany|full leak|unternehmen|"
    r"manufacturing|business services|data collection.*|\d+(?:\.\d+)?\s*(?:gb|tb|mb)|"
    r"revenue\s*:\s*.*|zip-\d+.*)$",
    flags=re.IGNORECASE,
)


def clean_description(raw_desc: any):
    """Return a genuine narrative incident description, or np.nan if the raw value
    is missing, a placeholder ('[AI generated] N/A', 'Germany'), or a bare domain/label."""
    if pd.isna(raw_desc):
        return np.nan
    d = fix_text_all(str(raw_desc)).strip()
    if not d or d.lower() in ("nan", "none", "unknown", "not available", "n/a", "undetermined"):
        return np.nan
    if _JUNK_DESCRIPTION_PATTERNS.match(d):
        return np.nan
    # Filter out bare domain names or single-word/two-word labels under 25 characters without verbs
    if len(d) < 25 and (" " not in d or re.match(r"^[a-z0-9.\-]+\.[a-z]{2,}$", d.lower())):
        return np.nan
    return d


if __name__ == "__main__":
    from pathlib import Path
    SCRIPT_DIR = Path(__file__).resolve().parent
    RAW = SCRIPT_DIR.parent / "data" / "raw" if (SCRIPT_DIR.parent / "data" / "raw").is_dir() else SCRIPT_DIR / "raw"
    umd = pd.read_excel(RAW / "umd_cyber_events.xlsx")
    ude = umd[(umd["country"] == "Germany") | (umd["country_iso3"] == "DEU")].copy()
    secs = [resolve_umd_sector(i, o, d) for i, o, d in zip(ude["industry"], ude["organization"], ude["description"])]
    print("UMD new sector distribution:")
    print(pd.Series(secs).value_counts())
