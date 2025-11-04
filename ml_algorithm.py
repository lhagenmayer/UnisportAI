import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, RandomizedSearchCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils.class_weight import compute_class_weight
import joblib


data = pd.read_excel('Sportangebot_ML_ready.xlsx')  # Read data from Excel file


print(data.head(10))  # Show columns of the data

target_column = 'Angebot'   # This will be the target variable we want to predict
start_column = 'endurance'    # This is the first feature column
end_column = 'standort_campus_on_campus'      # This is the last feature column
model_path = 'ml_model.joblib'  # Path to save/load the model

# specify features explicitly (these columns will be used for training by the model)
featured_columns = [
'endurance', 
'relaxation',
'intensity',
'setting_gruppe_fun', 
'setting_gruppe_competitive',
'setting_gruppe_teamsport',
'setting_ort_indoor',
'setting_ort_outdoor',
'standort_campus_off_campus',
'standort_campus_on_campus'
]

print("using featured columns: ", featured_columns) # Show selected feature columns 

# X = training features, y = target variable
X = data[featured_columns].copy()   
y = data[target_column].copy()

# train/test split without sampling. 80% train, 20% test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=None, random_state=66) # random_state is used for reproducibility

# compute class weights for the case of classes are rarely occurring
classes = np.unique(y_train)
cw_vals = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
class_weights = {cls: w for cls, w in zip(classes, cw_vals)}


# missing value imputation and feature scaling,
preprocessor = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ])


# model pipeline
rf = RandomForestClassifier(n_jobs=-1, class_weight=class_weights, random_state=66)


pipeline = Pipeline([("preproc", preprocessor), ("clf", rf)])

param_distributions = {
    "clf__n_estimators": [100, 200, 300],           # number of trees in the forest
    "clf__max_depth": [10, 20, 30, None],           # maximum depth of the tree
    "clf__min_samples_split": [2, 5, 10],           # minimum samples required to split an internal node
    "clf__max_features": ["sqrt", "log2"],          # number of features to consider when looking for the best split
}

search = RandomizedSearchCV(
    estimator=pipeline,                         # the pipeline with preprocessing and classifier
    param_distributions=param_distributions,    # the parameter grid to search
    n_iter=20,                                  # number of parameter settings that are sampled
    scoring="accuracy",                         # evaluation metric
    cv=3,                                       # number of cross-validation folds
    n_jobs=-1,                                  # use all available cpu cores
    verbose=1,                                  # shows progress
    random_state=66)


print("Starting training...")            # Train the model with hyperparameter tuning
search.fit(X_train, y_train)               


best = search.best_estimator_                   # best model from the search
print("Best params:", search.best_params_)

# Testen
y_pred = best.predict(X_test)
print("Test accuracy:", accuracy_score(y_test, y_pred))
print("Classification report:\n", classification_report(y_test, y_pred))

# Speichern
joblib.dump(best, "ml_model.joblib")
print("Saved model to ml_model.joblib")



