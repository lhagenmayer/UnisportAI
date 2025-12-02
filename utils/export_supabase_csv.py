import os
from pathlib import Path

import pandas as pd
from supabase import create_client


ROOT_DIR = Path(__file__).resolve().parents[1]
SECRETS_PATH = ROOT_DIR / ".streamlit" / "secrets.toml"
EXPORT_DIR = ROOT_DIR / "assets" / "exports"


def _read_supabase_credentials():
    """
    Liest SUPABASE_URL und SUPABASE_KEY aus .streamlit/secrets.toml,
    ohne eine zusätzliche TOML-Library zu benötigen.
    Erwartet Zeilen im Format:
        SUPABASE_URL = "..."
        SUPABASE_KEY = "..."
    """
    url = None
    key = None

    if not SECRETS_PATH.exists():
        raise FileNotFoundError(f"Secrets-Datei nicht gefunden: {SECRETS_PATH}")

    with SECRETS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("SUPABASE_URL"):
                # SUPABASE_URL = "https://...supabase.co"
                _, value = stripped.split("=", 1)
                url = value.strip().strip('"').strip("'")
            elif stripped.startswith("SUPABASE_KEY"):
                _, value = stripped.split("=", 1)
                key = value.strip().strip('"').strip("'")

    if not url or not key:
        raise RuntimeError(
            "Konnte SUPABASE_URL oder SUPABASE_KEY nicht aus secrets.toml lesen. "
            "Bitte prüfe die Datei .streamlit/secrets.toml."
        )

    return url, key


def _create_supabase_client():
    url, key = _read_supabase_credentials()
    return create_client(url, key)


def _array_to_semicolon_str(value):
    """
    Hilfsfunktion zum Konvertieren von Postgres-ARRAYs (oder None)
    in ein ';'-getrenntes String-Feld für CSV.
    """
    if value is None:
        return ""
    # Falls es bereits ein String ist, unverändert zurückgeben
    if isinstance(value, str):
        return value
    try:
        return ";".join(str(x) for x in value)
    except TypeError:
        # Fallback: einfach in String casten
        return str(value)


def _canonical_focus_tag(raw: str):
    """
    Normalisiert die Focus-Bezeichnungen aus der Excel-Datei auf die
    im Schema verwendeten Tags (balance, flexibility, coordination,
    relaxation, strength, endurance, longevity).
    """
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not raw:
        return None

    # Werte wie 'Strength (50%)' -> 'strength'
    base = raw.split("(", 1)[0].strip().lower()
    mapping = {
        "balance": "balance",
        "flexibility": "flexibility",
        "coordination": "coordination",
        "relaxation": "relaxation",
        "strength": "strength",
        "endurance": "endurance",
        "longevity": "longevity",
    }
    return mapping.get(base)


def _canonical_setting_tag(raw: str):
    """
    Normalisiert Setting_Gruppe aus der Excel-Datei auf die im Schema
    verwendeten Tags (team, fun, duo, solo, competitive).
    """
    if not isinstance(raw, str):
        return None
    base = raw.strip().lower()
    mapping = {
        "team": "team",
        "fun": "fun",
        "duo": "duo",
        "solo": "solo",
        "competition": "competitive",
        "competitive": "competitive",
    }
    return mapping.get(base)


def enrich_offers_from_excel():
    """
    Nutzt die lokale Datei 'Sportangebot inkl. Kategorien.xlsx', um
    die CSV 'sportangebote_all.csv' mit sinnvollen Werten für
    intensity, focus und setting anzureichern.

    Die Verbindung zwischen Excel und Angeboten erfolgt über:
      Excel.KursNR -> Supabase.sportkurse.kursnr -> offer_href
    und wird dann auf die Zeilen in sportangebote_all.csv (Spalte href)
    gemappt.
    """
    xlsx_path = ROOT_DIR / "Sportangebot inkl. Kategorien.xlsx"
    csv_path = EXPORT_DIR / "sportangebote_all.csv"

    if not xlsx_path.exists():
        print(f"Excel-Datei nicht gefunden, Überspringe Enrichment: {xlsx_path}")
        return
    if not csv_path.exists():
        print(f"CSV-Datei nicht gefunden, Überspringe Enrichment: {csv_path}")
        return

    # Excel einlesen
    df_x = pd.read_excel(xlsx_path)
    # Erwartete Spaltennamen prüfen
    required_cols = {"KursNR", "Angebot", "Focus 1", "Focus 2", "Focus 3", "Intensity"}
    missing = required_cols - set(df_x.columns)
    if missing:
        print(f"Fehlende Spalten in Excel, Überspringe Enrichment: {missing}")
        return

    client = _create_supabase_client()

    # Aus Supabase: Mapping KursNR -> offer_href
    courses_resp = client.table("sportkurse").select("kursnr,offer_href").execute()
    df_courses = pd.DataFrame(courses_resp.data)
    if df_courses.empty:
        print("Keine Kurse in Supabase gefunden, Überspringe Enrichment.")
        return

    # Join: Excel.KursNR -> sportkurse.kursnr
    df_x = df_x.rename(columns={"KursNR": "kursnr"})
    merged = pd.merge(df_x, df_courses, on="kursnr", how="inner")
    if merged.empty:
        print("Kein Match zwischen Excel.KursNR und sportkurse.kursnr, Überspringe Enrichment.")
        return

    # Pro offer_href aggregieren wir Intensity, Focus-Tags und Setting-Tags
    grouped = merged.groupby("offer_href")
    per_offer = {}
    for href, g in grouped:
        # Intensity: häufigster (modus) nicht-leerer Wert
        intensities = (
            g["Intensity"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.lower()
        )
        intensity = ""
        if not intensities.empty:
            intensity = intensities.mode().iloc[0]

        # Focus-Tags aus Focus 1–3
        focus_tags = set()
        for col in ["Focus 1", "Focus 2", "Focus 3"]:
            if col in g.columns:
                for raw in g[col].dropna().astype(str):
                    tag = _canonical_focus_tag(raw)
                    if tag:
                        focus_tags.add(tag)

        # Setting-Tags aus Setting_Gruppe (falls vorhanden)
        setting_tags = set()
        if "Setting_Gruppe" in g.columns:
            for raw in g["Setting_Gruppe"].dropna().astype(str):
                tag = _canonical_setting_tag(raw)
                if tag:
                    setting_tags.add(tag)

        per_offer[href] = {
            "intensity": intensity,
            "focus": sorted(focus_tags),
            "setting": sorted(setting_tags),
        }

    if not per_offer:
        print("Keine aggregierten Kategorien aus Excel, Überspringe Enrichment.")
        return

    # Bestehende CSV laden und anreichern
    df_csv = pd.read_csv(csv_path)
    if df_csv.empty or "href" not in df_csv.columns:
        print("CSV ist leer oder Spalte 'href' fehlt, Überspringe Enrichment.")
        return

    def _enrich_row(row):
        info = per_offer.get(row["href"])
        if not info:
            return row

        # Nur überschreiben, wenn im CSV noch nichts Sinnvolles steht
        # (leerer String oder NaN).
        if (pd.isna(row.get("intensity")) or not str(row.get("intensity")).strip()) and info["intensity"]:
            row["intensity"] = info["intensity"]

        if (pd.isna(row.get("focus")) or not str(row.get("focus")).strip()) and info["focus"]:
            row["focus"] = ";".join(info["focus"])

        if (pd.isna(row.get("setting")) or not str(row.get("setting")).strip()) and info["setting"]:
            row["setting"] = ";".join(info["setting"])

        return row

    df_enriched = df_csv.apply(_enrich_row, axis=1)
    df_enriched.to_csv(csv_path, index=False)
    print(f"'sportangebote_all.csv' mit Excel-Kategorien angereichert.")


def export_offers_and_quality_csvs():
    """
    Exportiert drei CSV-Dateien nach assets/exports:

    1) sportangebote_all.csv
       - alle Angebote mit Spalten: href, name, intensity, focus, setting

    2) sportangebote_ohne_kurse.csv
       - alle Angebote ohne zugehörige Kurse (per offer_href)

    3) sportkurse_ohne_termine.csv
       - alle Kurse ohne Termine (per kursnr)
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    client = _create_supabase_client()

    # --- 1. Tabellen aus Supabase lesen ---
    # Angebote (inkl. Beschreibungstext)
    offers_resp = (
        client.table("sportangebote")
        .select("href,name,description,intensity,focus,setting")
        .execute()
    )
    offers = pd.DataFrame(offers_resp.data)

    # Kurse
    courses_resp = (
        client.table("sportkurse")
        .select("kursnr,offer_href,details,preis,buchung")
        .execute()
    )
    courses = pd.DataFrame(courses_resp.data)

    # Termine
    termine_resp = client.table("kurs_termine").select("kursnr").execute()
    termine = pd.DataFrame(termine_resp.data)

    # --- 2. Daten etwas aufbereiten ---
    if not offers.empty:
        offers["intensity"] = offers["intensity"].fillna("")
        offers["focus"] = offers["focus"].apply(_array_to_semicolon_str)
        offers["setting"] = offers["setting"].apply(_array_to_semicolon_str)

    # 2a) Alle Angebote (direkt exportierbar)
    offers_all_path = EXPORT_DIR / "sportangebote_all.csv"
    offers.sort_values("name").to_csv(offers_all_path, index=False)

    # 2b) Angebote ohne Kurse:
    #     = alle hrefs, die nicht in courses.offer_href vorkommen
    if courses.empty:
        offers_without_courses = offers.copy()
    else:
        offers_with_courses = set(courses["offer_href"].dropna().unique())
        mask_no_course = ~offers["href"].isin(offers_with_courses)
        offers_without_courses = offers.loc[mask_no_course].copy()

    offers_without_courses_path = EXPORT_DIR / "sportangebote_ohne_kurse.csv"
    offers_without_courses.sort_values("name").to_csv(
        offers_without_courses_path, index=False
    )

    # 2c) Kurse ohne Termine:
    #     = alle kursnr in courses, die nicht in termine.kursnr vorkommen
    if termine.empty:
        courses_without_termine = courses.copy()
    else:
        kurs_with_termine = set(termine["kursnr"].dropna().unique())
        mask_no_termine = ~courses["kursnr"].isin(kurs_with_termine)
        courses_without_termine = courses.loc[mask_no_termine].copy()

    courses_without_termine_path = EXPORT_DIR / "sportkurse_ohne_termine.csv"
    courses_without_termine.sort_values("kursnr").to_csv(
        courses_without_termine_path, index=False
    )

    print(f"CSV-Exporte geschrieben nach: {EXPORT_DIR}")
    print(f"- {offers_all_path.name}")
    print(f"- {offers_without_courses_path.name}")
    print(f"- {courses_without_termine_path.name}")


if __name__ == "__main__":
    export_offers_and_quality_csvs()
    # Anschließend die Angebots-CSV mit den Kategorien aus der Excel-Datei anreichern
    enrich_offers_from_excel()


