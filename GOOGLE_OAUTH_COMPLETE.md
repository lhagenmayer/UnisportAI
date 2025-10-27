# ✅ Google OAuth Setup - Komplett

## Was wurde implementiert

### 1. Authentifizierung
- ✅ Google OIDC Integration über Streamlit's native `st.login` API
- ✅ Dynamische Redirect URIs (keine manuelle Port-Konfiguration)
- ✅ Automatische Benutzer-Synchronisation mit Supabase
- ✅ Token-Ablauf-Prüfung

### 2. Datenbank
- ✅ Migration ausgeführt: `add_oidc_fields_to_users`
- ✅ Bestehende `users` Tabelle erweitert mit:
  - `sub` (OIDC unique identifier)
  - `name`, `given_name`, `family_name`
  - `picture`
  - `role`
  - `provider`
  - `last_login`
  - `is_active`
- ✅ Indizes für schnelle Abfragen erstellt

### 3. Code-Implementierung
- ✅ `data/auth.py` - Authentifizierungs-Logik
- ✅ `data/supabase_client.py` - Erweiterte DB-Funktionen
- ✅ `streamlit_app.py` - Integration der Auth-Prüfung
- ✅ Kompatibel mit bestehender `users` Tabelle

### 4. Dokumentation
- ✅ `AUTHENTICATION_SETUP.md` - Detaillierte Anleitung
- ✅ `REDIRECT_URI_GUIDE.md` - Redirect URI Konfiguration
- ✅ `setup_google_oauth.py` - Setup-Script
- ✅ `GOOGLE_OAUTH_COMPLETE.md` - Diese Datei

## Nächste Schritte

### 1. Google Cloud Console Konfiguration

Sie müssen noch in der Google Cloud Console konfigurieren:

**URL**: https://console.cloud.google.com/

**Schritte**:

1. **Projekt wählen/erstellen**
   - Gehen Sie zur Cloud Console
   - Wählen Sie ein Projekt oder erstellen Sie ein neues

2. **OAuth Consent Screen konfigurieren**
   - APIs & Services → OAuth consent screen
   - Extern wählen
   - App-Name: "Unisport App"
   - Support-E-Mail: Ihre E-Mail
   - Speichern

3. **OAuth Client-ID erstellen**
   - APIs & Services → Credentials
   - "CREATE CREDENTIALS" → "OAuth client ID"
   - Application type: "Web application"
   - Name: "Unisport Streamlit"
   
   **Autorierte Redirect URIs** (hier alle URIs hinzufügen):
   ```
   http://localhost:8501/oauth2callback
   http://localhost:8502/oauth2callback
   http://localhost:8503/oauth2callback
   http://localhost:8504/oauth2callback
   http://localhost:8505/oauth2callback
   https://unisportai.streamlit.app/oauth2callback
   ```
   
   ⚠️ **Wichtig**: 
   - "Autorisierte JavaScript-Quellen" Feld **LEER LASSEN** (nicht benötigt für Streamlit)
   - Nur "Autorisierte Redirect URIs" ausfüllen
   - "Autorisierte Ursprünge" kann ebenfalls leer bleiben

4. **Credentials kopieren**
   - Client ID kopieren
   - Client Secret kopieren (wird nur einmal angezeigt!)

### 2. secrets.toml aktualisieren

Bearbeiten Sie `.streamlit/secrets.toml`:

```toml
[auth]
cookie_secret = "GENERIERTES_COOKIE_SECRET"  # Mindestens 32 Zeichen!

[auth.google]
client_id = "Ihre Google Client ID"
client_secret = "Ihr Google Client Secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

**Cookie Secret generieren**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. App testen

```bash
streamlit run streamlit_app.py
```

**Erwartetes Verhalten**:
1. Login-Seite wird angezeigt
2. "Mit Google anmelden" Button
3. OAuth-Flow führt zu Google-Anmeldung
4. Nach Anmeldung wird Benutzer zugeordnet in Supabase

### 4. Streamlit Cloud Deployment

Für `https://unisportai.streamlit.app`:

1. Gehen Sie zu: https://share.streamlit.io/
2. Wählen Sie Ihre App
3. Settings → Secrets
4. Fügen Sie die gleichen Secrets hinzu (ohne redirect_uri!)
5. Deploy

## FAQ

### Warum funktioniert der Login nicht?

**Mögliche Ursachen**:
- Google Client ID nicht in secrets.toml eingetragen
- Redirect URI nicht in Google Cloud Console eingetragen
- Cookie Secret zu kurz (< 32 Zeichen)
- App noch nicht deployed

### Wie ändere ich den User-Role?

```sql
-- In Supabase SQL Editor
UPDATE users SET role = 'admin' WHERE email = 'ihre@email.com';
```

### Wie teste ich lokal?

1. `cookie_secret` in secrets.toml generieren
2. Google Client ID eintragen
3. App starten: `streamlit run streamlit_app.py`
4. Port in Google Console als redirect_uri eintragen

### Wie sehe ich, ob ein User in der DB ist?

```sql
-- In Supabase SQL Editor
SELECT * FROM users;
```

## Architektur

```
┌─────────────────┐
│  Streamlit App  │
│  (st.login)     │◄─────┐
└────────┬────────┘      │
         │                │
         │ OAuth Flow     │ OAuth Redirect
         ▼                │
┌─────────────────┐       │
│   Google OIDC   │       │
│   Provider      │───────┘
└────────┬────────┘
         │
         │ Token + User Info
         ▼
┌─────────────────┐
│ Supabase Users  │
│   Table         │
└─────────────────┘
```

## Sicherheit

✅ **Konfiguriert**:
- Cookie-basierte Sessions
- Token-Ablauf-Prüfung
- Service Role Key für DB-Zugriff
- Row Level Security (wird von App-Schicht gesteuert)

⚠️ **Wichtig**:
- Niemals `secrets.toml` in Git committen!
- Cookie Secret geheim halten
- Client Secret geheim halten
- Regelmäßig prüfen, wer Zugriff auf die App hat

## Support

Bei Problemen:
1. Überprüfen Sie die Logs in der App
2. Überprüfen Sie Supabase Logs
3. Überprüfen Sie Google Cloud Console OAuth-Setup
4. Siehe `AUTHENTICATION_SETUP.md` für detaillierte Troubleshooting-Anleitung

## Nächste Features

Mögliche Erweiterungen:
- ✅ User-Profile-Verwaltung
- ✅ Rollen-basierte Zugriffssteuerung
- ✅ User-Präferenzen speichern
- ✅ Favoriten-Lernfunktionen
- ✅ Personalisierte Empfehlungen

