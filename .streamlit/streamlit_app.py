import streamlit as st
from typing import Any, Dict, List, Optional

# Diese App zeigt die in Supabase gespeicherten Daten (Angebote, Kurse, Termine) an.
# Wichtige Idee: Wir verbinden Streamlit mit Supabase über die offizielle Connection
# ("st-supabase-connection"). Die Zugangsdaten kommen aus `.streamlit/secrets.toml`.
#
# Tipp: In `requirements.txt` muss `st-supabase-connection` stehen, sonst kennt
# Streamlit diesen Connection-Typ nicht.


def get_supabase_conn() -> Any:
    """
    Baut eine Streamlit-Connection zu Supabase auf.

    Erwartete Keys in `.streamlit/secrets.toml` unter [connections.supabase]:
    - Bevorzugt: url, key
    - Alternativ: SUPABASE_URL, SUPABASE_KEY
    Die Connection liest automatisch aus secrets; wir übergeben ggf. Fallbacks.
    """
    # Schritt 1: Secrets lesen. Wir erwarten in `.streamlit/secrets.toml` einen Block
    # [connections.supabase] mit `url` und `key` (oder alternativ SUPABASE_URL/KEY).
    secrets = st.secrets.get("connections", {}).get("supabase", {})
    # Unterstütze beide Schreibweisen, damit Einsteiger weniger Fehlerquellen haben.
    url = secrets.get("url") or secrets.get("SUPABASE_URL")
    key = secrets.get("key") or secrets.get("SUPABASE_KEY")

    # Wenn url/key fehlen, trotzdem versuchen, da die Connection sie ggf. selbst liest
    # Schritt 2: Connection herstellen.
    # - Wenn wir url/key haben, geben wir sie explizit mit.
    # - Sonst überlässt Streamlit das Laden den Secrets (falls korrekt hinterlegt).
    if url and key:
        return st.connection(
            "supabase",
            type="st_supabase_connection.SupabaseConnection",
            url=url,
            key=key,
        )
    return st.connection("supabase", type="st_supabase_connection.SupabaseConnection")


def safe_query(conn: Any, table: str, select: str = "*") -> List[Dict[str, Any]]:
    # Diese Funktion kapselt das Lesen aus einer Tabelle.
    # Warum? So bricht die App nicht komplett ab, wenn etwas schiefgeht –
    # stattdessen zeigen wir eine Warnung und eine leere Liste.
    try:
        # Die Streamlit-Connection stellt einen Supabase-Client unter `conn.client` bereit.
        client = getattr(conn, "client", None)
        if client is None:
            raise RuntimeError("Supabase-Client nicht verfügbar (conn.client ist None)")
        # Standardabfrage: SELECT <spalten> FROM <table>
        resp = client.table(table).select(select).execute()
        return resp.data or []
    except Exception as e:
        # Für Einsteiger: Fehler sichtbar machen, aber die App läuft weiter.
        st.warning(f"Fehler beim Laden aus {table}: {e}")
        return []


def main() -> None:
    # Seiten-Layout und Titel für die App festlegen.
    # layout="wide" gibt mehr Platz für Tabellen.
    st.set_page_config(page_title="UnisportAI", layout="wide")
    # Visueller Header als Collage mit HSG-Bildern und Overlay-Text (größerer Banner)
    st.markdown(
        """
        <div style="position: relative; height: 280px; border-radius: 10px; overflow: hidden; margin-bottom: 0.5rem;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 4px; height: 100%;">
            <div style="background-image:url('https://www.unisg.ch/fileadmin/_processed_/5/c/csm_HSG_Bibliothek_1_182bdcd9cf.jpg'); background-size:cover; background-position:center;"></div>
            <div style="background-image:url('https://www.unisg.ch/fileadmin/_processed_/e/f/csm_HSG_Hauptgebaeude_2_e959f946be.jpg'); background-size:cover; background-position:center;"></div>
            <div style="background-image:url('https://www.unisg.ch/fileadmin/_processed_/d/2/csm_HSG_SQUARE_1_43e4002cea.jpg'); background-size:cover; background-position:center;"></div>
            <div style="background-image:url('https://www.unisg.ch/fileadmin/_processed_/3/c/csm_HSG_SQUARE_2_2426171a5d.jpg'); background-size:cover; background-position:center;"></div>
          </div>
          <div style="position:absolute; bottom:12px; left:12px; 
                      background: rgba(0,0,0,0.55); color:#fff; padding:10px 14px; border-radius: 8px; 
                      font-weight: 700; font-size: 22px;">
            UnisportAI – Datenansicht
          </div>
          <div style="position:absolute; bottom:12px; right:12px; 
                      background: rgba(0,0,0,0.55); color:#fff; padding:6px 10px; border-radius: 6px; 
                      font-size: 12px;">
            © Universität St.Gallen (HSG)
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Streamlit + Supabase via st.connection")
    # Kurzer Überblick für Nicht‑Techniker: Was passiert hier?
    st.markdown(
        """
        **Was passiert hier – in einfachen Worten?**

        1. Drei Python‑Skripte scrapen die Unisport‑Webseiten (Angebote, Kurse, Termine, Standorte).
           - Heute starten wir sie noch manuell im Terminal.
           - Bald laufen sie automatisch nach Zeitplan (Schedule) über GitHub.

        2. Die Daten landen in Supabase – das ist unsere gehostete Postgres‑Datenbank.

        3. Diese Streamlit‑App lädt die Daten 1:1 aus Supabase und zeigt sie hier in Tabs an.
           - Oben kannst du nach Name, Kursnummer, Datum oder "canceled" filtern.

        4. Als Nächstes bereiten wir die Daten sinnvoll auf: Analysen, hilfreiche Visualisierungen,
           Entscheidungs‑Dashboards, Kalender‑Integration (iCal‑Export), sowie synthetische Daten und
           ML‑Time‑Series‑Training, um Prognosen zu ermöglichen.
        """
    )

    # Linke Seitenleiste: Team anzeigen, darunter Kurs-Hinweis
    with st.sidebar:
        st.header("Projektteam")
        team = [
            (
                "Tamara Nessler",
                "https://www.linkedin.com/in/tamaranessler/",
                "https://media.licdn.com/dms/image/v2/D4D03AQHoFx3FqbKv8Q/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1729070262001?e=1762387200&v=beta&t=qxTtWz-rqXh2ooOxkLCaODftWKDB-mCnB1Kf6nu4JPU",
            ),
            (
                "Till Banerjee",
                "https://www.linkedin.com/in/till-banerjee/",
                "https://media.licdn.com/dms/image/v2/D4E03AQFL1-Ud8CLN3g/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1708701675021?e=1762387200&v=beta&t=msstC8263pJyCfjiZwNzfYF3l57yHvSpIuMO77A-U0A",
            ),
            (
                "Sarah Bugg",
                "https://www.linkedin.com/in/sarah-bugg/",
                "https://media.licdn.com/dms/image/v2/D4E03AQEanhywBsKAPA/profile-displayphoto-scale_400_400/B4EZkoux6gKkAg-/0/1757324976456?e=1762387200&v=beta&t=Gicl6-C96pUuB2MUNVwbKzctjVaqaQDn39blJxdkjAo",
            ),
            (
                "Antonia Büttiker",
                "https://www.linkedin.com/in/antonia-büttiker-895713254/",
                "https://media.licdn.com/dms/image/v2/D4E03AQHZuEjmbys12Q/profile-displayphoto-shrink_400_400/B4EZVwmujrG0Ak-/0/1741350956527?e=1762387200&v=beta&t=s3ypqYDZ6Od8XU9ktFTwRNnwSHckHmFejMpnn8GdhWg",
            ),
            (
                "Luca Hagenmayer",
                "https://www.linkedin.com/in/lucahagenmayer/",
                "https://media.licdn.com/dms/image/v2/D4E03AQFGdchJCbDXFQ/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1730973343664?e=1762387200&v=beta&t=1awZw8RSI5xBKF9gFxOlFYsNDxGalTcgK3z-Ma8R0qU",
            ),
        ]

        for name, url, avatar in team:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(avatar, width=72)
            with col2:
                st.markdown(f"[{name}]({url})", unsafe_allow_html=True)

        # Hinweis unterhalb der Projektmitglieder
        st.markdown(
            """
            ---
            **Hinweis zur Entstehung:**
            Dieses Projekt und das Projektteam entstanden im Kurs
            „Fundamentals and Methods of Computer Science“ an der Universität St.Gallen,
            geleitet von Prof. Dr. Stephan Aier, Dr. Bernhard Bermeitinger und Prof. Dr. Simon Mayer.

            Status: noch in Entwicklung und (noch) nicht von den Professoren reviewed.

            Feature‑Wünsche oder Bugs? Bitte eines der Teammitglieder via LinkedIn kontaktieren (siehe oben).
            """
        )

    # Supabase-Verbindung herstellen (aus den Secrets)
    conn = get_supabase_conn()

    # UI: Drei Tabs – je eine Tabelle. So bleibt es übersichtlich.
    st.subheader("Tabellen")
    tabs = st.tabs(["sportangebote", "sportkurse", "kurs_termine", "unisport_locations"])  # legacy: kurs_termine

    with tabs[0]:
        # Tab 1: Sportangebote – zeige alle Spalten (1:1 zur DB)
        st.write("Alle Sportangebote")
        data = safe_query(conn, "sportangebote", "*")
        # Einfacher Textfilter: zeigt nur Zeilen, deren Name den Suchbegriff enthält
        search = st.text_input("Filter nach Name…", key="f1")
        if search:
            data = [r for r in data if search.lower() in (r.get("name") or "").lower()]
        # Tabelle in voller Breite anzeigen
        st.dataframe(data, use_container_width=True)

    with tabs[1]:
        # Tab 2: Kurse – alle Spalten anzeigen
        st.write("Alle Kurse")
        data = safe_query(conn, "sportkurse", "*")
        # Zwei nebeneinander liegende Filter-Eingabefelder
        col1, col2 = st.columns(2)
        with col1:
            f_offer = st.text_input("Filter Angebot…", key="f2")
        with col2:
            f_kurs = st.text_input("Filter Kursnr…", key="f3")
        # Optional filtern (Case-insensitive)
        if f_offer:
            data = [r for r in data if f_offer.lower() in (r.get("offer_name") or "").lower()]
        if f_kurs:
            data = [r for r in data if f_kurs.lower() in (r.get("kursnr") or "").lower()]
        st.dataframe(data, use_container_width=True)

    with tabs[2]:
        # Tab 3: Einzeltermine – alle Spalten anzeigen
        st.write("Kurs-Termine (legacy: kurs_termine)")
        data = safe_query(conn, "kurs_termine", "*")
        col1, col2, col3 = st.columns(3)
        with col1:
            f_kurs = st.text_input("Filter Kursnr…", key="f4")
        with col2:
            f_date = st.text_input("Filter Datum (YYYY-MM-DD)…", key="f5")
        with col3:
            # Dieses Häkchen zeigt nur Termine mit canceled=true (also abgesagt)
            canceled_only = st.checkbox("Nur canceled=true", value=False)
        # Optional filtern nach Kursnummer, Datum-Präfix und Absage-Status
        if f_kurs:
            data = [r for r in data if f_kurs.lower() in (r.get("kursnr") or "").lower()]
        if f_date:
            data = [r for r in data if (r.get("datum") or "").startswith(f_date)]
        if canceled_only:
            data = [r for r in data if bool(r.get("canceled"))]
        st.dataframe(data, use_container_width=True)

    with tabs[3]:
        # Tab 4: Standorte – alle Spalten anzeigen
        st.write("Standorte")
        data = safe_query(conn, "unisport_locations", "*")
        f_name = st.text_input("Filter Standortname…", key="f6")
        if f_name:
            data = [r for r in data if f_name.lower() in (r.get("name") or "").lower()]
        st.dataframe(data, use_container_width=True)


if __name__ == "__main__":
    main()