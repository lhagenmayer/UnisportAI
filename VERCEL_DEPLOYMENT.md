# Vercel Deployment Guide

## 🚀 Deployment für iCal Feed (FastAPI)

Das Projekt ist bereit für Vercel Deployment!

### 📁 Struktur

```
Unisport/
├── api/
│   ├── main.py              # FastAPI App
│   ├── requirements.txt      # Python Dependencies
│   └── README.md            # API Docs
├── vercel.json              # Vercel Config
└── data/user_management.py  # Updated URLs
```

### ⚙️ Environment Variables

Füge diese in Vercel Dashboard hinzu:

```bash
SUPABASE_URL=https://mcbbjvjezbgekbmcajii.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 🔧 Deployment Steps

#### Option 1: Vercel Dashboard (Empfohlen)

1. **Projekt erstellen:**
   - Gehe zu [vercel.com](https://vercel.com)
   - Klicke "Add New Project"
   - Verbinde mit GitHub Repo
   - Wähle dieses Repository

2. **Root Directory setzen:**
   - Root Directory: `/` (Projekt Root)
   - Framework Preset: None
   - Build Command: None
   - Output Directory: None

3. **Environment Variables:**
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

4. **Deploy!**

#### Option 2: Vercel CLI (Wenn installiert)

```bash
# Login
vercel login

# Deploy
vercel deploy

# Production Deploy
vercel --prod
```

### 🌐 Nach Deployment

1. **Notiere die Vercel URL**, z.B.:
   ```
   https://unisport-ical.vercel.app
   ```

2. **Update Streamlit Secrets:**
   Füge zu `.streamlit/secrets.toml` hinzu:
   ```toml
   [vercel]
   url = "https://deine-app.vercel.app"
   ```

3. **Teste den Endpoint:**
   ```bash
   curl "https://deine-app.vercel.app/ical-feed?token=DEIN_TOKEN"
   ```

### 📊 API Endpoints

- `GET /` - Health Check
- `GET /ical-feed?token=TOKEN` - iCal Feed
- `GET /api/health` - API Health

### 🧪 Lokales Testen

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```

### 📝 Features

✅ FastAPI mit icalendar Library  
✅ Personalisiert pro User (Token-basiert)  
✅ Friend ATTENDEE Support  
✅ GEO-Coordinates für Maps  
✅ Automatische Updates  
✅ Vercel Serverless  

### ⚠️ Wichtige Notes

- Die Vercel URL kann im Streamlit Secrets gespeichert werden
- Falls Vercel nicht verfügbar, nutzt die App automatisch Supabase Edge Function
- Die Edge Function bleibt als Backup aktiv

