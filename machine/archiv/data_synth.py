"""Synthetic data generator for course occupancy (archival).

This helper script creates synthetic training examples intended for
testing and experiments. It queries the project's Supabase instance
for existing course numbers and location ids and then generates a
CSV file named ``training_data.csv`` containing occupancy and
temporal features.

This script is part of the ``archiv/`` folder and is used for
prototyping; it should not be used in production without review.
"""

from supabase import create_client, Client
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

supabaseUrl = 'https://mcbbjvjezbgekbmcajii.supabase.co'
supabaseKey = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(supabaseUrl, supabaseKey)

kurs_response = supabase.table("sportkurse").select("kursnr").execute()
loc_response = supabase.table("unisport_locations").select("id").execute()

kursnummern = [k["kursnr"] for k in kurs_response.data]
location_ids = [l["id"] for l in loc_response.data]

print(f"Kurse gefunden: {len(kursnummern)}, Locations: {len(location_ids)}")

def generate_training_data(n_samples=1000):
    data = []
    
    for _ in range(n_samples):
        datum = datetime.now() + timedelta(days=random.randint(-365, 180))
        wochentag = datum.weekday() + 1  # 1=Monday, 7=Sunday
        monat = datum.month
        uhrzeit = random.randint(6, 22)
        temperatur = random.randint(15, 35) if monat in [5, 6, 7, 8, 9] else random.randint(-5, 20)
        
        # Base load
        auslastung = random.uniform(0.5, 0.9)
        
        # Summer effect (June–September): indoor courses are less attended
        if monat in [6, 7, 8, 9]:
            auslastung *= 0.6
        
        # Winter effect (November–February): more visitors
        if monat in [11, 12, 1, 2]:
            auslastung *= 1.3
        
        # Wednesday: less going on (going out)
        if wochentag == 3:
            auslastung *= 0.7
        
        # Thursday morning (6–11 a.m.): very empty
        if wochentag == 4 and uhrzeit < 12:
            auslastung *= 0.5
        
        # Friday generally empty
        if wochentag == 5:
            auslastung *= 0.6
        
        # Hot days: gym less busy
        if temperatur > 28:
            auslastung *= 0.7

        # Time-of-day effect: evening classes are more popular
        if 8 < uhrzeit < 12:
            auslastung *= 0.3
        elif 12 <= uhrzeit < 13:
            auslastung *= 1.1
        elif uhrzeit >= 18:
            auslastung *= 1.3

        # Limit to 0–1
        auslastung = min(1.0, max(0.1, auslastung))
        teilnehmer = int(auslastung * random.randint(25, 35))
        
        record = {
            'kursnr': random.choice(kursnummern),
            'location_id': random.choice(location_ids),
            'teilnehmer': teilnehmer,
            'auslastung': round(auslastung, 2),
            'wochentag': wochentag,
            'uhrzeit': uhrzeit,
            'monat': monat,
            'temperatur': temperatur,
            'datum': datum.strftime('%Y-%m-%d')
        }
        data.append(record)
    
    return pd.DataFrame(data)

df = generate_training_data(1000)
df.to_csv('training_data.csv', index=False)
print(f"✓ {len(df)} Trainingsbeispiele generiert und gespeichert")
print(df.head())
print(f"\nDurchschnittliche Auslastung: {df['auslastung'].mean():.2f}")
print(f"Auslastung nach Wochentag:\n{df.groupby('wochentag')['auslastung'].mean()}")