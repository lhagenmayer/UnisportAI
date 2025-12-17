# UnisportAI

**Course Project: Fundamentals and Methods of Computer Science**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://unisportai.streamlit.app)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg) ![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg) ![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green.svg) ![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3+-f7931e.svg) ![pandas](https://img.shields.io/badge/pandas-2.0+-150458.svg) ![NumPy](https://img.shields.io/badge/NumPy-1.24+-013243.svg) ![Plotly](https://img.shields.io/badge/Plotly-5.15+-3f4f75.svg) ![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4.x-green.svg)

A Streamlit web application for discovering university sports courses at the University of St. Gallen (HSG). This project demonstrates the application of programming, databases, data science, and machine learning concepts learned in the course.

## Project Overview

This application helps students find sports activities that match their preferences using:
- **Data filtering**: Search by time, location, sport type, and intensity
- **Machine learning**: KNN-based recommendations for personalized suggestions
- **Data visualization**: Charts showing course availability patterns
- **User interaction**: Interactive filters and personalized recommendations

## Data Flow Architecture

```mermaid
flowchart TD
    %% Datenquellen
    A[🌐 Unisport Website\nwww.sportprogramm.unisg.ch] --> B[Web Scraping]

    %% ETL Prozess
    B --> C[📊 Scraper Scripts]
    C --> D[Extract Offers\nextract_offers()]
    C --> E[Extract Courses\nextract_courses_for_offer()]
    C --> F[Extract Locations\nextract_locations()]
    C --> G[Extract Dates\nextract_course_dates()]

    %% Datenbank Layer
    D --> H[(📚 Supabase PostgreSQL)]
    E --> H
    F --> H
    G --> H

    H --> I[sportangebote\nAngebote & Metadaten]
    H --> J[sportkurse\nKonkrete Kurse]
    H --> K[kurs_termine\nTermine & Zeiten]
    H --> L[unisport_locations\nStandorte & Koordinaten]
    H --> M[trainer\nTrainer-Informationen]
    H --> N[kurs_trainer\nKurs-Trainer Beziehungen]

    %% ML Pipeline
    I --> O[🔧 ML Training Data View\nml_training_data]
    O --> P[🤖 KNN Training\ntrain.py]
    P --> Q[💾 Trained Model\nknn_recommender.joblib]

    %% Views für App
    I --> R[👁️ Application Views]
    J --> R
    K --> R
    L --> R
    M --> R
    N --> R

    R --> S[vw_offers_complete\nAngebote mit Trainern]
    R --> T[vw_termine_full\nTermine mit Details]

    %% Streamlit Application
    S --> U[🎯 Streamlit App\nstreamlit_app.py]
    T --> U
    Q --> U

    U --> V[🏃‍♂️ Sports Overview\nGefilterte Angebote]
    U --> W[📅 Course Dates\nTermin-Details]
    U --> X[👤 My Profile\nBenutzerprofil]
    U --> Y[📊 Analytics\nTeam-Matrix & Charts]

    %% Benutzerinteraktion
    V --> Z[🔍 Filtering\nZeit, Ort, Sportart]
    Z --> AA[🎯 ML Recommendations\nKNN-basierte Vorschläge]
    AA --> V

    %% Feedback Loop
    U --> BB[📝 ETL Logging\netl_runs Tabelle]
    BB --> CC[🔄 Scheduled Updates\nGitHub Actions]
    CC --> B

    %% Styling
    classDef source fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef process fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef storage fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    classDef ml fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef app fill:#fff8e1,stroke:#f57f17,stroke-width:2px
    classDef user fill:#fce4ec,stroke:#c2185b,stroke-width:2px

    class A source
    class B,C,D,E,F,G process
    class H,I,J,K,L,M,N storage
    class O,P,Q ml
    class R,S,T storage
    class U,V,W,X,Y app
    class Z,AA user
    class BB,CC process
```

**Data Flow Overview**: This diagram shows the complete data pipeline from web scraping Unisport website data through database storage, ML training, and user interface display. The system includes automated ETL processes, machine learning recommendations, and real-time filtering.

## Getting Started

### Prerequisites
- Python 3.9+
- Supabase account (free tier available)

### Quick Setup

1. **Clone and install:**
   ```bash
   git clone https://github.com/lhagenmayer/UnisportAI.git
   cd UnisportAI
   pip install -r requirements.txt
   ```

2. **Set up database:**
   - Create a Supabase project at https://supabase.com
   - Run the SQL from `schema.sql` in your Supabase SQL editor

3. **Configure credentials:**
   Create `.streamlit/secrets.toml`:
   ```toml
   [connections.supabase]
   SUPABASE_URL = "your_supabase_url"
   SUPABASE_KEY = "your_supabase_key"
   ```

4. **Run the app:**
   ```bash
   streamlit run streamlit_app.py
   ```

### Course Requirements Met

This project fulfills all mandatory course requirements:

1. ✅ **Problem statement**: Helps students discover suitable sports courses
2. ✅ **Data loading**: Loads course data from Supabase database and web scraping
3. ✅ **Data visualization**: Interactive charts for course availability and recommendations
4. ✅ **User interaction**: Filters, personalization, and ML recommendations
5. ✅ **Machine learning**: KNN algorithm for personalized sport suggestions
6. ✅ **Documentation**: Well-commented source code
7. ✅ **Team contributions**: Documented in analytics section
8. ✅ **Video presentation**: 4-minute demo video (separate deliverable)

---

## Features

### 🏋️ Sports Discovery
- Browse available sports courses with detailed information
- Filter by intensity, focus areas, and social settings
- Search by location, time, and sport type

### 🤖 AI Recommendations
- Machine learning-powered personalized suggestions
- KNN algorithm matches user preferences to sports
- Adjustable match score thresholds

### 📊 Analytics & Charts
- Course availability by weekday and time of day
- Interactive visualizations using Plotly
- Team contribution matrix

### 👤 User Features
- Optional Google OAuth authentication
- Personalized filter preferences
- Session management

## Filter System Architecture

```mermaid
flowchart TD
    %% Benutzerinteraktion
    A[👤 Benutzer] --> B[Streamlit Sidebar]

    %% Sidebar Filter-Komponenten
    B --> C[🎯 Offer-Filter]
    B --> D[📅 Event-Filter]
    B --> E[🤖 ML-Filter]

    C --> F[Intensität\nlow/moderate/high]
    C --> G[Focus\nstrength/endurance/flexibility...]
    C --> H[Setting\nteam/solo/duo/competitive...]
    C --> I[Show Upcoming Only\nBoolean]

    D --> J[Sports\nYoga, Fitness, etc.]
    D --> K[Weekdays\nMonday, Tuesday, ...]
    D --> L[Time Range\nStart-End Time]
    D --> M[Date Range\nStart-End Date]
    D --> N[Locations\nGym A, Hall B, ...]
    D --> O[Hide Cancelled\nBoolean]

    E --> P[Min Match Score\n0-100%]
    E --> Q[ML Min Match\nThreshold für KNN]

    %% Session State Speicherung
    F --> R[(Session State)]
    G --> R
    H --> R
    I --> R
    J --> R
    K --> R
    L --> R
    M --> R
    N --> R
    O --> R
    P --> R
    Q --> R

    %% Filter-Verarbeitung
    R --> S[get_filter_values_from_session()]
    S --> T{Filter Typ\nprüfen}

    T -->|Offer-Filter aktiv| U[filter_offers()\nHard Filter: intensity/focus/setting]
    T -->|Event-Filter aktiv| V[filter_events()\nEvent-Level Filter]
    T -->|Beide aktiv| W[load_and_filter_offers()\n+ load_and_filter_events()]

    %% Offer-Filtering Prozess
    U --> X[100% Match Score\nfür gefilterte Offers]
    X --> Y[apply_ml_recommendations_to_offers()]
    Y --> Z[KNN Model laden]
    Z --> AA[User Preferences\naus Filtern extrahieren]
    AA --> BB[Feature Vector bauen]
    BB --> CC[KNN Neighbors finden\nÄhnliche Sportarten]
    CC --> DD[Match Scores berechnen\n0-100% basierend auf Distanz]
    DD --> EE[Merge: Hard + ML Results\nHöherer Score gewinnt]

    %% Event-Filtering Prozess
    V --> FF[_check_event_matches_filters()]
    FF --> GG{Sport Filter?}
    GG -->|Ja| HH[sport_name in selected_sports]
    GG -->|Nein| II{Next: Hide Cancelled?}

    II -->|Ja| JJ[event.canceled == False]
    II -->|Nein| KK{Next: Weekday?}

    KK -->|Ja| LL[start_time.strftime('%A')\nin selected_weekdays]
    KK -->|Nein| MM{Next: Date Range?}

    MM -->|Ja| NN[event_date in [date_start, date_end]]
    MM -->|Nein| OO{Next: Time Range?}

    OO -->|Ja| PP[event_time in [time_start, time_end]]
    OO -->|Nein| QQ{Next: Location?}

    QQ -->|Ja| RR[location_name in selected_locations]
    QQ -->|Nein| SS[✅ Event matches ALL filters\nAND Logic]

    %% Soft Filter Anwendung
    EE --> TT[apply_soft_filters_to_score()]
    SS --> TT

    TT --> UU{Future Events Check\nshow_upcoming_only?}
    UU -->|Ja, keine Events| VV[Score -20%]
    UU -->|Nein| WW{Event Filter Match?}

    WW -->|Nein, Events vorhanden| XX[Score -15%]
    WW -->|Ja| YY[Score unverändert]

    VV --> ZZ[Score ≥ min_match_score?]
    XX --> ZZ
    YY --> ZZ

    ZZ -->|Ja| AAA[✅ Offer/Event angezeigt]
    ZZ -->|Nein| BBB[❌ Offer/Event ausgeblendet]

    %% Kombinierte Filterung
    W --> CCC[Offer-Filter anwenden]
    W --> DDD[Event-Filter anwenden]
    CCC --> TT
    DDD --> TT

    %% UI-Anzeige
    AAA --> EEE[📊 Streamlit UI\nSports Overview]
    EEE --> FFF[Match Score Anzeige\nFarbcodierung]
    EEE --> GGG[Sortierung\nNach Score absteigend]

    %% Styling
    classDef user fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef input fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef process fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef logic fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef storage fill:#fff8e1,stroke:#f57f17,stroke-width:2px
    classDef ml fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef ui fill:#fce4ec,stroke:#c2185b,stroke-width:2px

    class A user
    class B,C,D,E input
    class F,G,H,I,J,K,L,M,N,O,P,Q input
    class S,U,V,W,FF,TT process
    class T,GG,II,KK,MM,OO,QQ,UU,WW,ZZ logic
    class R storage
    class Y,Z,AA,BB,CC,DD,EE ml
    class EEE,FFF,GGG ui
```

**Filter System Overview**: This diagram illustrates the sophisticated filtering architecture with offer-level (sports characteristics) and event-level (specific dates/times) filters, combined with KNN-based ML recommendations. The system uses AND logic for hard filtering and score reduction for soft filtering to ensure relevant results.

## Technologies Used

- **Frontend**: Streamlit
- **Backend**: Python, Supabase (PostgreSQL)
- **ML**: scikit-learn (KNN algorithm)
- **Data**: pandas, numpy
- **Visualization**: Plotly
- **Web scraping**: requests, beautifulsoup4

## Project Structure

```
UnisportAI/
├── streamlit_app.py           # Main application
├── utils/                     # Utility modules
├── ml/                       # Machine learning components
├── .scraper/                 # Web scraping scripts
├── schema.sql                # Database schema
└── requirements.txt          # Python dependencies
```

## Database Schema

The application uses Supabase (PostgreSQL) with the following core tables:

### Core Tables
- **`users`** - User accounts and authentication data
- **`sportangebote`** - Sports offers (name, description, intensity, focus, setting)
- **`sportkurse`** - Individual courses within offers
- **`kurs_termine`** - Course dates and times with location info
- **`unisport_locations`** - Physical locations with coordinates
- **`trainer`** - Instructor information
- **`kurs_trainer`** - Many-to-many relationship between courses and trainers
- **`etl_runs`** - Logging for data scraping operations

### Views
- **`vw_offers_complete`** - Enriched offers with event counts and trainer lists
- **`vw_termine_full`** - Course dates with sport names and trainer info
- **`ml_training_data`** - Feature vectors for machine learning (13 numeric columns)

The complete schema is defined in `schema.sql` and should be run in a fresh Supabase project.

## Team & Contributions

This project was developed by a team of 5 students as part of the "Fundamentals and Methods of Computer Science" course at the University of St. Gallen (HSG):

### Team Members
- **[Tamara Nessler](https://www.linkedin.com/in/tamaranessler/)**
- **[Till Banerjee](https://www.linkedin.com/in/till-banerjee/)**
- **[Sarah Bugg](https://www.linkedin.com/in/sarah-bugg/)**
- **[Antonia Büttiker](https://www.linkedin.com/in/antonia-büttiker-895713254/)**
- **[Luca Hagenmayer](https://www.linkedin.com/in/lucahagenmayer/)**
