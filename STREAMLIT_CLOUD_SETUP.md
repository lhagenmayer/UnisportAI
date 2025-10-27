# Streamlit Cloud Setup Guide

## Secrets Configuration

You need to add your secrets to Streamlit Cloud through the web interface:

### Step 1: Access Streamlit Cloud Dashboard
1. Go to https://share.streamlit.io
2. Log in with your GitHub account
3. Find your UnisportAI app
4. Click "Manage app" (lower right corner)

### Step 2: Add Secrets
1. Go to **Settings** tab
2. Click on **Secrets** section
3. Click **Edit secrets**
4. Paste the following secrets in TOML format:

```toml
# Supabase Connection Configuration
[connections.supabase]
url = "https://mcbbjvjezbgekbmcajii.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1jYmJqdmplemJnZWtibWNhamlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0ODE3MzEsImV4cCI6MjA3NTA1NzczMX0.oFYzF9FeUtEUqfV85dSwyoC_y3IFKwxB_1zHh9UZDU8"

# OIDC Authentication Configuration
[auth]
cookie_secret = "PdOopUY7t6QvHXnL7CNUuaJzPJGT6fuTYDcb05nfkdA"
redirect_uri = "https://unisportai.streamlit.app/oauth2callback"

[auth.google]
client_id = "308462755179-mna1d0u68c7oo1rji1b6qndfu2guucl9.apps.googleusercontent.com"
client_secret = "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"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

### Step 3: Save and Deploy
1. Click **Save**
2. The app will automatically redeploy
3. Wait for the deployment to complete

## Important Notes

### Security
- Never commit secrets to GitHub
- The `.streamlit/secrets.toml` file is already in `.gitignore`
- Always use the Streamlit Cloud dashboard for production secrets

### Redirect URIs
Make sure you've added the production URL to your Google OAuth configuration:
- **Production**: `https://unisportai.streamlit.app/oauth2callback`

### Local Development
For local development, use `.streamlit/secrets.toml` (already configured)

## Deployment Status

Once secrets are configured, the app should:
1. ✅ Start successfully
2. ✅ Show login page
3. ✅ Allow Google OAuth authentication
4. ✅ Connect to Supabase database

## Troubleshooting

If the app still shows errors after adding secrets:
1. Check that secrets are saved in Streamlit Cloud dashboard
2. Verify the redirect URI is correct in Google Cloud Console
3. Check deployment logs in Streamlit Cloud
4. Verify Supabase URL and anon key are correct

## Next Steps

1. Add secrets to Streamlit Cloud dashboard
2. Verify the app deploys successfully
3. Test login with Google OAuth
4. Check that data is syncing to Supabase

