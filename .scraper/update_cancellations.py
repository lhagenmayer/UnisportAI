import os
import re
import subprocess
from typing import List, Dict
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv

"""
Dieses Skript liest Trainingsausfälle (Absagen) und markiert passende Termine in Supabase.
Erklärung für Anfänger (nur Scratch-Erfahrung nötig):

Was passiert hier – in einfachen Schritten:
1) Wir lesen eine HSG-Webseite ein, auf der Absagen als Text stehen (Datum, Kursname, Startzeit).
2) Wir übersetzen Datum in ein technisches Format (JJJJ-MM-TT) und die Startzeit in eine Zahl (HHMM).
3) Wir fragen in unserer Datenbank die Kurse ab (Kursnummern je Kursname).
4) Für diese Kursnummern suchen wir an dem Datum die Termine und vergleichen die Startzeit.
5) Treffer werden als canceled=true gespeichert (Upsert: einfügen oder aktualisieren).

Wofür sind die Imports?
- os/dotenv: holen die Zugangsdaten (URL, KEY) aus deiner Umgebung/.env
- requests: laden die Webseite
- BeautifulSoup: hilft, aus dem Webseiten-Text reinen Text zu machen
- re: findet Datum/Zeit mit Mustern im Text
- supabase.create_client: Verbindung zur Datenbank
"""

# Mini-Tutorial (leicht verständlich):
# - Schritt 1: Absagen-Webseite laden und Text herausziehen (parse_cancellations)
# - Schritt 2: Datum in JJJJ-MM-TT umwandeln, Startzeit als HHMM-Zahl berechnen
# - Schritt 3: Kurse aus DB laden und Name→Kursnummern-Mapping bauen
# - Schritt 4: Termine am passenden Datum holen und Zeiten vergleichen
# - Schritt 5: Treffer als canceled=true upserten (keine Duplikate)


def fetch_html(url: str) -> str:
    # Browser-ähnlicher Header, damit die Seite uns wie einen normalen Besucher behandelt
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse_cancellations() -> List[Dict[str, str]]:
    url_cancel = "https://www.unisg.ch/de/universitaet/ueber-uns/beratungs-und-fachstellen/unisport/"
    html = fetch_html(url_cancel)
    if not html:
        return []
    # Schritt 1: Gesamten Text der Seite holen (ohne HTML-Tags)
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    pattern = re.compile(r"(\d{2}\.\d{2}\.\d{4})\s*,\s*([^,]+?)\s*,\s*(\d{1,2}[:\.]\d{2})")
    out: List[Dict[str, str]] = []
    # Schritt 2: Aus jedem Treffer ein kleines Dictionary bauen
    for m in pattern.finditer(text):
        date_raw = m.group(1)
        name = m.group(2).strip()
        time_raw = m.group(3).strip()
        try:
            date_iso = datetime.strptime(date_raw, "%d.%m.%Y").date().isoformat()
        except Exception:
            continue
        time_digits = re.sub(r"[^0-9]", "", time_raw)
        if len(time_digits) >= 3:
            start_hhmm = int(time_digits[:2] + time_digits[2:4])
            out.append({"offer_name": name, "datum": date_iso, "start_hhmm": start_hhmm})
    return out


def extract_start_hhmm(zeit_txt: str) -> int:
    # Schritt 3: Aus einem Text wie "18:15 - 19:15" die Startzeit 1815 als Zahl machen
    start_part = zeit_txt.split("-")[0].strip()
    digits = re.sub(r"[^0-9]", "", start_part)
    if len(digits) >= 3:
        return int(digits[:2] + digits[2:4])
    return -1


def main() -> None:
    load_dotenv()  # SUPABASE_URL und SUPABASE_KEY aus .env lesen (falls vorhanden)
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("Bitte SUPABASE_URL und SUPABASE_KEY als ENV setzen.")
        return
    supabase = create_client(supabase_url, supabase_key)

    cancellations = parse_cancellations()  # Liste von {offer_name, datum, start_hhmm}
    if not cancellations:
        print("Keine Ausfälle gefunden oder Seite nicht erreichbar.")
        return

    # Mapping Kursname(lower) -> [kursnr]
    # Wir holen die Kurse gesammelt aus der DB, um offer_name → kursnr zu bilden
    resp = supabase.table("sportkurse").select("kursnr, offer_name").execute()  # Kurse laden
    kurs_rows = resp.data or []
    name_to_kursnrs: Dict[str, List[str]] = {}
    for row in kurs_rows:
        key = (row.get("offer_name") or "").strip().lower()
        if not key or not row.get("kursnr"):
            continue
        name_to_kursnrs.setdefault(key, []).append(row["kursnr"])

    rows_to_upsert: List[Dict[str, object]] = []
    for canc in cancellations:  # jeden Ausfall prüfen
        key = canc["offer_name"].strip().lower()
        kursnrs = name_to_kursnrs.get(key, [])
        if not kursnrs:
            continue
        resp2 = (
            supabase.table("kurs_termine")
            .select("kursnr, datum, zeit")
            .in_("kursnr", kursnrs)
            .eq("datum", canc["datum"])
            .execute()
        )
        term_rows = resp2.data or []
        for tr in term_rows:
            if extract_start_hhmm(tr.get("zeit", "")) == canc["start_hhmm"]:
                rows_to_upsert.append({"kursnr": tr["kursnr"], "datum": tr["datum"], "canceled": True})

    if rows_to_upsert:
        # Deduplizieren
        seen = set()
        uniq: List[Dict[str, object]] = []
        for r in rows_to_upsert:
            k = (r["kursnr"], r["datum"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        # Schritt 5: Idempotentes Upsert pro (kursnr, datum)
        supabase.table("kurs_termine").upsert(uniq, on_conflict="kursnr,datum").execute()
        print(f"Supabase: {len(uniq)} Ausfälle als canceled=true markiert (idempotent).")
    else:
        print("Keine passenden Termine zum Markieren gefunden.")


if __name__ == "__main__":
    main()