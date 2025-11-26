"""ml_algorithm
-----------------
Training script for a RandomForest-based sport classifier.

This script fetches preprocessed training rows from the Supabase
view ``ml_training_data``, trains a scikit-learn pipeline (imputer +
scaler + RandomForest) and persists the resulting pipeline to
``ml_model.joblib``. The script is intended to be run as a one-off
training job or from CI when the training dataset changes.

Notes:
- The dataset is expected to already contain the numeric feature
    columns used for model training and a target column named
    ``Angebot`` (sport name).
- Because many sports may have only a single example, the script
    uses a simple pipeline without cross-validation by default; the
    printed messages explain this limitation.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils.class_weight import compute_class_weight
import joblib
import os
from dotenv import load_dotenv
from supabase import create_client
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()
env_path = script_dir / '.env'

# Load environment variables from specific path
load_dotenv(dotenv_path=env_path)

# Connect to Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase = create_client(supabase_url, supabase_key)

print("Fetching training data from Supabase ml_training_data view...")

# Fetch pre-transformed data from the view
response = supabase.table("ml_training_data").select("*").execute()

if not response.data:
    raise ValueError("No data found in ml_training_data view")

# Convert to DataFrame - data is already transformed!
data = pd.DataFrame(response.data)

print(f"\nFetched {len(data)} training samples from Supabase")
print("\nData preview:")
print(data.head())

target_column = 'Angebot'
model_path = 'ml_model.joblib'

# Feature columns
featured_columns = [
    'balance', 'flexibility', 'coordination', 'relaxation', 
    'strength', 'endurance', 'longevity',
    'intensity',
    'setting_team', 'setting_fun', 'setting_duo', 
    'setting_solo', 'setting_competitive'
]

print("\nUsing featured columns:", featured_columns)

# Check class distribution
print("\nClass distribution:")
class_counts = data[target_column].value_counts()
print(f"Total classes: {len(class_counts)}")
print(f"Classes with only 1 sample: {(class_counts == 1).sum()}")

# X = training features, y = target variable
X = data[featured_columns].copy()   
y = data[target_column].copy()

# train/test split without stratification
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=None, random_state=66)

print(f"\nTraining set: {len(X_train)} samples")
print(f"Test set: {len(X_test)} samples")

# compute class weights
classes = np.unique(y_train)
cw_vals = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
class_weights = {cls: w for cls, w in zip(classes, cw_vals)}

# missing value imputation and feature scaling
preprocessor = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

# Build final pipeline with good default parameters
# Since each sport appears only once, we use a simpler model
pipeline = Pipeline([
    ("preproc", preprocessor),
    ("clf", RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=2,
        max_features="sqrt",
        class_weight=class_weights,
        n_jobs=-1,
        random_state=66
    ))
])

print("\nTraining model (no cross-validation due to single samples per class)...")
pipeline.fit(X_train, y_train)

# Test
y_pred = pipeline.predict(X_test)
test_acc = accuracy_score(y_test, y_pred)

print(f"\nTest accuracy: {test_acc:.4f}")
print(f"\nNote: With only 1 sample per sport, the model memorizes training data.")
print("This is expected behavior - it will recommend based on feature similarity.")

print("\nClassification report (top 10 classes):\n")
report = classification_report(y_test, y_pred, zero_division=0, output_dict=True)

# Show only classes that appeared in test set
for sport in list(y_test.unique())[:10]:
    if sport in report:
        metrics = report[sport]
        print(f"{sport}: precision={metrics['precision']:.2f}, recall={metrics['recall']:.2f}")

# Save
joblib.dump(pipeline, "ml_model.joblib")
print("\n Saved model to ml_model.joblib")
print("\n Training complete!")