"""
Kleines Verifikationsskript für CI:

Prüft, ob die Tabelle `unisport_locations` in Supabase erreichbar ist und
gibt die Anzahl der aktuell vorhandenen Zeilen aus.

Wird im GitHub-Action-Workflow nach den Scraper-Skripten aufgerufen.
"""

import os
import sys

from supabase import create_client
from dotenv import load_dotenv


def main() -> int:
    # .env einlesen, falls lokal vorhanden – im CI kommen die Werte über ENV.
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print(
            "Supabase verification: SUPABASE_URL / SUPABASE_KEY nicht gesetzt – "
            "Überspringe Verifikation."
        )
        return 0

    try:
        supabase = create_client(supabase_url, supabase_key)
        # Für unsere Größenordnung reicht ein einfaches Select aus.
        resp = supabase.table("unisport_locations").select("name").execute()
        data = resp.data or []
        count = len(data)
        print(f"Supabase verification: unisport_locations hat {count} Zeilen.")
        return 0
    except Exception as e:  # pragma: no cover - nur für CI-Monitoring relevant
        # Wenn wir die Tabelle nicht lesen können (z.B. wegen Rechten/Netzwerk),
        # soll der CI-Lauf hart fehlschlagen.
        print("Supabase verification: Fehler beim Lesen von unisport_locations:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())


