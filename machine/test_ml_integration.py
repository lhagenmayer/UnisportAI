"""
Test ML Integration
===================
This script tests the ML integration without needing the full Streamlit app
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.ml_integration import get_sport_recommendations, validate_user_preferences, load_ml_model

def test_model_loading():
    """Test if model can be loaded"""
    print("Testing model loading...")
    model = load_ml_model()
    if model is None:
        print("❌ Failed to load model")
        return False
    print("✅ Model loaded successfully")
    print(f"   Model type: {type(model)}")
    return True

def test_recommendations():
    """Test getting recommendations"""
    print("\nTesting recommendations...")
    
    # Sample preferences (balanced athlete)
    user_preferences = {
        'balance': 0.7,
        'flexibility': 0.6,
        'coordination': 0.8,
        'relaxation': 0.3,
        'strength': 0.7,
        'endurance': 0.8,
        'longevity': 0.6,
        'intensity': 0.8,
        'setting_team': 1.0,
        'setting_fun': 1.0,
        'setting_duo': 0.0,
        'setting_solo': 0.0,
        'setting_competitive': 0.5
    }
    
    # Validate
    if not validate_user_preferences(user_preferences):
        print("❌ Preferences validation failed")
        return False
    print("✅ Preferences validated")
    
    # Get recommendations
    recommendations = get_sport_recommendations(user_preferences, top_n=5)
    
    if not recommendations:
        print("❌ No recommendations returned")
        return False
    
    print(f"✅ Got {len(recommendations)} recommendations:")
    for i, (sport, confidence) in enumerate(recommendations, 1):
        print(f"   {i}. {sport}: {confidence:.1f}%")
    
    return True

def test_edge_cases():
    """Test edge cases"""
    print("\nTesting edge cases...")
    
    # All zeros
    all_zeros = {
        'balance': 0.0,
        'flexibility': 0.0,
        'coordination': 0.0,
        'relaxation': 0.0,
        'strength': 0.0,
        'endurance': 0.0,
        'longevity': 0.0,
        'intensity': 0.0,
        'setting_team': 0.0,
        'setting_fun': 0.0,
        'setting_duo': 0.0,
        'setting_solo': 0.0,
        'setting_competitive': 0.0
    }
    
    recs = get_sport_recommendations(all_zeros, top_n=3)
    if recs:
        print(f"✅ All zeros test passed ({len(recs)} recommendations)")
    else:
        print("❌ All zeros test failed")
        return False
    
    # All ones
    all_ones = {k: 1.0 for k in all_zeros.keys()}
    recs = get_sport_recommendations(all_ones, top_n=3)
    if recs:
        print(f"✅ All ones test passed ({len(recs)} recommendations)")
    else:
        print("❌ All ones test failed")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("ML Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Model Loading", test_model_loading),
        ("Recommendations", test_recommendations),
        ("Edge Cases", test_edge_cases)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed")
        sys.exit(1)
