
"""Update cancellations script

This script scrapes a public Unisport webpage for announcements of cancelled
courses and marks matching course sessions in the Supabase database with
``canceled = true``. The cancellation flag is only ever set (true) and is
not reverted to false by this script.

High-level steps:
1. Download a webpage containing cancellation notices.
2. Extract date, course name and start time from the text.
3. Map course names to internal course numbers (``kursnr``) using DB data.
4. Find course sessions on the given date and match by start time.
5. Upsert matching sessions with ``canceled = true`` (idempotent).

Only documentation and non-functional comments are changed in this file.
"""

import os
import re
import subprocess
from typing import List, Dict
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv

# Mini tutorial:
# - Step 1: Load the cancellations page and extract the text (parse_cancellations)
# - Step 2: Convert the date to YYYY-MM-DD, compute the start time as an HHMM number
# - Step 3: Load courses from the DB and build a name→course number mapping
# - Step 4: Fetch dates on the matching day and compare times
# - Step 5: Upsert matches as canceled=true (no duplicates)


def fetch_html(url: str) -> str:
    """Fetch the HTML content for a URL.

    A simple wrapper around ``requests.get`` that sets a browser-like
    ``User-Agent`` header and raises on non-2xx responses.

    Args:
        url (str): The URL to download.

    Returns:
        str: The raw HTML content of the response.
    """
    # Browser-like header so the server treats the request as a normal visitor
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse_cancellations() -> List[Dict[str, str]]:
    """Parse cancellation announcements from the Unisport page.

    The function downloads a known cancellations page, extracts textual
    occurrences that match the pattern "DD.MM.YYYY, <name>, HH:MM" and
    returns a list of dicts with normalized fields.

    Returns:
        List[Dict[str, str]]: Each dict contains keys ``offer_name``,
            ``datum`` (ISO date string) and ``start_hhmm`` (int, e.g. 1815).
    """
    url_cancel = "https://www.unisg.ch/de/universitaet/ueber-uns/beratungs-und-fachstellen/unisport/"
    html = fetch_html(url_cancel)
    if not html:
        return []
    # Extract the textual content of the page
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    pattern = re.compile(r"(\d{2}\.\d{2}\.\d{4})\s*,\s*([^,]+?)\s*,\s*(\d{1,2}[:\.]\d{2})")
    out: List[Dict[str, str]] = []
    for m in pattern.finditer(text):
        date_raw = m.group(1)
        name = m.group(2).strip()
        time_raw = m.group(3).strip()
        try:
            date_iso = datetime.strptime(date_raw, "%d.%m.%Y").date().isoformat()
        except Exception:
            continue
        time_digits = re.sub(r"[^0-9]", "", time_raw)
        if len(time_digits) >= 3:
            start_hhmm = int(time_digits[:2] + time_digits[2:4])
            out.append({"offer_name": name, "datum": date_iso, "start_hhmm": start_hhmm})
    return out


def extract_start_hhmm(zeit_txt: str) -> int:
    """Extract start time from a time range string as an HHMM integer.

    Examples:
        "18:15 - 19:15" -> 1815

    Args:
        zeit_txt (str): Time range string.

    Returns:
        int: HHMM integer or -1 if parsing fails.
    """
    if not zeit_txt:
        return -1
    start_part = zeit_txt.split("-")[0].strip()
    digits = re.sub(r"[^0-9]", "", start_part)
    if len(digits) >= 3:
        return int(digits[:2] + digits[2:4])
    return -1


def main() -> None:
    """Main entry point: find cancellations and upsert canceled flags.

    The function reads environment variables for Supabase credentials,
    parses cancellations from the public page and marks matching course
    sessions as canceled in the database.
    """
    load_dotenv()  # Read SUPABASE_URL and SUPABASE_KEY from .env (if present)
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("Bitte SUPABASE_URL und SUPABASE_KEY als ENV setzen.")
        return
    supabase = create_client(supabase_url, supabase_key)

    cancellations = parse_cancellations()  # list of {offer_name, datum, start_hhmm}
    if not cancellations:
        print("Keine Ausfälle gefunden oder Seite nicht erreichbar.")
        return

    # Mapping course name(lower) -> [kursnr]
    # We fetch offers and courses in bulk from the DB to build offer_name → kursnr
    # offer_name is now in sportangebote, linked via offer_href
    resp = supabase.table("sportkurse").select("kursnr, offer_href").execute()  # Kurse laden
    kurs_rows = resp.data or []
    
    # Load offers for mapping offer_href -> name
    resp_offers = supabase.table("sportangebote").select("href, name").execute()
    offer_mapping = {row["href"]: row["name"] for row in (resp_offers.data or [])}
    
    name_to_kursnrs: Dict[str, List[str]] = {}
    for row in kurs_rows:
        offer_href = row.get("offer_href")
        if not offer_href:
            continue
        # Get offer name from sportangebote
        offer_name = offer_mapping.get(offer_href, "").strip().lower()
        if not offer_name or not row.get("kursnr"):
            continue
        name_to_kursnrs.setdefault(offer_name, []).append(row["kursnr"])

    rows_to_upsert: List[Dict[str, object]] = []
    for canc in cancellations:  # check the cancellations
        key = canc["offer_name"].strip().lower()
        kursnrs = name_to_kursnrs.get(key, [])
        if not kursnrs:
            continue
        
        # Use start_time instead of datum+zeit (new schema)
        # start_time is timestamptz; we only need the date
        resp2 = (
            supabase.table("kurs_termine")
            .select("kursnr, start_time")
            .in_("kursnr", kursnrs)
            .gte("start_time", canc["datum"] + " 00:00:00")
            .lt("start_time", canc["datum"] + " 23:59:59")
            .execute()
        )
        term_rows = resp2.data or []
        
        for tr in term_rows:
            start_time_str = tr.get("start_time", "")
            if start_time_str:
                # Extract hour and minute from start_time
                from datetime import datetime as dt_from_str
                start_dt = dt_from_str.fromisoformat(start_time_str.replace("Z", "+00:00"))
                start_hhmm = start_dt.hour * 100 + start_dt.minute
                
                if start_hhmm == canc["start_hhmm"]:
                    rows_to_upsert.append({"kursnr": tr["kursnr"], "start_time": start_time_str, "canceled": True})

    if rows_to_upsert:
        # Deduplicate
        seen = set()
        uniq: List[Dict[str, object]] = []
        for r in rows_to_upsert:
            k = (r["kursnr"], r["start_time"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        # Schritt 5: Idempotentes Upsert pro (kursnr, start_time)
        supabase.table("kurs_termine").upsert(uniq, on_conflict="kursnr,start_time").execute()
        print(f"Supabase: {len(uniq)} Ausfälle als canceled=true markiert (idempotent).")
    else:
        print("Keine passenden Termine zum Markieren gefunden.")

    # IMPORTANT: canceled flag is only SET, never reset to false
    # The script scrape_sportangebote.py must take the canceled flag into account during upsert
    # (implemented in scrape_sportangebote.py)
    
    # Log ETL run
    try:
        supabase.table("etl_runs").insert({"component": "update_cancellations"}).execute()
    except Exception:
        pass


if __name__ == "__main__":
    main()

# Note (Academic Integrity): The tool "Cursor" was used as a supporting aid
# in the creation of this file.
