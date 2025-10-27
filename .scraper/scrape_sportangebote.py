"""
Dieses Python-Skript sammelt das Sportprogramm (Angebote, Kurse, Termine) und speichert
es in Supabase.

Was wird gespeichert? Drei Ebenen:
- Angebote (z. B. "Boxen", "TRX" …) → Tabelle: sportangebote
- Kurse pro Angebot (mit Kursnummer, Tag, Zeit, Ort, …) → Tabelle: sportkurse
- Termine pro Kurs (einzelne Tage/Zeiten) → Tabelle: kurs_termine

Warum so? Webseiten sind für Menschen gemacht. Wir "lesen" HTML, extrahieren Infos
und speichern sie strukturiert in der Datenbank, damit Apps oder Analysen damit arbeiten können.

Wie ist der Ablauf?
1) extract_offers: Hauptseite des Sportprogramms lesen → Liste der Angebote (Name + Link)
2) extract_courses_for_offer: Für jedes Angebot die Kurs-Tabelle der Detailseite lesen
3) extract_course_dates: Für jeden Kurs die Unterseite mit allen Terminen öffnen
4) main: Alles zusammenbauen und in Supabase upserten (Upsert = Insert oder Update)

Wichtige Tabellen/Felder in Supabase:
- sportangebote: { name, href }
- sportkurse:    { kursnr, offer_href, details, zeitraum_href, preis, … }
  • offer_name wird temporär als _offer_name gespeichert (für update_cancellations.py)
  • tag, zeit und leitung wurden entfernt (redundant mit kurs_termine/trainer)
- kurs_termine:  { kursnr, start_time, end_time, ort_href, location_name }
  • Primary Key: (kursnr, start_time) - ein Kurs kann zu verschiedenen Zeiten stattfinden
  • location_name verbindet die Termine mit der Standort-Tabelle `unisport_locations.name`
  • start_time/end_time: vollständige Timestamps (z. B. "2025-10-22T16:10:00")
- trainer:        { name (PK), rating (1-5), created_at }
- kurs_trainer:  { kursnr, trainer_name (FK) }
  • Many-to-many: Ein Kurs kann mehrere Trainer haben, ein Trainer mehrere Kurse
  • Trainer-Namen werden aus "leitung" extrahiert (komma-separiert)

Voraussetzungen (ENV-Variablen):
- SUPABASE_URL: URL deines Supabase-Projekts
- SUPABASE_KEY: API-Key (am besten Service-Role)

Hinweise:
- HTML-Selektoren wie "table.bs_kurse" sind wie "Wegweiser" zu den richtigen Stellen im HTML.
- Wir verwenden Listen/Dictionaries, weil sie sich einfach zu JSON und DB-Zeilen abbilde
  n lassen.
"""

# Mini-Tutorial:
# - Schritt 1: Angebote von der Hauptseite ziehen (extract_offers)
# - Schritt 2: Für jedes Angebot Kurse lesen (extract_courses_for_offer)
# - Schritt 3: Für jeden Kurs alle Termine lesen (extract_course_dates)
# - Schritt 4: Alles idempotent (Upsert) in Supabase schreiben

# Imports (Einsteiger-Erklärung, wofür wir sie in DIESEM Skript brauchen)
# Stell dir die Imports wie Bausteine in Scratch vor – jeder macht eine bestimmte Sache gut.
# - os: Um Umgebungsvariablen (SUPABASE_URL/KEY) aus dem System/.env zu lesen (unsere "Einstellungen")
import os
# - typing: Für Typ-Hinweise (List, Dict), damit der Code verständlicher ist (nur für Menschen/Werkzeuge)
from typing import List, Dict, Optional
# - datetime: Um Datumstexte (z. B. 03.10.2025) in ein maschinenlesbares ISO-Format umzuwandeln
from datetime import datetime
# - urllib.parse.urljoin: Macht aus relativen Links vollständige Internetadressen
from urllib.parse import urljoin, urlparse, parse_qs
# - re: "Suchen mit Muster" in Texten (z. B. Datum/Zeit erkennen)
import re
# - requests: Holt Webseiten aus dem Internet
import requests
# - bs4.BeautifulSoup: "HTML-Lupe", um Tabellen und Zellen zu finden
from bs4 import BeautifulSoup
# - supabase.create_client: Stecker zur Datenbank (lesen/schreiben)
from supabase import create_client
# - dotenv.load_dotenv: Liest die .env-Datei (damit Keys nicht im Code stehen)
from dotenv import load_dotenv


def fetch_html(url: str) -> str:
    """
    Lädt den HTML-Text einer URL herunter (einfach mit requests).
    """
    # Browser-ähnlicher Header hilft, nicht aussortiert zu werden.
    import ssl
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # SSL-Problem umgehen durch disable_warnings und verify=False
    session = requests.Session()
    session.verify = False
    
    r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return r.text


def extract_offers(source: str) -> List[Dict[str, str]]:
    """
    Liest die Hauptseite des Sportprogramms und findet die Liste aller Angebote.

    Was suchen wir im HTML?
    - Die Angebote stehen in einer Liste mit dem CSS-Selektor "dl.bs_menu dd a".
    - Jedes <a> hat den sichtbaren Namen (z. B. "Boxen") und einen Link (href) zur Detailseite.

    Was machen wir damit?
    - Wir bauen aus Name und Link ein Dictionary: {"name": ..., "href": ...}.
    - Wir wandeln relative Links in absolute um (urljoin). So funktionieren sie auch außerhalb der Seite.
    - Wir entfernen Duplikate, falls ein Link mehrfach auftaucht.
    - Wir filtern bestimmte Nicht-Sportangebote aus (z. B. Kurssuche, Filter-Seiten).
    """
    # Liste von Angeboten, die ausgeschlossen werden sollen
    excluded_offers = {
        "alle freien Kursplätze dieses Zeitraums",
    }
    
    if source.startswith("http://") or source.startswith("https://"):
        base_url = source
        html = fetch_html(source)
    else:
        base_url = ""
        with open(source, "r", encoding="utf-8") as f:
            html = f.read()
    soup = BeautifulSoup(html, "lxml")

    offers: List[Dict[str, str]] = []
    seen_hrefs = set()
    for a in soup.select("dl.bs_menu dd a"):
        name = a.get_text(strip=True)
        href = a.get("href")
        if not name or not href:
            continue
        
        # Überspringe ausgeschlossene Angebote
        if name in excluded_offers:
            continue
            
        full_href = urljoin(base_url or "", href)
        if full_href in seen_hrefs:
            continue
        seen_hrefs.add(full_href)
        offers.append({"name": name, "href": full_href})
    return offers


def extract_courses_for_offer(offer: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Liest die Detailseite eines Angebots und holt die Kursliste (eine Tabelle).

    Was steht da drin?
    - Jede Tabellenzeile ist ein Kurs mit vielen Spalten (Kursnr, Tag, Zeit, Ort …)
    - Wir holen die Texte mit Selektoren wie "td.bs_sknr" (Kursnummer) oder "td.bs_szeit" (Zeit).
    - In manchen Zellen gibt es Links, die wir zusätzlich als href speichern (z. B. Ort-Link).
    - Besonders wichtig: In der Spalte "Zeitraum" gibt es einen Link zu einer Unterseite mit allen Terminen.
      Diesen Link speichern wir als "zeitraum_href", um später die exakten Termine zu laden.
    """
    href = offer["href"]
    name = offer["name"]
    if not (href.startswith("http://") or href.startswith("https://")):
        return []
    html = fetch_html(href)
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.bs_kurse")
    if not table:
        return []
    tbody = table.find("tbody") or table
    rows: List[Dict[str, str]] = []
    for tr in tbody.select("tr"):
        def text(sel: str) -> str:
            el = tr.select_one(sel)
            return el.get_text(" ", strip=True) if el else ""
        kursnr = text("td.bs_sknr")
        if not kursnr:
            continue
        details = text("td.bs_sdet")
        tag = text("td.bs_stag")
        zeit = text("td.bs_szeit")
        ort_cell = tr.select_one("td.bs_sort")
        # Ort-Texte werden nicht mehr in sportkurse gespeichert. Wir benötigen hier primär
        # location_name für kurs_termine (kommt in extract_course_dates) und belassen sportkurse schlank.
        ort = ort_cell.get_text(" ", strip=True) if ort_cell else ""
        ort_link = ort_cell.select_one("a") if ort_cell else None
        ort_href = urljoin(href, ort_link.get("href")) if (ort_link and ort_link.get("href")) else None
        zr_cell = tr.select_one("td.bs_szr")
        zr_link = zr_cell.select_one("a") if zr_cell else None
        zeitraum_href = urljoin(href, zr_link.get("href")) if (zr_link and zr_link.get("href")) else None
        leitung = text("td.bs_skl")
        preis = text("td.bs_spreis")
        buch_cell = tr.select_one("td.bs_sbuch")
        buchung = buch_cell.get_text(" ", strip=True) if buch_cell else ""
        
        # Speichere temporäre Felder für Trainer-Extraktion (werden nicht in DB geschrieben)
        course_data = {
            "offer_href": href,
            "kursnr": kursnr,
            "details": details,
            "zeitraum_href": zeitraum_href,
            "preis": preis,
            "buchung": buchung,
            # Temporäre Felder mit _ markiert
            "_offer_name": name,  # Wird für update_cancellations.py benötigt
            "_leitung": leitung,  # Wird für Trainer-Extraktion benötigt
        }
        rows.append(course_data)
    return rows


def extract_offer_metadata(offer: Dict[str, str]) -> Dict[str, str]:
    """
    Extrahiert Bild-URL und Beschreibungstext von einer Angebotsseite.
    
    Sucht nach:
    - Dem ersten <img> Tag nach dem h1-Titel (nicht das Logo)
    - Allen <p> Tags vor der Kurs-Tabelle, die die Beschreibung enthalten
    """
    href = offer["href"]
    if not (href.startswith("http://") or href.startswith("https://")):
        return {}
    
    html = fetch_html(href)
    soup = BeautifulSoup(html, "lxml")
    
    result = {}
    
    # Finde das Element mit dem Titel (kann h1 oder div.bs_head sein)
    title_element = soup.find("h1") or soup.find("div", class_="bs_head")
    if title_element:
        # Nach dem Titel suchen wir nach dem ersten <img> Tag
        # Starte vom Titel und gehe durch alle Geschwister und deren Kinder
        img_tag = None
        current = title_element.find_next_sibling()
        
        while current and current.name != "table":
            # Prüfe ob current selbst ein img ist
            if current.name == "img":
                img_tag = current
                break
            # Prüfe in allen Kindern dieses Elements
            if hasattr(current, 'find_all'):
                img = current.find("img")
                if img and img.get("src"):
                    img_src = img.get("src")
                    if "logo" not in img_src.lower() and "icon" not in img_src.lower():
                        img_tag = img
                        break
            current = current.find_next_sibling()
        
        if img_tag and img_tag.get("src"):
            img_src = img_tag.get("src")
            # Ignoriere Logos und Icons (oft mit "logo" oder "icon" im src)
            if "logo" not in img_src.lower() and "icon" not in img_src.lower():
                # Konvertiere relative URLs zu absoluten URLs
                result["image_url"] = urljoin(href, img_src)
    
    # Finde die Tabelle
    table = soup.select_one("table.bs_kurse")
    
    # Sammle alle <p> Tags nach dem Titel
    paragraphs = []
    
    if title_element:
        # Finde alle p-Tags nach dem Titel-Element
        # Suche in allen nachfolgenden Geschwister-Elementen
        current = title_element
        while current:
            current = current.next_sibling
            
            # Wenn wir eine Tabelle erreichen, stoppe
            if current and hasattr(current, 'name') and current.name == "table":
                break
                
            # Wenn current ein p-Tag ist, nimm es
            if current and hasattr(current, 'name') and current.name == "p":
                paragraphs.append(str(current))
            
            # Wenn current Kinder hat, suche nach p-Tags in den Kindern
            if current and hasattr(current, 'find_all'):
                for p in current.find_all("p"):
                    paragraphs.append(str(p))
    
    # Entferne Duplikate - behalte die Reihenfolge bei
    unique_paragraphs = []
    seen = set()
    for p in paragraphs:
        if p not in seen:
            unique_paragraphs.append(p)
            seen.add(p)
    
    if unique_paragraphs:
        result["description"] = "\n".join(unique_paragraphs)
    
    return result


def extract_trainer_names(leitung: str) -> List[str]:
    """
    Extrahiert einzelne Trainer-Namen aus dem Leitung-Feld.
    Trennt bei Kommas und bereinigt Whitespace.
    
    Beispiel: "Max Mustermann, Anna Schmidt" -> ["Max Mustermann", "Anna Schmidt"]
    """
    if not leitung or not leitung.strip():
        return []
    
    # Split bei Kommas und trimme Whitespace
    names = [name.strip() for name in leitung.split(",")]
    # Entferne leere Strings
    names = [name for name in names if name]
    return names


def parse_time_range(zeit_txt: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parst Zeit-String im Format "HH.MM - HH.MM" oder "HH:MM - HH:MM"
    und gibt (start_time, end_time) als ISO-Strings zurück.
    
    Beispiel: "16.10 - 17.40" -> ("16:10:00", "17:40:00")
    """
    if not zeit_txt or not zeit_txt.strip():
        return None, None
    
    # Ersetze Punkt durch Doppelpunkt für konsistentes Format
    zeit_normalized = zeit_txt.strip().replace(".", ":")
    
    # Versuche verschiedene Formate zu parsen
    patterns = [
        r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})",  # 16:10 - 17:40
        r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2})\.(\d{2})",  # 16:10 - 17.40
        r"(\d{1,2})\.(\d{2})\s*-\s*(\d{1,2}):(\d{2})",  # 16.10 - 17:40
    ]
    
    for pattern in patterns:
        match = re.match(pattern, zeit_normalized)
        if match:
            h1, m1, h2, m2 = match.groups()
            start_hour = int(h1)
            start_min = int(m1)
            end_hour = int(h2)
            end_min = int(m2)
            return f"{start_hour:02d}:{start_min:02d}:00", f"{end_hour:02d}:{end_min:02d}:00"
    
    return None, None


def extract_course_dates(kursnr: str, zeitraum_href: str) -> List[Dict[str, str]]:
    """
    Öffnet die Unterseite mit den geplanten Terminen eines einzelnen Kurses
    und sammelt jede Zeile (Tag + Datum + Zeit + Ort) als Datensatz.

    Wichtige Idee hier:
    - Die Seite zeigt oft eine Tabelle mit mehreren Zeilen, jede Zeile ein Termin.
    - Das Datum steht im Format TT.MM.JJJJ. Wir wandeln es in ISO-Format (JJJJ-MM-TT) um,
      damit die Datenbank damit gut arbeiten kann und es weltweit eindeutig ist.
    - Die Zeit steht im Format "HH.MM - HH.MM" und wird in start_time/end_time umgewandelt.
    """
    html = fetch_html(zeitraum_href)
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.bs_kurse")
    if not table:
        return []
    out: List[Dict[str, str]] = []
    for tr in table.select("tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        wochentag = tds[0].get_text(" ", strip=True)
        datum_raw = tds[1].get_text(" ", strip=True)
        zeit_txt = tds[2].get_text(" ", strip=True)
        ort_cell = tds[3]
        ort_txt = ort_cell.get_text(" ", strip=True)
        a = ort_cell.find("a")
        ort_href = urljoin(zeitraum_href, a.get("href")) if (a and a.get("href")) else None
        try:
            datum_iso = datetime.strptime(datum_raw, "%d.%m.%Y").date().isoformat()
        except Exception:
            continue
        
        # Parse Zeit in start_time und end_time
        start_time, end_time = parse_time_range(zeit_txt)
        
        location_name = ort_txt.strip() or None
        
        # Kombiniere datum mit start_time/end_time für timestamp
        # Falls keine Zeit geparst werden kann, überspringen wir diesen Eintrag
        if not start_time:
            print(f"⚠️  Konnte Zeit nicht parsen für {kursnr} am {datum_iso}: '{zeit_txt}' - Überspringe Eintrag")
            continue
        
        start_timestamp = f"{datum_iso}T{start_time}"
        end_timestamp = f"{datum_iso}T{end_time}" if end_time else None
        
        out.append({
            "kursnr": kursnr,
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "ort_href": ort_href,
            "location_name": location_name,
        })
    return out


def main() -> None:
    # 1) Umgebungsvariablen aus einer .env-Datei laden (falls vorhanden)
    #    Warum? So müssen sensible Daten (z. B. Datenbank-Schlüssel) nicht im Code stehen.
    #    Stattdessen schreibt ihr sie in eine Datei ".env" im Projektordner, z. B.:
    #      SUPABASE_URL=https://…
    #      SUPABASE_KEY=…
    load_dotenv()  # holt SUPABASE_URL und SUPABASE_KEY aus .env (wenn vorhanden)
    # 2) Wir verwenden immer die Live-URL der Hauptseite (kein lokaler Pfad nötig)
    html_source = "https://www.sportprogramm.unisg.ch/unisg/angebote/aktueller_zeitraum/index.html"
    #    Wir holen die Angebote (Name + Link) und speichern sie in einer Liste von Dictionaries.
    offers = extract_offers(html_source)  # Liste von {name, href}

    # 3) Mit Supabase verbinden (wir brauchen URL und API-Key aus der .env-Datei)
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("Bitte SUPABASE_URL und SUPABASE_KEY als ENV setzen.")
        return
    supabase = create_client(supabase_url, supabase_key)  # Verbindung zur DB

    # 4) Zuerst schreiben wir die Angebote in die Tabelle "sportangebote".
    #    Upsert bedeutet: Wenn ein Eintrag schon existiert (gleicher Schlüssel), wird er aktualisiert.
    #    Schlüssel hier ist die Spalte "href" (der Link zur Angebotsseite).
    # Idempotent: gleiche href → wird aktualisiert statt dupliziert
    supabase.table("sportangebote").upsert(offers, on_conflict="href").execute()
    print(f"Supabase: {len(offers)} Angebote upserted (idempotent).")

    # 4b) Extrahiere Bild-URL und Beschreibungstext von jeder Angebotsseite
    #     und aktualisiere die Einträge in der Datenbank
    updated_count = 0
    for offer in offers:
        metadata = extract_offer_metadata(offer)
        if metadata:
            # Bereite Update vor: href + name + neue Felder
            update_data = {
                "href": offer["href"],
                "name": offer["name"]
            }
            if "image_url" in metadata:
                update_data["image_url"] = metadata["image_url"]
            if "description" in metadata:
                update_data["description"] = metadata["description"]
            # Upsert mit den neuen Feldern
            supabase.table("sportangebote").upsert(update_data, on_conflict="href").execute()
            updated_count += 1
    print(f"Supabase: Bild-URL und Beschreibungen aktualisiert für {updated_count} Angebote.")

    # 5) Als nächstes sammeln wir alle Kurse aller Angebote.
    #    Dafür besuchen wir für jedes Angebot die Detailseite und lesen die Kurstabelle.
    all_courses: List[Dict[str, str]] = []
    for off in offers:  # jede Angebotsseite besuchen
        all_courses.extend(extract_courses_for_offer(off))
    #    Dann schreiben wir alle Kurse in die Tabelle "sportkurse".
    #    Schlüssel ist die Kursnummer ("kursnr").
    # Bereinige temporäre Felder (_leitung) vor dem Upsert
    courses_for_db = [
        {k: v for k, v in course.items() if not k.startswith("_")}
        for course in all_courses
    ]
    
    # Idempotent: gleiche kursnr → wird aktualisiert
    supabase.table("sportkurse").upsert(courses_for_db, on_conflict="kursnr").execute()
    print(f"Supabase: {len(courses_for_db)} Kurse upserted (idempotent).")

    # 5b) Extrahiere Trainer-Namen aus allen Kursen und speichere sie
    trainer_to_courses: Dict[str, List[str]] = {}  # trainer_name -> [kursnr, kursnr, ...]
    
    for course in all_courses:
        leitung = course.get("_leitung", "").strip() if course.get("_leitung") else ""
        if leitung:
            trainer_names = extract_trainer_names(leitung)
            for trainer_name in trainer_names:
                # Track which courses each trainer teaches
                if trainer_name not in trainer_to_courses:
                    trainer_to_courses[trainer_name] = []
                trainer_to_courses[trainer_name].append(course["kursnr"])
    
    # Entdubliziere Trainer-Liste (trainer_name -> rating dict)
    all_trainers: List[Dict[str, object]] = [
        {"name": trainer_name, "rating": 3}
        for trainer_name in trainer_to_courses.keys()
    ]
    
    # Speichere Trainer in die trainer Tabelle (idempotent)
    if all_trainers:
        supabase.table("trainer").upsert(all_trainers, on_conflict="name").execute()
        print(f"Supabase: {len(all_trainers)} Trainer upserted (idempotent).")
    
    # Speichere Verknüpfungen in kurs_trainer Tabelle
    kurs_trainer_rows: List[Dict[str, object]] = []
    for trainer_name, kursnrs in trainer_to_courses.items():
        for kursnr in kursnrs:
            kurs_trainer_rows.append({"kursnr": kursnr, "trainer_name": trainer_name})
    
    if kurs_trainer_rows:
        # Delete existing relationships for these courses first to avoid duplicates
        kursnrs_to_update = [course["kursnr"] for course in all_courses]
        for kursnr in kursnrs_to_update:
            supabase.table("kurs_trainer").delete().eq("kursnr", kursnr).execute()
        # Insert new relationships
        supabase.table("kurs_trainer").insert(kurs_trainer_rows).execute()
        print(f"Supabase: {len(kurs_trainer_rows)} Kurs-Trainer-Verknüpfungen gespeichert.")

    # 6) Jetzt kommen die exakten Termine pro Kurs.
    #    Für jeden Kurs gibt es einen Link (zeitraum_href) zu einer Unterseite mit allen geplanten Terminen.
    all_dates: List[Dict[str, str]] = []
    for c in all_courses:  # Termine-Seite pro Kurs besuchen
        if c.get("zeitraum_href") and c.get("kursnr"):
            all_dates.extend(extract_course_dates(c["kursnr"], c["zeitraum_href"]))
    #    Diese Termine schreiben wir zurück in "kurs_termine" (Legacy-Tabelle), jetzt mit location_name-Verknüpfung.
    if all_dates:
        # Vor Upsert: ungültige location_name bereinigen (NULL setzen, falls nicht in unisport_locations)
        loc_resp = supabase.table("unisport_locations").select("name").execute()  # erlaubte Standorte holen
        valid_names = { (r.get("name") or "").strip() for r in (loc_resp.data or []) if r.get("name") }
        for row in all_dates:
            ln = (row.get("location_name") or "").strip()
            if not ln or (valid_names and ln not in valid_names):
                row["location_name"] = None
        # MERGE Strategy: canceled Flag wird NICHT überschrieben, nur wenn es nicht gesetzt ist
        # Lade bestehende canceled Status für alle Termine in einem Query
        kursnrs_with_dates = [(row["kursnr"], row["start_time"]) for row in all_dates]
        existing_canceled = {}
        
        # Batch-query für effiziente Status-Abfrage
        if kursnrs_with_dates:
            # Hole alle bestehenden canceled Werte
            kursnrs_set = set(kr[0] for kr in kursnrs_with_dates)
            for kursnr in kursnrs_set:
                resp = supabase.table("kurs_termine").select("kursnr, start_time, canceled").eq("kursnr", kursnr).execute()
                for term in resp.data or []:
                    existing_canceled[(term["kursnr"], term["start_time"])] = term.get("canceled", False)
        
        # Setze canceled nur wenn es noch nicht existiert
        for row in all_dates:
            key = (row["kursnr"], row["start_time"])
            if key in existing_canceled:
                # Behalte den bestehenden canceled Status
                row["canceled"] = existing_canceled[key]
            else:
                # Neuer Termin, canceled = false
                row["canceled"] = False
        
        supabase.table("kurs_termine").upsert(all_dates, on_conflict="kursnr,start_time").execute()  # Idempotent pro (kursnr, start_time)
        print(f"Supabase: {len(all_dates)} Termine upserted (kurs_termine, idempotent, canceled Status behalten).")
    else:
        print("Hinweis: Keine Termine gefunden.")

    # ETL-Run protokollieren
    try:
        supabase.table("etl_runs").insert({"component": "scrape_sportangebote"}).execute()
    except Exception:
        pass

    # Hinweis: Die Logik zum Erkennen und Markieren von Trainingsausfällen
    #          wurde nach update_cancellations.py ausgelagert, damit beide
    #          Skripte unabhängig voneinander lauffähig sind.


if __name__ == "__main__":
    main()

# Hinweis (Academic Integrity): Bei der Erstellung dieser Datei wurde das Tool "Cursor"
# unterstützend verwendet.