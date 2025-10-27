# Unisport Streamlit App

Eine Streamlit-App zur Anzeige von Unisport-Angeboten mit Filterfunktionen.

## 🚀 Features

- **🔐 Google OAuth Authentifizierung**: Sichere Anmeldung mit Google-Konten
- **📊 Overview Page**: Übersicht aller Sportangebote mit Cards
- **📅 Details Page**: Detaillierte Kurs-Termine für ausgewählte Aktivitäten
- **📆 Calendar Page**: Wochenansicht aller verfügbaren Termine
- **🔍 Umfangreiche Filterfunktionen**: Nach Intensität, Fokus, Zeit, Ort, etc.
- **👤 Trainer-Informationen**: Trainer-Details mit Bewertungen
- **⭐ Bewertungssystem**: Durchschnittsbewertungen für alle Aktivitäten
- **👥 Benutzerverwaltung**: Persistente Benutzerdaten in Supabase

## 📦 Installation

```bash
pip install -r requirements.txt
```

## 🔧 Konfiguration

### 1. Supabase Setup

Erstellen Sie `.streamlit/secrets.toml`:

```toml
[connections.supabase]
url = "Ihre Supabase URL"
key = "Ihr Supabase Key"

# OIDC Authentication (Google)
# Hinweis: redirect_uri wird automatisch von Streamlit gesetzt
# Lokal: http://localhost:PORT/oauth2callback
# Production: https://unisportai.streamlit.app/oauth2callback
[auth]
cookie_secret = "MINIMAL_32_ZEICHEN_LANGES_GEHEIMNIS"

[auth.google]
client_id = "Ihre Google Client ID"
client_secret = "Ihr Google Client Secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

### 2. Google OAuth einrichten

Folgen Sie der detaillierten Anleitung in `AUTHENTICATION_SETUP.md` um:
- Google Cloud Console zu konfigurieren
- OAuth Client-ID zu erstellen
- Die Benutzertabelle in Supabase zu erstellen

> 💡 **Wichtig**: Für die Konfiguration der Redirect URIs mit dynamischen Ports und der Production-URL (`unisportai.streamlit.app`), siehe `REDIRECT_URI_GUIDE.md`

### 3. Datenbank-Migration

Führen Sie die SQL-Migration aus:
```bash
# In Supabase SQL Editor
supabase_migrations/create_users_table.sql
```

## ▶️ Starten

```bash
streamlit run streamlit_app.py
```

## 📁 Projektstruktur

- **pages/** - Streamlit-Seiten
  - `overview.py` - Hauptübersicht aller Aktivitäten
  - `details.py` - Detailansicht für Kurs-Termine
  - `calendar.py` - Wochenansicht aller Termine
- **data/** - Datenzugriff und Logik
  - `state_manager.py` - Session State Management
  - `supabase_client.py` - Supabase Client
  - `filters.py` - Filter-Funktionen
  - `shared_sidebar.py` - Gemeinsame Sidebar
- **.scraper/** - Scraping-Tools

## 🎯 Namenskonvention

Die App verwendet ein Entity-Prefix-System:
- `offer_*` - Sportangebote
- `event_*` - Termine
- `course_*` - Kurse
- `trainer_*` - Trainer
- `location_*` - Standorte
- `state_*` - Session State
- `filter_*` - Filter

## 📚 Dokumentation

- `VARIABLE_INDEX.md` - Variablen-Index
- `MIGRATION_SUMMARY.md` - Migrations-Zusammenfassung
- `TESTING_INSTRUCTIONS.md` - Test-Anweisungen

## 🏗️ Architektur

Die App ist in drei Hauptseiten unterteilt:

1. **Overview** (`overview.py`) - Zeigt alle Sportangebote mit Filter-Optionen
2. **Details** (`details.py`) - Zeigt Kurs-Termine für ausgewählte Aktivitäten
3. **Calendar** (`calendar.py`) - Zeigt Wochenansicht aller Termine

Jede Seite nutzt die `render_shared_sidebar()` Funktion für konsistente Filter.
