"""Extract Unisport location data and persist to Supabase.

This script collects venue/location information from the Unisport website
and writes it into the ``unisport_locations`` table in Supabase. It
combines data from two sources on the page:

1. A JavaScript `markers` array containing coordinates and names.
2. A location menu that contains links (from which a ``spid`` parameter
    can be extracted) and the list of sports offered at each location.

The resulting records contain fields such as ``name``, ``lat``, ``lng``,
``ort_href``, ``spid`` and ``sports``. If Supabase credentials are not
present in the environment the script will only print a summary.
"""
# Mini tutorial:
# - Step 1: We load the website (fetch_html).
# - Step 2: We read coordinates and names from the JS list (parse_markers).
# - Step 3: We read sports per location from the menu (parse_location_sports).
# - Step 4: We read location links and IDs (parse_location_links).
# - Step 5: We merge everything per location (merged).
# - Step 6: We write everything idempotently to Supabase (upsert by name, which is the primary key).

import json
import os
import re
import html  # Add this import
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv
from difflib import SequenceMatcher  # For fuzzy matching

# Explanation of the imports (like "building blocks" in Scratch):
# - json: Converts data to text (JSON) and back. We need it to make lists/objects readable.
# - os: Access to environment variables (e.g., SUPABASE_URL). Like a backpack full of settings.
# - re: "Search & find" in texts using patterns (regular expressions). Like a magnifying glass with a filter.
# - typing (Dict, List, Optional): Only for humans/development tools to describe data types.
# - requests: Load web pages.
# - dotenv: Reads a .env file so we don’t have to write keys/URLs directly into the code.
# - supabase.create_client: The plug to the database. With it we can insert/read/update data.

from bs4 import BeautifulSoup  # type: ignore


# Live source: event venues/rooms

SOURCE_URL = "https://www.sportprogramm.unisg.ch/unisg/cgi/webpage.cgi?orte"
# This is the live page with all event venues. We only read it (no login required).


def fetch_html(url: str) -> str:
    """
    Loads the text of a website using only requests.
    """

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse_markers(html: str) -> List[Dict[str, object]]:
    """
    Extracts marker entries from a JS array literal like:
    var markers=[[47.42901,9.38402,"Athletik Zentrum, Gymnastikraum"], ...];
    Returns list of dicts: {"name": str, "lat": float, "lng": float}
    In the HTML text, we search for a section where coordinates and names
    are stored in a list. Then we extract each entry from it.
    """

    m = re.search(r"var\s+markers\s*=\s*\[(.*?)\];", html, re.S)
    if not m:
        return []
    body = m.group(1)
    # Split top-level arrays; handle "]],[" boundaries robustly
    raw_items = re.split(r"\],\s*\[", body.strip()[1:-1]) if body.strip().startswith("[") else body.split("],[")
    out: List[Dict[str, object]] = []
    for item in raw_items:
        # Normalize quotes and brackets
        item_norm = item.strip().strip("[]")
        parts = []
        current = []
        in_quotes = False
        i = 0
        while i < len(item_norm):
            ch = item_norm[i]
            if ch == '"':
                in_quotes = not in_quotes
                current.append(ch)
            elif ch == ',' and not in_quotes:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(ch)
            i += 1
        if current:
            parts.append(''.join(current).strip())
        if len(parts) < 3:
            continue
        try:
            lat = float(parts[0])
            lng = float(parts[1])
            name = parts[2].strip()
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            out.append({"name": name, "lat": lat, "lng": lng})
        except Exception:
            continue
    return out


def parse_location_sports(html_content: str) -> Dict[str, List[str]]:
    """
    Extract mapping from location name to list of sports using the 'bs_flmenu' menu.
    Returns dict: name -> [sports]
    On the page, there is also a menu where the sports are listed under each location.
    We go through this list and build a dictionary: location → [sports].
    """

    mapping: Dict[str, List[str]] = {}
    soup = BeautifulSoup(html_content, "lxml")
    menu = soup.select_one("div.bs_flmenu > ul")
    if not menu:
        return mapping
    for li in menu.find_all("li", recursive=False):
        name_el = li.select_one("span.bs_spname")
        if not name_el:
            continue
        # Decode HTML entities (&#228; → ä, etc.)
        loc_name = html.unescape(name_el.get_text(strip=True))
        sports: List[str] = []
        for sub in li.select("ul > li > a"):
            sport_name = html.unescape(sub.get_text(strip=True))
            if sport_name:
                sports.append(sport_name)
        mapping[loc_name] = [s for s in sports if s != loc_name]
    return mapping


def parse_location_links(html_content: str, base_url: Optional[str] = None) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Reads the location links (href) from the menu (div.bs_flmenu) and extracts spid.
    Returns: name -> {"href": absolute URL|None, "spid": str|None}
    Idea: Each location also has a link to a detail page. From this link we extract
    the full address (href) and an internal identifier (spid).
    """
    out: Dict[str, Dict[str, Optional[str]]] = {}
    soup = BeautifulSoup(html_content, "lxml")
    menu = soup.select_one("div.bs_flmenu > ul")
    if not menu:
        return out
    effective_base = base_url or "https://www.sportprogramm.unisg.ch/unisg/angebote/aktueller_zeitraum/"
    from urllib.parse import urljoin, urlparse, parse_qs
    for li in menu.find_all("li", recursive=False):
        name_el = li.select_one("span.bs_spname")
        if not name_el:
            continue
        # Decode HTML entities (&#228; → ä, etc.)
        loc_name = html.unescape(name_el.get_text(strip=True))
        top_a = li.select_one("a[href]")
        href_rel = top_a.get("href") if top_a else None
        full_href: Optional[str] = None
        spid: Optional[str] = None
        if href_rel:
            full_href = urljoin(effective_base, href_rel)
            try:
                q = parse_qs(urlparse(full_href).query)
                spid = (q.get("spid") or [None])[0]
            except Exception:
                spid = None
        out[loc_name] = {"href": full_href, "spid": spid}
    return out


def fuzzy_match_name(target: str, candidates: List[str], threshold: float = 0.85) -> Optional[str]:
    """
    Attempts to find a close match for target in candidates using fuzzy matching.
    This handles minor whitespace, encoding, and case differences.
    Returns the best match if similarity >= threshold, else None.
    """
    target_normalized = target.strip().lower()
    best_match = None
    best_ratio = 0.0
    for candidate in candidates:
        candidate_normalized = candidate.strip().lower()
        ratio = SequenceMatcher(None, target_normalized, candidate_normalized).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate
    if best_ratio >= threshold:
        return best_match
    return None


def main() -> None:
    # 1) load site (using cached file for testing)
    cached_file = "/Users/lucah/Library/CloudStorage/OneDrive-FreigegebeneBibliotheken–UniversitaetSt.Gallen/CS_Gruppe6.3_2025 - UnisportAI/.scraper/Universität St.Gallen | Über uns | Services | Unisport St.Gallen.html"
    
    if os.path.exists(cached_file):
        print(f"📂 Using cached HTML file: {cached_file}")
        with open(cached_file, 'r', encoding='utf-8') as f:
            html = f.read()
    else:
        print(f"🌐 Fetching from live website...")
        html = fetch_html(SOURCE_URL)
    
    markers = parse_markers(html)
    loc_to_sports = parse_location_sports(html)
    loc_links = parse_location_links(html)

    print(f"\n=== DEBUG INFO ===")
    print(f"Markers found: {len(markers)}")
    print(f"Marker names (first 5): {[m['name'] for m in markers[:5]]}")
    print(f"\nLocation sports keys: {len(loc_to_sports)}")
    print(f"Sample keys (first 5): {list(loc_to_sports.keys())[:5]}")
    print(f"\nLocation links keys: {len(loc_links)}")
    print(f"Sample keys (first 5): {list(loc_links.keys())[:5]}")
    print("=================\n")

    # 2) Assemble information
    merged: List[Dict[str, object]] = []
    seen_names = set()
    fuzzy_matches = []
    exact_matches = 0
    
    for m in markers:
        name = str(m["name"])
        if name in seen_names:
            continue
        seen_names.add(name)
        
        # Try exact match first, then fuzzy match
        link_data = loc_links.get(name, {})
        if link_data:
            exact_matches += 1
        else:
            # Try fuzzy matching
            fuzzy_match = fuzzy_match_name(name, list(loc_links.keys()))
            if fuzzy_match:
                fuzzy_matches.append((name, fuzzy_match))
                print(f"⚠️  Fuzzy match: '{name}' → '{fuzzy_match}'")
                link_data = loc_links.get(fuzzy_match, {})
        
        merged.append({
            "name": name,
            "lat": m["lat"],
            "lng": m["lng"],
            "ort_href": link_data.get("href") if link_data else None,
            "spid": link_data.get("spid") if link_data else None,
        })

    # Also include locations that appear only in the menu but not in markers
    menu_only = []
    for name, sports in loc_to_sports.items():
        if name not in seen_names:
            menu_only.append(name)
            merged.append({
                "name": name,
                "lat": None,
                "lng": None,
                "ort_href": loc_links.get(name, {}).get("href") if loc_links else None,
                "spid": loc_links.get(name, {}).get("spid") if loc_links else None,
            })

    # Print summary
    print("\n=== MERGE RESULTS ===")
    print(f"✅ Exact matches: {exact_matches}")
    print(f"🤔 Fuzzy matches: {len(fuzzy_matches)}")
    if fuzzy_matches:
        for orig, matched in fuzzy_matches:
            print(f"   '{orig}' → '{matched}'")
    print(f"📍 Locations only in markers: {len(markers)}")
    print(f"📍 Locations only in menu: {len(menu_only)}")
    if menu_only:
        print(f"   {menu_only[:5]}...")
    print(f"📊 Total merged: {len(merged)}")
    
    # Check for empty entries
    print("\n=== EMPTY ENTRIES CHECK ===")
    entries_missing_coords = []
    entries_missing_link = []
    entries_missing_spid = []
    
    for entry in merged:
        if entry.get("lat") is None or entry.get("lng") is None:
            entries_missing_coords.append(entry["name"])
        if entry.get("ort_href") is None:
            entries_missing_link.append(entry["name"])
        if entry.get("spid") is None:
            entries_missing_spid.append(entry["name"])
    
    print(f"❌ Missing coordinates: {len(entries_missing_coords)}")
    if entries_missing_coords:
        print(f"   {entries_missing_coords[:10]}")
    print(f"❌ Missing ort_href: {len(entries_missing_link)}")
    if entries_missing_link:
        print(f"   {entries_missing_link[:10]}")
    print(f"❌ Missing spid: {len(entries_missing_spid)}")
    if entries_missing_spid:
        print(f"   {entries_missing_spid[:10]}")
    
    print("\n=== SAMPLE ENTRIES ===")
    for i, entry in enumerate(merged[:5]):
        print(f"{i+1}. {entry['name']}")
        print(f"   Coords: ({entry['lat']}, {entry['lng']})")
        print(f"   Href: {entry['ort_href']}")
        print(f"   SPID: {entry['spid']}")
    
    print("\n=== ENTRIES WITH MISSING DATA ===")
    for i, entry in enumerate(merged):
        missing = []
        if entry.get("lat") is None:
            missing.append("lat")
        if entry.get("lng") is None:
            missing.append("lng")
        if entry.get("ort_href") is None:
            missing.append("href")
        if entry.get("spid") is None:
            missing.append("spid")
        if missing:
            print(f"{i+1}. {entry['name']} - Missing: {', '.join(missing)}")


if __name__ == "__main__":
    main()

# Note (Academic Integrity): The tool "Cursor" was used as a supporting aid
# in the creation of this file.
