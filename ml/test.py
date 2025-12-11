"""
================================================================================
TEST KNN MODEL
================================================================================

Purpose: Script to test the KNN sport recommender model with different user personas.
Demonstrates how the trained model works with various user preference combinations.
================================================================================
"""

from ml.recommender import KNNSportRecommender
from utils.db import get_ml_training_data_cli

# =============================================================================
# MODEL TESTING
# =============================================================================
# PURPOSE: Test the trained KNN recommender with sample user personas

def test_model():
    """Test the trained KNN recommender with sample user personas.
    
    Creates test personas with different preferences, queries the model,
    and displays recommendations to verify the model works correctly.
    
    Test Personas:
        1. "Fitness Enthusiast": High intensity, Strength + Endurance, Solo
           - Seeks intense, results-focused solo training sessions
           - Prioritizes muscle building and cardiovascular fitness
           - Prefers individual activities with schedule flexibility
        
        2. "Wellness Seeker": Relaxation + Flexibility, Low intensity, Duo
           - Prioritizes gentle movement, stress relief, and partner bonding
           - Seeks therapeutic benefits over entertainment
           - Prefers shared activities that strengthen relationships
    
    Note:
        This function loads training data from the database, trains a new
        recommender instance, and tests it with two different user personas
        to demonstrate how the model works with various preference combinations.
    """
    print("\n" + "="*60)
    print("KNN SPORT RECOMMENDER - MODEL TESTING")
    print("="*60 + "\n")
    
    # Load training data from database via client layer
    print("Loading training data from database...")
    training_data = get_ml_training_data_cli()
    
    # Create and train recommender (or load from saved model)
    recommender = KNNSportRecommender(n_neighbors=10)  # Create a new recommender that finds 10 similar sports
    recommender.load_and_train(training_data)  # Train model with loaded data
    
    print("\n" + "="*60)
    print("TESTING RECOMMENDATIONS")
    print("="*60 + "\n")
    
    # Test case 1: High intensity, Strength + Endurance, Solo
    print("Test 1: High intensity, Strength + Endurance, Solo")
    print("-" * 60)
    # Test persona: "Fitness Enthusiast" - someone seeking intense, results-focused solo training sessions
    user_prefs_1 = {
        'balance': 0.0,
        'flexibility': 0.0,
        'coordination': 0.0,
        'relaxation': 0.0,
        'strength': 1.0,  # Primary goal: maximize muscle building and power development
        'endurance': 1.0,  # Secondary goal: improve cardiovascular fitness and stamina
        'longevity': 0.0,
        'intensity': 1.0,  # Seeks maximum exertion, high heart rate, challenging workouts
        'setting_team': 0.0,
        'setting_fun': 0.0,
        'setting_duo': 0.0,
        'setting_solo': 1.0,  # Strongly prefers individual activities with complete schedule flexibility
        'setting_competitive': 0.0
    }
    
    recommendations = recommender.get_recommendations(user_prefs_1, top_n=5)
    
    print("\nTop 5 KNN Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['sport']}: {rec['match_score']}% match")
    
    # Test case 2: Relaxation + Flexibility, Low intensity, Duo
    print("\n" + "="*60)
    print("Test 2: Relaxation + Flexibility, Low intensity, Duo")
    print("-" * 60)
    # Test persona: "Wellness Seeker" - someone prioritizing gentle movement, stress relief, and partner bonding
    user_prefs_2 = {
        'balance': 0.0,
        'flexibility': 1.0,  # Primary goal: increase range of motion, reduce stiffness, improve mobility
        'coordination': 0.0,
        'relaxation': 1.0,  # Major priority: stress reduction, mental calm, mindfulness integration
        'strength': 0.0,
        'endurance': 0.0,
        'longevity': 0.0,
        'intensity': 0.33,  # Prefers gentle, low-impact activities (33% = mild exertion, sustainable pace)
        'setting_team': 0.0,
        'setting_fun': 0.0,
        'setting_duo': 1.0,  # Strongly prefers shared activities that strengthen relationships
        'setting_solo': 0.0,
        'setting_competitive': 0.0
    }
    
    recommendations = recommender.get_recommendations(user_prefs_2, top_n=5)
    
    print("\nTop 5 KNN Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['sport']}: {rec['match_score']}% match")
    
    print("\n" + "="*60)
    print("✅ Model testing completed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_model()

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.