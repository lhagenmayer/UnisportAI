"""Archive helpers: Excel -> ML-ready transformer
--------------------------------------------------
This archival script contains utilities used to transform the
original Excel sheets (course / sport descriptions) into a
numerical, ML-ready file named ``Sportangebot_ML_ready.xlsx``.

The script is older and kept in ``archiv/`` for reproducibility.
It performs tasks such as percent-to-float conversion, qualitative
value mapping, tag splitting and automatic one-hot encoding for
textual tag columns.

Note: The script is kept intentionally permissive (heuristics) and
should be reviewed before reusing on different input files.
"""

import pandas as pd
import re

# === 1. Read Excel file ===
df = pd.read_excel("Sportangebot inkl. Kategorien.xlsx")

# === 2. Convert all percentage values to numbers (0–1) ===
def percent_to_float(x):
    """Convert percentage-like strings to floats in 0..1 range.

    Examples:
        "50%" -> 0.5
        "75"  -> 75 (caller must decide if this is percent or raw)

    Args:
        x: Cell value (possibly a string containing "%").

    Returns:
        float or original value when not convertible.
    """
    if isinstance(x, str) and "%" in x:
        return float(re.sub("[^0-9.]", "", x)) / 100
    return x

df = df.applymap(percent_to_float)

# === 3. Replace qualitative values ===
replace_map = {
    "Solo": 1, "Duo": 0.5, "Team": 0,
    "High": 1, "Moderate": 0.5, "Low": 0
}
df = df.replace(replace_map)

# === 4. Automatic one-hot encoding for all tag columns ===
# (if tags in a column are stored as a list or comma-separated)
def split_tags(cell):
    if isinstance(cell, str):
        tags = re.split(r'[,;/\|]', cell)
        return [t.strip() for t in tags if t.strip()]
    return []

# We look for text columns with tags
for col in df.columns:
    if df[col].dtype == object:
        # Collect all occurring tags
        all_tags = set(tag for cell in df[col].dropna() for tag in split_tags(cell))
        # Create one column for each tag
        for tag in all_tags:
            df[tag] = df[col].apply(lambda x: 1 if isinstance(x, str) and tag in x else 0)

# === 5. Nicht-numerische Spalten entfernen, falls sie keine Zahlen enthalten ===
df_cleaned = df.select_dtypes(include=["number", "float", "int"])

# === 6. Save result ===
df_cleaned.to_excel("Sportangebot_ML_ready.xlsx", index=False)
print("✅ Datei gespeichert: Sportangebot_ML_ready.xlsx")
# ...existing code...
import pandas as pd
import numpy as np
import re

INPUT = "Sportangebot inkl. Kategorien.xlsx"
OUTPUT = "Sportangebot_ML_ready.xlsx"

# === Configuration: columns that should remain unchanged (case-insensitive) ===
# Detection function for "kurs nr" and "angebot"
def is_preserved(colname: str):
    s = re.sub(r"\s+", "", colname.lower())
    if "angebot" in s:
        return True
    if "kurs" in s and ("nr" in s or "nummer" in s or "no" in s):
        return True
    # additional exact matches:
    if s in ("kursnr","kursnummer","kurs","angebot"):
        return True
    return False

# === Rename map for focus columns (adjust as needed) ===
rename_map = {
    "focus1": "endurance",
    "focus 1": "endurance",
    "focus2": "relaxation",
    "focus 2": "relaxation",
    # add further mappings here, e.g. "focus3": "team"
}

# Helper functions
SEP_PATTERN = r'[,;/\|]+'  # Separator
QUAL_MAP = {
    "solo": 1.0, "duo": 0.5, "team": 0.0,
    "high": 1.0, "moderate": 0.5, "medium": 0.5, "low": 0.0
}

def percent_to_float_str(s: str):
    """Parse a percentage-like string and return a float.

    Tries to find a number followed by a percent sign and converts it
    to a 0..1 float. If only a number is present, heuristically
    interprets values in (1..100] as percents and divides by 100.

    Args:
        s: Input string (e.g. "45%", "75", "12,5%").

    Returns:
        Float value or ``None`` when parsing fails.
    """
    m = re.search(r"([-+]?\d+[.,]?\d*)\s*%", s)
    if m:
        val = float(m.group(1).replace(",", "."))
        return val / 100.0
    # Fallback: treat a pure number heuristically as a percent if 1 < val <= 100
    m2 = re.search(r"([-+]?\d+[.,]?\d*)", s)
    if m2:
        v = float(m2.group(1).replace(",", "."))
        if 1 < v <= 100:
            return v / 100.0
        return v
    return None

def normalize_cell(cell):
    """Normalize a single Excel cell to numeric or a cleaned string.

    Behavior:
    - ``NaN`` values are preserved.
    - Numeric types are converted to ``float``.
    - Strings are stripped and various heuristics are applied:
      percent detection, qualitative mapping (e.g. "solo" -> 1.0),
      and numeric parsing with comma-decimal handling.

    Args:
        cell: Original cell value.

    Returns:
        Normalized numeric value, ``np.nan``, or the original string
        when no numeric interpretation is possible.
    """
    if pd.isna(cell):
        return np.nan
    if isinstance(cell, (int, float, np.number)):
        val = float(cell)
        # if an integer between 2..100, probably a percentage -> do not automatically convert here
        return val
    if isinstance(cell, str):
        s = cell.strip()
        if s == "":
            return np.nan
        low = s.lower()
        # Percentage detection
        if "%" in s:
            pct = percent_to_float_str(s)
            if pct is not None:
                return float(pct)
        # Direct mapping of qualitative values
        if low in QUAL_MAP:
            return QUAL_MAP[low]
        # pure number as string
        try:
            v = float(s.replace(",", "."))
            if 1 < v <= 100:
                return v / 100.0
            return v
        except Exception:
            pass
    # if not convertible: return original string (for tag processing)
    return cell

def split_tags(cell):
    """Split a tag-like cell into individual tag strings.

    Removes parenthetical content and splits on common separators
    (comma, semicolon, slash, pipe).

    Args:
        cell: Input string containing tags.

    Returns:
        List[str] of cleaned tag tokens.
    """
    if not isinstance(cell, str):
        return []
    text = re.sub(r"\(.*?\)", "", cell)
    parts = re.split(SEP_PATTERN, text)
    return [p.strip() for p in parts if p and p.strip()]

def safe_colname(name: str):
    """Return a filesystem/column-safe lowercase identifier.

    Converts characters not matching ``\w`` to underscores and trims
    surrounding underscores.
    """
    return re.sub(r"[^\w]+", "_", name.strip().lower()).strip("_")

# === 1. Read in ===
df = pd.read_excel(INPUT, dtype=object)
orig_cols = list(df.columns)

# === 2. Prepare result frame: keep course/offer, fill remaining columns numerically ===
out = pd.DataFrame(index=df.index)

# Keep preserved columns unchanged (original values)
for c in orig_cols:
    if is_preserved(c):
        out[c] = df[c]

# === 3. Process all other columns ===
# 3a) First apply the rename map to column names (if matching columns exist)
col_rename_lookup = {}
for c in orig_cols:
    key = c.strip().lower()
    if key in rename_map:
        col_rename_lookup[c] = rename_map[key]
    else:
        
        k2 = key.replace(" ", "")
        if k2 in rename_map:
            col_rename_lookup[c] = rename_map[k2]

# Collect generated tag columns to avoid name conflicts
generated_cols = set(out.columns)

for col in orig_cols:
    if is_preserved(col):
        continue

    new_col_base = col_rename_lookup.get(col, col)  
    new_col_base_safe = safe_colname(new_col_base)

    normalized = df[col].apply(normalize_cell)

    # If all values are numeric (or NaN) -> take them over directly under the new name
    if normalized.dropna().apply(lambda x: isinstance(x, (int, float, np.number))).all():
        target = new_col_base_safe
        i = 1
        while target in generated_cols:
            target = f"{new_col_base_safe}_{i}"
            i += 1
        out[target] = normalized.astype(float)
        generated_cols.add(target)
        continue

    # Otherwise: columns contain text/tags -> split into binary tag columns
    # Collect all tags
    all_tags = set()
    for cell in normalized.dropna():
        if isinstance(cell, str):
            for t in split_tags(cell):
                all_tags.add(t)
    # If there are no multi-tags but a few distinct single values -> one-hot encode these values
    if len(all_tags) == 0:
        uniques = sorted({v for v in normalized.dropna().astype(str)})
        if len(uniques) == 1:
            colname = f"{new_col_base_safe}"
            i = 1
            while colname in generated_cols:
                colname = f"{new_col_base_safe}_{i}"
                i += 1
            out[colname] = normalized.apply(lambda x: 1.0 if str(x).strip() == uniques[0] else 0.0 if pd.notna(x) else np.nan)
            generated_cols.add(colname)
        else:
            for val in uniques:
                tag_safe = safe_colname(f"{new_col_base_safe}_{val}")
                i = 1
                tagname = tag_safe
                while tagname in generated_cols:
                    tagname = f"{tag_safe}_{i}"
                    i += 1
                out[tagname] = normalized.apply(lambda x: 1.0 if pd.notna(x) and str(x).strip() == val else 0.0)
                generated_cols.add(tagname)
        continue

    for tag in sorted(all_tags):
        tag_safe = safe_colname(f"{new_col_base_safe}_{tag}")
        i = 1
        tagname = tag_safe
        while tagname in generated_cols:
            tagname = f"{tag_safe}_{i}"
            i += 1
        out[tagname] = normalized.apply(lambda x: 1.0 if isinstance(x, str) and tag in split_tags(x) else 0.0)
        generated_cols.add(tagname)

# === 4. Optional: handle certain NaNs in numerical features (currently not imputed automatically) ===
# Example: out.fillna(0, inplace=True)  # if desired

# === 5. Save ===
out.to_excel(OUTPUT, index=False)
print(f"✅ Datei gespeichert: {OUTPUT} ({out.shape[0]} Zeilen, {out.shape[1]} Spalten)")