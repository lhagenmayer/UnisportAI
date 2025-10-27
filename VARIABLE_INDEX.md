# Variable Names, Columns, and Row Names Index

Dieses Dokument enthält eine vollständige Aufstellung aller Variablennamen, Spaltennamen und Row-Bezeichnungen im Repository.

## Inhaltsverzeichnis
- [Session State Keys](#session-state-keys)
- [Filter State Keys](#filter-state-keys)
- [DataFrame Spalten](#dataframe-spalten)
- [Database Felder](#database-felder)
- [Funktionsparameter](#funktionsparameter)
- [Lokale Variablen](#lokale-variablen)
- [Dictionary Keys](#dictionary-keys)
- [Supabase Tabellen und Views](#supabase-tabellen-und-views)

---

## Session State Keys

### Hauptstatus
- `state_sports_data` - Gespeicherte Sportdaten für spätere Verwendung
- `state_selected_offer` - Ausgewähltes Sportangebot
- `state_page2_multiple_offers` - Liste von Angeboten für Seite 2

### Page Navigation Keys
- `state_nav_offer_hrefs` - Liste von hrefs für Filter von Seite 3 nach Seite 2
- `state_nav_date` - Datum für Filter von Seite 3 nach Seite 2
- `state_nav_time` - Zeit für Filter von Seite 3 nach Seite 2
- `state_nav_offer_name` - Normalisierter Sportname für Filter von Seite 3 nach Seite 2

### Multiselect Keys
- `state_selected_offers_multiselect` - Ausgewählte Angebote im Multiselect

---

## Filter State Keys

### Hauptseiten-Filter
- `state_filter_show_upcoming_only` - Nur kommende Termine anzeigen
- `state_filter_search_text` - Suchtext
- `state_filter_intensity` - Intensität Filter
- `state_filter_focus` - Fokus Filter
- `state_filter_setting` - Setting Filter

### Detail-Filter
- `state_filter_offers` - Sportaktivitäten Filter
- `state_filter_hide_cancelled` - Nur nicht stornierte Termine
- `state_filter_date_start` - Startdatum
- `state_filter_date_end` - Enddatum
- `state_filter_location` - Standort Filter
- `state_filter_weekday` - Wochentag Filter
- `state_filter_time_start` - Startzeit Filter
- `state_filter_time_end` - Endzeit Filter

---

## DataFrame Spalten

### Page 2 (Detailansicht)
- `Date` - Datum des Termins (formatiert mit Wochentag)
- `Time` - Zeit des Termins (Start - Ende)
- `Canceled` - Stornierungsstatus (✓ oder leer)
- `Kurs Nr` - Kursnummer
- `Location` - Standortname
- `Trainer` - Trainer Informationen (Name mit Rating)
- `Preis` - Preis
- `Buchung` - Buchungsinformationen
- `Details` - Kursdetails

### Page 1 (Hauptseite - Kommende Termine)
- `Date` - Datum (formatiert als "Tag, DD.MM.YYYY")
- `Time` - Zeit (HH:MM - HH:MM)
- `Course` - Kursnummer und Details
- `Location` - Standortname

---

## Database Felder

### Sportangebote (`sportangebote_with_ratings`)
- `href` - Eindeutiger Identifier für das Angebot
- `name` - Name des Sportangebots
- `description` - Beschreibung des Angebots
- `icon` - Icon/Emoji des Angebots
- `intensity` - Intensitätsstufe
- `focus` - Fokus-Array
- `setting` - Setting-Array
- `avg_rating` - Durchschnittliches Rating
- `rating_count` - Anzahl der Bewertungen
- `image_url` - URL des Hintergrundbildes
- `future_events_count` - Anzahl zukünftiger Termine
- `trainers` - Liste der Trainer

### Termine (`vw_termine_full`)
- `offer_href` - Referenz zum Sportangebot
- `start_time` - Startzeit des Termins (ISO Format)
- `end_time` - Endzeit des Termins (ISO Format)
- `canceled` - Boolean, ob storniert
- `sport_name` - Name des Sports (aus Angebot)
- `sport_icon` - Icon des Sports
- `location_name` - Name des Standorts
- `kursnr` - Kursnummer
- `trainers` - JSON-Array mit Trainer-Informationen
- `preis` - Preis des Kurses
- `buchung` - Buchungsinformationen
- `details` - Weitere Details zum Kurs
- `kurs_details` - Alternative Feld für Kursdetails

### Trainer (aus JSON in Termine)
- `name` - Name des Trainers
- `rating` - Rating des Trainers (Zahl oder 'N/A')

---

## Funktionsparameter

### filter_offers()
- `offers` - Liste von Sportangeboten
- `show_upcoming_only` - Boolean: Nur mit Terminen
- `search_text` - Suchtext
- `intensity` - Intensitätsfilter (Liste)
- `focus` - Fokus-Filter (Liste)
- `setting` - Setting-Filter (Liste)

### filter_events()
- `events` - Liste von Events (Termine)
- `sport_filter` - Sport-Filter (Liste)
- `weekday_filter` - Wochentag-Filter (Liste)
- `date_start` - Startdatum
- `date_end` - Enddatum
- `time_start` - Startzeit
- `time_end` - Endzeit
- `location_filter` - Standort-Filter (Liste)
- `hide_cancelled` - Nur nicht stornierte Termine

### filter_offers_by_events()
- `offers` - Liste von Sportangeboten
- `events_mapping` - Mapping von href zu Events
- `sport_filter` - Sport-Filter (Liste)
- `weekday_filter` - Wochentag-Filter (Liste)
- `date_start` - Startdatum
- `date_end` - Enddatum
- `time_start` - Startzeit
- `time_end` - Endzeit
- `location_filter` - Standort-Filter (Liste)
- `hide_cancelled` - Nur nicht stornierte Termine

### render_shared_sidebar()
- `filter_type` - Typ des Filters: 'main', 'detail', 'weekly'
- `sports_data` - Sportdaten (für 'main')
- `termins` - Termindaten (für 'detail' oder 'weekly')

### state_manager Funktionen
- `get_filter_state(filter_name, default)` - Holt Filter-State
- `set_filter_state(filter_name, value)` - Setzt Filter-State
- `clear_filter_states()` - Löscht alle Filter-States
- `init_multiple_offers_state(all_hrefs, multiselect_key)` - Initialisiert Multiple-Offers State
- `get_multiselect_value(multiselect_key, default)` - Holt Multiselect-Wert
- `set_multiselect_value(multiselect_key, value)` - Setzt Multiselect-Wert
- `get_selected_offers_for_page2(multiple_offers_key, multiselect_key, default)` - Holt ausgewählte Angebote für Seite 2
- `store_page_3_to_page_2_filters(date_str, time_obj, sport_name, all_hrefs)` - Speichert Filter von Seite 3 für Seite 2
- `clear_page_3_filters()` - Entfernt Filter von Seite 3

### Supabase Client Funktionen
- `supaconn()` - Gibt Supabase-Verbindung zurück
- `_parse_trainers_json(trainers_data)` - Konvertiert Trainer-Daten von JSON
- `_convert_termin_fields(termin)` - Konvertiert Termin-Felder
- `angebote_mit_ratings()` - Lädt alle Sportangebote mit Ratings
- `termine_for_all_angebote()` - Lädt alle zukünftigen Termine
- `termine_for_angebot(href)` - Lädt Termine für ein Angebot
- `count_future_termins_for_all()` - Zählt zukünftige Termine für alle Angebote
- `get_termins_by_offer_mapping()` - Lädt Termine gruppiert nach offer_href
- `trainers_for_all_angebote()` - Lädt Trainer für alle Angebote

---

## Lokale Variablen

### Streamlit App
- `main_page` - Page-Objekt für Hauptseite
- `page_2` - Page-Objekt für Seite 2
- `page_3` - Page-Objekt für Seite 3
- `pg` - Navigation Objekt

### Seite 1 (main_page.py)
- `data` - Geladene Sportdaten
- `counts` - Anzahl zukünftiger Termine
- `all_trainers` - Trainer für alle Angebote
- `item` - Aktuelles Sportangebot in Loop
- `show_only_dates` - Nur Datums-Filter aktiv
- `search_text` - Suchtext Filter
- `selected_intensity` - Ausgewählte Intensitäten
- `selected_focus` - Ausgewählte Fokuse
- `selected_setting` - Ausgewählte Settings
- `selected_sports` - Ausgewählte Sportarten
- `show_only_non_cancelled` - Nur nicht stornierte Filter
- `start_date` - Startdatum Filter
- `end_date` - Enddatum Filter
- `selected_locations` - Ausgewählte Standorte
- `selected_weekdays` - Ausgewählte Wochentage
- `start_time_filter` - Startzeit Filter
- `end_time_filter` - Endzeit Filter
- `has_detail_filters` - Ob Detail-Filter aktiv sind
- `filtered_data` - Gefilterte Daten
- `termins_mapping` - Mapping von href zu Terminen
- `col1`, `col2` - Spalten für Layout
- `image_url` - URL des Hintergrundbildes
- `intensity` - Intensitäts-String
- `info_parts` - Info-Parts Liste
- `focus_short` - Kurzer Fokus-String
- `termins_count` - Anzahl der Termine
- `trainers` - Trainer-Liste
- `trainer_names` - Trainer-Namen Liste
- `trainers_str` - Trainer-String
- `rating` - Rating-String
- `termins` - Termine für ein Angebot
- `today` - Heutiges Datum
- `future_termins` - Zukünftige Termine
- `start_time` - Startzeit
- `start_dt` - Startdatetime
- `event_date` - Event-Datum
- `display_data` - Display-Daten Array
- `termin` - Aktueller Termin
- `start_time` - Startzeit
- `end_time` - Endzeit
- `time_formatted` - Formatierte Zeit
- `end_formatted` - Formatierte Endzeit
- `weekday_en` - Englischer Wochentag
- `weekday_de_short` - Kurzer deutscher Wochentag
- `date_formatted` - Formatierter Datum-String
- `time_string` - Zeit-String
- `date_string` - Datum-String
- `course_details` - Kursdetails
- `kursnr` - Kursnummer
- `course_display` - Anzeige-String für Kurs
- `row` - Row-Dictionary

### Seite 2 (page_2.py)
- `has_selected_angebot` - Ob ein Angebot ausgewählt ist
- `selected` - Ausgewähltes Angebot
- `showing_multiple_offers` - Ob mehrere Angebote angezeigt werden
- `description` - Beschreibungstext
- `termins` - Alle Termine
- `selected_offers_to_use` - Ausgewählte Angebote zum Verwenden
- `all_termins` - Alle Termine
- `seen` - Set für Deduplizierung
- `unique_termins` - Deduplizierte Termine
- `key` - Key für Deduplizierung
- `filtered_count` - Anzahl gefilterter Termine
- `t` - Aktueller Termin in Loop
- `sport_name` - Sportname
- `start_time_obj` - Startzeit-Objekt
- `start_dt_for_weekday` - Datetime für Wochentag
- `event_weekday` - Event-Wochentag
- `start_dt_for_time` - Datetime für Zeit
- `event_time` - Event-Zeit
- `filtered_termins` - Gefilterte Termine
- `weekdays_de` - Mapping von englischen zu deutschen Wochentagen
- `display_data` - Display-Daten Array
- `preis` - Preis-String
- `buchung` - Buchungs-String
- `details` - Details-String
- `trainer_ratings` - Trainer-Ratings Liste
- `trainer_display` - Trainer-Anzeige Liste
- `i` - Index
- `trainer_name` - Trainer-Name
- `rating` - Rating-Wert
- `trainer_string` - Trainer-String

### Seite 3 (page_3.py)
- `termins` - Alle Termine
- `normalize_sport_name(name)` - Funktion zum Normalisieren von Sportnamen
- `normalized` - Normalisierter String
- `grouped_by_key` - Dictionary gruppiert nach Key
- `start_dt` - Start-Datetime
- `date_str` - Datum als String
- `time_str` - Zeit als String
- `normalized_sport_name` - Normalisierter Sportname
- `sport_icon` - Sport-Icon
- `location` - Standort-String
- `key` - Gruppierungs-Key
- `grouped_by_key` - Gruppiert nach Key
- `item` - Item im Dictionary
- `existing_item` - Bestehendes Item
- `current_href` - Aktueller Href
- `all_offer_hrefs` - Alle Angebots-Hrefs
- `grouped_by_date` - Gruppiert nach Datum
- `sorted_dates` - Sortierte Datumsliste
- `first_date` - Erstes Datum
- `last_date` - Letztes Datum
- `monday_of_first_week` - Montag der ersten Woche
- `weeks_to_show` - Anzahl anzuzeigender Wochen
- `week_num` - Wochernummer
- `week_start` - Wochenanfang
- `week_end` - Wochenende
- `week_label` - Wochen-Label
- `cols` - Spalten für Layout
- `day_names` - Wochentagnamen Liste
- `i` - Index
- `col` - Spalte
- `day_date` - Tag-Datum
- `is_today` - Ob heute
- `day_name` - Tagname
- `termins_by_day` - Termine nach Tag gruppiert
- `days_diff` - Tage-Differenz
- `date_obj` - Datums-Objekt
- `day_termins` - Termine eines Tages
- `idx` - Index
- `hrefs_str` - Hrefs als String
- `button_key` - Button-Key
- `is_cancelled` - Ob storniert
- `color` - Farb-Indikator
- `bg_color` - Hintergrundfarbe
- `border_color` - Randfarbe

### filters.py
- `termin` - Termin-Objekt
- `sport_filter` - Sport-Filter
- `weekday_filter` - Wochentag-Filter
- `date_start` - Startdatum
- `date_end` - Enddatum
- `time_start` - Startzeit
- `time_end` - Endzeit
- `location_filter` - Standort-Filter
- `non_cancelled` - Nicht-storniert Filter
- `filtered` - Gefilterte Liste
- `item` - Item in Loop

### state_manager.py
- `filter_name` - Filtername
- `default` - Standardwert
- `value` - Wert
- `key` - Key im session_state
- `all_hrefs` - Alle Hrefs
- `multiselect_key` - Multiselect-Key
- `multiple_offers_key` - Multiple-Offers-Key
- `date_str` - Datum als String
- `time_obj` - Zeit-Objekt
- `sport_name` - Sportname
- `keys_to_remove` - Zu entfernende Keys

### shared_sidebar.py
- `filter_type` - Filter-Typ
- `sports_data` - Sportdaten
- `termins` - Termine
- `show_only_dates_state` - Zustand "Nur Datum"
- `show_only_dates` - Checkbox-State
- `search_text_state` - Suchtext-Zustand
- `search_text` - Suchtext
- `intensities` - Intensitäten-Liste
- `all_focuses` - Alle Fokusse
- `all_settings` - Alle Settings
- `focuses` - Fokusse-Liste
- `settings` - Settings-Liste
- `selected_intensity` - Ausgewählte Intensität
- `selected_focus` - Ausgewählter Fokus
- `selected_setting` - Ausgewähltes Setting
- `sport_names` - Sportnamen-Liste
- `default_sports` - Standard-Sportarten
- `selected_name` - Ausgewählter Name
- `sport_state` - Sport-Zustand
- `selected_sports` - Ausgewählte Sportarten
- `non_cancelled_state` - Nicht-storniert-Zustand
- `show_only_non_cancelled` - Nur nicht-storniert Checkbox
- `preset_start_date` - Voreingestelltes Startdatum
- `preset_end_date` - Voreingestelltes Enddatum
- `start_date_state` - Startdatum-Zustand
- `end_date_state` - Enddatum-Zustand
- `start_date` - Startdatum
- `end_date` - Enddatum
- `date_col1`, `date_col2` - Datumsspalten
- `locations` - Standorte
- `location_state` - Standort-Zustand
- `selected_locations` - Ausgewählte Standorte
- `weekdays_de` - Deutsche Wochentage Mapping
- `weekdays_options` - Wochentagsoptionen
- `weekday_state` - Wochentag-Zustand
- `selected_weekdays` - Ausgewählte Wochentage
- `time_col1`, `time_col2` - Zeitspalten
- `preset_start_time` - Voreingestellte Startzeit
- `start_time_state` - Startzeit-Zustand
- `end_time_state` - Endzeit-Zustand
- `start_time_filter` - Startzeit-Filter
- `end_time_filter` - Endzeit-Filter
- `all_angebote_for_select` - Alle Angebote zur Auswahl
- `href_to_offer` - Mapping von href zu Angebot
- `offer_options` - Angebotsoptionen
- `current_selected` - Aktuell Ausgewählte
- `selected_offers` - Ausgewählte Angebote
- `selected_names` - Ausgewählte Namen

### supabase_client.py
- `conn` - Supabase-Verbindung
- `url` - Supabase-URL
- `key` - Supabase-Key
- `trainers_data` - Trainer-Daten
- `termin` - Termin-Objekt
- `trainers` - Trainer-Array
- `result` - Query-Ergebnis
- `now` - Aktueller Zeitpunkt
- `termins_result` - Termine-Ergebnis
- `termins` - Termine
- `counts` - Anzahl-Dictionary
- `offer_href` - Angebots-Href
- `mapping` - Mapping-Dictionary
- `termin_result` - Termin-Ergebnis
- `href_to_trainers` - Mapping von href zu Trainern
- `trainer` - Trainer-Objekt
- `trainer_dict` - Trainer-Dictionary

---

## Dictionary Keys

### weekdays_de Mapping
- `Monday` → `Mo`
- `Tuesday` → `Di`
- `Wednesday` → `Mi`
- `Thursday` → `Do`
- `Friday` → `Fr`
- `Saturday` → `Sa`
- `Sunday` → `So`

### weekdays_de Mapping (Langform in page_2.py)
- `Monday` → `Montag`
- `Tuesday` → `Dienstag`
- `Wednesday` → `Mittwoch`
- `Thursday` → `Donnerstag`
- `Friday` → `Freitag`
- `Saturday` → `Samstag`
- `Sunday` → `Sonntag`

### weekdays_en Mapping (page_3.py)
- `'Monday': 'Mo'`
- `'Tuesday': 'Di'`
- `'Wednesday': 'Mi'`
- `'Thursday': 'Do'`
- `'Friday': 'Fr'`
- `'Saturday': 'Sa'`
- `'Sunday': 'So'`

### day_names Array (page_3.py)
- `'Montag'`, `'Dienstag'`, `'Mittwoch'`, `'Donnerstag'`, `'Freitag'`, `'Samstag'`, `'Sonntag'`

---

## Supabase Tabellen und Views

### Tabellen
- `sportangebote_with_ratings` - View mit Sportangeboten und Bewertungen
- `vw_termine_full` - View mit vollständigen Termininformationen

### View Struktur: vw_termine_full
Enthält folgende Felder:
- `offer_href` - Referenz zum Sportangebot
- `start_time` - Startzeit (ISO Format)
- `end_time` - Endzeit (ISO Format)
- `canceled` - Boolean Stornierungsstatus
- `sport_name` - Name des Sports
- `sport_icon` - Icon des Sports
- `location_name` - Name des Standorts
- `kursnr` - Kursnummer
- `trainers` - JSON-Array mit Trainer-Informationen
- `preis` - Preis
- `buchung` - Buchungsinformationen
- `details` - Kursdetails

---

## Globale Schlüssel in der Anwendung

### Streamlit Konfiguration
- `st.connection` - Supabase-Verbindung über Streamlit Connection
- `st.cache_data` - Caching-Dekorator für Daten-Funktionen
- `ttl` - Time-to-Live für Cache (300-600 Sekunden)

### Supabase Secrets Keys
- `connections.supabase.url` - Supabase-URL aus Secrets
- `connections.supabase.key` - Supabase-API-Key aus Secrets

---

## Farb- und Stil-Indikatoren

### Status-Indikatoren
- `🔴` - Storniert (rot)
- `🟢` - Aktiv (grün)
- `✓` - Checkmark für Storniert-Status

### Hintergrundfarben
- `#ffebee` - Storniert (helles Rot)
- `#e8f5e9` - Aktiv (helles Grün)

---

*Index erstellt am: {{ current_date }}*

