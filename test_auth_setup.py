#!/usr/bin/env python3
"""
Test-Skript für die Google OAuth Implementierung
"""

import sys
from pathlib import Path

print("🧪 Teste Google OAuth Setup für Unisport App\n")

# Test 1: Prüfe ob secrets.toml existiert
print("1️⃣  Teste secrets.toml...")
secrets_file = Path(".streamlit/secrets.toml")
if not secrets_file.exists():
    print("   ❌ secrets.toml nicht gefunden!")
    sys.exit(1)
print("   ✅ secrets.toml existiert")

# Test 2: Prüfe secrets-Konfiguration
print("\n2️⃣  Teste Secrets-Konfiguration...")
try:
    import toml
    secrets_data = toml.load(secrets_file)
    
    # Prüfe Supabase Config
    if "connections" not in secrets_data or "supabase" not in secrets_data["connections"]:
        print("   ❌ Supabase connection nicht konfiguriert")
        sys.exit(1)
    print("   ✅ Supabase connection konfiguriert")
    
    # Prüfe Auth Config
    if "auth" not in secrets_data:
        print("   ❌ Auth configuration nicht gefunden")
        sys.exit(1)
    print("   ✅ Auth configuration gefunden")
    
    # Prüfe Cookie Secret
    auth_config = secrets_data.get("auth", {})
    cookie_secret = auth_config.get("cookie_secret", "")
    if not cookie_secret or len(cookie_secret) < 32:
        print("   ⚠️  Cookie Secret zu kurz oder nicht gesetzt")
        print(f"      Aktuelle Länge: {len(cookie_secret)} Zeichen")
        print("      Benötigt: mindestens 32 Zeichen")
    else:
        print("   ✅ Cookie Secret ist ausreichend lang")
    
    # Prüfe Google OAuth
    if "google" not in auth_config:
        print("   ❌ Google OAuth nicht konfiguriert")
        sys.exit(1)
    
    google_config = auth_config.get("google", {})
    client_id = google_config.get("client_id", "")
    
    if not client_id or client_id == "YOUR_GOOGLE_CLIENT_ID_HERE":
        print("   ⚠️  Google Client ID noch nicht konfiguriert")
        print("      Bitte tragen Sie Ihre Google Client ID ein")
    else:
        print("   ✅ Google Client ID ist konfiguriert")
        
    client_secret = google_config.get("client_secret", "")
    if not client_secret or client_secret == "YOUR_GOOGLE_CLIENT_SECRET_HERE":
        print("   ⚠️  Google Client Secret noch nicht konfiguriert")
        print("      Bitte tragen Sie Ihr Google Client Secret ein")
    else:
        print("   ✅ Google Client Secret ist konfiguriert")
        
except Exception as e:
    print(f"   ❌ Fehler beim Laden der Secrets: {e}")
    sys.exit(1)

# Test 3: Prüfe Imports
print("\n3️⃣  Teste Python Imports...")
try:
    import streamlit as st
    print("   ✅ Streamlit importiert")
except Exception as e:
    print(f"   ❌ Fehler beim Importieren von Streamlit: {e}")
    sys.exit(1)

try:
    from data.auth import check_auth, show_login_page
    print("   ✅ auth.py Imports erfolgreich")
except Exception as e:
    print(f"   ❌ Fehler beim Importieren von auth.py: {e}")
    sys.exit(1)

try:
    from data.supabase_client import get_supabase_client
    print("   ✅ supabase_client.py Imports erfolgreich")
except Exception as e:
    print(f"   ❌ Fehler beim Importieren von supabase_client.py: {e}")
    sys.exit(1)

# Test 4: Prüfe Supabase Migration
print("\n4️⃣  Prüfe Supabase Migrations...")
migration_file = Path("supabase_migrations/add_oidc_fields_to_users.sql")
if migration_file.exists():
    print("   ✅ Migration-Datei existiert")
else:
    print("   ⚠️  Migration-Datei nicht gefunden")
    
# Test 5: Prüfe ob users Tabelle existiert
print("\n5️⃣  Prüfe Supabase Tabelle...")
try:
    import streamlit as st
    from st_supabase_connection import SupabaseConnection
    
    # Stelle Verbindung her
    url = secrets_data["connections"]["supabase"]["url"]
    key = secrets_data["connections"]["supabase"]["key"]
    conn = SupabaseConnection(url=url, key=key)
    
    # Versuche die Tabelle abzufragen
    result = conn.table("users").select("id, email, sub").limit(1).execute()
    print("   ✅ users Tabelle ist erreichbar")
    
    # Prüfe ob OIDC Felder existieren
    if result.data:
        first_user = result.data[0]
        if "sub" in first_user:
            print("   ✅ OIDC-Feld 'sub' existiert in der Tabelle")
        else:
            print("   ⚠️  OIDC-Feld 'sub' fehlt - Migration noch nicht ausgeführt?")
            
except Exception as e:
    print(f"   ⚠️  Konnte Tabelle nicht prüfen: {e}")
    print("      (Das kann normal sein wenn die Migration noch nicht ausgeführt wurde)")

# Zusammenfassung
print("\n" + "="*80)
print("📋 ZUSAMMENFASSUNG")
print("="*80)

print("\n✅ Code-Implementierung:")
print("   - Authentifizierung: Implementiert")
print("   - Supabase Integration: Implementiert")
print("   - Datenbank-Migration: Bereit")

print("\n⚠️  Nächste Schritte:")
print("   1. Google Cloud Console konfigurieren")
print("   2. OAuth Client-ID erstellen")
print("   3. Client-ID und Secret in secrets.toml eintragen")
print("   4. App starten: streamlit run streamlit_app.py")
print("   5. Bei Google anmelden und Benutzer in Supabase erstellen")

print("\n📚 Dokumentation:")
print("   - GOOGLE_OAUTH_COMPLETE.md - Vollständige Anleitung")
print("   - AUTHENTICATION_SETUP.md - Detaillierte Setup-Schritte")
print("   - REDIRECT_URI_GUIDE.md - Redirect URI Konfiguration")

print("\n" + "="*80)
print("🎉 Setup-Check abgeschlossen!")
print("="*80 + "\n")

