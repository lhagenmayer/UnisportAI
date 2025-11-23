# Sport Feature Radar Chart - Feature Documentation

## Overview
The Sport Feature Radar Chart is an interactive visualization that displays the 13 machine learning features used in UnisportAI's recommendation system. This feature helps users understand:
- Why certain sports are recommended
- How different sports compare based on ML features
- What their preference profile looks like

## Location
The radar charts appear in the **"✨ You Might Also Like"** section on the Sports Overview page, next to each AI recommendation.

## Features

### 1. Individual Sport Radar Charts
Each ML recommendation now includes an expandable section:
- **"📊 View ML Feature Breakdown for [Sport Name]"**
- Shows all 13 ML features in an interactive radar chart
- Includes a comparison selector to compare with other sports

### 2. User Preference Profile
A special radar chart showing:
- **"🎯 Your Preference Profile"**
- How your selected filters translate into ML features
- Helps you understand what the AI is looking for

### 3. Interactive Comparison
Users can:
- Select any sport from a dropdown to compare features
- See two sports overlaid on the same radar chart
- Understand similarities and differences visually

## The 13 ML Features

### Focus Features (7)
1. **Balance** - Improves balance and stability
2. **Flexibility** - Enhances flexibility and range of motion
3. **Coordination** - Develops hand-eye coordination
4. **Relaxation** - Promotes relaxation and stress relief
5. **Strength** - Builds muscular strength
6. **Endurance** - Improves cardiovascular endurance
7. **Longevity** - Supports long-term health and longevity

### Intensity Feature (1)
8. **Intensity** - Exercise intensity level (0.33=low, 0.67=moderate, 1.0=high)

### Setting Features (5)
9. **Team** - Team-based activities
10. **Fun** - Recreation-focused activities
11. **Duo** - Partner/duo activities
12. **Solo** - Individual activities
13. **Competitive** - Competition-oriented activities

## Technical Implementation

### Files Modified/Created
1. **`data/visualizations.py`** (NEW)
   - `get_sport_features()` - Retrieves features for a sport
   - `create_radar_chart()` - Creates Plotly radar chart
   - `render_sport_radar_chart()` - Streamlit widget for sport charts
   - `render_user_preferences_radar()` - Streamlit widget for user preferences

2. **`data/shared_sidebar.py`** (MODIFIED)
   - Enhanced `render_ml_recommendations_section()` to include radar charts
   - Added expandable sections for each recommendation
   - Added user preference profile section

### Dependencies
- **plotly** - For interactive radar charts (already in requirements.txt)
- Uses existing ML infrastructure (KNN model, feature definitions)

## Usage Examples

### In Code
```python
# Display radar chart for a specific sport
from data.visualizations import render_sport_radar_chart

render_sport_radar_chart("Badminton", allow_comparison=True)
```

### For Users
1. Navigate to **Sports Overview** page
2. Select filters (intensity, focus, setting) in the sidebar
3. Scroll to **"✨ You Might Also Like"** section
4. Click **"📊 View ML Feature Breakdown"** for any sport
5. Optionally select a comparison sport from the dropdown
6. View **"🎯 Your Preference Profile"** to see your filter preferences

## Visual Design
- **Primary Sport**: Purple gradient (`#667eea`)
- **Comparison Sport**: Pink gradient (`#f093fb`)
- **Scale**: 0 to 1 (normalized feature values)
- **Interactive**: Hover to see exact values
- **Responsive**: Adapts to container width

## Benefits

### For Users
✅ **Transparency** - Understand why sports are recommended
✅ **Discovery** - Find similar sports through comparison
✅ **Insight** - See how your preferences map to ML features
✅ **Engagement** - Interactive and visually appealing

### For ML Showcase
✅ **Unique** - Specific to your ML implementation
✅ **Educational** - Teaches users about ML features
✅ **Professional** - Publication-quality visualizations
✅ **Interactive** - More engaging than static explanations

## Testing

Run the test script:
```bash
cd machine
python test_radar_chart.py
```

This verifies:
- Feature extraction from KNN model
- Radar chart creation
- Comparison functionality

## Future Enhancements

Possible improvements:
1. Add feature importance/weighting display
2. Allow users to adjust feature weights
3. Show which features contributed most to the recommendation
4. Add tooltips explaining each feature in detail
5. Export charts as images
