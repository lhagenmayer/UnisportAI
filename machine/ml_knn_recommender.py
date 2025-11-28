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
import pandas as pd  # Powerful data manipulation library - converts database results into organized tables we can analyze
import numpy as np  # Essential numerical computing library - handles arrays and mathematical operations for ML algorithms
from sklearn.neighbors import NearestNeighbors  # The core KNN machine learning algorithm that finds sports most similar to user preferences
from sklearn.preprocessing import StandardScaler  # Critical preprocessing tool that normalizes feature scales so no single feature dominates similarity calculations
import joblib  # Model serialization library - saves our fully trained ML model to disk so we can reload it instantly later
import os  # Operating system interface - allows us to read sensitive configuration data from environment variables
from dotenv import load_dotenv  # Environment file loader - securely reads database credentials from .env file without hardcoding secrets
from supabase import create_client  # Official Supabase client library - establishes secure connection to our cloud database
from pathlib import Path  # Modern file system path handler - safely constructs file paths that work across different operating systems

# Load environment variables (secure configuration setup)
script_dir = Path(__file__).parent.absolute()  # Find the exact directory where this Python file is located on the file system
env_path = script_dir / '.env'  # Construct path to .env file that should be in the same folder as this script
load_dotenv(dotenv_path=env_path)  # Safely load database credentials from .env file into environment variables (keeps secrets out of code)

supabase_url = os.environ.get("SUPABASE_URL")  # Extract the Supabase project URL from environment variables (e.g., https://xyz.supabase.co)
supabase_key = os.environ.get("SUPABASE_KEY")  # Extract the Supabase API key from environment variables (allows authenticated access)

if not supabase_url or not supabase_key:  # Validate that both required credentials are present before proceeding
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")  # Fail fast with clear error message if setup incomplete

supabase = create_client(supabase_url, supabase_key)  # Establish authenticated connection to Supabase database using loaded credentials

# Feature columns (13 features) - These define the complete "personality" of each sport for ML comparison
FEATURE_COLUMNS = [  # Comprehensive feature set that captures all important dimensions of sports activities
    'balance', 'flexibility', 'coordination', 'relaxation',  # Physical skill development features (body control, range of motion, mental calmness)
    'strength', 'endurance', 'longevity',  # Fitness improvement features (muscle building, cardiovascular health, long-term wellness)
    'intensity',  # Workout intensity level (from gentle stretching to high-intensity interval training)
    'setting_team', 'setting_fun', 'setting_duo',  # Social context features (group dynamics, enjoyment factor, partner activities)
    'setting_solo', 'setting_competitive'  # Individual preference features (solitary activities, competitive environment)
]

class KNNSportRecommender:
    """
    Machine Learning Recommender using K-Nearest Neighbors
    This IS machine learning because KNN learns from data patterns
    """
    
    def __init__(self, n_neighbors=10):  # Initialize the machine learning recommender system with configurable parameters
        self.n_neighbors = n_neighbors  # Number of most similar sports to return in recommendations (10 gives good variety without overwhelming user)
        self.knn_model = NearestNeighbors(  # Initialize the K-Nearest Neighbors machine learning algorithm for similarity detection
            n_neighbors=n_neighbors,  # Configure how many similar sports the algorithm should find during each query
            metric='cosine',  # Use cosine similarity metric - ideal for preference vectors as it measures angle between feature vectors regardless of magnitude
            algorithm='brute'  # Use exhaustive brute-force search algorithm - slower but guarantees finding true nearest neighbors (good for small/medium datasets)
        )
        self.scaler = StandardScaler()  # Initialize feature scaling tool that will normalize all features to have mean=0 and std=1 (prevents features with larger ranges from dominating)
        self.sports_df = None  # Placeholder for pandas DataFrame that will store all sports data and metadata after loading from database
        self.is_fitted = False  # Boolean flag tracking whether the model has been trained on data (prevents using untrained model)
    
    def load_and_train(self):
        """Load features from Supabase and train the internal KNN.

        The method queries the Supabase view ``ml_training_data`` and
        expects the view to contain one row per sport with the numeric
        feature columns defined in :data:`FEATURE_COLUMNS`.

        Raises:
            ValueError: If the view returns no data.
        """
        print("Loading sports data from Supabase...")  # Inform user that data loading phase has started
        response = supabase.table("ml_training_data").select("*").execute()  # Execute SQL query to fetch all rows and columns from the ml_training_data view in Supabase
        
        if not response.data:  # Validate that the database query returned actual data rows
            raise ValueError("No data found in ml_training_data view")  # Fail immediately with descriptive error if database is empty or query failed
        
        self.sports_df = pd.DataFrame(response.data)  # Convert raw JSON response from Supabase into structured pandas DataFrame for easy data manipulation
        print(f"Loaded {len(self.sports_df)} sports")  # Display count of sports loaded to give user feedback on dataset size
        
        # Filter out entries with all features = 0 (like Schliessfachvermietung)
        feature_sums = self.sports_df[FEATURE_COLUMNS].fillna(0).sum(axis=1)
        valid_sports_mask = feature_sums > 0
        
        if not valid_sports_mask.all():
            invalid_sports = self.sports_df[~valid_sports_mask]['Angebot'].tolist()
            print(f"Filtering out {len(invalid_sports)} sports with no features: {invalid_sports}")
            self.sports_df = self.sports_df[valid_sports_mask].reset_index(drop=True)
            print(f"Using {len(self.sports_df)} valid sports for training")
        
        # Extract features and handle missing values (convert categorical data to numerical format for ML algorithm)
        X = self.sports_df[FEATURE_COLUMNS].values  # Extract only the 13 feature columns and convert to NumPy array format required by scikit-learn
        
        # Replace any NaN/null values with 0.0 (missing features default to neutral/inactive)
        X = pd.DataFrame(X, columns=FEATURE_COLUMNS).fillna(0.0).values  # Handle missing values by filling with 0.0 (neutral preference)
        print(f"Preprocessed features - shape: {X.shape}")  # Show data dimensions after preprocessing
        
        # Scale features (critical preprocessing step for distance-based ML algorithms)
        X_scaled = self.scaler.fit_transform(X)  # Fit scaler on training data to learn mean/std, then transform features to have mean=0 std=1 (prevents features like 'intensity' from overwhelming smaller features)
        
        # Train KNN model (the actual machine learning training step)
        print("Training KNN model...")  # Notify user that ML training phase has begun
        self.knn_model.fit(X_scaled)  # Build the KNN search index from scaled training data - algorithm learns the feature space structure for fast similarity searches
        self.is_fitted = True  # Set flag indicating model is now trained and ready for making recommendations
        
        print(f"KNN model trained with {len(self.sports_df)} sports")
    
    def get_recommendations(self, user_preferences: dict, top_n: int = 5):
        """
        Get sport recommendations using trained KNN model
        
        Args:
            user_preferences: Dict with 13 feature values
            top_n: Number of recommendations
            
        Returns:
            List of dicts with sport name and match score
        """
        if not self.is_fitted:  # Safety check to ensure model has been trained before attempting to make predictions
            raise ValueError("Model not trained. Call load_and_train() first.")  # Prevent crashes by failing fast with clear error message
        
        # Build user feature vector (convert user preferences to format compatible with trained ML model)
        user_vector = np.array([user_preferences.get(col, 0.0) for col in FEATURE_COLUMNS])  # Transform user preference dictionary into ordered numerical array matching training data format (defaults missing features to 0.0)
        user_vector = user_vector.reshape(1, -1)  # Reshape from 1D array to 2D array with shape (1, 13) as required by scikit-learn's transform methods
        
        # Scale user vector (apply same normalization used during training)
        user_vector_scaled = self.scaler.transform(user_vector)  # Apply exact same scaling transformation used on training data to ensure user preferences are in comparable feature space
        
        # Find K nearest neighbors (this is the actual ML prediction/inference step)
        distances, indices = self.knn_model.kneighbors(user_vector_scaled, n_neighbors=top_n)  # Query the trained KNN index to find sports with most similar feature vectors to user preferences (returns cosine distances and database indices)
        
        # Build recommendations (convert ML algorithm output to human-readable format)
        recommendations = []  # Initialize empty list to accumulate formatted recommendation results
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):  # Iterate through each similar sport found by KNN algorithm
            sport_name = self.sports_df.iloc[idx]['Angebot']  # Look up human-readable sport name using database index returned by KNN
            # Convert distance to similarity score (0-100%) - ML algorithms return distances, but users understand percentages better
            # Lower cosine distance = higher similarity between preference vectors
            similarity = (1 - distance) * 100  # Transform distance metric (0=identical, 1=completely different) to similarity percentage (100%=perfect match, 0%=no similarity)
            
            recommendations.append({  # Add this sport recommendation to results list
                'sport': sport_name,  # Human-readable name of recommended sport
                'match_score': round(similarity, 1)  # Similarity percentage rounded to 1 decimal place for readability
            })
        
        return recommendations  # Return list of recommended sports sorted by similarity to user preferences
    
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
        if not self.is_fitted:  # Validate that model has been trained before attempting to save (prevents saving empty/invalid model)
            raise ValueError("Model not trained. Call load_and_train() first.")  # Fail with clear error message if trying to save untrained model
        
        joblib.dump({  # Serialize complete model bundle to disk using joblib's efficient binary format (much faster than pickle for NumPy arrays)
            'knn_model': self.knn_model,  # The fully trained KNN algorithm with built search index containing all sports feature vectors
            'scaler': self.scaler,  # The fitted StandardScaler that knows the mean/std of training features (essential for consistent normalization)
            'sports_df': self.sports_df,  # Complete DataFrame with sport names and metadata (needed to convert ML indices back to human-readable sport names)
            'feature_columns': FEATURE_COLUMNS,  # Ordered list of feature names (ensures consistent feature ordering when loading model)
            'n_neighbors': self.n_neighbors  # Model configuration parameter (preserves the k-value used during training)
        }, path)  # Write the complete model bundle to specified file path as compressed binary data
        print(f"Saved KNN model to {path}")  # Confirm successful model persistence to user
    
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
        data = joblib.load(path)  # Deserialize the complete model bundle from disk back into Python objects (automatically handles decompression and NumPy array reconstruction)
        recommender = KNNSportRecommender.__new__(KNNSportRecommender)  # Create new instance using __new__ to bypass __init__ (avoids re-initializing empty model components)
        recommender.knn_model = data['knn_model']  # Restore the fully trained KNN algorithm with complete search index (ready for immediate similarity queries)
        recommender.scaler = data['scaler']  # Restore the fitted StandardScaler with learned mean/std parameters (ensures consistent feature normalization)
        recommender.sports_df = data['sports_df']  # Restore complete sports DataFrame with all metadata (enables converting ML indices to sport names)
        recommender.n_neighbors = data['n_neighbors']  # Restore original k-value configuration (maintains consistency with training setup)
        recommender.is_fitted = True  # Set trained flag to indicate model is ready for recommendations (skips training validation checks)
        return recommender  # Return fully reconstructed recommender system ready for immediate use without any retraining