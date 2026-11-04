import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import re
import pandas as pd
from harmonize_helpers import fix_text_all

RANSOMWARE_FAMILIES = [
    ("LockBit", r"\blockbit(?:\s*[23]\.0|\s*black)?\b"),
    ("Black Basta", r"\bblack\s*basta\b"),
    ("Akira", r"\bakira\b"),
    ("Play", r"\bplay\s+ransomware\b|\bplay\s+gang\b|\bgroup\s+play\b|^play$"),
    ("ALPHV / BlackCat", r"\b(?:alphv|alphvm|blackcat)\b"),
    ("Cl0p", r"\bcl[0o]p\b"),
    ("BianLian", r"\bbianlian\b"),
    ("Qilin", r"\bqilin\b|\bagenda\s+ransomware\b"),
    ("Royal", r"\broyal\s+ransomware\b|^royal$"),
    ("8Base", r"\b8base\b"),
    ("Vice Society", r"\bvice\s+society\b"),
    ("RansomHub", r"\bransomhub\b"),
    ("Conti", r"\bconti\b"),
    ("Hive", r"\bhive\s+ransomware\b|^hive$"),
    ("WannaCry", r"\bwannacry\b"),
    ("NotPetya", r"\bnotpetya\b|\bpetya\b"),
    ("REvil / Sodinokibi", r"\brevil\b|\bsodinokibi\b"),
    ("Medusa", r"\bmedusa\b"),
    ("Cactus", r"\bcactus\b"),
    ("Rhysida", r"\brhysida\b"),
    ("NoEscape", r"\bnoescape\b"),
    ("INC Ransom", r"\binc\s*ransom\b"),
    ("SafePay", r"\bsafepay\b"),
    ("Lynx", r"\blynx\b"),
    ("Hunters International", r"\bhunters\s+international\b"),
    ("BlackSuit", r"\bblacksuit\b"),
    ("DragonForce", r"\bdragonforce\b"),
    ("Karakurt", r"\bkarakurt\b"),
    ("Snatch", r"\bsnatch\b"),
    ("RansomHouse", r"\bransom\s*house\b"),
    ("Cuba", r"\bcuba\s+ransomware\b|^cuba$"),
    ("Lorenz", r"\blorenz\b"),
    ("Babuk", r"\bbabuk\b"),
    ("Netwalker", r"\bnetwalker\b"),
    ("DoppelPaymer", r"\bdoppelpaymer\b|\bgrief\b"),
    ("Ryuk", r"\bryuk\b"),
    ("Maze", r"\bmaze\s+ransomware\b|^maze$"),
    ("Nefilim", r"\bnefilim\b"),
    ("AvosLocker", r"\bavoslocker\b"),
    ("Trigona", r"\btrigona\b"),
    ("Mallox", r"\bmallox\b"),
    ("BlackByte", r"\bblackbyte\b"),
    ("Phobos", r"\bphobos\b"),
    ("Daixin", r"\bdaixin\b"),
    ("Ragnar Locker", r"\bragnar\s*locker\b"),
    ("Monti", r"\bmonti\b"),
    ("Sarcoma", r"\bsarcoma\b"),
    ("KillSec", r"\bkillsec\b"),
    ("Cicada3301", r"\bcicada3301\b"),
    ("Meow", r"\bmeow\s+ransomware\b|^meow$"),
    ("RansomEXX", r"\bransomexx\b"),
    ("Egregor", r"\begregor\b"),
    ("Fog", r"\bfog\s+ransomware\b|^fog$"),
    ("Embargo", r"\bembargo\b"),
    ("Akira", r"\bakira\b"),
]


def extract_ransomware_family(actor_str: str = "", desc_str: str = "") -> str:
    act = fix_text_all(actor_str).strip()
    desc = fix_text_all(desc_str).strip()
    # Check actor name directly first (allows exact short names like 'Play', 'Royal', 'Hive', 'Cuba')
    for fam, pat in RANSOMWARE_FAMILIES:
        if re.search(pat, act, flags=re.I):
            return fam
    # Check description (excluding anchor-only patterns that require exact actor match)
    for fam, pat in RANSOMWARE_FAMILIES:
        if re.search(pat, desc, flags=re.I):
            return fam
    return "No Ransomware / Unknown"


def standardize_attack_type(raw_type: str, description: str = "", r_family: str = "No Ransomware / Unknown") -> str:
    rt = fix_text_all(raw_type).lower()
    desc = fix_text_all(description).lower()
    combined = f"{rt} {desc}".strip()
    if not combined or combined in {"unknown", "undetermined", "not available"}:
        return "Unknown"

    if r_family and pd.notna(r_family) and r_family != "No Ransomware / Unknown":
        return "Ransomware"
    if re.search(r"\bransomware\b|\bransomeware\b|\berpressungstrojaner\b|\bverschlüsselungstrojaner\b|\blösegeld\b|\bhacker\s+erpressen\b|\bdaten\s+verschlüsselt\b|\bsysteme\s+verschlüsselt\b|\bdouble[- ]extortion\b", combined):
        return "Ransomware"
    if re.search(r"\bencrypt(?:ed|ing|s)\b.{0,45}\b(?:systems?|servers?|networks?|data|files|computers?|it)\b", combined):
        return "Ransomware"

    if re.search(r"\bddos\b|\bdenial[- ]of[- ]service\b|\bdos attack\b|\büberlastungsangriff\w*\b", combined):
        return "DDoS / Disruption"
    if re.search(r"\bphish\w*\b|\bspear[- ]?phish\w*\b|\bsocial engineering\b|\bceo[- ]fraud\b|\bvoice clon\w*\b|\bdeepfake\b|\bspoof(?:ed)? e-?mails?\b", combined):
        return "Phishing / Social Engineering"
    if re.search(r"\bdata theft\b|\bdata breach\b|\bdoxx?ing\b|\bexfiltrat\w*\b|\bstol(?:e|en) .{0,30}\b(?:data|files|documents|emails|records|secrets)\b|\bleak(?:ed|ing)? .{0,30}\b(?:data|files|documents|passwords|credentials|records)\b|\bdatenabfluss\b|\bdatenleck\b|\bdaten\s+(?:gestohlen|erbeutet|abgeflossen|ausgespäht)\b|\bpatientendaten\s+ausgespäht\b", combined):
        return "Data Breach / Data Theft"
    if re.search(r"\bhijack\w*\b|\bintrusion\b|\bespionage\b|\bunauthorized access\b|\bunauthorised access\b|\bgained access\b|\bmalware\b|\bwiper\b|\btrojan\w*\b|\bbackdoor\b|\bdefac\w*\b|\binfiltrat\w*\b|\bschadsoftware\b|\bschadprogramm\b|\bspyware\b|\bcryptomin\w*\b|\bbitcoin\s+zu\s+schürfen\b", combined):
        return "System Intrusion / Malware"
    if "disrupt" in rt:
        return "DDoS / Disruption"
    if "exploitive" in rt or "data attack" in rt:
        return "Data Breach / Data Theft"
    return "Unknown"


if __name__ == "__main__":
    RAW = SCRIPT_DIR.parent / "data" / "raw" if (SCRIPT_DIR.parent / "data" / "raw").is_dir() else (SCRIPT_DIR / "raw" if (SCRIPT_DIR / "raw").is_dir() else SCRIPT_DIR.parent / "raw")
    umd = pd.read_excel(RAW / "umd_cyber_events.xlsx")
    ude = umd[(umd["country"] == "Germany") | (umd["country_iso3"] == "DEU")].copy()
    fams = [extract_ransomware_family(a, d) for a, d in zip(ude["actor"], ude["description"])]
    atts = [standardize_attack_type(f"{et} {es}", d, f) for et, es, d, f in zip(ude["event_type"], ude["event_subtype"], ude["description"], fams)]
    print("UMD Ransomware Families (Top 15):")
    print(pd.Series(fams).value_counts().head(15))
    print("\nUMD Attack Types:")
    print(pd.Series(atts).value_counts())
    # Verify WannaCry & Mastodon & Miniduke
    wc = ude[ude["description"].astype(str).str.contains("WannaCry", na=False)]
    print("WannaCry UMD attack_types:", [standardize_attack_type(f"{r['event_type']} {r['event_subtype']}", r["description"], extract_ransomware_family(r["actor"], r["description"])) for _, r in wc.iterrows()])
    mast = ude[ude["organization"].astype(str).str.contains("Mastodon", na=False)]
    print("Mastodon UMD attack_types:", [standardize_attack_type(f"{r['event_type']} {r['event_subtype']}", r["description"], extract_ransomware_family(r["actor"], r["description"])) for _, r in mast.iterrows()])
