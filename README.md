## UnisportAI – Übersicht für Einsteiger

Dieses Projekt liest Daten von der Unisport-Webseite (HSG) aus und speichert sie
strukturiert in einer Supabase-Datenbank. Ziel: Alle Informationen (Standorte,
Angebote, Kurse, Termine, Ausfälle) maschinenlesbar und konsistent verfügbar machen.

### Wichtige Tabellen in Supabase
- `unisport_locations`: Alle Veranstaltungsorte mit Name, Koordinaten, Link (ort_href), spid und Sportliste
- `sportangebote`: Liste der Sportangebote (z. B. "Boxen", "TRX")
- `sportkurse`: Kurstabelle (Kursnummer, Tag, Zeit, Ort, Links ...)
- `course_dates`: Einzeltermine pro Kurs. Verbunden über `location_name` → `unisport_locations.name`

### Die drei Skripte

1) `extract_locations_from_html.py`
   - Lädt die Live-Seite `https://www.sportprogramm.unisg.ch/unisg/cgi/webpage.cgi?orte`.
   - Extrahiert Orte aus zwei Quellen: Marker-Liste (Koordinaten) und Menü (Sportliste, ort_href, spid).
   - Schreibt die Orte direkt in `unisport_locations` (Upsert per `name`).
   - Felder: `name, lat, lng, google_maps_id (="lat,lng"), ort_href, spid, sports[]`.
   - Voraussetzung: ENV-Variablen `SUPABASE_URL` und `SUPABASE_KEY`.

2) `scrape_sportangebote.py`
   - Lädt das Sportprogramm (Angebote, Kurse, Termine) von den Unisport-Seiten.
   - Speichert Angebote in `sportangebote`, Kurse in `sportkurse` und Termine in `course_dates`.
   - Wichtig: Termine enthalten `location_name`, sodass `course_dates.location_name`
     auf `unisport_locations.name` zeigt (FK). So sind Termine an echte Orte gebunden.

3) `update_cancellations.py`
   - Liest (falls veröffentlicht) Trainingsausfälle (Datum, Kursname, Startzeit) von der HSG-Seite.
   - Sucht die passenden `kurs_termine` (bzw. `course_dates`) in Supabase und markiert sie mit `canceled=true`.
   - Nutzt Kursnamen-Mapping (`sportkurse.offer_name` → `kursnr`) und Zeitvergleich (Startzeit zu HHMM normalisiert).

### Reihenfolge – so benutzt du die Skripte
1. Locations laden (einmalig oder bei Änderungen):
   ```bash
   export SUPABASE_URL=...
   export SUPABASE_KEY=...
   python3 extract_locations_from_html.py
   ```
2. Sportprogramm laden (regelmäßig, z. B. täglich):
   ```bash
   export SUPABASE_URL=...
   export SUPABASE_KEY=...
   python3 scrape_sportangebote.py
   ```
3. Ausfälle aktualisieren (nach Bedarf):
   ```bash
   export SUPABASE_URL=...
   export SUPABASE_KEY=...
   python3 update_cancellations.py
   ```

### Wie hängen die Teile zusammen?
- `extract_locations_from_html.py` baut den „Ort-Katalog“. `course_dates.location_name`
  referenziert `unisport_locations.name`. Dadurch sind Kurs-Termine direkt Orten zugeordnet.
- `scrape_sportangebote.py` füllt Angebote/Kurse/Termine. Die Termin-Orte werden als Text
  mitgeführt und landen in `location_name`. So entsteht die Verbindung zu `unisport_locations`.
- `update_cancellations.py` nutzt die Kursnamen, um betroffene Kurse zu finden und setzt die
  Flagge `canceled` bei passenden Terminen.

### Typische Fehler und Tipps
- Fehlende ENV-Variablen: Die Skripte brechen ab oder schreiben nichts.
- Webseitenlayout ändert sich: Selektoren `bs_*` oder die Marker-Struktur müssen angepasst werden.
- Schreibrechte in Supabase: Verwende für Imports einen Key mit Schreibrechten (Service Role).

### Sicherheit
- Keine sensiblen Keys im Code ablegen. Stattdessen per ENV setzen oder `.env` nutzen.
- Service Role Key nur in sicherer Umgebung verwenden (nicht in Client-Apps).

### Streamlit + Supabase schnell starten

1. Requirements installieren:
   ```bash
   pip install -r requirements.txt
   ```
2. Secrets lokal anlegen: Lege `.streamlit/secrets.toml` an (oder kopiere von `.streamlit/secrets.example.toml`, falls vorhanden) und trage `SUPABASE_URL` sowie `SUPABASE_KEY` ein:
   ```toml
   [connections.supabase]
   SUPABASE_URL = "https://PROJECT_REF.supabase.co"
   SUPABASE_KEY = "<ANON ODER SERVICE KEY>"
   ```
3. Streamlit lokal starten:
   ```bash
streamlit run .streamlit/streamlit_app.py
   ```
4. Deployment (Streamlit Community Cloud): `requirements.txt` ist vorbereitet. Secrets im Dashboard unter „Edit Secrets" hinterlegen (gleicher Inhalt wie lokale `secrets.toml`).

