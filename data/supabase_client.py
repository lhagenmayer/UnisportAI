import streamlit as st
from st_supabase_connection import SupabaseConnection

def supaconn():
    conn = st.connection("supabase",type=SupabaseConnection)
    return conn

def angebote():
    conn = supaconn()
    result = conn.table("sportangebote").select("*").execute()
    return result.data

def kurse_mit_angeboten():
    conn = supaconn()
    result = conn.table("sportkurse").select("*, sportangebote(name)").execute()
    return result.data

def kurse():
    conn = supaconn()
    result = conn.table("sportkurse").select("*").execute()
    return result.data

def termine():
    conn = supaconn()
    result = conn.table("kurs_termine").select("*").execute()
    return result.data

def standorte():
    conn = supaconn()
    result = conn.table("unisport_locations").select("*").execute()
    return result.data

def trainer():
    conn = supaconn()
    result = conn.table("trainer").select("*").execute()
    return result.data

def kurs_trainer():
    conn = supaconn()
    result = conn.table("kurs_trainer").select("*").execute()
    return result.data

def datum_scrape():
    conn = supaconn()
    result = conn.table("etl_runs").select("*").execute()
    return result.data