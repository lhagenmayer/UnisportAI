## 🎯 UnisportAI

An intelligent Streamlit-based web application for discovering and managing university sports offers at the University of St. Gallen (HSG).

The app focuses on:

- **Discovery**: Find sports activities that match your intensity, focus and setting preferences.
- **Filtering**: Powerful sidebar filters for time, location, weekday and more.
- **Ratings**: Rate activities and trainers and see community feedback.
- **Personalization**: Save filter defaults and favourites per user.

All of the content below is **fully up to date** with the current project structure:

- `streamlit_app.py` - Main application entry point
- `utils/` - Utility modules (auth, db, rating, filters, ml_utils, formatting)
- `ml/` - ML training utilities and model artifacts

---

## 📦 Features

### 🔐 Authentication & Security

- **Google OAuth 2.0 via Streamlit Auth**
  - Login directly in the sidebar with `st.login("google")`
  - No password handling inside the app
- **User synchronisation to Supabase**
  - On successful login, the user is written/updated in the `users` table
  - Last login time and basic profile data are stored
- **Session management**
  - Session state is cleared on logout
  - Optional token expiry check for long‑running sessions

### 🏋️ Sports & Course Management

- **Sports overview**
  - List of all sports offers from the `vw_offers_complete` Supabase view
  - Aggregated stats: average rating, rating count, upcoming events
- **Rich filter sidebar**
  - **Activity Type**
    - Intensity (Low / Moderate / High)
    - Focus (Strength, Endurance, Flexibility, Longevity, …)
    - Setting (Solo, Duo, Team, Competitive, Fun)
  - **Course filters**
    - Location
    - Weekday
    - Sport name
    - Hide cancelled courses
    - Date range
    - Time range
  - **AI Settings**
    - Minimum match score (0–100 %)
    - Maximum number of recommendations
- **Course dates**
  - Table view of upcoming course dates (from `vw_termine_full`)
  - Cancellation status, location and trainers per event

### ⭐ Ratings & Social Layer

- **Activity ratings**
  - Users can rate each sport (1–5 stars) and leave comments
  - Ratings are stored in `sportangebote_user_ratings`
  - Average ratings and counts are shown in the UI and analytics views
- **Trainer ratings**
  - Trainers have their own rating stream (`trainer_user_ratings`)
  - Dedicated widgets to rate and review trainers
  - Overview of trainer ratings in the course dates tab
- **Public profiles & social graph**
  - Users can mark their profile as public
  - Public athletes can be discovered in the “Athletes” tab
  - Friendships & friend requests are managed in `user_friends` / `friend_requests`

### 🤖 Machine Learning Recommendations

- **K‑Nearest Neighbours (KNN) recommender**
  - Trained on feature vectors from `ml_training_data` view
  - 13‑dimensional feature space covering focus, intensity and setting
- **Model usage in the app**
  - Pre‑trained model bundle loaded from `ml/models/knn_recommender.joblib`
  - `streamlit_app.py` builds a preference vector from the sidebar filters
  - ML recommendations are filtered by a minimum match score and max result count
- **Training utilities (optional)**
  - `ml/train.py`: CLI script to train and save the KNN model
  - `ml/test.py`: CLI script to test the model with sample personas

### 📊 Analytics & Visualisations

- **Rating distribution**
  - Histogram over average ratings of sports
- **Top rated sports**
  - Horizontal bar chart of the best rated sports with min rating count
- **ML feature analysis**
  - Radar chart for sport feature profiles
  - Feature variance chart showing which features are most discriminative
- **Intensity & setting distribution**
  - Pie chart of intensity levels
  - Bar chart of settings (Solo, Duo, Team, …)

---

## 🧱 Technology Stack

**Languages & runtime**

- Python 3.9+
- Streamlit (latest)

**Backend & database**

- Supabase (PostgreSQL)
- `st-supabase-connection` for native Streamlit ↔ Supabase integration

**Machine Learning & data**

- scikit‑learn – KNN, StandardScaler
- pandas, numpy – data wrangling & numeric operations
- joblib – model persistence

**Visualisation**

- Plotly (graph_objects + express)

See `requirements.txt` for the exact dependency list.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/RadicatorCH/UnisportAI.git
cd UnisportAI
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Supabase credentials

Create `.streamlit/secrets.toml` in the project root:

```toml
[connections.supabase]
url = "https://your-project-id.supabase.co"
key = "your-anon-or-service-key"

[auth]
cookie_secret = "a-random-string-with-at-least-32-characters"

[auth.google]
client_id = "your-google-oauth-client-id"
client_secret = "your-google-oauth-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

**Important:**

- Never commit `.streamlit/secrets.toml` or `.env` to version control.
- Ensure that the Supabase project has the required tables/views (see below).

### 5. Configure Google OAuth

High‑level steps:

1. Go to the Google Cloud Console.
2. Create a project (e.g. `UnisportAI`).
3. Configure the OAuth consent screen (App name, support email, scopes).
4. Create OAuth 2.0 credentials of type **Web application**.
5. Add redirect URIs:

   **For local development:**
   ```text
   http://localhost:8501/oauth2callback
   ```

   **For production (Streamlit Cloud):**
   ```text
   https://your-app-name.streamlit.app/oauth2callback
   ```
   
   ⚠️ **IMPORTANT:** 
   - In production, **DO NOT** use `localhost` redirect URIs
   - Use **ONLY** your production Streamlit Cloud URL
   - The redirect URI must **exactly match** your app's URL (including `https://` and `/oauth2callback`)

6. Copy client ID and client secret into `.streamlit/secrets.toml` under `[auth.google]`.

### 6. Run the app

```bash
streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser if it does not open automatically.

Log in with your Google account using the button in the sidebar.

---

### 7. Optional: Configure GitHub Actions Scraper

This repo contains a `.scraper/` folder with Python scripts that periodically scrape the Unisport website and write data into Supabase (offers, courses, dates, cancellations).

To run these scripts automatically via GitHub Actions you need to:

1. Ensure your Supabase schema is created (see **Database Schema** section below).
2. In your GitHub repository, go to **Settings → Secrets and variables → Actions → New repository secret** and add:
   - `SUPABASE_URL` – your Supabase project URL (e.g. `https://mcbbjje...supabase.co`)
   - `SUPABASE_KEY` – a key that is allowed to write to the tables (`service_role` is simplest, but handle it carefully).
3. Check the workflow file in `.github/workflows/` (e.g. `scraper.yml`) to see which secrets it expects and how often it runs.

The Action will then:

- Run the scripts in `.scraper/` on the configured schedule.
- Use the GitHub secrets to connect to Supabase (no secrets are committed to the repo).

---

## 🗄 Database Schema (Supabase)

The app expects a PostgreSQL database (via Supabase) with at least the following tables/views:

- `users` – user accounts, profile data and stored preferences
- `sportangebote` – sports offers (base table with focus/setting/intensity features)
- `sportkurse` – course definitions grouped by course number
- `kurs_termine` – individual course dates (time, location, cancellation flag)
- `unisport_locations` – physical locations with coordinates and indoor/outdoor flag
- `sportangebote_user_ratings` – user ratings for sports
- `trainer` – trainers with base metadata and default rating
- `trainer_user_ratings` – user ratings for trainers
- `user_friends` – friendship graph between users
- `friend_requests` – pending and historical friend requests
- `etl_runs` – simple ETL bookkeeping table for scraper components
- `ml_training_data` (view) – feature matrix for the ML recommender
- `vw_offers_complete` (view) – enriched sports offers with ratings, event counts & trainers
- `vw_termine_full` (view) – enriched upcoming course dates with trainer and location data

### Creating the schema from this repository

To create the full schema on a fresh Supabase project:

1. Open the SQL editor in the Supabase dashboard of your project.
2. Copy the contents of `schema.sql` from this repository.
3. Paste it into the SQL editor and run it once.

This will create all required tables and views used by the application and the ML components.

---

## 🧭 Project Structure

Current (simplified) layout:

```text
UnisportAI/
├── streamlit_app.py    # Main Streamlit application
├── utils/              # Utility modules (refactored from root)
│   ├── __init__.py     # Package exports
│   ├── auth.py         # Authentication helpers (Streamlit + Google OAuth)
│   ├── db.py           # Supabase data access layer
│   ├── rating.py       # Rating widgets for sports & trainers
│   ├── filters.py      # Event and offer filtering logic
│   ├── ml_utils.py     # ML model loading and recommendations
│   └── formatting.py   # HTML formatting utilities
├── ml/                 # ML recommender utilities and model
│   ├── recommender.py  # KNN recommender class (training / testing)
│   ├── train.py        # CLI script to train and save the model
│   ├── test.py         # CLI script to test recommendations
│   └── models/
│       └── knn_recommender.joblib  # Saved model bundle used by the app
├── requirements.txt    # Python dependencies
├── .streamlit/         # (optional) local Streamlit config & secrets
└── .github/, .scraper/ # CI and scraping utilities (not required for basic usage)
```

### Module overview

- **`streamlit_app.py`**
  - Entry point of the web application
  - Configures page layout and sidebar
  - Calls `utils.auth` helpers to check login and synchronise users
  - Reads filters from session state
  - Loads offers and events via `utils.db` helpers
  - Integrates ML recommender and analytics views
  - Contains UI components: `render_unified_sidebar()`, `render_analytics_section()`

- **`utils/auth.py`**
  - `is_logged_in()` – checks Streamlit user session
  - `handle_logout()` – clears session state and logs out
  - `check_token_expiry()` – optional expiry check
  - `sync_user_to_supabase()` – creates/updates user row in Supabase
  - Accessors like `get_user_sub()` and `get_user_email()`

- **`utils/db.py`**
  - Creates a cached Supabase connection via `st-supabase-connection`
  - Provides high‑level query functions:
    - `get_offers_complete()`
    - `get_events(offer_href)`
    - `get_user_complete(user_sub)`
    - `update_user_settings(...)`
    - `get_public_users()`, `get_user_friends()`, friend request helpers
    - Ratings helpers and ML training data loaders
    - `test_database_connection()` – connection validation
    - `get_data_timestamp()` – ETL run timestamp retrieval

- **`utils/rating.py`**
  - Streamlit UI components for ratings
  - Uses `utils.rating.submit_*_rating` and `utils.db` rating queries
  - Expander‑based widgets for activities and trainers

- **`utils/filters.py`**
  - Event and offer filtering logic
  - `check_event_matches_filters()` – single event filter validation
  - `filter_events()` – filter list of events
  - `filter_offers()` – filter sports offers with ML scoring

- **`utils/ml_utils.py`**
  - ML model loading and recommendation functions
  - `load_knn_model()` – load pre-trained KNN model with caching
  - `build_user_preferences_from_filters()` – convert filters to feature vector
  - `get_ml_recommendations()` – get ML-based sport recommendations

- **`utils/formatting.py`**
  - HTML formatting utilities
  - `create_user_info_card_html()` – user info card HTML generation

- **`ml/`**
  - Not required for running the app if a pre‑trained model exists
  - Useful when you want to retrain or experiment with the recommender

---

## 👨‍💻 Development Guide

### Code style

- Follow **PEP 8** for Python code.
- Keep UI logic in `streamlit_app.py` and `utils/rating.py`; keep `utils/db.py` free of UI.
- Function names: `snake_case`
- Class names: `PascalCase`
- Constants: `UPPER_CASE`
- Private functions: `_leading_underscore`
- Code is written in a beginner-friendly style with explicit loops and clear variable names

### Working with session state

The app relies heavily on `st.session_state` to store:

- Filter values (intensity, focus, setting, location, weekday, …)
- AI settings (min match score, max results)
- Currently selected offer
- User activities (lightweight log)

Pattern:

```python
if "intensity" not in st.session_state:
    st.session_state["intensity"] = []

selected_intensity = st.multiselect(
    "Intensity",
    options=intensities,
    default=st.session_state["intensity"],
)
st.session_state["intensity"] = selected_intensity
```

### Adding new features

1. **New filter in the sidebar**
   - Add the widget and state handling inside `render_unified_sidebar` in `streamlit_app.py`.
   - Pass the new state into the filter functions in `utils/filters.py` or ML recommender in `utils/ml_utils.py`.

2. **New database query**
   - Implement it in `utils/db.py` with clear docstring.
   - If it is read‑only and used in the UI, consider `@st.cache_data`.

3. **New visualisation**
   - Implement a Plotly figure function directly in `streamlit_app.py` or create a helper function.
   - Call `st.plotly_chart(fig)` from the relevant place in `streamlit_app.py`.

### Testing locally

Manual test checklist:

- Authentication works (login/logout).
- Sidebar filters update results and persist via session state.
- Ratings can be created and updated for both sports and trainers.
- ML recommendations behave sensibly for different filter combinations.
- Public profiles and friend lists load without errors (if used).

---

## 🚢 Deployment

### Streamlit Cloud

1. Push your repository to GitHub.
2. Go to Streamlit Community Cloud and create a new app:
   - Repo: `your-user/UnisportAI`
   - Branch: `main`
   - Main file: `streamlit_app.py`
3. Configure secrets in the Streamlit Cloud UI (copy contents from your local `.streamlit/secrets.toml`).
4. **CRITICAL:** Update Google OAuth redirect URIs in Google Cloud Console:
   - Go to Google Cloud Console → APIs & Services → Credentials
   - Edit your OAuth 2.0 Client ID
   - **Remove** any `localhost` redirect URIs
   - **Add** your production URL: `https://your-app-name.streamlit.app/oauth2callback`
   - The redirect URI must match your Streamlit Cloud app URL exactly

### Other deployment options

- **Docker + any cloud provider**

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

- **Custom hosting** via e.g. Heroku, Fly.io or similar – treated like a normal Python web service.

---

## 🧪 Troubleshooting

### Supabase connection issues

- **“URL not provided” / “key not provided”**
  - Check `[connections.supabase]` section in `.streamlit/secrets.toml`.
  - Ensure variable names are correct and there is no trailing slash in the URL.

- **Row Level Security (RLS) errors**
  - Verify that your RLS policies allow `authenticated` users to read/write the required tables.

### Google OAuth issues

- **`redirect_uri_mismatch`**
  - Ensure all redirect URIs configured in Google exactly match the URLs used by Streamlit.
  - **In production:** Remove `localhost` redirect URIs from Google Cloud Console
  - **In production:** Use only your production URL: `https://your-app-name.streamlit.app/oauth2callback`
  - The redirect URI must match exactly (including protocol `https://` and path `/oauth2callback`)

- **"This app isn't verified"**
  - For development, add your test accounts as test users in the OAuth consent screen.

- **Redirect to localhost in production**
  - This happens if `localhost` redirect URIs are still configured in Google Cloud Console
  - Solution: Remove all `localhost` redirect URIs and keep only your production URL

### Streamlit issues

- **Port already in use**
  - Run on another port: `streamlit run streamlit_app.py --server.port 8502`.

- **Stale cache / old data**
  - Clear cache with `streamlit cache clear` or via the hamburger menu in the app.

---

## 🤖 AI‑Assisted Development Transparency

Parts of this project were built and refactored using AI‑assisted tools (Cursor, AI coding agents).

- All generated code has been **reviewed and adapted** by a human.
- Responsibility for correctness and behaviour of the code lies with the project maintainers.
- This README was rewritten in English to reflect the current project state and structure.

---

**Made with ❤️ for the University of St. Gallen (HSG)**


