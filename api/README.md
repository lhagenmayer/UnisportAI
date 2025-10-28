# Unisport iCal Feed - FastAPI auf Vercel

## Deployment zu Vercel

### Option 1: Vercel CLI
```bash
npm install -g vercel
vercel deploy
```

### Option 2: Git Integration
1. Commit und push zu GitHub
2. Verbinde Repo in Vercel Dashboard
3. Automatisches Deployment

## Environment Variables

Füge diese in Vercel Dashboard hinzu:
- `SUPABASE_URL` - Deine Supabase URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase Service Role Key

## API Endpoint

Nach Deployment:
```
https://your-app.vercel.app/ical-feed?token=USER_TOKEN
```

## Lokales Testen

```bash
uvicorn api.main:app --reload
```

## Struktur

- `api/main.py` - FastAPI App
- `api/requirements.txt` - Python Dependencies
- `vercel.json` - Vercel Configuration

