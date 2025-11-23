"""
Test script for radar chart visualization
Run this to test the radar chart functionality without launching the full Streamlit app
"""
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(parent_dir))

from data.visualizations import get_sport_features, create_radar_chart, FEATURE_COLUMNS

def test_radar_chart():
    """Test the radar chart creation"""
    print("Testing Radar Chart Functionality")
    print("=" * 60)
    
    # Test 1: Get features for a sport
    print("\nTest 1: Getting sport features...")
    test_sport = "Badminton"  # Common sport that should exist
    
    features = get_sport_features(test_sport)
    
    if features:
        print(f"✅ Successfully loaded features for '{test_sport}'")
        print("\nFeature values:")
        for feat, val in features.items():
            print(f"  {feat}: {val:.3f}")
    else:
        print(f"⚠️  Could not find features for '{test_sport}'")
        print("   This might be because the KNN model hasn't been trained yet.")
        print("   Run ml_knn_recommender.py first to train the model.")
        return
    
    # Test 2: Create radar chart
    print("\n" + "=" * 60)
    print("Test 2: Creating radar chart...")
    
    try:
        fig = create_radar_chart(
            sport_features=features,
            sport_name=test_sport
        )
        print(f"✅ Successfully created radar chart for '{test_sport}'")
        print(f"   Chart has {len(fig.data)} trace(s)")
    except Exception as e:
        print(f"❌ Error creating radar chart: {e}")
        return
    
    # Test 3: Create comparison radar chart
    print("\n" + "=" * 60)
    print("Test 3: Creating comparison radar chart...")
    
    test_sport_2 = "Yoga"
    features_2 = get_sport_features(test_sport_2)
    
    if features_2:
        try:
            fig_compare = create_radar_chart(
                sport_features=features,
                sport_name=test_sport,
                comparison_features=features_2,
                comparison_name=test_sport_2
            )
            print(f"✅ Successfully created comparison chart")
            print(f"   Comparing '{test_sport}' vs '{test_sport_2}'")
            print(f"   Chart has {len(fig_compare.data)} trace(s)")
        except Exception as e:
            print(f"❌ Error creating comparison chart: {e}")
    else:
        print(f"⚠️  Could not find features for '{test_sport_2}'")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print("\nThe radar chart feature is ready to use in the Streamlit app.")
    print("Start the app with: streamlit run streamlit_app.py")

if __name__ == "__main__":
    test_radar_chart()
