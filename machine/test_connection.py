"""test_connection
------------------
Small CLI script to verify Supabase connectivity and the presence
of the ``ml_training_data`` view used by the project's ML
components.

Run this script when you need to confirm that credentials in the
local ``.env`` file are correct and the Supabase view returns data.
"""

import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()
env_path = script_dir / '.env'

print("=" * 60)
print("TESTING SUPABASE CONNECTION")
print("=" * 60)

print(f"\nLooking for .env at: {env_path}")
print(f"File exists: {env_path.exists()}")

# Load environment variables from specific path
load_dotenv(dotenv_path=env_path)

# Connect to Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("❌ ERROR: Missing credentials in .env file")
    print(f"SUPABASE_URL: {supabase_url}")
    print(f"SUPABASE_KEY: {supabase_key}")
    exit(1)

print(f"\n✅ Loaded credentials from .env")
print(f"URL: {supabase_url}")
print(f"Key: {supabase_key[:20]}...{supabase_key[-10:]}")  # Show partial key for security

try:
    supabase = create_client(supabase_url, supabase_key)
    print("\n✅ Supabase client created successfully")
except Exception as e:
    print(f"\n❌ Failed to create Supabase client: {e}")
    exit(1)

print("\n" + "=" * 60)
print("FETCHING DATA FROM ml_training_data VIEW")
print("=" * 60)

try:
    response = supabase.table("ml_training_data").select("*").execute()
    
    if not response.data:
        print("\n❌ No data returned from ml_training_data view")
        exit(1)
    
    print(f"\n✅ Successfully fetched {len(response.data)} records")
    
    # Convert to DataFrame
    data = pd.DataFrame(response.data)
    
    print("\n" + "=" * 60)
    print("DATA PREVIEW")
    print("=" * 60)
    print(f"\nShape: {data.shape} (rows, columns)")
    print(f"\nColumns: {list(data.columns)}")
    print(f"\nData types:\n{data.dtypes}")
    print(f"\nFirst 5 records:")
    print(data.head())
    
    print("\n" + "=" * 60)
    print("DATA QUALITY CHECK")
    print("=" * 60)
    print(f"\nMissing values per column:")
    print(data.isnull().sum())
    
    print(f"\nUnique sports (target variable): {data['Angebot'].nunique()}")
    print(f"Sport names: {list(data['Angebot'].unique()[:10])}...")  # Show first 10
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - READY TO TRAIN!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error fetching data: {e}")
    import traceback
    traceback.print_exc()
    exit(1)