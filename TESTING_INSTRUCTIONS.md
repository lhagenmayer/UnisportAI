# Testing Instructions for UnisportAI Streamlit App

## Overview
This document provides step-by-step instructions for AI agents using browser capabilities and MCP (Model Context Protocol) to test the UnisportAI application.

## Application URLs
- **Local:** http://localhost:8501
- **Live:** https://unisportai.streamlit.app

## Prerequisites
1. Browser MCP tools available (cursor-playwright)
2. Access to both local and live versions
3. Supabase connection configured

## Testing Procedure

### 1. Local Testing

#### Step 1: Navigate to Local Version
```python
# Use browser MCP tool
mcp_cursor-playwright_browser_navigate(url="http://localhost:8501")
```

#### Step 2: Wait for Page Load
```python
# Wait for content to load
mcp_cursor-playwright_browser_wait_for(time=5)
```

#### Step 3: Verify Components
Check for:
- ✅ Left sidebar with navigation (Main Page, Page 2, Page 3)
- ✅ Page title "Unisport Planner"
- ✅ Data table with columns: `kursnr`, `details`, `preis`, `buchung`, `offer_href`
- ✅ No error messages
- ✅ Custom CSS styles applied (sidebar width, content width)

#### Step 4: Test Navigation
- Click each page link in sidebar
- Verify page content changes
- Check for errors on each page

### 2. Live Testing

#### Step 1: Navigate to Live Version
```python
# Use browser MCP tool
mcp_cursor-playwright_browser_navigate(url="https://unisportai.streamlit.app")
```

#### Step 2: Wait for Deployment
```python
# Live version may take 10-20 seconds to deploy
mcp_cursor-playwright_browser_wait_for(time=15)
```

#### Step 3: Verify Live Deployment
Check for:
- ✅ Same components as local version
- ✅ Data loads correctly from Supabase
- ✅ No connection errors
- ✅ Responsive layout

### 3. Using MCP for Testing

#### Supabase MCP Integration
If connection issues occur, use Supabase MCP tools:

```python
# Get project URL
mcp_supabase_get_project_url(project_id="mcbbjvjezbgekbmcajii")

# Get anon key
mcp_supabase_get_anon_key(project_id="mcbbjvjezbgekbmcajii")

# Verify secrets are configured
# Update .streamlit/secrets.toml if needed
```

## Common Issues & Solutions

### Issue 1: "Supabase URL not provided"
**Solution:**
- Check `.streamlit/secrets.toml` exists locally
- Verify secrets in Streamlit Cloud dashboard
- Ensure format: `[connections.supabase]` with `url` and `key`

### Issue 2: App not loading
**Solution:**
- Check if Streamlit server is running locally
- Verify port 8501 is not blocked
- Restart: `streamlit run streamlit_app.py`

### Issue 3: Data not displaying
**Solution:**
- Verify Supabase connection credentials
- Check if database tables exist
- Review error messages in page snapshot

## Automated Test Checklist

Use `browser_snapshot` to capture page state and verify:

- [ ] Navigation sidebar appears (width: 200-400px)
- [ ] Main content area loads (width: 69%)
- [ ] "Unisport Planner" title visible
- [ ] Data table with Sportkurs entries loads
- [ ] No red error alerts
- [ ] DataFrame controls visible (download, search, etc.)
- [ ] Custom CSS styles applied

## Screenshot Documentation

Take screenshots at each step:
```python
# Screenshot successful load
mcp_cursor-playwright_browser_take_screenshot(
    filename="unisport_test_local.png"
)

# Screenshot live version
mcp_cursor-playwright_browser_take_screenshot(
    filename="unisport_test_live.png"
)
```

## Browser Tools Reference

### Available Tools
- `mcp_cursor-playwright_browser_navigate(url)` - Navigate to page
- `mcp_cursor-playwright_browser_wait_for(time)` - Wait for timeout
- `mcp_cursor-playwright_browser_snapshot()` - Get page state
- `mcp_cursor-playwright_browser_take_screenshot(filename)` - Capture screenshot
- `mcp_cursor-playwright_browser_click(element, ref)` - Interact with elements

### Example Test Workflow
```python
# 1. Navigate
browser_navigate(url="http://localhost:8501")

# 2. Wait for load
browser_wait_for(time=5)

# 3. Get snapshot
snapshot = browser_snapshot()

# 4. Verify content
assert "Unisport Planner" in snapshot

# 5. Take screenshot
browser_take_screenshot(filename="test_result.png")
```

## Success Criteria

✅ **Local Version:**
- Loads without errors
- Displays Supabase data
- Navigation works
- Layout is optimized (sidebar narrow, content wide)

✅ **Live Version:**
- Same as local
- Deploys successfully
- Secrets configured correctly
- Loads within 20 seconds

## Notes
- Local testing requires Streamlit server running on port 8501
- Live version requires Supabase secrets configured in Streamlit Cloud
- Both versions should behave identically
- Use browser tools for visual verification
- Use MCP tools for backend verification if needed

