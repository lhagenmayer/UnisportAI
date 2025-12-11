# This script checks the Unisport website for cancelled courses
# and marks them as canceled in the database

import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv


# Function to get HTML from a website
def fetch_html(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    return response.text


# Function to get cancellation notices from the website
def parse_cancellations():
    url = "https://www.unisg.ch/de/universitaet/ueber-uns/beratungs-und-fachstellen/unisport/"
    html = fetch_html(url)
    if not html:
        return []
    
    # Get text from the page
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    
    # Find patterns like "DD.MM.YYYY, Name, HH:MM"
    pattern = re.compile(r"(\d{2}\.\d{2}\.\d{4})\s*,\s*([^,]+?)\s*,\s*(\d{1,2}[:\.]\d{2})")
    
    cancellations = []
    for match in pattern.finditer(text):
        date_raw = match.group(1)
        name = match.group(2).strip()
        time_raw = match.group(3).strip()
        
        # Convert date to ISO format
        try:
            date_obj = datetime.strptime(date_raw, "%d.%m.%Y")
            date_iso = date_obj.date().isoformat()
        except:
            continue
        
        # Extract time digits (remove colons/dots)
        time_digits = re.sub(r"[^0-9]", "", time_raw)
        if len(time_digits) >= 3:
            # Convert to HHMM format (e.g., "18:15" becomes 1815)
            start_hhmm = int(time_digits[:2] + time_digits[2:4])
            cancellations.append({"offer_name": name, "datum": date_iso, "start_hhmm": start_hhmm})
    
    return cancellations


# Function to extract start time from a time range (e.g., "18:15 to 19:15" becomes 1815)
def extract_start_hhmm(zeit_txt):
    if not zeit_txt:
        return -1
    
    # Get the part before the dash
    parts = zeit_txt.split("-")
    start_part = parts[0].strip()
    
    # Remove all non-digits
    digits = re.sub(r"[^0-9]", "", start_part)
    
    if len(digits) >= 3:
        return int(digits[:2] + digits[2:4])
    
    return -1


def main():
    # Load environment variables
    load_dotenv()
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("Please set SUPABASE_URL and SUPABASE_KEY as environment variables.")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Get cancellations from website
    cancellations = parse_cancellations()
    if not cancellations:
        print("No cancellations found or page not reachable.")
        return
    
    # Build mapping from offer name to course numbers
    # First get all courses
    resp = supabase.table("sportkurse").select("kursnr, offer_href").execute()
    kurs_rows = resp.data or []
    
    # Get all offers
    resp_offers = supabase.table("sportangebote").select("href, name").execute()
    offer_mapping = {}
    if resp_offers.data:
        for row in resp_offers.data:
            offer_mapping[row["href"]] = row["name"]
    
    # Build name to kursnr mapping
    name_to_kursnrs = {}
    for row in kurs_rows:
        offer_href = row.get("offer_href")
        if not offer_href:
            continue
        
        offer_name = offer_mapping.get(offer_href, "").strip().lower()
        if not offer_name or not row.get("kursnr"):
            continue
        
        if offer_name not in name_to_kursnrs:
            name_to_kursnrs[offer_name] = []
        name_to_kursnrs[offer_name].append(row["kursnr"])
    
    # Find matching course sessions and mark as canceled
    rows_to_upsert = []
    for canc in cancellations:
        key = canc["offer_name"].strip().lower()
        kursnrs = name_to_kursnrs.get(key, [])
        if not kursnrs:
            continue
        
        # Get all sessions for these courses on the cancellation date
        date_str = canc["datum"]
        resp2 = (
            supabase.table("kurs_termine")
            .select("kursnr, start_time")
            .in_("kursnr", kursnrs)
            .gte("start_time", date_str + " 00:00:00")
            .lt("start_time", date_str + " 23:59:59")
            .execute()
        )
        term_rows = resp2.data or []
        
        # Check if start time matches
        for term in term_rows:
            start_time_str = term.get("start_time", "")
            if start_time_str:
                # Convert start_time to HHMM format
                start_dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                start_hhmm = start_dt.hour * 100 + start_dt.minute
                
                if start_hhmm == canc["start_hhmm"]:
                    rows_to_upsert.append({
                        "kursnr": term["kursnr"],
                        "start_time": start_time_str,
                        "canceled": True
                    })
    
    if rows_to_upsert:
        # Remove duplicates
        seen = set()
        uniq = []
        for r in rows_to_upsert:
            k = (r["kursnr"], r["start_time"])
            if k not in seen:
                seen.add(k)
                uniq.append(r)
        
        # Save to database
        supabase.table("kurs_termine").upsert(uniq, on_conflict="kursnr,start_time").execute()
        print("Supabase:", len(uniq), "cancellations marked as canceled=true")
    else:
        print("No matching sessions found to mark")
    
    # Log that we ran
    try:
        supabase.table("etl_runs").insert({"component": "update_cancellations"}).execute()
    except:
        pass


if __name__ == "__main__":
    main()

# Academic Integrity Notice:
# This file was developed by AI-based tools (Cursor and Github Copilot).
# All code was reviewed, validated, and modified by the author.
