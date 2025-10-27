import streamlit as st
from st_supabase_connection import SupabaseConnection

def supaconn():
    try:
        # Versuche die Verbindung - zuerst über st.connection mit expliziten Parametern
        # Falls Secrets vorhanden sind, lese sie und übergebe direkt
        try:
            # Versuche Secrets zu lesen
            url = st.secrets["connections"]["supabase"]["url"]
            key = st.secrets["connections"]["supabase"]["key"]
            conn = st.connection("supabase", type=SupabaseConnection, url=url, key=key)
            return conn
        except:
            # Falls das nicht funktioniert, versuche die Standard-Verbindung
            conn = st.connection("supabase", type=SupabaseConnection)
            return conn
    except Exception as e1:
        # Fallback: Environment-Variablen als Alternative
        import os
        if "SUPABASE_URL" in os.environ and "SUPABASE_KEY" in os.environ:
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")
            conn = st.connection("supabase", type=SupabaseConnection, url=url, key=key)
            return conn
        else:
            st.error(f"Fehler bei der Supabase-Verbindung: {str(e1)}")
            st.info("Bitte stellen Sie sicher, dass die Supabase-Credentials in .streamlit/secrets.toml (lokal) oder in den Streamlit Cloud Secrets konfiguriert sind.")
            raise

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