# This script gets all sport offers, courses, and course dates from the Unisport website
# and saves them to the database

import os
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
import re
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv

# Location extraction (name + coordinates + links) from separate helper module
from extract_locations_from_html import extract_locations


# Function to get HTML from a website
def fetch_html(url):
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Create a session and disable SSL verification (needed for some websites)
    session = requests.Session()
    session.verify = False
    
    response = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    return response.text


# Function to get all sport offers from the main page
def extract_offers(source):
    # Offers we don't want to include
    excluded = ["alle freien Kursplätze dieses Zeitraums"]
    
    # Check if it's a URL or a file path
    if source.startswith("http://") or source.startswith("https://"):
        base_url = source
        html = fetch_html(source)
    else:
        base_url = ""
        with open(source, "r", encoding="utf-8") as f:
            html = f.read()
    
    soup = BeautifulSoup(html, "lxml")
    
    offers = []
    seen_hrefs = set()
    
    # Find all links in the menu
    for link in soup.select("dl.bs_menu dd a"):
        name = link.get_text(strip=True)
        href = link.get("href")
        
        if not name or not href:
            continue
        
        # Skip excluded offers
        if name in excluded:
            continue
        
        # Make full URL
        full_href = urljoin(base_url, href)
        
        # Skip if we already have this one
        if full_href in seen_hrefs:
            continue
        
        seen_hrefs.add(full_href)
        offers.append({"name": name, "href": full_href})
    
    return offers


# Function to get all courses for one offer
def extract_courses_for_offer(offer):
    href = offer["href"]
    name = offer["name"]
    
    if not (href.startswith("http://") or href.startswith("https://")):
        return []
    
    html = fetch_html(href)
    soup = BeautifulSoup(html, "lxml")
    
    # Find the course table
    table = soup.select_one("table.bs_kurse")
    if not table:
        return []
    
    tbody = table.find("tbody")
    if not tbody:
        tbody = table
    
    courses = []
    
    # Go through each row in the table
    for row in tbody.select("tr"):
        # Helper function to get text from a cell
        def get_cell_text(selector):
            cell = row.select_one(selector)
            if cell:
                return cell.get_text(" ", strip=True)
            return ""
        
        kursnr = get_cell_text("td.bs_sknr")
        if not kursnr:
            continue
        
        details = get_cell_text("td.bs_sdet")
        tag = get_cell_text("td.bs_stag")
        zeit = get_cell_text("td.bs_szeit")
        
        # Get location info
        ort_cell = row.select_one("td.bs_sort")
        ort = ""
        ort_href = None
        if ort_cell:
            ort = ort_cell.get_text(" ", strip=True)
            ort_link = ort_cell.select_one("a")
            if ort_link and ort_link.get("href"):
                ort_href = urljoin(href, ort_link.get("href"))
        
        # Get link to course dates page
        zr_cell = row.select_one("td.bs_szr")
        zeitraum_href = None
        if zr_cell:
            zr_link = zr_cell.select_one("a")
            if zr_link and zr_link.get("href"):
                zeitraum_href = urljoin(href, zr_link.get("href"))
        
        leitung = get_cell_text("td.bs_skl")
        preis = get_cell_text("td.bs_spreis")
        
        buch_cell = row.select_one("td.bs_sbuch")
        buchung = ""
        if buch_cell:
            buchung = buch_cell.get_text(" ", strip=True)
        
        # Store course data
        # Fields starting with _ are temporary and not saved to database
        course_data = {
            "offer_href": href,
            "kursnr": kursnr,
            "details": details,
            "zeitraum_href": zeitraum_href,
            "preis": preis,
            "buchung": buchung,
            "_offer_name": name,  # temporary field
            "_leitung": leitung,  # temporary field
        }
        courses.append(course_data)
    
    return courses


# Function to get image and description for an offer
def extract_offer_metadata(offer):
    href = offer["href"]
    if not (href.startswith("http://") or href.startswith("https://")):
        return {}
    
    html = fetch_html(href)
    soup = BeautifulSoup(html, "lxml")
    
    result = {}
    
    # Find the title
    title_element = soup.find("h1")
    if not title_element:
        title_element = soup.find("div", class_="bs_head")
    
    # Find image after title
    if title_element:
        img_tag = None
        current = title_element.find_next_sibling()
        
        while current and current.name != "table":
            if current.name == "img":
                img_tag = current
                break
            if hasattr(current, 'find_all'):
                img = current.find("img")
                if img and img.get("src"):
                    img_src = img.get("src")
                    if "logo" not in img_src.lower() and "icon" not in img_src.lower():
                        img_tag = img
                        break
            current = current.find_next_sibling()
        
        if img_tag and img_tag.get("src"):
            img_src = img_tag.get("src")
            if "logo" not in img_src.lower() and "icon" not in img_src.lower():
                result["image_url"] = urljoin(href, img_src)
    
    # Find description paragraphs
    paragraphs = []
    if title_element:
        current = title_element
        while current:
            current = current.next_sibling
            
            if current and hasattr(current, 'name') and current.name == "table":
                break
            
            if current and hasattr(current, 'name') and current.name == "p":
                paragraphs.append(str(current))
            
            if current and hasattr(current, 'find_all'):
                for p in current.find_all("p"):
                    paragraphs.append(str(p))
    
    # Remove duplicates
    unique_paragraphs = []
    seen = set()
    for p in paragraphs:
        if p not in seen:
            unique_paragraphs.append(p)
            seen.add(p)
    
    if unique_paragraphs:
        result["description"] = "\n".join(unique_paragraphs)
    
    return result


# Function to split trainer names (they are separated by commas)
def extract_trainer_names(leitung):
    if not leitung or not leitung.strip():
        return []
    
    # Split by comma and remove extra spaces
    names = []
    for name in leitung.split(","):
        name = name.strip()
        if name:
            names.append(name)
    
    return names


# Function to parse time ranges like "16:10 - 17:40" or "440-100" into start/end times
def parse_time_range(zeit_txt):
    """
    Supported examples:
    - "16:10 - 17:40"
    - "16.10-17.40"
    - "440-100"  (interpreted as 04:40-01:00)
    """
    if not zeit_txt or not zeit_txt.strip():
        return None, None

    # Split at the dash into start and end part
    parts = zeit_txt.split("-")
    if len(parts) != 2:
        return None, None

    def parse_part(part):
        # Keep only digits (removes ":" or ".")
        digits = re.sub(r"[^0-9]", "", part)
        if len(digits) < 3:
            return None
        # Last two digits are minutes, the rest are hours
        hour = int(digits[:-2])
        minute = int(digits[-2:])
        return f"{hour:02d}:{minute:02d}:00"

    start_time = parse_part(parts[0])
    end_time = parse_part(parts[1])

    if not start_time:
        return None, None

    return start_time, end_time


# Function to get all dates for a course
def extract_course_dates(kursnr, zeitraum_href):
    html = fetch_html(zeitraum_href)
    soup = BeautifulSoup(html, "lxml")
    
    table = soup.select_one("table.bs_kurse")
    if not table:
        return []
    
    dates = []
    
    # Go through each row in the table
    for row in table.select("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        
        # Get data from cells
        wochentag = cells[0].get_text(" ", strip=True)
        datum_raw = cells[1].get_text(" ", strip=True)
        zeit_txt = cells[2].get_text(" ", strip=True)
        ort_cell = cells[3]
        ort_txt = ort_cell.get_text(" ", strip=True)
        
        # Get location link if available
        ort_link = ort_cell.find("a")
        ort_href = None
        if ort_link and ort_link.get("href"):
            ort_href = urljoin(zeitraum_href, ort_link.get("href"))
        
        # Convert date to ISO format
        try:
            date_obj = datetime.strptime(datum_raw, "%d.%m.%Y")
            datum_iso = date_obj.date().isoformat()
        except:
            continue
        
        # Parse time range
        start_time, end_time = parse_time_range(zeit_txt)
        
        location_name = ort_txt.strip()
        if not location_name:
            location_name = None
        
        # Skip if we couldn't parse the time
        if not start_time:
            print("Could not parse time for", kursnr, "on", datum_iso, "- skipping")
            continue
        
        # Combine date and time
        start_timestamp = datum_iso + "T" + start_time
        end_timestamp = None
        if end_time:
            end_timestamp = datum_iso + "T" + end_time
        
        dates.append({
            "kursnr": kursnr,
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "ort_href": ort_href,
            "location_name": location_name,
        })
    
    return dates


def main():
    # Load environment variables
    load_dotenv()
    
    # =========================================================================
    # STEP 1: Get all offers from the website
    # =========================================================================
    html_source = "https://www.sportprogramm.unisg.ch/unisg/angebote/aktueller_zeitraum/index.html"
    offers = extract_offers(html_source)
    
    # Connect to database
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("Please set SUPABASE_URL and SUPABASE_KEY in the environment.")
        return
    
    supabase = create_client(supabase_url, supabase_key)

    # =========================================================================
    # STEP 2: Update locations table (unisport_locations)
    # =========================================================================
    # Important for:
    # - Analytics (Top 10 locations, Indoor/Outdoor)
    # - Validation of kurs_termine.location_name
    # If this step fails, the entire scraper run should fail in CI,
    # so that the problem does not go unnoticed.
    try:
        locations = extract_locations()
        if locations:
            # Only take relevant fields for the unisport_locations table
            rows = []
            for loc in locations:
                rows.append(
                    {
                        "name": loc.get("name"),
                        "lat": loc.get("lat"),
                        "lng": loc.get("lng"),
                        "ort_href": loc.get("ort_href"),
                        "spid": loc.get("spid"),
                        # indoor_outdoor remains optional and can be added later
                    }
                )
            supabase.table("unisport_locations").upsert(
                rows, on_conflict="name"
            ).execute()
            print("Supabase:", len(rows), "locations saved")
        else:
            # Empty result list is a hard error for the production pipeline,
            # because then all location-related analytics would run into the void.
            print("Error: No locations extracted from website - aborting scraper run.")
            sys.exit(1)
    except Exception as e:
        # In case of error, abort with exit code != 0, so the GitHub Action run fails.
        print("Error: Failed to update locations:", e)
        sys.exit(1)
    
    # =========================================================================
    # STEP 3: Save offers to database
    # =========================================================================
    supabase.table("sportangebote").upsert(offers, on_conflict="href").execute()
    print("Supabase:", len(offers), "offers saved")
    
    # Get images and descriptions for each offer
    updated_count = 0
    for offer in offers:
        metadata = extract_offer_metadata(offer)
        if metadata:
            update_data = {
                "href": offer["href"],
                "name": offer["name"]
            }
            if "image_url" in metadata:
                update_data["image_url"] = metadata["image_url"]
            if "description" in metadata:
                update_data["description"] = metadata["description"]
            supabase.table("sportangebote").upsert(update_data, on_conflict="href").execute()
            updated_count += 1
    print("Supabase: Images and descriptions updated for", updated_count, "offers")
    
    # Get all courses for all offers
    all_courses = []
    for offer in offers:
        courses = extract_courses_for_offer(offer)
        all_courses.extend(courses)
    
    # Remove temporary fields (starting with _) before saving
    courses_for_db = []
    for course in all_courses:
        course_clean = {}
        for key, value in course.items():
            if not key.startswith("_"):
                course_clean[key] = value
        courses_for_db.append(course_clean)
    
    # Save courses to database
    supabase.table("sportkurse").upsert(courses_for_db, on_conflict="kursnr").execute()
    print("Supabase:", len(courses_for_db), "courses saved")
    
    # Extract trainer names and save them
    trainer_to_courses = {}
    
    for course in all_courses:
        leitung = course.get("_leitung", "")
        if leitung:
            leitung = leitung.strip()
            if leitung:
                trainer_names = extract_trainer_names(leitung)
                for trainer_name in trainer_names:
                    if trainer_name not in trainer_to_courses:
                        trainer_to_courses[trainer_name] = []
                    trainer_to_courses[trainer_name].append(course["kursnr"])
    
    # Save trainers
    all_trainers = []
    for trainer_name in trainer_to_courses.keys():
        all_trainers.append({"name": trainer_name})
    
    if all_trainers:
        supabase.table("trainer").upsert(all_trainers, on_conflict="name").execute()
        print("Supabase:", len(all_trainers), "trainers saved")
    
    # Save course trainer relationships
    kurs_trainer_rows = []
    for trainer_name, kursnrs in trainer_to_courses.items():
        for kursnr in kursnrs:
            kurs_trainer_rows.append({"kursnr": kursnr, "trainer_name": trainer_name})
    
    if kurs_trainer_rows:
        # Delete old relationships first
        kursnrs_to_update = []
        for course in all_courses:
            kursnrs_to_update.append(course["kursnr"])
        for kursnr in kursnrs_to_update:
            supabase.table("kurs_trainer").delete().eq("kursnr", kursnr).execute()
        # Insert new relationships
        supabase.table("kurs_trainer").insert(kurs_trainer_rows).execute()
        print("Supabase:", len(kurs_trainer_rows), "course-trainer relationships saved")
    
    # Get all course dates
    all_dates = []
    for course in all_courses:
        if course.get("zeitraum_href") and course.get("kursnr"):
            dates = extract_course_dates(course["kursnr"], course["zeitraum_href"])
            all_dates.extend(dates)
    
    if all_dates:
        # Check which location names are valid
        loc_resp = supabase.table("unisport_locations").select("name").execute()
        valid_names = set()
        if loc_resp.data:
            for r in loc_resp.data:
                name = r.get("name")
                if name:
                    valid_names.add(name.strip())
        
        # Set invalid location names to None
        for row in all_dates:
            ln = row.get("location_name")
            if ln:
                ln = ln.strip()
                if ln not in valid_names:
                    row["location_name"] = None
            else:
                row["location_name"] = None
        
        # Load existing canceled status
        existing_canceled = {}
        kursnrs_set = set()
        for row in all_dates:
            kursnrs_set.add(row["kursnr"])
        
        for kursnr in kursnrs_set:
            resp = supabase.table("kurs_termine").select("kursnr, start_time, canceled").eq("kursnr", kursnr).execute()
            if resp.data:
                for term in resp.data:
                    key = (term["kursnr"], term["start_time"])
                    existing_canceled[key] = term.get("canceled", False)
        
        # Set canceled status
        for row in all_dates:
            key = (row["kursnr"], row["start_time"])
            if key in existing_canceled:
                row["canceled"] = existing_canceled[key]
            else:
                row["canceled"] = False
        
        # Save dates to database
        supabase.table("kurs_termine").upsert(all_dates, on_conflict="kursnr,start_time").execute()
        print("Supabase:", len(all_dates), "dates saved")
    else:
        print("Note: No dates found")
    
    # Log that we ran
    try:
        supabase.table("etl_runs").insert({"component": "scrape_sportangebote"}).execute()
    except:
        pass

if __name__ == "__main__":
    main()

# Academic Integrity Notice:
# This file was developed by AI-based tools (Cursor and Github Copilot).
# All code was reviewed, validated, and modified by the author.
