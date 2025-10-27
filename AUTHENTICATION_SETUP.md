# 🔐 Authentifizierungs-Setup

Diese Anleitung erklärt, wie Sie die Google OAuth Authentifizierung für die Unisport Streamlit-App einrichten.

## 📋 Übersicht

Die App verwendet:
- **Streamlit's native OIDC-Integration** für die Anmeldung
- **Google als Identity Provider**
- **Supabase** als Backend für Benutzerverwaltung

## 🚀 Schritt-für-Schritt Anleitung

### Schritt 1: Google Cloud Console Konfiguration

1. **Gehen Sie zur Google Cloud Console**
   - Öffnen Sie: https://console.cloud.google.com/
   
2. **Erstellen Sie ein neues Projekt** (oder wählen Sie ein bestehendes)
   - Klicken Sie auf "Projekt auswählen" → "Neues Projekt"
   - Geben Sie einen Namen ein (z.B. "Unisport App")
   
3. **Aktivieren Sie die Google+ API**
   - Gehen Sie zu "APIs & Services" → "Bibliothek"
   - Suchen Sie nach "Google+ API"
   - Klicken Sie auf "Aktivieren"
   
4. **Erstellen Sie OAuth-Anmeldedaten**
   - Gehen Sie zu "APIs & Services" → "Anmeldedaten"
   - Klicken Sie auf "Anmeldedaten erstellen" → "OAuth-Client-ID"
   - Falls Sie zum ersten Mal OAuth verwenden, erstellen Sie eine "Consent Screen"
   
5. **Consent Screen konfigurieren** (falls noch nicht vorhanden):
   - Wählen Sie "Extern" (für Produktion: "Intern")
   - Geben Sie einen App-Namen ein (z.B. "Unisport")
   - Fügen Sie eine Support-E-Mail-Adresse hinzu
   - Speichern Sie
   
6. **OAuth Client-ID erstellen**
   - Anwendungstyp: "Webanwendung"
   - Name: "Unisport Streamlit"
   - Autorisierte Umleitungs-URIs:
     - Für lokale Entwicklung (verschiedene Ports): 
       - `http://localhost:8501/oauth2callback`
       - `http://localhost:8502/oauth2callback`
       - `http://localhost:8503/oauth2callback`
       - (Streamlit kann verschiedene Ports verwenden)
     - Für Production: `https://unisportai.streamlit.app/oauth2callback`
     - Optional: Wildcard für Entwicklung `http://localhost:*/oauth2callback`
   - Klicken Sie auf "Erstellen"
   
7. **Client-ID und Secret kopieren**
   - Speichern Sie die Client-ID und das Client-Geheimnis sicher

### Schritt 2: Supabase Datenbank Setup

1. **Loggen Sie sich in Ihr Supabase Dashboard ein**
   - Gehen Sie zu: https://supabase.com/dashboard
   - Wählen Sie Ihr Projekt aus

2. **SQL Editor öffnen**
   - Klicken Sie auf "SQL Editor" in der linken Sidebar

3. **Users-Tabelle erstellen**
   - Öffnen Sie die Datei `supabase_migrations/create_users_table.sql`
   - Kopieren Sie den gesamten SQL-Code
   - Fügen Sie ihn in den SQL Editor ein
   - Klicken Sie auf "Run"

### Schritt 3: Streamlit Secrets konfigurieren

1. **Lokale Entwicklung**
   
   Bearbeiten Sie die Datei `.streamlit/secrets.toml`:
   
   ```toml
   # Supabase Connection
   [connections.supabase]
   url = "Ihre Supabase URL"
   key = "Ihr Supabase Anonym Key"
   
   # OIDC Authentication
   [auth]
   redirect_uri = "http://localhost:8501/oauth2callback"
   cookie_secret = "IHR_ZUFÄLLIGES_GEHEIMNIS_MINDESTENS_32_ZEICHEN"
   
   [auth.google]
   client_id = "Ihre Google Client ID"
   client_secret = "Ihr Google Client Secret"
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
   ```

2. **Cookie Secret generieren**
   
   Generieren Sie ein sicheres Cookie Secret:
   
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```
   
   Oder verwenden Sie einen Online-Generator

3. **Streamlit Cloud** (https://unisportai.streamlit.app)
   
   - Gehen Sie zu https://share.streamlit.io/
   - Wählen Sie Ihre App aus
   - Gehen Sie zu "Settings" → "Secrets"
   - Fügen Sie den Inhalt hinzu (ohne redirect_uri, da diese automatisch gesetzt wird):
     ```toml
     [connections.supabase]
     url = "Ihre Supabase URL"
     key = "Ihr Supabase Key"
     
     [auth]
     cookie_secret = "Ihr Cookie Secret"
     
     [auth.google]
     client_id = "Ihre Google Client ID"
     client_secret = "Ihr Google Client Secret"
     server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
     ```
   - Die redirect_uri wird automatisch als `https://unisportai.streamlit.app/oauth2callback` gesetzt

### Schritt 4: App testen

1. **App starten**
   ```bash
   streamlit run streamlit_app.py
   ```

2. **Anmelden**
   - Sie sollten die Login-Seite sehen
   - Klicken Sie auf "Mit Google anmelden"
   - Wählen Sie Ihr Google-Konto aus
   - Bestätigen Sie die Berechtigungen

3. **Überprüfen**
   - Nach erfolgreicher Anmeldung sehen Sie die App mit Ihrem Namen in der Sidebar
   - Überprüfen Sie in Supabase, ob ein neuer Datensatz in der `users` Tabelle erstellt wurde

## 🔧 Troubleshooting

### Problem: "Redirect URI mismatch"

**Lösung**: Stellen Sie sicher, dass die Redirect-URI in Google Cloud Console genau mit der `redirect_uri` in `secrets.toml` übereinstimmt.

### Problem: "Invalid client secret"

**Lösung**: Überprüfen Sie, ob Sie das Client-Geheimnis korrekt aus der Google Cloud Console kopiert haben (keine zusätzlichen Leerzeichen).

### Problem: "Not logged in" Fehler

**Lösung**: 
- Überprüfen Sie die Secrets-Konfiguration
- Stellen Sie sicher, dass `cookie_secret` mindestens 32 Zeichen lang ist
- Überprüfen Sie die Logs auf weitere Fehlermeldungen

### Problem: Benutzer wird nicht in Supabase erstellt

**Lösung**:
- Überprüfen Sie die Supabase-Verbindung in `secrets.toml`
- Überprüfen Sie die SQL-Migration wurde korrekt ausgeführt
- Überprüfen Sie die Logs in Streamlit

## 🎯 Nächste Schritte

Nach erfolgreicher Einrichtung können Sie:

1. **Benutzerrollen verwalten**
   - Bearbeiten Sie die `role` Spalte in der `users` Tabelle in Supabase
   - Fügen Sie Rollen wie 'admin', 'moderator' hinzu

2. **Benutzerprofile erweitern**
   - Fügen Sie benutzerdefinierte Felder in der `users` Tabelle hinzu
   - Verwenden Sie das `preferences` JSON-Feld für Einstellungen

3. **Zusätzliche OAuth-Provider hinzufügen**
   - Folgen Sie den gleichen Schritten für Microsoft, GitHub, etc.
   - Fügen Sie neue `[auth.provider]` Abschnitte hinzu

## 📚 Weitere Ressourcen

- [Streamlit OAuth Documentation](https://docs.streamlit.io/develop/concepts/authentication/oauth)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Supabase Documentation](https://supabase.com/docs)

## 🔒 Sicherheitshinweise

1. **Nie committen Sie `secrets.toml`** mit echten Credentials in Git
2. **Verwenden Sie starke Cookie Secrets**
3. **Limitieren Sie Zugriff** auf die Supabase Keys
4. **Überprüfen Sie die Berechtigungen** in Google Cloud Console regelmäßig
5. **Aktivieren Sie RLS** (Row Level Security) in Supabase für besseren Schutz

## 📝 Checkliste

- [ ] Google Cloud Projekt erstellt
- [ ] Google+ API aktiviert
- [ ] OAuth Client-ID erstellt
- [ ] Redirect URIs konfiguriert
- [ ] Supabase `users` Tabelle erstellt
- [ ] Streamlit Secrets konfiguriert
- [ ] Cookie Secret generiert
- [ ] Lokale App erfolgreich getestet
- [ ] Cloud Deployment konfiguriert (falls zutreffend)

