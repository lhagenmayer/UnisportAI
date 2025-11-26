"""ml_knn_recommender
---------------------------------
K-Nearest Neighbors based sport recommender utilities.

This module provides a small KNN-based recommender that loads
feature vectors for sports from a Supabase view named
``ml_training_data``, trains a nearest-neighbor index and exposes
utility methods to obtain human-readable sport recommendations
for a given user preferences vector.

Notes:
- The KNN model uses cosine distance and a ``StandardScaler`` to
    normalize features before computing similarities.
- The code is intentionally lightweight — the primary goal is to
    return nearest neighbors (feature-similar sports) rather than
    train a large classification model.

The main class is :class:`KNNSportRecommender` which exposes
``load_and_train()``, ``get_recommendations()`` and model persistence
helpers.
"""
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
import joblib
import os
from dotenv import load_dotenv
from supabase import create_client
from pathlib import Path

# Load environment variables
script_dir = Path(__file__).parent.absolute()
env_path = script_dir / '.env'
load_dotenv(dotenv_path=env_path)

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase = create_client(supabase_url, supabase_key)

# Feature columns (13 features)
FEATURE_COLUMNS = [
    'balance', 'flexibility', 'coordination', 'relaxation', 
    'strength', 'endurance', 'longevity',
    'intensity',
    'setting_team', 'setting_fun', 'setting_duo', 
    'setting_solo', 'setting_competitive'
]

class KNNSportRecommender:
    """
    Machine Learning Recommender using K-Nearest Neighbors
    This IS machine learning because KNN learns from data patterns
    """
    
    def __init__(self, n_neighbors=10):
        self.n_neighbors = n_neighbors
        self.knn_model = NearestNeighbors(
            n_neighbors=n_neighbors,
            metric='cosine',  # Cosine similarity for feature matching
            algorithm='brute'
        )
        self.scaler = StandardScaler()
        self.sports_df = None
        self.is_fitted = False
    
    def load_and_train(self):
        """Load features from Supabase and train the internal KNN.

        The method queries the Supabase view ``ml_training_data`` and
        expects the view to contain one row per sport with the numeric
        feature columns defined in :data:`FEATURE_COLUMNS`.

        Raises:
            ValueError: If the view returns no data.
        """
        print("Loading sports data from Supabase...")
        response = supabase.table("ml_training_data").select("*").execute()
        
        if not response.data:
            raise ValueError("No data found in ml_training_data view")
        
        self.sports_df = pd.DataFrame(response.data)
        print(f"Loaded {len(self.sports_df)} sports")
        
        # Extract features
        X = self.sports_df[FEATURE_COLUMNS].values
        
        # Scale features (important for distance-based algorithms)
        X_scaled = self.scaler.fit_transform(X)
        
        # Train KNN model (ML step!)
        print("Training KNN model...")
        self.knn_model.fit(X_scaled)
        self.is_fitted = True
        
        print(f"✅ KNN model trained with {len(self.sports_df)} sports")
    
    def get_recommendations(self, user_preferences: dict, top_n: int = 5):
        """
        Get sport recommendations using trained KNN model
        
        Args:
            user_preferences: Dict with 13 feature values
            top_n: Number of recommendations
            
        Returns:
            List of dicts with sport name and match score
        """
        if not self.is_fitted:
            raise ValueError("Model not trained. Call load_and_train() first.")
        
        # Build user feature vector
        user_vector = np.array([user_preferences.get(col, 0.0) for col in FEATURE_COLUMNS])
        user_vector = user_vector.reshape(1, -1)
        
        # Scale user vector
        user_vector_scaled = self.scaler.transform(user_vector)
        
        # Find K nearest neighbors (ML prediction!)
        distances, indices = self.knn_model.kneighbors(user_vector_scaled, n_neighbors=top_n)
        
        # Build recommendations
        recommendations = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            sport_name = self.sports_df.iloc[idx]['Angebot']
            # Convert distance to similarity score (0-100%)
            # Lower distance = higher similarity
            similarity = (1 - distance) * 100
            
            recommendations.append({
                'sport': sport_name,
                'match_score': round(similarity, 1)
            })
        
        return recommendations
    
    def save_model(self, path: str = "knn_recommender.joblib"):
        """Persist the trained model and artifacts to disk.

        Writes a joblib file containing the fitted KNN object, the
        scaler, the training DataFrame and metadata required to reload
        the recommender with :meth:`load_model`.

        Args:
            path: File path where the model bundle is saved.

        Raises:
            ValueError: If called before the model is trained.
        """
        if not self.is_fitted:
            raise ValueError("Model not trained. Call load_and_train() first.")
        
        joblib.dump({
            'knn_model': self.knn_model,
            'scaler': self.scaler,
            'sports_df': self.sports_df,
            'feature_columns': FEATURE_COLUMNS,
            'n_neighbors': self.n_neighbors
        }, path)
        print(f"✅ Saved KNN model to {path}")
    
    @staticmethod
    def load_model(path: str = "knn_recommender.joblib"):
        """Load a saved recommender bundle from disk.

        This is a convenience loader that reconstructs a
        :class:`KNNSportRecommender` instance from the joblib payload
        created by :meth:`save_model`.

        Args:
            path: Path to the joblib file.

        Returns:
            KNNSportRecommender: A recommender instance marked as
            fitted and ready to call :meth:`get_recommendations`.
        """
        data = joblib.load(path)
        recommender = KNNSportRecommender.__new__(KNNSportRecommender)
        recommender.knn_model = data['knn_model']
        recommender.scaler = data['scaler']
        recommender.sports_df = data['sports_df']
        recommender.n_neighbors = data['n_neighbors']
        recommender.is_fitted = True
        return recommender


def main():
    """Train and test the KNN recommender"""
    print("\n" + "="*60)
    print("KNN SPORT RECOMMENDER - MACHINE LEARNING")
    print("="*60 + "\n")
    
    # Create and train recommender
    recommender = KNNSportRecommender(n_neighbors=10)
    recommender.load_and_train()
    
    print("\n" + "="*60)
    print("TESTING RECOMMENDATIONS")
    print("="*60 + "\n")
    
    # Test case 1: High intensity, Strength + Endurance, Solo
    print("Test 1: High intensity, Strength + Endurance, Solo")
    print("-" * 60)
    user_prefs_1 = {
        'balance': 0.0,
        'flexibility': 0.0,
        'coordination': 0.0,
        'relaxation': 0.0,
        'strength': 1.0,
        'endurance': 1.0,
        'longevity': 0.0,
        'intensity': 1.0,
        'setting_team': 0.0,
        'setting_fun': 0.0,
        'setting_duo': 0.0,
        'setting_solo': 1.0,
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
    user_prefs_2 = {
        'balance': 0.0,
        'flexibility': 1.0,
        'coordination': 0.0,
        'relaxation': 1.0,
        'strength': 0.0,
        'endurance': 0.0,
        'longevity': 0.0,
        'intensity': 0.33,
        'setting_team': 0.0,
        'setting_fun': 0.0,
        'setting_duo': 1.0,
        'setting_solo': 0.0,
        'setting_competitive': 0.0
    }
    
    recommendations = recommender.get_recommendations(user_prefs_2, top_n=5)
    
    print("\nTop 5 KNN Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['sport']}: {rec['match_score']}% match")
    
    # Save the model
    print("\n" + "="*60)
    recommender.save_model()
    print("✅ KNN ML Model ready for production!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()