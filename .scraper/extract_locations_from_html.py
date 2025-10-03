"""
Dieses Skript sammelt alle Unisport-Veranstaltungsorte (Locations) direkt von der
Live-Webseite und speichert sie unmittelbar in Supabase (Tabelle `unisport_locations`).

Was macht das Skript in einfachen Worten?
- Es lädt eine Unisport-Seite, auf der alle Orte aufgelistet sind.
- In dieser Seite stehen zwei wichtige Informationsquellen:
  1) Eine JavaScript-Liste mit Markern ("var markers=[...]"), in der für viele Orte die
     GPS-Koordinaten (Breite/Länge) und der Name stehen.
  2) Ein Menü mit allen Orten, in dem zusätzlich die Sportarten je Ort und der Detail-Link
     ("ort_href") enthalten sind. Aus dem Link liest das Skript auch eine interne ID ("spid") aus.
- Aus diesen beiden Quellen baut das Skript eine saubere Liste aller Orte zusammen.
- Dann schreibt es diese Liste direkt in die Datenbank (Supabase), ohne einen Zwischenschritt.

Welche Daten landen in der Tabelle `unisport_locations`?
- name: der Name des Standorts (z. B. "HSG, Halle 1")
- lat / lng: geografische Koordinaten (soweit vorhanden)
- google_maps_id: hier verwenden wir einfach den Text "lat,lng" (z. B. "47.42989,9.37185")
- ort_href: absoluter Link zur Standort-Unterseite (z. B. zum Unisport-Menüeintrag)
- spid: die Standort-ID, die im Link als Parameter steckt
- sports: ein Array (Liste) der Sportangebote am Standort

Voraussetzungen, damit das Schreiben in Supabase klappt:
- Umgebungsvariablen setzen:
  SUPABASE_URL = URL deines Supabase-Projekts
  SUPABASE_KEY = API-Key (am besten Service-Role Key für Writes)

So führst du das Skript aus:
- Im Terminal:
    export SUPABASE_URL=...  # deine URL
    export SUPABASE_KEY=...  # dein Key
    python3 extract_locations_from_html.py

Hinweis: Wenn die Variablen fehlen, wird nur die Anzahl gefundener Orte ausgegeben.
"""

# Mini-Tutorial (leicht verständlich):
# - Schritt 1: Wir laden die Webseite (fetch_html).
# - Schritt 2: Wir lesen Koordinaten und Namen aus der JS-Liste (parse_markers).
# - Schritt 3: Wir lesen Sportarten je Standort aus dem Menü (parse_location_sports).
# - Schritt 4: Wir lesen Standort-Links und IDs (parse_location_links).
# - Schritt 5: Wir führen alles pro Standort zusammen (merged).
# - Schritt 6: Wir schreiben alles idempotent in Supabase (Upsert nach name).

import json
import os
import re
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv

from supabase import create_client  # type: ignore

# Erklärung zu den Imports (wie "Bausteine" in Scratch):
# - json: Wandelt Daten in Text (JSON) und zurück. Brauchen wir, um Listen/Objekte lesbar zu machen.
# - os: Zugriff auf Umgebungsvariablen (z. B. SUPABASE_URL). Wie ein Rucksack mit Einstellungen.
# - re: "Suchen & Finden" in Texten mit Mustern (Reguläre Ausdrücke). Wie eine Lupe mit Filter.
# - typing (Dict, List, Optional): Nur für Menschen/Entwicklungswerkzeuge, um Datentypen zu beschreiben.
# - requests: Webseiten laden
# - dotenv: Liest eine .env-Datei ein, damit wir Keys/URLs nicht in den Code schreiben müssen.
# - supabase.create_client: Der Stecker zur Datenbank. Damit können wir Daten einfügen/lesen/ändern.

from bs4 import BeautifulSoup  # type: ignore


# Live-Quelle: Veranstaltungsorte/Räume
SOURCE_URL = "https://www.sportprogramm.unisg.ch/unisg/cgi/webpage.cgi?orte"
# Das ist die Live-Seite mit allen Veranstaltungsorten. Wir lesen sie nur (kein Login nötig).


def fetch_html(url: str) -> str:
    """
    Lädt den Text einer Webseite ausschließlich via requests.
    """
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse_markers(html: str) -> List[Dict[str, object]]:
    """
    Extracts marker entries from a JS array literal like:
    var markers=[[47.42901,9.38402,"Athletik Zentrum, Gymnastikraum"], ...];
    Returns list of dicts: {"name": str, "lat": float, "lng": float}
    Anfänger-Idee: Wir suchen in dem HTML-Text nach einer Stelle, wo Koordinaten und Namen
    in einer Liste stehen. Dann schneiden wir uns jeden Eintrag heraus.
    """
    m = re.search(r"var\s+markers\s*=\s*\[(.*?)\];", html, re.S)
    if not m:
        return []
    body = m.group(1)
    # Split top-level arrays; handle "]],[" boundaries robustly
    raw_items = re.split(r"\],\s*\[", body.strip()[1:-1]) if body.strip().startswith("[") else body.split("],[")
    out: List[Dict[str, object]] = []
    for item in raw_items:
        # Normalize quotes and brackets
        item_norm = item.strip().strip("[]")
        parts = []
        current = []
        in_quotes = False
        i = 0
        while i < len(item_norm):
            ch = item_norm[i]
            if ch == '"':
                in_quotes = not in_quotes
                current.append(ch)
            elif ch == ',' and not in_quotes:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(ch)
            i += 1
        if current:
            parts.append(''.join(current).strip())
        if len(parts) < 3:
            continue
        try:
            lat = float(parts[0])
            lng = float(parts[1])
            name = parts[2].strip()
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            out.append({"name": name, "lat": lat, "lng": lng})
        except Exception:
            continue
    return out


def parse_location_sports(html: str) -> Dict[str, List[str]]:
    """
    Extract mapping from location name to list of sports using the 'bs_flmenu' menu.
    Returns dict: name -> [sports]
    Anfänger-Idee: Auf der Seite gibt es auch ein Menü, wo unter jedem Ort die Sportarten
    aufgelistet sind. Wir laufen durch diese Liste und bauen ein Wörterbuch: Ort → [Sportarten].
    """
    mapping: Dict[str, List[str]] = {}
    soup = BeautifulSoup(html, "lxml")
    menu = soup.select_one("div.bs_flmenu > ul")
    if not menu:
        return mapping
    for li in menu.find_all("li", recursive=False):
        name_el = li.select_one("span.bs_spname")
        if not name_el:
            continue
        loc_name = name_el.get_text(strip=True)
        sports: List[str] = []
        for sub in li.select("ul > li > a"):
            sport_name = sub.get_text(strip=True)
            if sport_name:
                sports.append(sport_name)
        mapping[loc_name] = [s for s in sports if s != loc_name]
    return mapping


def parse_location_links(html: str, base_url: Optional[str] = None) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Liest aus dem Menü (div.bs_flmenu) die Standortlinks (href) und extrahiert spid.
    Gibt zurück: name -> {"href": absolute URL|None, "spid": str|None}
    Anfänger-Idee: Jeder Ort hat auch einen Link zu einer Detailseite. Aus dem Link holen wir
    die vollständige Adresse (href) und eine interne Kennung (spid) heraus.
    """
    out: Dict[str, Dict[str, Optional[str]]] = {}
    soup = BeautifulSoup(html, "lxml")
    menu = soup.select_one("div.bs_flmenu > ul")
    if not menu:
        return out
    effective_base = base_url or "https://www.sportprogramm.unisg.ch/unisg/angebote/aktueller_zeitraum/"
    from urllib.parse import urljoin, urlparse, parse_qs
    for li in menu.find_all("li", recursive=False):
        name_el = li.select_one("span.bs_spname")
        if not name_el:
            continue
        loc_name = name_el.get_text(strip=True)
        top_a = li.select_one("a[href]")
        href_rel = top_a.get("href") if top_a else None
        full_href: Optional[str] = None
        spid: Optional[str] = None
        if href_rel:
            full_href = urljoin(effective_base, href_rel)
            try:
                q = parse_qs(urlparse(full_href).query)
                spid = (q.get("spid") or [None])[0]
            except Exception:
                spid = None
        out[loc_name] = {"href": full_href, "spid": spid}
    return out


def main() -> None:
    # 1) Seite laden
    html = fetch_html(SOURCE_URL)
    markers = parse_markers(html)
    loc_to_sports = parse_location_sports(html)
    loc_links = parse_location_links(html)

    # 2) Informationen zusammenbauen
    # Idee: Aus den Markern bekommen wir Koordinaten + Name.
    #       Aus dem Menü bekommen wir Sportarten, Link und spid. Wir führen alles pro Name zusammen.
    # Merge by name; if multiple entries share name, keep first coords
    merged: List[Dict[str, object]] = []
    seen_names = set()
    for m in markers:
        name = str(m["name"])
        if name in seen_names:
            continue
        seen_names.add(name)
        merged.append({
            "name": name,
            "lat": m["lat"],
            "lng": m["lng"],
            "ort_href": loc_links.get(name, {}).get("href") if loc_links else None,
            "spid": loc_links.get(name, {}).get("spid") if loc_links else None,
            "google_maps_id": f"{m['lat']},{m['lng']}",
        })

    # Also include locations that appear only in the menu but not in markers
    for name, sports in loc_to_sports.items():
        if name not in seen_names:
            merged.append({
                "name": name,
                "lat": None,
                "lng": None,
                "ort_href": loc_links.get(name, {}).get("href") if loc_links else None,
                "spid": loc_links.get(name, {}).get("spid") if loc_links else None,
                "google_maps_id": None,
            })

    # 3) Direkt in die Datenbank (Supabase) schreiben
    # Upsert bedeutet: Neu einfügen ODER vorhandenen Datensatz aktualisieren (nach Schlüssel 'name').
    # Das macht das Skript "idempotent": Mehrfaches Ausführen führt nicht zu doppelten Einträgen.
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not (supabase_url and supabase_key and create_client):
        print(f"Hinweis: {len(merged)} Locations extrahiert. Setze SUPABASE_URL/SUPABASE_KEY, um direkt zu upserten.")
        return

    client = create_client(supabase_url, supabase_key)

    # In Batches upserten, um Payload klein zu halten
    batch_size = 100
    total = 0
    for i in range(0, len(merged), batch_size):
        batch = merged[i:i+batch_size]
        try:
            client.table("unisport_locations").upsert(batch, on_conflict="name").execute()
            total += len(batch)
        except Exception as e:
            print(f"Warnung: Upsert unisport_locations fehlgeschlagen (Batch {i}-{i+batch_size}): {e}")
    print(f"Supabase: {total} Locations upserted (idempotent).")
    # Fertig: Alle Orte liegen jetzt in der Tabelle unisport_locations.

    # Hinweis: Die relationale Verknüpfung zu Angeboten wird nicht mehr in einer Zwischentabelle gepflegt.
    # Abfragen können über Namen verknüpft werden (sportkurse.offer_name ↔ unisport_locations.name via kurs_termine.location_name).


if __name__ == "__main__":
    main()