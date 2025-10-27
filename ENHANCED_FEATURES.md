# ✨ Erweiterte Features - User Management

## 🎯 Übersicht

Die App wurde mit erweiterten User-Management-Features ausgestattet, inspiriert vom [Streamlit-Authenticator](https://github.com/mkhorasani/Streamlit-Authenticator), aber optimiert für OIDC + Supabase.

## 🆕 Neue Features

### 1. 👤 User-Profile Seite
**Ort:** `pages/profile.py`

**Features:**
- ✅ Persönliche Informationen anzeigen
- ✅ Präferenzen verwalten (Lieblings-Sportarten, Notifications, Theme)
- ✅ Profilbild anzeigen
- ✅ Aktivitäts-Log

**Verwendung:**
```python
from data.user_management import render_user_profile_page
render_user_profile_page()
```

### 2. 🔧 Admin-Panel
**Ort:** `pages/admin.py`

**Features:**
- ✅ Alle User auflisten und verwalten
- ✅ User-Rollen ändern (user ↔ admin)
- ✅ User-Status aktivieren/deaktivieren
- ✅ Statistik-Dashboard
- ✅ Nur für Admins zugänglich

**Verwendung:**
```python
from data.user_management import render_admin_panel, is_admin

if is_admin():
    render_admin_panel()
```

### 3. 🔐 Verbesserte Sidebar
**Erweiterte User-Menü:**
- Profil-Button
- Admin-Button (nur für Admins sichtbar)
- Abmelden-Button
- User-Informationen

### 4. 📊 User-Präferenzen
**Features:**
- Speichern von Lieblings-Sportarten
- Notification-Einstellungen
- Theme-Präferenzen
- Persistente Speicherung in Supabase

**Code:**
```python
from data.user_management import update_user_preferences

preferences = {
    'favorite_sports': ['Yoga', 'Fitness'],
    'notifications': True,
    'theme': 'dark'
}
update_user_preferences(preferences)
```

### 5. 🔍 Admin-Check Funktion
Prüft ob ein User Admin-Rechte hat:

```python
from data.user_management import is_admin

if is_admin():
    # Admin-only Features
    pass
```

### 6. 📝 Activity Logging
Protokolliert User-Aktivitäten:

```python
from data.user_management import log_user_activity

log_user_activity("view_sports", {"count": 10})
log_user_activity("filter_applied", {"filter": "intensity:high"})
```

## 📊 Vergleich: Vor vs. Nach

### Vorher
- ❌ Kein User-Profile
- ❌ Keine Präferenzen
- ❌ Kein Admin-Panel
- ❌ Begrenzte Session-Verwaltung

### Nachher
- ✅ Vollständiges User-Profile mit Tabs
- ✅ Präferenzen-System
- ✅ Admin-Panel für User-Verwaltung
- ✅ Activity Logging
- ✅ Rollen-basierte Zugriffssteuerung
- ✅ Benutzerfreundliche Navigation

## 🎨 Features im Detail

### User-Profile Seite

**Tab 1: Informationen**
```
👤 Mein Profil
━━━━━━━━━━━━━━━
📋 Informationen
━━━━━━━━━━━━━━━

Name: Max Mustermann
E-Mail: max@example.com
Rolle: User
Registriert: 2025-01-15
Letzter Login: 2025-10-27
```

**Tab 2: Präferenzen**
```
⚙️ Präferenzen
━━━━━━━━━━━━━━

Lieblings-Sportarten: [Yoga, Fitness]
☑ E-Mail Benachrichtigungen
Design-Theme: Dark
```

**Tab 3: Aktivität**
```
📊 Aktivität
━━━━━━━━━━━━
2025-10-27 10:30: view_sports
2025-10-27 11:15: filter_applied
```

### Admin-Panel

**Features:**
1. **User-Liste** - Alle registrierten User
2. **Rolle ändern** - Dropdown für Role-Management
3. **Status toggle** - User aktivieren/deaktivieren
4. **Statistiken** - Gesamtbenutzer, Aktive, Admins

**Verwendung:**
- Admin-Werden: `UPDATE users SET role = 'admin' WHERE email = '...'`
- User deaktivieren: Über das Admin-Panel

## 🔧 Technische Details

### Datenbank-Schema

Die `users` Tabelle wurde erweitert:

```sql
users (
    id UUID PRIMARY KEY,
    sub TEXT UNIQUE,        -- OIDC identifier
    email TEXT,
    name TEXT,
    role TEXT,              -- 'user' oder 'admin'
    preferences JSONB,      -- User-Präferenzen
    is_active BOOLEAN,      -- User-Status
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_login TIMESTAMP,
    -- ... weitere Felder
)
```

### Rollen-System

**Roles:**
- `user` - Standard-User
- `admin` - Administrator (voller Zugriff)

**Rolle setzen:**
```sql
-- Via SQL
UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';

-- Oder über Admin-Panel
```

### Session-Verwaltung

Aktivitäten werden in `st.session_state` gespeichert:
```python
st.session_state.user_activities = [
    {
        "timestamp": "2025-10-27T10:30:00",
        "activity_type": "view_sports",
        "details": {...}
    }
]
```

## 🚀 Verwendung

### 1. User-Profile öffnen
- Klicke auf "📝 Profil" in der Sidebar
- Oder: `st.switch_page("pages/profile.py")`

### 2. Admin-Panel öffnen
- Klicke auf "🔧 Admin" in der Sidebar (nur für Admins)
- Oder: `st.switch_page("pages/admin.py")`

### 3. Erste Admin erstellen
```sql
-- In Supabase SQL Editor
UPDATE users 
SET role = 'admin' 
WHERE email = 'ihre@email.com';
```

## 📚 Dokumentation

- `data/user_management.py` - User-Management-Module
- `pages/profile.py` - User-Profile Seite
- `pages/admin.py` - Admin-Panel Seite
- `AUTH_COMPARISON.md` - Vergleich der Ansätze

## 🎯 Best Practices

1. **Admin-Rechte vorsichtig vergeben**
2. **Präferenzen für personalisierte Erfahrungen nutzen**
3. **Activity Logs für Analytics verwenden**
4. **Regelmäßig User-Prüfung im Admin-Panel**

## 🔮 Zukunftige Erweiterungen

Mögliche Features:
- 📧 E-Mail-Benachrichtigungen
- 📊 Erweitertes Analytics
- 🎯 Empfehlungs-Engine basierend auf Präferenzen
- 👥 Freundesystem
- ⭐ Favoriten-System
- 📱 Mobile-optimierte Profile-Seite

