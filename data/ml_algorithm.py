import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
import joblib


data = pd.read_excel('Sportangebot_ML_ready.xlsx')  # Read data from Excel file


print(data.head(10))  # Show columns of the data

target_column = 'Angebot'   # This will be the target variable we want to predict
start_column = 'Focus 1'    # This is the first feature column
end_column = 'Focus 5'      # This is the last feature column
model_path = 'ml_model.joblib'  # Path to save/load the model

# specify features explicitly (edit list to match your sheet)
featured_columns = ['endurance', 'relaxation', 'intesity', 'setting_gruppe_fun', 'setting_gruppe_competitive', 'setting_gruppe_teamsport', 'setting_ort_indoor', 'setting_ort_outdoor', ' standort_campus_off_campus', 'standort_campus_on_campus']

print("using featured columns: ", featured_columns)





