# UnisportAI - Comprehensive Presentation Guide

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Component Deep Dive](#3-component-deep-dive)
4. [Data Flow](#4-data-flow)
5. [Machine Learning Implementation](#5-machine-learning-implementation)
6. [Database Design](#6-database-design)
7. [Web Scraping Pipeline](#7-web-scraping-pipeline)
8. [Expected Professor Questions & Answers](#8-expected-professor-questions--answers)

---

## 1. Project Overview

### What is UnisportAI?
UnisportAI is a **Streamlit web application** that helps students at the University of St. Gallen (HSG) discover sports courses offered by Unisport. The app uses **machine learning (KNN algorithm)** to provide personalized recommendations based on user preferences.

### Core Problem Solved
Students struggle to find sports activities that match their preferences (time, location, intensity, type). This app automates the discovery process with intelligent filtering and AI-powered recommendations.

### Key Features
1. **Smart Filtering**: Filter by sport type, intensity, focus areas, social settings, location, day, and time
2. **AI Recommendations**: KNN-based personalized sport suggestions
3. **Real-time Data**: Automated web scraping keeps course data current
4. **Analytics Dashboard**: Visualizations of course availability patterns
5. **User Authentication**: Google OAuth integration for personalized experience

---

## 2. System Architecture

### High-Level Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Unisport      │     │  GitHub Actions  │     │    Supabase     │
│   Website       │────▶│  (Scraper)       │────▶│   (PostgreSQL)  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              │
                        │   Streamlit App  │◀─────────────┘
                        │  (Frontend + ML) │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │     Browser      │
                        │    (User UI)     │
                        └──────────────────┘
```

### Technology Stack
| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Streamlit | Python-based web UI framework |
| Database | Supabase (PostgreSQL) | Cloud-hosted relational database |
| ML | scikit-learn | K-Nearest Neighbors algorithm |
| Visualization | Plotly | Interactive charts |
| Authentication | Google OAuth | User login via Streamlit's built-in auth |
| Web Scraping | BeautifulSoup + requests | Extract data from Unisport website |
| Automation | GitHub Actions | Scheduled scraper execution |

---

## 3. Component Deep Dive

### 3.1 Main Application (`streamlit_app.py`)
**Purpose**: Entry point and main UI logic

**Key Sections**:
1. **Sidebar** (lines 137-384): Unified filter panel with sport, intensity, focus, setting, location, date/time filters
2. **Tab 1 - Sports Overview** (lines 447-613): Displays filtered offers with ML match scores
3. **Tab 2 - Course Dates** (lines 619-708): Detailed view of selected sport's schedule
4. **Tab 3 - My Profile** (lines 714-770): User profile for logged-in users
5. **Tab 4 - About** (lines 776-843): Project info and team credits

**Important Pattern**: 
- Sidebar renders ONCE at module level (not inside tabs)
- Filter values stored in `st.session_state`
- Tabs read filter values from session_state

### 3.2 Utils Modules (`utils/`)

#### `db.py` - Database Access Layer
**Purpose**: Centralized database operations

**Key Functions**:
- `supaconn()`: Cached Supabase connection (singleton per session)
- `get_offers_complete()`: Load all sport offers with features
- `get_events()`: Load course dates with pagination (1000 rows per page)
- `load_and_filter_offers()`: Combined load + filter with optional ML
- `load_and_filter_events()`: Combined load + filter for events

**Caching Strategy**:
- `@st.cache_resource`: For connection (singleton)
- `@st.cache_data(ttl=300)`: For data (5-minute TTL)

#### `auth.py` - Authentication
**Purpose**: Google OAuth and user session management

**Key Functions**:
- `is_logged_in()`: Check auth status via `st.user.email`
- `sync_user_to_supabase()`: Upsert user data on login
- `handle_logout()`: Clear session + Streamlit logout
- `get_user_sub()`: Get OIDC "sub" claim (unique user ID)

#### `filters.py` - Filtering Logic
**Purpose**: Filter offers and events based on user criteria

**Key Concepts**:
- **Hard Filters**: Must match exactly (sport name, location) - items excluded if no match
- **Soft Filters**: Reduce match score instead of excluding (used in ML recommendations)
- **AND Logic**: All hard filters must match (items excluded if any filter fails)

**Key Functions**:
- `filter_events()`: Apply all event filters
- `filter_offers()`: Apply offer filters (intensity/focus/setting)
- `apply_ml_recommendations_to_offers()`: Combine rule-based + ML filtering
- `get_merged_recommendations()`: Merge filtered results with KNN recommendations

#### `formatting.py` - Display Helpers
**Purpose**: Format data for UI display

**Key Functions**:
- `parse_event_datetime()`: Convert ISO strings to datetime
- `format_intensity_display()`: Add emoji indicators (🟢/🟡/🔴)
- `convert_events_to_table_data()`: Prepare events for dataframe display
- `create_offer_metadata_df()`: Create pandas DataFrame for offer details

#### `analytics.py` - Visualizations
**Purpose**: Render analytics charts

**Key Components**:
- Course availability by weekday (bar chart)
- Course availability by time of day (histogram)
- AI recommendations podium (top 3)
- Sports similarity chart (horizontal bar)
- Team contribution matrix (heatmap)

#### `ml_utils.py` - ML Utilities
**Purpose**: KNN model loading and preference conversion

**Key Functions**:
- `load_knn_model()`: Load trained model from disk (cached)
- `build_user_preferences_from_filters()`: Convert UI selections → 13-D feature vector
- `get_ml_recommendations()`: Get recommendations from KNN model

### 3.3 Machine Learning (`ml/`)

#### `recommender.py` - KNN Recommender Class
**Purpose**: Core ML implementation

**Class**: `KNNSportRecommender`
- `__init__()`: Initialize with n_neighbors=10, cosine metric
- `load_and_train()`: Train on feature data from database
- `get_recommendations()`: Find similar sports for user preferences
- `save_model()` / `load_model()`: Persist model to/from disk

**13 Features**:
1. balance, flexibility, coordination, relaxation (physical skills)
2. strength, endurance, longevity (fitness dimensions)
3. intensity (0.33=low, 0.67=moderate, 1.0=high)
4. setting_team, setting_fun, setting_duo, setting_solo, setting_competitive

#### `train.py` - Training Script
**Purpose**: Orchestrate model training

**Workflow**:
1. Load training data from `ml_training_data` view
2. Create `KNNSportRecommender` instance
3. Call `load_and_train()`
4. Save to `ml/models/knn_recommender.joblib`

### 3.4 Web Scraper (`.scraper/`)

#### `scrape_sportangebote.py` - Main Scraper
**Purpose**: Extract all sport data from Unisport website

**Workflow**:
1. Extract offers from main menu
2. Update locations table
3. Save offers to database
4. Get images and descriptions for each offer
5. Extract courses for each offer
6. Extract trainer names
7. Save course-trainer relationships
8. Extract individual course dates
9. Save dates to database

#### `extract_locations_from_html.py` - Location Extractor
**Purpose**: Extract location coordinates and metadata

**Data Sources**:
1. JavaScript markers (coordinates)
2. HTML menu (sports per location)
3. Links (URLs and SPIDs)

**Combines data using fuzzy matching** for names that differ slightly.

#### `update_cancellations.py` - Cancellation Checker
**Purpose**: Mark cancelled courses in database

**Workflow**:
1. Scrape cancellation notices from Unisport website
2. Match with existing course dates by name + time
3. Set `canceled=true` in database

---

## 4. Data Flow

### User Request Flow
```
1. User selects filters in sidebar
   ↓
2. Session state updated with filter values
   ↓
3. Tab reads filters from session_state
   ↓
4. load_and_filter_offers() called
   ↓
5. Database query via get_offers_complete()
   ↓
6. If ML filters set: get_merged_recommendations()
   ↓
7. KNN model finds similar sports
   ↓
8. Results sorted by match_score
   ↓
9. UI renders filtered offers with scores
```

### Scraper Data Flow
```
1. GitHub Actions triggers (daily at 6 AM UTC)
   ↓
2. Scraper downloads Unisport website HTML
   ↓
3. BeautifulSoup parses HTML structure
   ↓
4. Data extracted and transformed
   ↓
5. Supabase upsert operations
   ↓
6. ETL run logged to etl_runs table
```

---

## 5. Machine Learning Implementation

### Algorithm: K-Nearest Neighbors (KNN)

**Why KNN?**
1. **Simple and interpretable**: Easy to explain in presentations
2. **No training required**: Works on feature similarity
3. **Good for small datasets**: ~100 sports is ideal for KNN
4. **Real-time predictions**: Fast inference

### How It Works

**Step 1: Feature Engineering**
Each sport is represented as a 13-dimensional vector:
```python
FEATURE_COLUMNS = [
    'balance', 'flexibility', 'coordination', 'relaxation',  # 4 features
    'strength', 'endurance', 'longevity',                     # 3 features
    'intensity',                                               # 1 feature
    'setting_team', 'setting_fun', 'setting_duo',             # 3 features
    'setting_solo', 'setting_competitive'                      # 2 features
]
```

**Step 2: Scaling**
StandardScaler normalizes features to mean=0, std=1:
- Prevents larger values from dominating distance calculations
- Example: intensity (0-1) vs binary flags (0 or 1)

**Step 3: Distance Calculation**
Uses **cosine similarity** (angle between vectors):
- `distance = 1 - cosine_similarity`
- `match_score = (1 - distance) * 100`

**Step 4: Finding Neighbors**
KNN finds K (default=10) sports with smallest distances.

### Example
```python
# User preferences:
{'strength': 1.0, 'endurance': 1.0, 'intensity': 1.0, 'setting_solo': 1.0}

# Sports with similar vectors (high strength, endurance, intensity):
# - Weight Training: 95% match
# - CrossFit: 88% match
# - Running: 82% match
```

---

## 6. Database Design

### Schema Overview (PostgreSQL via Supabase)

#### Core Tables
| Table | Primary Key | Purpose |
|-------|-------------|---------|
| `users` | `id` (UUID) | User accounts (linked via `sub` to OAuth) |
| `sportangebote` | `href` | Sport offers (e.g., "Yoga", "Swimming") |
| `sportkurse` | `kursnr` | Individual courses within offers |
| `kurs_termine` | `(kursnr, start_time)` | Course dates and times |
| `unisport_locations` | `name` | Physical locations with coordinates |
| `trainer` | `name` | Instructor names |
| `kurs_trainer` | `(kursnr, trainer_name)` | Many-to-many: courses ↔ trainers |
| `etl_runs` | `id` | Scraper run logging |

#### Views (Denormalized for Performance)
| View | Purpose |
|------|---------|
| `vw_offers_complete` | Offers with future event counts and trainer lists |
| `vw_termine_full` | Course dates with sport names and trainers |
| `ml_training_data` | One-hot encoded features for ML (13 numeric columns) |

### Key Relationships
```
sportangebote (1) ←───→ (*) sportkurse
sportkurse (1) ←───→ (*) kurs_termine
sportkurse (*) ←───→ (*) trainer (via kurs_trainer)
kurs_termine (*) ───→ (1) unisport_locations
```

---

## 7. Web Scraping Pipeline

### Schedule
- **When**: Daily at 6:00 AM UTC (7:00 AM Switzerland)
- **How**: GitHub Actions cron job
- **Fallback**: Manual trigger via `workflow_dispatch`

### Workflow YAML Structure
```yaml
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:      # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      1. Checkout repository
      2. Set up Python 3.11
      3. Install dependencies
      4. Run extract_locations_from_html.py
      5. Run scrape_sportangebote.py
      6. Run update_cancellations.py
```

### Error Handling
- Location extraction failure → Script exits with code 1 → GitHub Action fails
- Database errors → Logged but don't crash (graceful degradation)
- ETL runs logged to `etl_runs` table for monitoring

---

## 8. Expected Professor Questions & Answers

### Category A: Technical Architecture

#### Q1: Why did you choose Streamlit over other frameworks (Flask, Django, React)?
**Answer**: 
- Streamlit is **Python-native** and ideal for data science projects
- Rapid prototyping: built-in widgets reduce development time
- No HTML/CSS/JS knowledge required
- Perfect for course project scope
- Built-in caching, session state, and authentication
- Easy deployment to Streamlit Cloud

#### Q2: How do you handle state management in Streamlit?
**Answer**:
- We use `st.session_state` dictionary to persist values across reruns
- Filter values are stored when user interacts with widgets
- Session state survives tab switches and page reruns
- We explicitly initialize defaults in `initialize_session_state()`
- Example: `st.session_state['intensity'] = selected_intensity`

#### Q3: Why use Supabase instead of SQLite or local storage?
**Answer**:
- **Cloud-hosted**: Accessible from Streamlit Cloud deployment
- **PostgreSQL**: Supports views, JSONB, arrays, and complex queries
- **Real-time**: Built-in auth and REST API
- **Free tier**: Sufficient for our data volume
- **Scalability**: Can handle concurrent users

### Category B: Machine Learning

#### Q4: Why did you choose KNN over other algorithms (Random Forest, Neural Networks)?
**Answer**:
- **Interpretability**: Easy to explain "sports similar to your preferences"
- **No training loop**: KNN simply stores data and computes distances
- **Small dataset**: ~100 sports is ideal (large datasets would be slow)
- **Real-time**: Prediction is instant (single distance calculation)
- **Similarity-based**: Matches our recommendation use case

#### Q5: What does cosine similarity mean and why use it?
**Answer**:
- Cosine similarity measures the **angle** between two vectors
- Values range from -1 (opposite) to 1 (identical direction)
- **Why for recommendations**: It measures "direction" of preferences, not magnitude
- Example: A user who selects all options still matches sports proportionally
- Formula: `cos(θ) = (A·B) / (||A|| × ||B||)`

#### Q6: How do you convert user selections to feature vectors?
**Answer**:
```python
# User selects: focus=['strength'], intensity=['high'], setting=['solo']
# Converted to 13-D vector:
{
    'balance': 0.0, 'flexibility': 0.0, 'coordination': 0.0, 'relaxation': 0.0,
    'strength': 1.0, 'endurance': 0.0, 'longevity': 0.0,
    'intensity': 1.0,  # high=1.0, moderate=0.67, low=0.33
    'setting_team': 0.0, 'setting_fun': 0.0, 'setting_duo': 0.0,
    'setting_solo': 1.0, 'setting_competitive': 0.0
}
```

#### Q7: Why do you use StandardScaler?
**Answer**:
- Distance-based algorithms are **scale-sensitive**
- Without scaling: intensity (0-1) would dominate binary flags (0/1)
- StandardScaler transforms: `z = (x - mean) / std`
- Result: All features have mean=0, std=1
- Ensures fair contribution of all features to distance

#### Q8: What is the match score and how is it calculated?
**Answer**:
```python
# KNN returns distance (0 = identical, 2 = opposite for cosine)
# We convert to percentage:
match_score = (1 - distance) * 100

# 100% = perfect match (distance = 0)
# 50% = moderate similarity
# 0% = no similarity
```

### Category C: Database Design

#### Q9: Why did you create SQL views instead of using direct queries?
**Answer**:
- **Simplicity**: Single query returns all needed data (no joins in Python)
- **Performance**: Database optimizes view execution
- **Reusability**: Views are used by both app and ML training
- **Maintainability**: Schema changes only affect view definition

#### Q10: Explain your database normalization choices
**Answer**:
- **3NF** (Third Normal Form) for transactional tables
- `sportangebote` → `sportkurse` → `kurs_termine` hierarchy
- Many-to-many for trainers (via `kurs_trainer` junction table)
- **Denormalized views** for read performance (`vw_offers_complete`)

#### Q11: How do you handle the ML training data view?
**Answer**:
```sql
-- ml_training_data view one-hot encodes features:
SELECT
    href,
    name AS "Angebot",
    CASE WHEN 'strength' = ANY(focus) THEN 1.0 ELSE 0.0 END AS strength,
    CASE WHEN 'balance' = ANY(focus) THEN 1.0 ELSE 0.0 END AS balance,
    -- ... more features
    CASE intensity WHEN 'high' THEN 1.0 WHEN 'moderate' THEN 0.67 ELSE 0.33 END AS intensity
FROM sportangebote;
```

### Category D: Web Scraping

#### Q12: How do you handle website changes or scraping failures?
**Answer**:
- **Error handling**: try/except blocks with graceful degradation
- **Hard failures**: Location extraction failure stops the script (exit code 1)
- **Logging**: ETL runs recorded in `etl_runs` table
- **GitHub Actions**: Failed runs are visible in workflow history
- **Fallback**: App works with stale data if scraper fails

#### Q13: What ethical considerations apply to web scraping?
**Answer**:
- We only scrape **public university data** (no login required)
- Scraping runs **once daily** (minimal server load)
- Data is used for **educational purposes** (course project)
- No commercial use or resale
- Scraping is limited to university sports pages (targeted URLs, not full crawling)

#### Q14: How do you parse complex HTML structures?
**Answer**:
- **BeautifulSoup**: Python library for HTML parsing
- **CSS selectors**: Target specific elements (e.g., `table.bs_kurse td.bs_sknr`)
- **Regex**: Extract data from JavaScript (e.g., `var markers=[...]`)
- **Fuzzy matching**: Handle slight name variations between data sources

### Category E: Software Engineering

#### Q15: How do you handle caching in Streamlit?
**Answer**:
```python
# For expensive objects (DB connections, ML models):
@st.cache_resource
def load_knn_model():
    return joblib.load(path)

# For data that changes (with TTL):
@st.cache_data(ttl=300)  # 5 minutes
def get_offers_complete():
    return supaconn().table("vw_offers_complete").select("*").execute()
```

#### Q16: How do you handle authentication securely?
**Answer**:
- **Google OAuth**: Industry-standard secure login
- **OIDC "sub" claim**: Unique user identifier from Google
- **Session clearing**: All data cleared on logout
- **Secrets management**: Credentials in Streamlit secrets, not code
- **No passwords stored**: OAuth tokens handled by Streamlit

#### Q17: What design patterns did you use?
**Answer**:
1. **Repository Pattern**: `utils/db.py` centralizes all database access
2. **Factory Pattern**: `KNNSportRecommender.load_model()` creates instances
3. **Singleton**: `@st.cache_resource` for DB connection
4. **Facade Pattern**: `load_and_filter_offers()` hides complexity
5. **Strategy Pattern**: Different filter functions for offers vs events

### Category F: Project Management

#### Q18: How did your team collaborate on this project?
**Answer**:
- **Git branches**: Feature branches for parallel development
- **GitHub Issues**: Task tracking and bug reports
- **Code reviews**: Pull request reviews before merging
- **Task division**: Clear areas of responsibility (see contribution matrix)
- **Regular meetings**: Weekly syncs to coordinate progress

#### Q19: What were the biggest challenges?
**Answer**:
1. **Streamlit state management**: Widget keys and session state conflicts
2. **ML integration**: Ensuring consistent feature encoding
3. **Scraper reliability**: Handling website structure changes
4. **Caching bugs**: Stale data when filters changed
5. **Cross-browser testing**: UI differences

### Category G: Future Improvements

#### Q20: What would you improve with more time?
**Answer**:
1. **User favorites**: Save preferred sports to profile
2. **Calendar integration**: Export courses to Google Calendar
3. **Push notifications**: Alert when new courses match preferences
4. **Collaborative filtering**: "Users like you also tried..."
5. **Mobile app**: Native iOS/Android versions
6. **More ML models**: Try matrix factorization or neural networks

---

## Quick Reference: Key Code Locations

| Feature | File | Lines |
|---------|------|-------|
| Main UI | `streamlit_app.py` | 1-843 |
| Sidebar filters | `streamlit_app.py` | 137-384 |
| Database queries | `utils/db.py` | Full file |
| Filter logic | `utils/filters.py` | Full file |
| ML recommendations | `utils/ml_utils.py` | Full file |
| KNN model | `ml/recommender.py` | Full file |
| Model training | `ml/train.py` | Full file |
| Main scraper | `.scraper/scrape_sportangebote.py` | Full file |
| Location extractor | `.scraper/extract_locations_from_html.py` | Full file |
| Analytics charts | `utils/analytics.py` | Full file |
| DB schema | `schema.sql` | Full file |
| GitHub Actions | `.github/workflows/scraper.yml` | Full file |

---

## Presentation Tips

1. **Start with the demo**: Show the app working before explaining code
2. **Use the analytics tab**: Visualizations are impressive
3. **Explain ML in simple terms**: "Find sports similar to your preferences"
4. **Show the scraper workflow**: GitHub Actions is tangible automation
5. **Highlight team contributions**: Use the contribution matrix
6. **Be ready for follow-ups**: Professors may dig into any component

Good luck with your presentation! 🎯
