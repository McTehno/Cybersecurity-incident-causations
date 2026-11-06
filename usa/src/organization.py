"""auditable organization-name consolidation for incident datasets."""

from pathlib import Path
import re
import unicodedata

import pandas as pd


UNKNOWN_PATTERNS = (
    r"\b(?:undetermined|unidentified|undisclosed|unnamed|unspecified)\b",
    r"\bunknown\s+(?:company|organization|entity|agency|victim|target|vendor)\b",
)

MULTIPLE_PATTERNS = (
    r"^(?:\d[\d,]*|eight|several|about one dozen)\s+"
    r"(?:[\w'-]+\s+){0,5}"
    r"(?:agencies|universities|companies|organizations|"
    r"restaurants|locations|websites|cities|firms)\b",
    r"^multiple\s+(?!sclerosis\b)",
    r"^group of\b",
    r"^at least (?:two|three|four|\d+)\b",
    r"\b(?:organizations|universities)\s+(?:across|in|based in)\s+the\s+u\.?s\.?\b",
    r"^colleges and universities\b",
    r"^election systems in \d+\b",
    r"^it help desks across\b",
    r"^several road signs\b",
)

PERSON_ACCOUNT_PATTERNS = (
    r"\b(?:twitter|instagram|facebook|snapchat|pinterest|gmail|social media|linkedin)\s+account\b",
    r"\b(?:customers|users|students|residents|investors|individuals)\b",
)


# Repair known text encoding artifacts
ENCODING_REPLACEMENTS = {
    "Ã¢â‚¬â„¢": "’",
    "Ã¢â‚¬Å“": "“",
    "Ã¢â‚¬Â": "”",
    "Ã¢â‚¬Ëœ": "‘",
    "Ã¢â‚¬â€œ": "–",
    "ÃƒÂ³": "ó",
    "ÃƒÂ©": "é",
    "ÃƒÂ±": "ñ",
    "ÃƒÂ¶": "ö",
    "Ã„Â": "ā",
    "Ã‚": "",
}

def _repair_encoding(value):
    for incorrect, correct in ENCODING_REPLACEMENTS.items():
        value = value.replace(incorrect, correct)
    return value



def _normalize_text(value):
    if pd.isna(value):
        return pd.NA

    value = _repair_encoding(str(value))
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value or pd.NA



def _status(value):
    if pd.isna(value):
        return "unknown"
    lowered = value.casefold()
    if any(re.search(p, lowered, re.I) for p in UNKNOWN_PATTERNS):
        return "unknown"
    if any(re.search(p, lowered, re.I) for p in MULTIPLE_PATTERNS):
        return "multiple_targets"
    if any(re.search(p, lowered, re.I) for p in PERSON_ACCOUNT_PATTERNS):
        return "individual_or_account"
    return "identified_candidate"


def consolidate_organizations(dataframe, mapping_path, column="organization"):
    """Add a standardized name and provisional review status without removing rows.

    The mapping CSV must contain two columns: original, canonical.
    Classification is conservative: 'identified_candidate' is not a verified entity.
    """
    if column not in dataframe:
        raise KeyError(f"Column not found: {column}")
    mapping_path = Path(mapping_path)
    mapping = pd.read_csv(mapping_path, dtype="string", keep_default_na=False)
    if not {"original", "canonical"}.issubset(mapping.columns):
        raise ValueError("Mapping requires 'original' and 'canonical' columns")
    mapping["original"] = mapping["original"].map(_normalize_text)
    mapping["canonical"] = mapping["canonical"].map(_normalize_text)
    if mapping["original"].isna().any() or mapping["canonical"].isna().any():
        raise ValueError("Mapping cannot contain blank names")
    if mapping["original"].duplicated().any():
        raise ValueError("Mapping contains duplicate original names")


    result = dataframe.copy()

    original = result[column].astype("string").map(_normalize_text)
    replacements = dict(zip(mapping["original"], mapping["canonical"]))

    cleaned = original.replace(replacements)
    status = original.map(_status).astype("string")

    result["organization_clean"] = cleaned.mask(status.eq("unknown"))
    result["organization_status"] = status

    # Preserve the original description of the affected target
    result["organization_target_detail"] = result[column].astype("string")

    return result

