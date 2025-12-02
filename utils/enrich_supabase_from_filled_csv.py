from pathlib import Path

import pandas as pd

from .export_supabase_csv import _create_supabase_client, ROOT_DIR, EXPORT_DIR


def push_filled_offers_to_supabase():
    """
    Liest die von Hand angereicherte CSV
    `assets/exports/sportangebote_all_filled.csv` ein und schreibt
    die Werte für intensity, focus und setting zurück nach Supabase
    in die Tabelle `sportangebote`.

    Annahme: Die CSV ist die „Source of Truth“ für diese drei Felder.
    D.h. vorhandene Werte in Supabase werden durch die in der CSV
    überschrieben, sofern sie dort nicht leer sind.
    """
    csv_path = EXPORT_DIR / "sportangebote_all_filled.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV-Datei nicht gefunden: {csv_path}")

    df = pd.read_csv(csv_path)
    required_cols = {"href", "intensity", "focus", "setting"}
    missing = required_cols - set(df.columns)
    if missing:
        raise RuntimeError(
            f"Erwartete Spalten in CSV fehlen: {missing} "
            f"in Datei {csv_path}"
        )

    client = _create_supabase_client()

    updates = 0
    for _, row in df.iterrows():
        href = row.get("href")
        if not isinstance(href, str) or not href.strip():
            continue

        update_data = {}

        intensity = row.get("intensity")
        if isinstance(intensity, str):
            intensity = intensity.strip().lower()
        if intensity:
            update_data["intensity"] = intensity

        focus_raw = row.get("focus")
        if isinstance(focus_raw, str):
            focus_tags = [t.strip().lower() for t in focus_raw.split(";") if t.strip()]
            if focus_tags:
                update_data["focus"] = focus_tags

        setting_raw = row.get("setting")
        if isinstance(setting_raw, str):
            setting_tags = [t.strip().lower() for t in setting_raw.split(";") if t.strip()]
            if setting_tags:
                update_data["setting"] = setting_tags

        if not update_data:
            continue

        client.table("sportangebote").update(update_data).eq("href", href).execute()
        updates += 1

    print(f"{updates} Angebote in Supabase mit Werten aus 'sportangebote_all_filled.csv' aktualisiert.")


if __name__ == "__main__":
    push_filled_offers_to_supabase()


