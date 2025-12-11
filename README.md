# UnisportAI

**Course finder and recommendations for Fundamentals and Methods of Computer Science**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://unisport.streamlit.app)

An intelligent Streamlit-based web application for discovering and managing university sports offers at the University of St. Gallen (HSG).

The app focuses on:

- **Discovery**: Find sports activities that match your intensity, focus and setting preferences.
- **Filtering**: Powerful sidebar filters for time, location, weekday and more.
- **Personalization**: Save filter defaults and favourites per user.
- **AI Recommendations**: Machine learning-powered sport suggestions using KNN algorithm.

## Quick Start

### Prerequisites
- Python 3.9+ (3.11 recommended)
- Streamlit account (for deployment)
- Supabase account (for database)
- Google OAuth credentials (optional, for user authentication)

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/RadicatorCH/UnisportAI.git
   cd UnisportAI
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # macOS/Linux:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Supabase database:**
   - Create a new Supabase project at https://supabase.com
   - Run the schema from `schema.sql` in your Supabase SQL editor
   - Note your project URL and anon key from Settings > API

5. **Configure secrets in `.streamlit/secrets.toml`:**
   ```toml
   [connections.supabase]
   SUPABASE_URL = "your_supabase_project_url"
   SUPABASE_KEY = "your_supabase_anon_key"

   # Google OAuth (for user authentication)
   GOOGLE_CLIENT_ID = "your_google_oauth_client_id"
   GOOGLE_CLIENT_SECRET = "your_google_oauth_client_secret"

   # Optional: Email notifications
   ADMIN_EMAIL = "your_admin_email@example.com"
   LOOPS_API_KEY = "your_loops_api_key"
   ```

6. **Run the application:**
   ```bash
   streamlit run streamlit_app.py
   ```

### Database Setup

The application uses Supabase as its database. To set up:

1. Create a Supabase project at https://supabase.com
2. Go to the SQL Editor in your Supabase dashboard
3. Run the contents of `schema.sql` to create all necessary tables
4. Copy your project URL and anon key from Settings > API

### ML Model Training (Optional)

If you want to retrain the recommendation model:

1. Ensure you have training data in your Supabase database
2. Run the training script:
   ```bash
   python ml/train.py
   ```
3. The trained model will be saved to `ml/models/knn_recommender.joblib`

### Deployment to Streamlit Cloud

1. Fork this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and select the forked repository
4. Set the main file path to `streamlit_app.py`
5. Add the following secrets in the Streamlit Cloud dashboard:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `ADMIN_EMAIL` (optional)
   - `LOOPS_API_KEY` (optional)

6. Deploy the app

### Environment Variables

The application requires several environment variables for full functionality:

**Required:**
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key

**Optional:**
- `GOOGLE_CLIENT_ID`: Google OAuth client ID for authentication
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `ADMIN_EMAIL`: Email address for notifications
- `LOOPS_API_KEY`: API key for email notifications

### Troubleshooting

**Common Issues:**

1. **"Model not found" error:**
   - Run `python ml/train.py` to train the ML model
   - Ensure `ml/models/knn_recommender.joblib` exists

2. **Database connection errors:**
   - Check your Supabase credentials in `.streamlit/secrets.toml`
   - Verify your Supabase project is active
   - Ensure the database schema is created using `schema.sql`

3. **Google OAuth not working:**
   - Verify redirect URIs in Google Cloud Console include your app's URL
   - For local development: `http://localhost:8501/oauth2callback`
   - For production: `https://your-app-name.streamlit.app/oauth2callback`

4. **Scraper scripts failing:**
   - Check GitHub Actions secrets are set correctly
   - Verify Supabase write permissions for the service key

**Getting Help:**
- Check the GitHub Actions logs for detailed error messages
- Ensure all dependencies are installed: `pip install -r requirements.txt`

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
  - Aggregated stats: upcoming events
- **Rich filter sidebar**
  - **Activity Type**
    - Intensity (Low / Moderate / High)
    - Focus (Balance, Flexibility, Coordination, Relaxation, Strength, Endurance, Longevity)
    - Setting (Solo, Duo, Team, Competitive, Fun)
  - **Course filters**
    - Location
    - Weekday
    - Sport name
    - Hide cancelled courses
    - Date range
    - Time range
  - **AI Settings**
    - Minimum match score (20–100 %, default: 50%)
- **Course dates**
  - Table view of upcoming course dates (from `vw_termine_full`)
  - Cancellation status, location and trainers per event

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

- **Course statistics**
  - Course availability by weekday (bar chart)
  - Course availability by time of day (bar chart)
- **AI-powered recommendations**
  - Top 3 recommendations with match scores (podest view)
  - Extended recommendations chart (top 10 sports with horizontal bar chart)
  - Recommendations appear automatically when activity filters are selected

---

## 🧱 Technology Stack

**Languages & runtime**

- Python 3.9+ (3.11 recommended)
- Streamlit (latest)

**Backend & database**

- Supabase (PostgreSQL)
- `st-supabase-connection` for native Streamlit ↔ Supabase integration

**Machine Learning & data**

- scikit-learn: KNN, StandardScaler for ML recommendations
- pandas, numpy: data wrangling & numeric operations
- joblib: model persistence

**Visualization**

- Plotly (graph_objects + express): interactive charts and analytics

**Web scraping** (for `.scraper/` scripts)

- requests: HTTP library for fetching web pages
- beautifulsoup4, lxml: HTML parsing
- urllib3: HTTP client utilities
- python-dateutil: date/time parsing

**Authentication**

- Streamlit Auth: built-in OAuth support
- Google OAuth 2.0: secure user authentication

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
   - `SUPABASE_URL`, your Supabase project URL (e.g. `https://mcbbjje...supabase.co`)
   - `SUPABASE_KEY`, a key that is allowed to write to the tables (`service_role` is simplest, but handle it carefully).
3. Check the workflow file in `.github/workflows/` (e.g. `scraper.yml`) to see which secrets it expects and how often it runs.

The Action will then:

- Run the scripts in `.scraper/` on the configured schedule.
- Use the GitHub secrets to connect to Supabase (no secrets are committed to the repo).

---

## 🗄 Database Schema (Supabase)

The app expects a PostgreSQL database (via Supabase) with at least the following tables/views:

- `users` - user accounts, profile data and stored preferences
- `sportangebote` - sports offers (base table with focus/setting/intensity features)
- `sportkurse` - course definitions grouped by course number
- `kurs_termine` - individual course dates (time, location, cancellation flag)
- `kurs_trainer` - join table linking courses to trainers (many-to-many)
- `unisport_locations` - physical locations with coordinates and indoor/outdoor flag
- `trainer` - trainers with base metadata
- `etl_runs` - simple ETL bookkeeping table for scraper components
- `ml_training_data` (view) - feature matrix for the ML recommender
- `vw_offers_complete` (view) - enriched sports offers with event counts and trainers
- `vw_termine_full` (view) - enriched upcoming course dates with trainer and location data

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
├── streamlit_app.py           # Main Streamlit application
├── utils/                     # Utility modules
│   ├── __init__.py           # Package initialization
│   ├── auth.py               # Authentication helpers (Streamlit + Google OAuth)
│   ├── db.py                 # Supabase data access layer
│   ├── filters.py            # Event and offer filtering logic
│   ├── ml_utils.py           # ML model loading and recommendations
│   ├── formatting.py         # HTML formatting utilities
│   └── analytics.py          # Analytics visualizations and charts
├── ml/                       # ML recommender utilities and model
│   ├── recommender.py        # KNN recommender class (training / testing)
│   ├── train.py              # CLI script to train and save the model
│   ├── test.py               # CLI script to test recommendations
│   └── models/
│       └── knn_recommender.joblib  # Saved model bundle used by the app
├── .scraper/                 # Web scraping scripts
│   ├── scrape_sportangebote.py        # Scrape sports offers and courses
│   ├── extract_locations_from_html.py # Extract location data
│   └── update_cancellations.py        # Update cancellation status
├── .github/                  # GitHub Actions workflows
│   └── workflows/
│       └── scraper.yml       # Automated data scraping workflow
├── .streamlit/               # Streamlit configuration and secrets
│   └── secrets.toml          # Local secrets (not committed)
├── assets/                   # Static assets
│   └── images/               # Team member photos
├── requirements.txt          # Python dependencies
├── schema.sql                # Database schema definition
├── CODE_OF_CONDUCT.md        # Community guidelines
├── CONTRIBUTING.md           # Contribution guidelines
├── LICENSE                   # MIT License
├── README.md                 # This file
└── SECURITY.md               # Security policy
```

### Module overview

- **`streamlit_app.py`**
  - Entry point of the web application
  - Configures page layout and sidebar
  - Calls `utils.auth` helpers to check login and synchronise users
  - Reads filters from session state
  - Loads offers and events via `utils.db` helpers
  - Integrates ML recommender and analytics views
  - Unified sidebar rendered at module level (before tabs)
  - Four main tabs: Sports Overview, Course Dates, My Profile, About

- **`utils/auth.py`**
  - `is_logged_in()` – checks Streamlit user session
  - `handle_logout()` – clears session state and logs out
  - `clear_user_session()` – clears all user-related session state data
  - `check_token_expiry()` – optional expiry check
  - `sync_user_to_supabase()` – creates/updates user row in Supabase
  - `get_user_info_dict()` – collects user info into a dictionary
  - `get_user_sub()` – get user subject ID
  - `get_user_email()` – get user email address

- **`utils/db.py`**
  - Creates a cached Supabase connection via `st-supabase-connection`
  - `supaconn()` – cached connection singleton
  - Provides high‑level query functions:
    - `get_offers_complete()` – load all sports offers
    - `get_events(offer_href)` – load events (optionally filtered by offer)
    - `load_and_filter_offers(filters)` – unified function to load and filter offers with ML
    - `load_and_filter_events(filters, offer_href)` – unified function to load and filter events
    - `get_user_complete(user_sub)` – load user profile
    - `get_events_grouped_by_offer()` – group events by offer for efficient lookup
    - `get_events_grouped_by_sport()` – group events by sport for efficient lookup
    - `group_events_by(field)` – generic grouping function
    - `get_events_by_weekday()` – analytics: count events by weekday
    - `get_events_by_hour()` – analytics: count events by hour of day
    - `get_ml_training_data_cli()` – load ML training data for CLI scripts
    - `create_or_update_user(user_data)` – create or update user in database

- **`utils/filters.py`**
  - Event and offer filtering logic
  - `filter_events()` – filter list of events by multiple criteria
  - `filter_offers()` – filter sports offers with ML scoring
  - `get_filter_values_from_session()` – extract all filter values from session state
  - `has_event_filters()` – check if any event filters are set
  - `has_offer_filters()` – check if any ML-relevant filters are set
  - `initialize_session_state()` – initialize filter session state with defaults
  - `get_filter_session_keys()` – return list of all filter session keys
  - `apply_soft_filters_to_score()` – reduce match score based on soft filters
  - `get_merged_recommendations()` – merge KNN ML and filtered results
  - `apply_ml_recommendations_to_offers()` – apply ML recommendations with fallback thresholds

- **`utils/ml_utils.py`**
  - ML model loading and recommendation functions
  - `ML_FEATURE_COLUMNS` – list of 13 feature column names for ML
  - `load_knn_model()` – load pre-trained KNN model with caching
  - `build_user_preferences_from_filters()` – convert filters to feature vector
  - `get_ml_recommendations()` – get ML-based sport recommendations
  - `ML_MODEL_PATH` – path to saved model file

- **`utils/formatting.py`**
  - HTML formatting utilities and date/time formatters
  - `format_intensity_display()` – format intensity with emoji indicator
  - `format_focus_display()` – format focus list for display
  - `format_setting_display()` – format setting list for display
  - `format_trainers_display()` – format trainers list for display
  - `create_offer_metadata_df()` – create DataFrame with offer metadata
  - `parse_event_datetime()` – parse ISO datetime strings
  - `format_weekday()` – format weekday from datetime
  - `format_time_range()` – format time range string
  - `get_match_score_style()` – get CSS style for match score badge
  - `render_user_avatar()` – render user avatar (image or initials)
  - `convert_events_to_table_data()` – convert events to DataFrame format

- **`utils/analytics.py`**
  - Analytics visualizations and charts
  - `render_analytics_section()` – main analytics dashboard with charts
  - `render_team_contribution_matrix()` – team contribution visualization
  - ML feature analysis, intensity/setting distributions

- **`ml/`**
  - Not required for running the app if a pre‑trained model exists
  - Useful when you want to retrain or experiment with the recommender

- **`.scraper/`**
  - Web scraping scripts for automated data collection
  - `scrape_sportangebote.py` – main scraper for offers, courses, and dates
  - `extract_locations_from_html.py` – location data extraction
  - `update_cancellations.py` – cancellation status updates
  - Designed to run via GitHub Actions on a schedule

- **`.github/workflows/scraper.yml`**
  - GitHub Actions workflow for automated data scraping
  - Runs daily at 6:00 AM UTC (7:00 AM CET)
  - Requires environment variables: SUPABASE_URL, SUPABASE_KEY, ADMIN_EMAIL, LOOPS_API_KEY
  - Can be triggered manually via GitHub UI


## 🤖 AI‑Assisted Development Transparency

Parts of this project were built and refactored using AI‑assisted tools (Cursor, AI coding agents).

- All generated code has been **reviewed and adapted** by a human.
- Responsibility for correctness and behaviour of the code lies with the project maintainers.
- This README was rewritten in English to reflect the current project state and structure.

---

**Made with ❤️ for the course "Fundamentals and Methods of Computer Science" at the University of St. Gallen (HSG)**


