#!/usr/bin/env python3
"""
Google OAuth Setup Script für Unisport App

Dieses Skript hilft bei der Konfiguration der Google OAuth Anmeldedaten.
"""

import os
import sys
import secrets
from pathlib import Path

def generate_cookie_secret():
    """Generiert ein sicheres Cookie Secret"""
    return secrets.token_urlsafe(32)

def create_secrets_template():
    """Erstellt ein Vorlage-Template für secrets.toml"""
    
    secrets_dir = Path(".streamlit")
    secrets_dir.mkdir(exist_ok=True)
    
    secrets_file = secrets_dir / "secrets.toml.template"
    
    template = """# Supabase Connection Configuration
# Kopieren Sie diese Datei zu .streamlit/secrets.toml und füllen Sie die Werte aus

[connections.supabase]
url = "https://mcbbjvjezbgekbmcajii.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1jYmJqdmplemJnZWtibWNhamlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0ODE3MzEsImV4cCI6MjA3NTA1NzczMX0.oFYzF9FeUtEUqfV85dSwyoC_y3IFKwxB_1zHh9UZDU8"

# OIDC Authentication Configuration
# redirect_uri wird automatisch von Streamlit gesetzt basierend auf der aktuellen URL
[auth]
cookie_secret = "{cookie_secret}"

[auth.google]
client_id = "IHR_GOOGLE_CLIENT_ID_HIER"
client_secret = "IHR_GOOGLE_CLIENT_SECRET_HIER"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
"""
    
    cookie_secret = generate_cookie_secret()
    
    with open(secrets_file, "w") as f:
        f.write(template.format(cookie_secret=cookie_secret))
    
    print(f"✅ Template erstellt: {secrets_file}")
    print(f"✅ Cookie Secret generiert: {cookie_secret[:20]}...")
    
    return secrets_file

def print_manual_setup_instructions():
    """Druckt manuelle Setup-Anweisungen"""
    
    print("\n" + "="*80)
    print("🔧 MANUELLE GOOGLE CLOUD CONSOLE KONFIGURATION")
    print("="*80)
    
    print("""
1. ÖFFNEN SIE GOOGLE CLOUD CONSOLE
   URL: https://console.cloud.google.com/

2. WÄHLEN SIE EIN PROJEKT
   - Klicken Sie auf "Projekt auswählen"
   - Wählen Sie ein bestehendes Projekt oder erstellen Sie ein neues

3. AKTIVIEREN SIE DIE GOOGLE+ API
   - Gehen Sie zu: APIs & Services → Bibliothek
   - Suchen Sie nach "Google+ API"
   - Klicken Sie auf "Aktivieren"

4. ERSTELLEN SIE EINE OAUTH CLIENT-ID
   - Gehen Sie zu: APIs & Services → Anmeldedaten
   - Klicken Sie auf "ANMELDEDATEN ERSTELLEN" → "OAuth-Client-ID"
   
5. KONFIGURIEREN SIE DEN CONSENT SCREEN
   (Falls noch nicht geschehen)
   - Wählen Sie "Extern" (oder "Intern" für Workspace)
   - App-Name: "Unisport App"
   - Support-E-Mail: Ihre E-Mail
   - Speichern Sie

6. ERSTELLEN SIE DEN OAUTH CLIENT
   - Anwendungstyp: "Webanwendung"
   - Name: "Unisport Streamlit App"
   
   Autorierte Umleitungs-URIs hinzufügen:
   
   ✅ FÜR LOKALE ENTWICKLUNG (Port 8501-8505):
      http://localhost:8501/oauth2callback
      http://localhost:8502/oauth2callback
      http://localhost:8503/oauth2callback
      http://localhost:8504/oauth2callback
      http://localhost:8505/oauth2callback
   
   ✅ FÜR PRODUCTION:
      https://unisportai.streamlit.app/oauth2callback
   
   - Klicken Sie auf "ERSTELLEN"

7. KOPIEREN SIE DIE CREDENTIALS
   - Client-ID: [Kopieren Sie dies]
   - Client Secret: [Kopieren Sie dies]

8. AKTUALISIEREN SIE IHR secrets.toml
   - Öffnen Sie .streamlit/secrets.toml
   - Ersetzen Sie "IHR_GOOGLE_CLIENT_ID_HIER" mit Ihrer Client-ID
   - Ersetzen Sie "IHR_GOOGLE_CLIENT_SECRET_HIER" mit Ihrem Client-Secret

9. TESTEN SIE DIE KONFIGURATION
   ```bash
   streamlit run streamlit_app.py
   ```
""")
    
    print("\n" + "="*80)
    print("📝 ALTERNATIVE: VERWENDEN SIE DEN GOOGLE CLOUD CONSOLE CLI")
    print("="*80)
    
    print("""
Falls Sie `gcloud` CLI installiert haben, können Sie:

# Authentifizierung
gcloud auth login

# Projekt setzen
gcloud config set project YOUR-PROJECT-ID

# OAuth Client erstellen
gcloud alpha iap oauth-clients create \
  --display_name="Unisport Streamlit" \
  --id_string="unisport-streamlit"

# Authorized redirect URIs hinzufügen
# (Dies muss über die Web Console gemacht werden)
    """)

def main():
    print("\n🚀 Google OAuth Setup für Unisport App")
    print("="*80)
    
    # Erstelle Template
    template_file = create_secrets_template()
    
    # Prüfe ob secrets.toml bereits existiert
    secrets_file = Path(".streamlit/secrets.toml")
    
    if not secrets_file.exists():
        print(f"\n⚠️  secrets.toml existiert noch nicht.")
        print(f"📝 Kopieren Sie {template_file} zu secrets.toml")
        print(f"   cp {template_file} {secrets_file}")
    else:
        print(f"\n✅ secrets.toml existiert bereits")
        print(f"   Überprüfen Sie, ob Ihre Google Credentials eingetragen sind.")
    
    # Drucke Anweisungen
    print_manual_setup_instructions()
    
    print("\n" + "="*80)
    print("✅ Setup-Vorbereitung abgeschlossen!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()

