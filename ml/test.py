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
    """
    Test the trained KNN recommender with sample user personas.
    
    HOW: Creates test personas with different preferences, queries the model,
    and displays recommendations to verify the model works correctly.
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
    user_prefs_1 = {  # Test persona: "Fitness Enthusiast" someone seeking intense, results-focused solo training sessions
        'balance': 0.0,  # Not interested in balance/stability training exercises
        'flexibility': 0.0,  # Not prioritizing stretching or mobility work
        'coordination': 0.0,  # Not seeking activities that develop hand-eye coordination or complex movement patterns
        'relaxation': 0.0,  # Actively avoids low-key, meditative, or stress-relief focused activities
        'strength': 1.0,  # Primary goal: maximize muscle building and power development
        'endurance': 1.0,  # Secondary goal: improve cardiovascular fitness and stamina
        'longevity': 0.0,  # Not focused on gentle activities for long-term joint health
        'intensity': 1.0,  # Seeks maximum exertion, high heart rate, challenging workouts
        'setting_team': 0.0,  # Prefers not to coordinate with groups or depend on teammates
        'setting_fun': 0.0,  # Prioritizes results over entertainment value
        'setting_duo': 0.0,  # Doesn't want partner-dependent activities or couples' exercises
        'setting_solo': 1.0,  # Strongly prefers individual activities with complete schedule flexibility
        'setting_competitive': 0.0  # Not interested in competing against others or keeping score
    }
    
    recommendations = recommender.get_recommendations(user_prefs_1, top_n=5)  # Query trained ML model to find 5 sports most similar to this user's preferences
    
    print("\nTop 5 KNN Recommendations:")  # Display header for ML algorithm results
    for i, rec in enumerate(recommendations, 1):  # Iterate through recommendations with human-friendly numbering starting from 1
        print(f"{i}. {rec['sport']}: {rec['match_score']}% match")  # Display each recommendation with sport name and ML-calculated similarity percentage
    
    # Test case 2: Relaxation + Flexibility, Low intensity, Duo
    print("\n" + "="*60)
    print("Test 2: Relaxation + Flexibility, Low intensity, Duo")
    print("-" * 60)
    user_prefs_2 = {  # Test persona: "Wellness Seeker" someone prioritizing gentle movement, stress relief, and partner bonding
        'balance': 0.0,  # Not specifically targeting balance or stability improvements
        'flexibility': 1.0,  # Primary goal: increase range of motion, reduce stiffness, improve mobility
        'coordination': 0.0,  # Not seeking complex movement patterns or skill development
        'relaxation': 1.0,  # Major priority: stress reduction, mental calm, mindfulness integration
        'strength': 0.0,  # Actively avoids muscle-building or resistance training
        'endurance': 0.0,  # Not interested in cardiovascular conditioning or stamina building
        'longevity': 0.0,  # Not specifically focused on long-term health maintenance
        'intensity': 0.33,  # Prefers gentle, low-impact activities (33% = mild exertion, sustainable pace)
        'setting_team': 0.0,  # Avoids large group dynamics or team coordination requirements
        'setting_fun': 0.0,  # Values therapeutic benefits over entertainment aspect
        'setting_duo': 1.0,  # Strongly prefers shared activities that strengthen relationships and provide mutual support
        'setting_solo': 0.0,  # Dislikes exercising alone, seeks social connection and accountability
        'setting_competitive': 0.0  # Completely avoids pressure, comparison, or performance metrics
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