import pandas as pd
import re

# === 1. Excel einlesen ===
df = pd.read_excel("Sportangebot inkl. Kategorien.xlsx")

# === 2. Alle Prozentwerte in Zahlen (0–1) umwandeln ===
def percent_to_float(x):
    if isinstance(x, str) and "%" in x:
        return float(re.sub("[^0-9.]", "", x)) / 100
    return x

df = df.applymap(percent_to_float)

# === 3. Qualitative Werte ersetzen ===
replace_map = {
    "Solo": 1, "Duo": 0.5, "Team": 0,
    "High": 1, "Moderate": 0.5, "Low": 0
}
df = df.replace(replace_map)

# === 4. Automatische One-Hot-Encoding für alle Tags-Spalten ===
# (falls Tags in einer Spalte als Liste oder Komma-getrennt stehen)
def split_tags(cell):
    if isinstance(cell, str):
        tags = re.split(r'[,;/\|]', cell)
        return [t.strip() for t in tags if t.strip()]
    return []

# Wir suchen nach Textspalten mit Tags
for col in df.columns:
    if df[col].dtype == object:
        # Alle vorkommenden Tags sammeln
        all_tags = set(tag for cell in df[col].dropna() for tag in split_tags(cell))
        # Für jeden Tag eine Spalte anlegen
        for tag in all_tags:
            df[tag] = df[col].apply(lambda x: 1 if isinstance(x, str) and tag in x else 0)

# === 5. Nicht-numerische Spalten entfernen, falls sie keine Zahlen enthalten ===
df_cleaned = df.select_dtypes(include=["number", "float", "int"])

# === 6. Ergebnis speichern ===
df_cleaned.to_excel("Sportangebot_ML_ready.xlsx", index=False)
print("✅ Datei gespeichert: Sportangebot_ML_ready.xlsx")
# ...existing code...
import pandas as pd
import numpy as np
import re

INPUT = "Sportangebot inkl. Kategorien.xlsx"
OUTPUT = "Sportangebot_ML_ready.xlsx"

# === Konfiguration: Spalten, die unverändert bleiben sollen (case-insensitive) ===
# Erkennungsfunktion für "kurs nr" und "angebot"
def is_preserved(colname: str):
    s = re.sub(r"\s+", "", colname.lower())
    if "angebot" in s:
        return True
    if "kurs" in s and ("nr" in s or "nummer" in s or "no" in s):
        return True
    # genaue Matches zusätzlich:
    if s in ("kursnr","kursnummer","kurs","angebot"):
        return True
    return False

# === Umbenennungs-Map für Focus-Spalten (anpassen nach Bedarf) ===
rename_map = {
    "focus1": "endurance",
    "focus 1": "endurance",
    "focus2": "relaxation",
    "focus 2": "relaxation",
    # weitere Zuordnungen hier hinzufügen, z.B. "focus3": "team"
}

# Hilfsfunktionen
SEP_PATTERN = r'[,;/\|]+'  # Trenner für Tag-Felder

QUAL_MAP = {
    "solo": 1.0, "duo": 0.5, "team": 0.0,
    "high": 1.0, "moderate": 0.5, "medium": 0.5, "low": 0.0
}

def percent_to_float_str(s: str):
    m = re.search(r"([-+]?\d+[.,]?\d*)\s*%", s)
    if m:
        val = float(m.group(1).replace(",", "."))
        return val / 100.0
    # Fallback: reine Zahl heuristisch als Prozent, wenn 1<val<=100
    m2 = re.search(r"([-+]?\d+[.,]?\d*)", s)
    if m2:
        v = float(m2.group(1).replace(",", "."))
        if 1 < v <= 100:
            return v / 100.0
        return v
    return None

def normalize_cell(cell):
    if pd.isna(cell):
        return np.nan
    if isinstance(cell, (int, float, np.number)):
        val = float(cell)
        # falls eine ganze Zahl zwischen 2..100 vermutlich Prozent -> nicht automatisch konvertieren hier
        return val
    if isinstance(cell, str):
        s = cell.strip()
        if s == "":
            return np.nan
        low = s.lower()
        # Prozenterkennung
        if "%" in s:
            pct = percent_to_float_str(s)
            if pct is not None:
                return float(pct)
        # direktes Mapping qualitative
        if low in QUAL_MAP:
            return QUAL_MAP[low]
        # reine Zahl als String
        try:
            v = float(s.replace(",", "."))
            if 1 < v <= 100:
                return v / 100.0
            return v
        except Exception:
            pass
    # falls nicht konvertierbar: retourniere Original string (für Tag-Processing)
    return cell

def split_tags(cell):
    if not isinstance(cell, str):
        return []
    text = re.sub(r"\(.*?\)", "", cell)  # Klammerinhalt entfernen
    parts = re.split(SEP_PATTERN, text)
    return [p.strip() for p in parts if p and p.strip()]

def safe_colname(name: str):
    return re.sub(r"[^\w]+", "_", name.strip().lower()).strip("_")

# === 1. Einlesen ===
df = pd.read_excel(INPUT, dtype=object)
orig_cols = list(df.columns)

# === 2. Ergebnis-Frame vorbereiten: bewahre Kurs/Angebot, fülle restliche Spalten numerisch ===
out = pd.DataFrame(index=df.index)

# Erhalte preserved columns unverändert (Originalwerte)
for c in orig_cols:
    if is_preserved(c):
        out[c] = df[c]

# === 3. Verarbeite alle anderen Spalten ===
# 3a) Zuerst rename map anwenden auf Spaltennamen (falls passende existieren)
col_rename_lookup = {}
for c in orig_cols:
    key = c.strip().lower()
    if key in rename_map:
        col_rename_lookup[c] = rename_map[key]
    else:
        # auch versuchen ohne Leerzeichen
        k2 = key.replace(" ", "")
        if k2 in rename_map:
            col_rename_lookup[c] = rename_map[k2]

# Sammle generierte Tag-Spalten um Namenskonflikte zu vermeiden
generated_cols = set(out.columns)

for col in orig_cols:
    if is_preserved(col):
        continue

    new_col_base = col_rename_lookup.get(col, col)  # entweder gemappt oder Originalname
    new_col_base_safe = safe_colname(new_col_base)

    # Normalisiere Zellen
    normalized = df[col].apply(normalize_cell)

    # Falls alle Werte numerisch (oder NaN) -> direkt übernehmen unter neuem Namen
    if normalized.dropna().apply(lambda x: isinstance(x, (int, float, np.number))).all():
        # sichere Spaltenbezeichnung
        target = new_col_base_safe
        i = 1
        while target in generated_cols:
            target = f"{new_col_base_safe}_{i}"
            i += 1
        out[target] = normalized.astype(float)
        generated_cols.add(target)
        continue

    # Sonst: Spalten enthalten Text / Tags -> splitten in binäre Tag-Spalten
    # Sammle alle Tags
    all_tags = set()
    for cell in normalized.dropna():
        if isinstance(cell, str):
            for t in split_tags(cell):
                all_tags.add(t)
    # Wenn keine multi-tags, aber wenige distinct single-values -> One-Hot für diese Werte
    if len(all_tags) == 0:
        # verbleibende unique string values
        uniques = sorted({v for v in normalized.dropna().astype(str)})
        # falls nur ein einzelner unique Wert -> mappe auf 1/0
        if len(uniques) == 1:
            colname = f"{new_col_base_safe}"
            i = 1
            while colname in generated_cols:
                colname = f"{new_col_base_safe}_{i}"
                i += 1
            out[colname] = normalized.apply(lambda x: 1.0 if str(x).strip() == uniques[0] else 0.0 if pd.notna(x) else np.nan)
            generated_cols.add(colname)
        else:
            # One-hot für alle unique strings
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

    # Erstelle binäre Spalte pro Tag
    for tag in sorted(all_tags):
        tag_safe = safe_colname(f"{new_col_base_safe}_{tag}")
        i = 1
        tagname = tag_safe
        while tagname in generated_cols:
            tagname = f"{tag_safe}_{i}"
            i += 1
        out[tagname] = normalized.apply(lambda x: 1.0 if isinstance(x, str) and tag in split_tags(x) else 0.0)
        generated_cols.add(tagname)

# === 4. Optional: bestimmte NaNs in numerischen Eigenschaften behandeln (aktuell nicht automatisch imputiert) ===
# Beispiel: out.fillna(0, inplace=True)  # falls gewünscht

# === 5. Speichern ===
out.to_excel(OUTPUT, index=False)
print(f"✅ Datei gespeichert: {OUTPUT} ({out.shape[0]} Zeilen, {out.shape[1]} Spalten)")