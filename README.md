# UnisportAI

**Course Project: Fundamentals and Methods of Computer Science**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://unisport.streamlit.app)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg) ![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg) ![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green.svg)

A Streamlit web application for discovering university sports courses at the University of St. Gallen (HSG). This project demonstrates the application of programming, databases, data science, and machine learning concepts learned in the course.

## Project Overview

This application helps students find sports activities that match their preferences using:
- **Data filtering**: Search by time, location, sport type, and intensity
- **Machine learning**: KNN-based recommendations for personalized suggestions
- **Data visualization**: Charts showing course availability patterns
- **User interaction**: Interactive filters and personalized recommendations

## Getting Started

### Prerequisites
- Python 3.9+
- Supabase account (free tier available)

### Quick Setup

1. **Clone and install:**
   ```bash
   git clone https://github.com/RadicatorCH/UnisportAI.git
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

## Team

This project was developed as part of the "Fundamentals and Methods of Computer Science" course at the University of St. Gallen (HSG).

Team members and their contributions are documented in the application's analytics section.
