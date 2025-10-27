# 📍 Redirect URI Konfigurations-Guide

## Überblick

Da Streamlit dynamisch Ports zuweist und sowohl lokal als auch in der Production-Umgebung läuft, muss die `redirect_uri` nicht mehr in den Secrets konfiguriert werden. Streamlit setzt diese automatisch basierend auf der aktuellen URL.

## Automatische Redirect URI

Streamlit erstellt automatisch die richtige `redirect_uri` basierend auf:

- **Lokale Entwicklung**: `http://localhost:PORT/oauth2callback`
  - Der Port kann variieren (8501, 8502, 8503, etc.)
  
- **Production (unisportai.streamlit.app)**: `https://unisportai.streamlit.app/oauth2callback`
  - Fest definierte URL für die Live-Umgebung

## Google Cloud Console Konfiguration

In Google Cloud Console müssen Sie alle möglichen Redirect URIs hinzufügen:

### Für lokale Entwicklung
```
http://localhost:8501/oauth2callback
http://localhost:8502/oauth2callback
http://localhost:8503/oauth2callback
http://localhost:8504/oauth2callback
http://localhost:8505/oauth2callback
```

**Tipp**: Streamlit verwendet standardmäßig Port 8501, kann aber andere Ports verwenden, wenn 8501 belegt ist.

### Für Production
```
https://unisportai.streamlit.app/oauth2callback
```

### Optionale Wildcard-Syntax
Einige OAuth-Provider unterstützen Wildcards (Google unterstützt dies nicht vollständig, aber Sie können es versuchen):
```
http://localhost:*/oauth2callback
```

## Streamlit Secrets Konfiguration

### Dynamische Port-Lösung

**Option 1: Fester Port (empfohlen für lokale Entwicklung)**

Bearbeiten Sie `.streamlit/secrets.toml` und setzen Sie einen festen redirect_uri-Port:

```toml
[auth]
cookie_secret = "Ihr Cookie Secret"
# Port entsprechend anpassen: 8501, 8502, 8503, etc.
redirect_uri = "http://localhost:8501/oauth2callback"

[auth.google]
client_id = "Ihre Google Client ID"
client_secret = "Ihr Google Client Secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Dann starten Sie die App immer auf diesem Port:
```bash
streamlit run streamlit_app.py --server.port 8501
```

**Option 2: redirect_uri im [auth] Abschnitt setzen**

Die `redirect_uri` kann auch im `[auth]` Abschnitt gesetzt werden statt bei `[auth.google]`.

## Best Practices

1. **Lokale Entwicklung**: Fügen Sie die 5 wichtigsten localhost-Port-Varianten hinzu
2. **Production**: Fügen Sie die genaue Production-URL hinzu
3. **Testen**: Testen Sie die Authentifizierung in beiden Umgebungen
4. **Sicherheit**: Überprüfen Sie regelmäßig, ob nur notwendige Redirect URIs vorhanden sind

## Troubleshooting

### Problem: "redirect_uri_mismatch" Fehler

**Ursache**: Die Redirect URI in Google Cloud Console stimmt nicht mit der tatsächlichen URL überein.

**Lösung**:
1. Überprüfen Sie, auf welchem Port Streamlit läuft (siehe Terminal-Output)
2. Fügen Sie den entsprechenden localhost-URI in Google Cloud Console hinzu
3. Warten Sie einige Minuten, bis die Änderungen propagiert sind
4. Versuchen Sie es erneut

### Problem: Port wechselt bei jedem Neustart

**Lösung**: 
- Nutzen Sie den `--port` Flag:
  ```bash
  streamlit run streamlit_app.py --server.port 8501
  ```
- Dann können Sie genau diesen Port in Google Cloud Console konfigurieren

### Für Production

In Streamlit Cloud wird die URL automatisch auf Ihre App-URL gesetzt:
- App-URL: `https://unisportai.streamlit.app`
- Redirect URI: `https://unisportai.streamlit.app/oauth2callback`

## Checkliste

- [ ] Lokale Redirect URIs hinzugefügt (Ports 8501-8505)
- [ ] Production Redirect URI hinzugefügt
- [ ] `redirect_uri` NICHT in `secrets.toml` vorhanden
- [ ] OAuth-Anmeldedaten in Google Cloud Console erstellt
- [ ] Secrets in Streamlit Cloud konfiguriert
- [ ] Getestet in lokaler Umgebung
- [ ] Getestet in Production-Umgebung

