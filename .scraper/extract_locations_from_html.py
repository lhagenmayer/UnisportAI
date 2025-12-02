# This script gets location data from the Unisport website
# Websites store data in different ways: this one has location data
# in two places: JavaScript code and HTML menus
# Our job is to combine both sources to get complete information about each location

import os
import re
import html
import requests
from bs4 import BeautifulSoup

# The website URL where we get the location data
# We found this URL by looking at the Unisport website
SOURCE_URL = "https://www.sportprogramm.unisg.ch/unisg/cgi/webpage.cgi?orte"


# Function to get the HTML from a website
# We use the requests library to download web pages
# The User-Agent header makes us look like a normal browser (some websites block scripts that don't have this)
# timeout=30 means we wait up to 30 seconds for the page to load
def fetch_html(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    # raise_for_status() checks if the request was successful
    # If the website returned an error (like 404), this will stop the script
    response.raise_for_status()
    # Return the HTML as text so we can search through it
    return response.text


# Function to find the markers in the HTML
# The website stores location coordinates in JavaScript code
# It looks like: var markers=[[47.42901,9.38402,"Athletik Zentrum"], ...];
# We need to extract this data and convert it to a format we can use
def parse_markers(html_text):
    # Use regular expressions to find the markers array
    # The pattern looks for "var markers=" followed by an array
    # re.S means "dot matches newline": this is needed because the array might span multiple lines
    pattern = r"var\s+markers\s*=\s*\[(.*?)\];"
    match = re.search(pattern, html_text, re.S)
    if not match:
        # If we can't find the markers, return empty list
        return []
    
    # match.group(1) gets the content inside the brackets
    # This is the actual array data
    content = match.group(1)
    
    # Split by "],[" to separate each marker entry
    # Each entry is one location with its coordinates
    items = content.split("],[")
    
    result = []
    for item in items:
        # Clean up the item: remove extra brackets and spaces
        item = item.strip()
        if item.startswith("["):
            item = item[1:]
        if item.endswith("]"):
            item = item[:-1]
        
        # Now we need to split by comma, but it's tricky because names might contain commas
        # For example: "Athletik Zentrum, Gymnastikraum" has a comma in the name
        # So we need to be smart about splitting: only split commas that are NOT inside quotes
        parts = []
        current_part = ""
        inside_quotes = False
        
        # Go through each character and build the parts
        for char in item:
            # If we see a quote, we're either entering or leaving a quoted section
            if char == '"':
                inside_quotes = not inside_quotes
                current_part += char
            # If we see a comma and we're NOT inside quotes, this is a real separator
            elif char == ',' and not inside_quotes:
                # Save the part we've built so far
                parts.append(current_part.strip())
                # Start a new part
                current_part = ""
            else:
                # Just add the character to the current part
                current_part += char
        
        # Don't forget the last part (after the last comma)
        if current_part:
            parts.append(current_part.strip())
        
        # Each marker should have at least 3 parts: latitude, longitude, and name
        # If it doesn't, skip it (it's probably corrupted data)
        if len(parts) < 3:
            continue
        
        # Try to convert the parts to the right format
        try:
            # Parts 0 and 1 are numbers (coordinates)
            lat = float(parts[0])
            lng = float(parts[1])
            # Part 2 is the location name (text)
            name = parts[2].strip()
            # Remove quotes if they're still there
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            # Add to our result list as a dictionary
            result.append({"name": name, "lat": lat, "lng": lng})
        except:
            # If conversion fails (maybe the coordinates aren't numbers), skip this marker
            continue
    
    return result


# Function to get the sports for each location from the menu
# The website has a menu that shows which sports are offered at each location
# We need to parse this HTML menu to extract that information
def parse_location_sports(html_content):
    # We'll build a dictionary: location name maps to list of sports
    mapping = {}
    # BeautifulSoup helps us parse HTML: it's like a magnifying glass for HTML
    soup = BeautifulSoup(html_content, "lxml")
    
    # Find the menu using CSS selectors
    # "div.bs_flmenu > ul" means: find a div with class "bs_flmenu", then find its direct child ul
    menu = soup.select_one("div.bs_flmenu > ul")
    if not menu:
        # If there's no menu, return empty dictionary
        return mapping
    
    # Go through each location in the menu
    # recursive=False means we only look at direct children, not nested items
    for li in menu.find_all("li", recursive=False):
        # Each location has a span with class "bs_spname" that contains the name
        name_element = li.select_one("span.bs_spname")
        if not name_element:
            # Skip if we can't find the name
            continue
        
        # Get the text and unescape HTML entities (like &#228; becomes ä)
        # This is important because the website uses HTML encoding
        location_name = html.unescape(name_element.get_text(strip=True))
        
        # Now find all the sports listed under this location
        # The sports are in links inside nested lists
        sports = []
        for link in li.select("ul > li > a"):
            sport_name = html.unescape(link.get_text(strip=True))
            # Only add if it's not empty and not the same as the location name
            if sport_name and sport_name != location_name:
                sports.append(sport_name)
        
        # Store the mapping
        mapping[location_name] = sports
    
    return mapping


# Function to get the links and IDs for each location
# Each location has a link to its detail page, and the link contains an ID (spid)
# We need to extract both the full URL and the ID from the link
def parse_location_links(html_content, base_url=None):
    from urllib.parse import urljoin, urlparse, parse_qs
    
    # Result will be: location name maps to {"href": full_url, "spid": id}
    result = {}
    soup = BeautifulSoup(html_content, "lxml")
    
    # Find the same menu as before
    menu = soup.select_one("div.bs_flmenu > ul")
    if not menu:
        return result
    
    # If no base URL is provided, use the default one
    # This is needed because links on the page might be relative (like "../page.html")
    # We need to convert them to absolute URLs (like "https://example.com/page.html")
    if base_url is None:
        base_url = "https://www.sportprogramm.unisg.ch/unisg/angebote/aktueller_zeitraum/"
    
    # Go through each location
    for li in menu.find_all("li", recursive=False):
        # Get location name (same as before)
        name_element = li.select_one("span.bs_spname")
        if not name_element:
            continue
        
        location_name = html.unescape(name_element.get_text(strip=True))
        
        # Find the link element
        # "a[href]" means: find an anchor tag that has an href attribute
        link_element = li.select_one("a[href]")
        full_href = None
        spid = None
        
        if link_element:
            # Get the href attribute (the link address)
            href = link_element.get("href")
            if href:
                # Convert relative URL to absolute URL
                # urljoin combines the base URL with the relative path
                full_href = urljoin(base_url, href)
                
                # Now extract the spid from the URL
                # URLs can have query parameters like: ?spid=123&other=value
                # We want to get the spid value
                try:
                    # urlparse splits the URL into parts
                    parsed_url = urlparse(full_href)
                    # parse_qs extracts the query parameters as a dictionary
                    query_params = parse_qs(parsed_url.query)
                    # Check if spid exists in the parameters
                    if "spid" in query_params:
                        # parse_qs returns lists, so we take the first element
                        spid = query_params["spid"][0]
                except:
                    # If something goes wrong, just set spid to None
                    spid = None
        
        # Store the result
        result[location_name] = {"href": full_href, "spid": spid}
    
    return result


# Function to find a similar name (for when names don't match exactly)
# Sometimes the same location has slightly different names in different parts of the website
# For example: "Athletik Zentrum" vs "Athletik Zentrum" (with different spacing)
# This function uses "fuzzy matching" to find the best match
def fuzzy_match_name(target, candidates, threshold=0.85):
    from difflib import SequenceMatcher
    
    # Convert to lowercase and remove extra spaces for comparison
    # This makes matching more reliable (case-insensitive)
    target_lower = target.strip().lower()
    best_match = None
    best_score = 0.0
    
    # Try each candidate and see which one is most similar
    for candidate in candidates:
        candidate_lower = candidate.strip().lower()
        # SequenceMatcher compares two strings and gives a score from 0.0 to 1.0
        # 1.0 means identical, 0.0 means completely different
        # ratio() gives us the similarity score
        similarity = SequenceMatcher(None, target_lower, candidate_lower).ratio()
        # Keep track of the best match we've found so far
        if similarity > best_score:
            best_score = similarity
            best_match = candidate
    
    # Only return a match if it's similar enough
    # threshold=0.85 means at least 85% similar
    # If the best match isn't good enough, return None (no match found)
    if best_score >= threshold:
        return best_match
    return None


def extract_locations(use_cached: bool = False, cached_file: str | None = None):
    """
    Extrahiert Locations (Name, Koordinaten, Links, SPID) von der
    Unisport-Webseite und gibt eine Liste von Dictionaries zurück:
        {
            \"name\": str,
            \"lat\": float | None,
            \"lng\": float | None,
            \"ort_href\": str | None,
            \"spid\": str | None,
        }

    Diese Funktion ist so gebaut, dass sie im produktiven Scraper
    wiederverwendet werden kann. `use_cached` und `cached_file` sind
    nur für lokale Debug-Zwecke gedacht.
    """
    # Optional: HTML aus Cache lesen (nur für lokale Tests)
    if use_cached and cached_file and os.path.exists(cached_file):
        print("Using cached HTML file")
        with open(cached_file, 'r', encoding='utf-8') as f:
            html_text = f.read()
    else:
        # Produktiver Standard: direkt von der Website laden
        print("Fetching locations HTML from website...")
        html_text = fetch_html(SOURCE_URL)

    # Now extract all the data from the HTML
    # We have three different sources of information:
    # 1. Markers: coordinates and names from JavaScript
    markers = parse_markers(html_text)
    # 2. Location sports: which sports are offered at each location (from the menu)
    loc_to_sports = parse_location_sports(html_text)
    # 3. Location links: URLs and IDs for each location (also from the menu)
    loc_links = parse_location_links(html_text)
    
    # Print debug information to see what we found
    # This helps us understand if our parsing is working correctly
    print("\n=== DEBUG INFO ===")
    print("Markers found:", len(markers))
    print("First 5 marker names:", [m['name'] for m in markers[:5]])
    print("Location sports count:", len(loc_to_sports))
    print("First 5 location names:", list(loc_to_sports.keys())[:5])
    print("Location links count:", len(loc_links))
    print("First 5 link names:", list(loc_links.keys())[:5])
    print("=================\n")
    
    # Now we need to combine all the data
    # The challenge is that the same location might appear in multiple sources
    # We need to match them up and merge the information
    merged = []
    seen_names = set()  # Keep track of names we've already processed (to avoid duplicates)
    fuzzy_matches = []  # Track when we used fuzzy matching (debug only)
    exact_matches = 0   # Count how many exact matches we found (debug only)
    
    # Process markers first (these have coordinates)
    for marker in markers:
        name = str(marker["name"])
        # Skip if we've already seen this name
        if name in seen_names:
            continue
        seen_names.add(name)
        
        # Try to find matching link data
        # First try exact match (same name)
        link_data = loc_links.get(name, {})
        if link_data:
            exact_matches += 1
        else:
            # If exact match fails, try fuzzy matching
            # This handles cases where names are slightly different
            fuzzy_match = fuzzy_match_name(name, list(loc_links.keys()))
            if fuzzy_match:
                fuzzy_matches.append((name, fuzzy_match))
                print("Fuzzy match found:", name, "->", fuzzy_match)
                link_data = loc_links.get(fuzzy_match, {})
        
        # Add to merged list with all the information we have
        merged.append({
            "name": name,
            "lat": marker["lat"],
            "lng": marker["lng"],
            "ort_href": link_data.get("href") if link_data else None,
            "spid": link_data.get("spid") if link_data else None,
        })
    
    # Also add locations that are only in the menu (not in markers)
    # These locations don't have coordinates, but they might have other information
    menu_only = []
    for name, sports in loc_to_sports.items():
        if name not in seen_names:
            menu_only.append(name)
            link_info = loc_links.get(name, {})
            merged.append({
                "name": name,
                "lat": None,  # No coordinates available
                "lng": None,  # No coordinates available
                "ort_href": link_info.get("href") if link_info else None,
                "spid": link_info.get("spid") if link_info else None,
            })

    return merged


def main():
    """
    Lokaler Debug-Einstieg: ruft extract_locations() auf und gibt
    einige Statistiken auf der Konsole aus. Für die produktive
    Pipeline sollte nur extract_locations() importiert und verwendet
    werden.
    """
    merged = extract_locations(use_cached=False)

    print("\n=== MERGE RESULTS ===")
    print("Total merged locations:", len(merged))
    print("=================\n")

    # Show sample entries
    print("\n=== SAMPLE ENTRIES ===")
    for i in range(min(5, len(merged))):
        entry = merged[i]
        print(i + 1, ".", entry['name'])
        print("   Coords: (", entry['lat'], ",", entry['lng'], ")")
        print("   Href:", entry['ort_href'])
        print("   SPID:", entry['spid'])


if __name__ == "__main__":
    main()

# Academic Integrity Notice:
# This file was developed by AI-based tools (Cursor and Github Copilot).
# All code was reviewed, validated, and modified by the author.
