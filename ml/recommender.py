"""
================================================================================
KNN SPORT RECOMMENDER
================================================================================

Purpose: K-Nearest Neighbors based sport recommender utilities. Provides a small
KNN-based recommender that loads feature vectors for sports from a Supabase view
named ml_training_data, trains a nearest-neighbor index and exposes utility methods
to obtain human-readable sport recommendations for a given user preferences vector.

HOW IT WORKS:
- The KNN model uses cosine distance and a StandardScaler to normalize features
  before computing similarities.
- The code is intentionally lightweight, the primary goal is to return nearest
  neighbors (feature-similar sports) rather than train a large classification model.

The main class is KNNSportRecommender which exposes load_and_train(),
get_recommendations() and model persistence helpers.
================================================================================
"""
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
import joblib
from typing import List, Dict

# =============================================================================
# FEATURE DEFINITIONS
# =============================================================================
# PURPOSE: Define feature columns used for ML comparison
# WHY: These represent the "personality" of each sport for ML comparison (13 features total)

FEATURE_COLUMNS = [
    'balance', 'flexibility', 'coordination', 'relaxation',  # Physical skills
    'strength', 'endurance', 'longevity',  # Fitness dimensions
    'intensity',  # Workout intensity
    'setting_team', 'setting_fun', 'setting_duo',  # Social settings
    'setting_solo', 'setting_competitive'  # Individual preferences
]

# =============================================================================
# KNN RECOMMENDER CLASS
# =============================================================================
# PURPOSE: Main class for KNN-based sport recommendations

class KNNSportRecommender:
    """Machine Learning Recommender using K-Nearest Neighbors.
    
    Finds sports most similar to user preferences based on feature vectors.
    Uses cosine distance and StandardScaler to normalize features before computing similarities.
    The code is intentionally lightweight, the primary goal is to return nearest
    neighbors (feature-similar sports) rather than train a large classification model.
    """
    
    def __init__(self, n_neighbors=10):
        """Initialize the KNN recommender.
        
        Args:
            n_neighbors (int, optional): Number of similar sports to find. Defaults to 10.
        """
        self.n_neighbors = n_neighbors
        # Use cosine similarity ideal for preference vectors
        # Measures angle between vectors rather than absolute distance
        self.knn_model = NearestNeighbors(
            n_neighbors=n_neighbors,
            metric='cosine',
            algorithm='brute'  # Exact search, good for small datasets
        )
        # Normalizes features to prevent larger values from dominating
        self.scaler = StandardScaler()
        self.sports_df = None
        self.is_fitted = False
    
    def load_and_train(self, training_data: List[Dict]):
        """Load features and train the internal KNN model.
        
        This is the CORE TRAINING LOGIC method of the KNNSportRecommender class.
        It handles data preprocessing, feature scaling, and KNN model fitting.
        
        This method is called by training scripts (e.g., ml/train.py) which
        handle the orchestration (loading data from database, creating the recommender
        instance, and saving the model). This method focuses solely on the training logic.

        Args:
            training_data (List[Dict]): List of sport feature dicts from database.
                Must be loaded via utils.db.get_ml_training_data_cli()
                or equivalent database access layer function.

        Raises:
            ValueError: If no training data is available.
            
        Note:
            Process:
            1. Convert training data to DataFrame
            2. Filter out entries with all features = 0 (e.g. locker rentals)
            3. Extract feature matrix and handle missing values
            4. Scale features using StandardScaler (mean=0, std=1)
            5. Train KNN model on scaled features
        """
        if not training_data:
            raise ValueError("No training data provided. Load data via utils.db.get_ml_training_data_cli()")
        
        self.sports_df = pd.DataFrame(training_data)
        print(f"Loaded {len(self.sports_df)} sports")
        
        # Filter out entries with all features = 0 (e.g. locker rentals)
        # These aren't actual sports and would skew recommendations
        feature_sums = self.sports_df[FEATURE_COLUMNS].fillna(0).sum(axis=1)
        valid_sports_mask = feature_sums > 0
        
        if not valid_sports_mask.all():
            invalid_sports = self.sports_df[~valid_sports_mask]['Angebot'].tolist()
            print(f"Filtering out {len(invalid_sports)} sports with no features: {invalid_sports}")
            self.sports_df = self.sports_df[valid_sports_mask].reset_index(drop=True)
            print(f"Using {len(self.sports_df)} valid sports for training")
        
        # Extract feature matrix and handle missing values
        X = self.sports_df[FEATURE_COLUMNS].values
        X = pd.DataFrame(X, columns=FEATURE_COLUMNS).fillna(0.0).values
        print(f"Preprocessed features - shape: {X.shape}")
        
        # Scale features: Transform to mean=0, std=1
        # Critical for distance-based algorithms to prevent feature dominance
        X_scaled = self.scaler.fit_transform(X)
        
        # Train KNN: Build search index from scaled features
        print("Training KNN model...")
        self.knn_model.fit(X_scaled)
        self.is_fitted = True
        
        print(f"KNN model trained with {len(self.sports_df)} sports")
    
    def get_recommendations(self, user_preferences: dict, top_n: int = 5):
        """Get sport recommendations using trained KNN model.
        
        Args:
            user_preferences (dict): Dictionary with feature values (keys from FEATURE_COLUMNS).
                Each key should map to a numeric value (0.0 to 1.0 for most features).
            top_n (int, optional): Number of recommendations to return. Defaults to 5.
            
        Returns:
            list: List of dictionaries, each containing:
                - 'sport' (str): Sport name
                - 'match_score' (float): Similarity score (0-100%), where 100% = perfect match
                
        Raises:
            ValueError: If called before the model is trained.
            
        Note:
            Process:
            1. Build user feature vector from preferences dict
            2. Apply same scaling transformation used during training
            3. Find K nearest neighbors in the feature space
            4. Convert distances to similarity percentages (lower distance = higher similarity)
        """
        if not self.is_fitted:
            raise ValueError("Model not trained. Call load_and_train() first.")
        
        # Build user feature vector from preferences dict
        user_vector = np.array([user_preferences.get(col, 0.0) for col in FEATURE_COLUMNS])
        user_vector = user_vector.reshape(1, -1)
        
        # Apply same scaling transformation used during training
        user_vector_scaled = self.scaler.transform(user_vector)
        
        # Find K nearest neighbors in the feature space
        distances, indices = self.knn_model.kneighbors(user_vector_scaled, n_neighbors=top_n)
        
        # Convert ML output to human-readable recommendations
        recommendations = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            sport_name = self.sports_df.iloc[idx]['Angebot']
            # Convert distance to similarity percentage
            # Lower cosine distance higher similarity
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
        the recommender with load_model().

        Args:
            path (str, optional): File path where the model bundle is saved.
                Defaults to "knn_recommender.joblib".

        Raises:
            ValueError: If called before the model is trained.
            
        Note:
            The saved bundle contains:
            - knn_model: Fitted KNN model
            - scaler: Fitted StandardScaler
            - sports_df: Training DataFrame with all sports
            - feature_columns: List of feature column names
            - n_neighbors: Number of neighbors used
        """
        if not self.is_fitted:
            raise ValueError("Model not trained. Call load_and_train() first.")
        
        # Save complete model bundle
        joblib.dump({
            'knn_model': self.knn_model,
            'scaler': self.scaler,
            'sports_df': self.sports_df,
            'feature_columns': FEATURE_COLUMNS,
            'n_neighbors': self.n_neighbors
        }, path)
        print(f"Saved KNN model to {path}")
    
    @staticmethod
    def load_model(path: str = "knn_recommender.joblib"):
        """Load a saved recommender bundle from disk.

        This is a convenience loader that reconstructs a
        KNNSportRecommender instance from the joblib payload
        created by save_model().

        Args:
            path (str, optional): Path to the joblib file.
                Defaults to "knn_recommender.joblib".

        Returns:
            KNNSportRecommender: A recommender instance marked as
            fitted and ready to call get_recommendations().
        """
        data = joblib.load(path)
        
        # Reconstruct recommender from saved components
        recommender = KNNSportRecommender.__new__(KNNSportRecommender)
        recommender.knn_model = data['knn_model']
        recommender.scaler = data['scaler']
        recommender.sports_df = data['sports_df']
        recommender.n_neighbors = data['n_neighbors']
        recommender.is_fitted = True
        
        return recommender

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.
