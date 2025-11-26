"""Scrape Unisport offers, courses and course dates into Supabase.

This script extracts structured data from the public Unisport website and
persists it into Supabase across three conceptual tables:

- ``sportangebote``: offers (e.g. "Boxen", "TRX")
- ``sportkurse``: courses for an offer (with ``kursnr``, details, and a
    ``zeitraum_href`` linking to the course dates page)
- ``kurs_termine``: concrete scheduled sessions (``start_time``, ``end_time``,
    ``location_name``)

Workflow summary:
1. ``extract_offers`` reads the main index and returns a list of offers.
2. ``extract_courses_for_offer`` parses the course table for an offer.
3. ``extract_course_dates`` parses individual course date pages.
4. ``main`` orchestrates the extraction and upserts data idempotently.

The script is written to be idempotent: primary keys (``href``, ``kursnr``,
``(kursnr,start_time)``) are used during upserts to avoid duplicates.
"""

# Mini tutorial:
# - Step 1: Fetch offers from the main page (extract_offers)
# - Step 2: For each offer, read the courses (extract_courses_for_offer)
# - Step 3: For each course, read all dates (extract_course_dates)
# - Step 4: Write everything idempotently (upsert) into Supabase

# Imports (beginner-friendly explanation of what we need them for in THIS script)
# Think of the imports as building blocks in Scratch – each one is good at a specific task.
# - os: To read environment variables (SUPABASE_URL/KEY) from the system/.env (our "settings")

import os
# - typing: For type hints (List, Dict) so the code is easier to understand

from typing import List, Dict, Optional
# - datetime: To convert date strings (e.g. 03.10.2025) into a machine-readable ISO format
from datetime import datetime
# - urllib.parse.urljoin: Turns relative links into full web addresses
from urllib.parse import urljoin, urlparse, parse_qs
# - re: "search with patterns" in texts (e.g. detect date/time)
import re
# - requests: Fetches web pages from the internet
import requests
# - bs4.BeautifulSoup: An "HTML magnifying glass" to find tables and cells
from bs4 import BeautifulSoup
# - supabase.create_client: Plug to the database (read/write)
from supabase import create_client
# - dotenv.load_dotenv: Reads the .env file (so keys don’t live in the code)
from dotenv import load_dotenv
import json
import urllib3


def fetch_html(url: str) -> str:
    """Download HTML content for a URL.

    Uses a requests session with SSL warnings disabled and ``verify=False``
    to maximize robustness when fetching pages. The function raises on
    non-success HTTP responses.

    Args:
        url (str): URL or local file path to fetch.

    Returns:
        str: Raw HTML content.
    """
    # A browser-like header helps to avoid being filtered out.
    import ssl
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Work around SSL issues using disable_warnings and verify=False
    session = requests.Session()
    session.verify = False
    
    r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return r.text


def extract_offers(source: str) -> List[Dict[str, str]]:
    """Extract the list of offers from the main index page.

    The function accepts either a URL or a local file path. It looks for
    anchor elements under the selector ``dl.bs_menu dd a`` and returns a
    list of ``{"name": ..., "href": ...}`` dictionaries with absolute
    ``href`` values.

    Args:
        source (str): URL or path to the HTML file.

    Returns:
        List[Dict[str, str]]: Unique offers found on the page.
    """
    # List of offers that should be excluded
    excluded_offers = {
        "alle freien Kursplätze dieses Zeitraums",
    }
    
    if source.startswith("http://") or source.startswith("https://"):
        base_url = source
        html = fetch_html(source)
    else:
        base_url = ""
        with open(source, "r", encoding="utf-8") as f:
            html = f.read()
    soup = BeautifulSoup(html, "lxml")

    offers: List[Dict[str, str]] = []
    seen_hrefs = set()
    for a in soup.select("dl.bs_menu dd a"):
        name = a.get_text(strip=True)
        href = a.get("href")
        if not name or not href:
            continue
        
        # Skip excluded offers
        if name in excluded_offers:
            continue
            
        full_href = urljoin(base_url or "", href)
        if full_href in seen_hrefs:
            continue
        seen_hrefs.add(full_href)
        offers.append({"name": name, "href": full_href})
    return offers


def extract_courses_for_offer(offer: Dict[str, str]) -> List[Dict[str, str]]:
    """Parse the course table for a single offer page.

    Returns a list of course dictionaries containing at minimum ``kursnr``
    and a ``zeitraum_href`` when available. Temporary fields prefixed with
    ``_`` (e.g. ``_offer_name``) are included to assist later processing
    (trainer extraction, cancellation mapping) but are not persisted to DB.

    Args:
        offer (Dict[str, str]): Offer dict with keys ``name`` and ``href``.

    Returns:
        List[Dict[str, str]]: Courses parsed from the offer page.
    """
    href = offer["href"]
    name = offer["name"]
    if not (href.startswith("http://") or href.startswith("https://")):
        return []
    html = fetch_html(href)
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.bs_kurse")
    if not table:
        return []
    tbody = table.find("tbody") or table
    rows: List[Dict[str, str]] = []
    for tr in tbody.select("tr"):
        def text(sel: str) -> str:
            el = tr.select_one(sel)
            return el.get_text(" ", strip=True) if el else ""
        kursnr = text("td.bs_sknr")
        if not kursnr:
            continue
        details = text("td.bs_sdet")
        tag = text("td.bs_stag")
        zeit = text("td.bs_szeit")
        ort_cell = tr.select_one("td.bs_sort")
        # Location texts are no longer stored in sportkurse. Here we primarily need
        # location_name for kurs_termine (comes in extract_course_dates) and keep sportkurse s
        ort = ort_cell.get_text(" ", strip=True) if ort_cell else ""
        ort_link = ort_cell.select_one("a") if ort_cell else None
        ort_href = urljoin(href, ort_link.get("href")) if (ort_link and ort_link.get("href")) else None
        zr_cell = tr.select_one("td.bs_szr")
        zr_link = zr_cell.select_one("a") if zr_cell else None
        zeitraum_href = urljoin(href, zr_link.get("href")) if (zr_link and zr_link.get("href")) else None
        leitung = text("td.bs_skl")
        preis = text("td.bs_spreis")
        buch_cell = tr.select_one("td.bs_sbuch")
        buchung = buch_cell.get_text(" ", strip=True) if buch_cell else ""
        
        # Store temporary fields for trainer extraction (not written to the DB)
        course_data = {
            "offer_href": href,
            "kursnr": kursnr,
            "details": details,
            "zeitraum_href": zeitraum_href,
            "preis": preis,
            "buchung": buchung,
            # Temporary fields marked with _
            "_offer_name": name,  # needed for update_cancellations.py
            "_leitung": leitung,  # needed for Trainer-Extraktion
        }
        rows.append(course_data)
    return rows


def extract_offer_metadata(offer: Dict[str, str]) -> Dict[str, str]:
    """Extract image URL and description paragraphs for an offer page.

    The function tries to find a representative image (not logos/icons)
    near the page title and collects paragraph tags before the course
    table to form a description string.

    Args:
        offer (Dict[str, str]): Offer dict with ``href`` key.

    Returns:
        Dict[str, str]: May contain keys ``image_url`` and ``description``.
    """
    href = offer["href"]
    if not (href.startswith("http://") or href.startswith("https://")):
        return {}
    
    html = fetch_html(href)
    soup = BeautifulSoup(html, "lxml")
    
    result = {}
    
    # Find the element with the title (can be h1 or div.bs_head)
    title_element = soup.find("h1") or soup.find("div", class_="bs_head")
    if title_element:
        # After the title, we search for the first <img> tag
        # Start from the title and go through all siblings and their children
        img_tag = None
        current = title_element.find_next_sibling()
        
        while current and current.name != "table":
            # Check whether current itself is an img
            if current.name == "img":
                img_tag = current
                break
            # Check all children of this element
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
            # Ignore logos and icons (often with "logo" or "icon" in src)
            if "logo" not in img_src.lower() and "icon" not in img_src.lower():
                # Convert relative URLs to absolute URLs
                result["image_url"] = urljoin(href, img_src)
    
    # find the table
    table = soup.select_one("table.bs_kurse")
    
    # Collect all <p> tags after the title
    paragraphs = []
    
    if title_element:
        # Find all <p> tags after the title element
        # Search in all following sibling elements
        current = title_element
        while current:
            current = current.next_sibling
            
            # When we reach a table, stop
            if current and hasattr(current, 'name') and current.name == "table":
                break
                
            # If current is a <p> tag, use it
            if current and hasattr(current, 'name') and current.name == "p":
                paragraphs.append(str(current))
            
            # If current has children, look for <p> tags in the children
            if current and hasattr(current, 'find_all'):
                for p in current.find_all("p"):
                    paragraphs.append(str(p))
    
    # Remove duplicates – keep the original order
    unique_paragraphs = []
    seen = set()
    for p in paragraphs:
        if p not in seen:
            unique_paragraphs.append(p)
            seen.add(p)
    
    if unique_paragraphs:
        result["description"] = "\n".join(unique_paragraphs)
    
    return result


def extract_trainer_names(leitung: str) -> List[str]:
    """Split a comma-separated trainers string into a list of names.

    Args:
        leitung (str): Comma-separated trainer names as presented on the site.

    Returns:
        List[str]: Cleaned trainer names.
    """
    if not leitung or not leitung.strip():
        return []
    
    # Split at commas and trim whitespace
    names = [name.strip() for name in leitung.split(",")]
    # Remove empty strings
    names = [name for name in names if name]
    return names


def parse_time_range(zeit_txt: str) -> tuple[Optional[str], Optional[str]]:
    """Parse a human-readable time range into start/end ISO time strings.

    Supports formats like "16.10 - 17.40" or "16:10 - 17:40" and returns
    a tuple of (start_time, end_time) where each is a string like
    ``HH:MM:SS`` or ``None`` when parsing fails.

    Returns:
        tuple[Optional[str], Optional[str]]: (start_time, end_time)
    """
    if not zeit_txt or not zeit_txt.strip():
        return None, None
    
    # Replace period with colon for a consistent format
    zeit_normalized = zeit_txt.strip().replace(".", ":")
    
    # Try to parse different formats
    patterns = [
        r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})",  # 16:10 - 17:40
        r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2})\.(\d{2})",  # 16:10 - 17.40
        r"(\d{1,2})\.(\d{2})\s*-\s*(\d{1,2}):(\d{2})",  # 16.10 - 17:40
    ]
    
    for pattern in patterns:
        match = re.match(pattern, zeit_normalized)
        if match:
            h1, m1, h2, m2 = match.groups()
            start_hour = int(h1)
            start_min = int(m1)
            end_hour = int(h2)
            end_min = int(m2)
            return f"{start_hour:02d}:{start_min:02d}:00", f"{end_hour:02d}:{end_min:02d}:00"
    
    return None, None


def extract_course_dates(kursnr: str, zeitraum_href: str) -> List[Dict[str, str]]:
    """Parse the course dates page for a given ``kursnr``.

    Each table row represents a scheduled session. Dates are converted to
    ISO format (YYYY-MM-DD) and times are converted to ``HH:MM:SS``. The
    function returns a list of dictionaries suitable for upserting into
    the ``kurs_termine`` table.

    Args:
        kursnr (str): Course number identifier.
        zeitraum_href (str): URL to the course dates page.

    Returns:
        List[Dict[str, str]]: Parsed date records with keys like
            ``start_time``, ``end_time``, ``location_name``.
    """
    html = fetch_html(zeitraum_href)
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.bs_kurse")
    if not table:
        return []
    out: List[Dict[str, str]] = []
    for tr in table.select("tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        wochentag = tds[0].get_text(" ", strip=True)
        datum_raw = tds[1].get_text(" ", strip=True)
        zeit_txt = tds[2].get_text(" ", strip=True)
        ort_cell = tds[3]
        ort_txt = ort_cell.get_text(" ", strip=True)
        a = ort_cell.find("a")
        ort_href = urljoin(zeitraum_href, a.get("href")) if (a and a.get("href")) else None
        try:
            datum_iso = datetime.strptime(datum_raw, "%d.%m.%Y").date().isoformat()
        except Exception:
            continue
        
        # Parse time into start_time and end_time
        start_time, end_time = parse_time_range(zeit_txt)
        
        location_name = ort_txt.strip() or None
        
        # Combine date with start_time/end_time to create a timestamp
        # If no time can be parsed, we skip this entry
        if not start_time:
            print(f"⚠️  Konnte Zeit nicht parsen für {kursnr} am {datum_iso}: '{zeit_txt}' - Überspringe Eintrag")
            continue
        
        start_timestamp = f"{datum_iso}T{start_time}"
        end_timestamp = f"{datum_iso}T{end_time}" if end_time else None
        
        out.append({
            "kursnr": kursnr,
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "ort_href": ort_href,
            "location_name": location_name,
        })
    return out


def apply_overrides(supabase) -> None:
        """Apply manual overrides from ``missing_overrides.json`` to the DB.

        The overrides JSON contains per-table entries that specify an
        identifier and fields to upsert. This helper upserts each provided
        override item into the corresponding table using the appropriate
        conflict key.
        """
    overrides_path = os.path.join(os.path.dirname(__file__), "missing_overrides.json")
    if not os.path.exists(overrides_path):
        return
    try:
        with open(overrides_path, "r", encoding="utf-8") as fh:
            data = json.load(fh) or {}
    except Exception as e:
        print(f"Warnung: missing_overrides.json konnte nicht gelesen werden: {e}")
        return

    def _safe_fields(d: Dict[str, object]) -> Dict[str, object]:
        return {k: v for k, v in (d or {}).items()}

    # sport offers by href
    for item in (data.get("sportangebote") or []):
        href = item.get("identifier")
        fields = _safe_fields(item.get("fields") or {})
        if not href or not fields:
            continue
        try:
            fields["href"] = href
            supabase.table("sportangebote").upsert(fields, on_conflict="href").execute()
        except Exception as e:
            print(f"Override sportangebote fehlgeschlagen ({href}): {e}")

    # courses by kursnr
    for item in (data.get("sportkurse") or []):
        kursnr = item.get("identifier")
        fields = _safe_fields(item.get("fields") or {})
        if not kursnr or not fields:
            continue
        try:
            fields["kursnr"] = kursnr
            supabase.table("sportkurse").upsert(fields, on_conflict="kursnr").execute()
        except Exception as e:
            print(f"Override sportkurse fehlgeschlagen ({kursnr}): {e}")

    # kurs_termine by (kursnr, start_time)
    for item in (data.get("kurs_termine") or []):
        ident = item.get("identifier") or ""
        fields = _safe_fields(item.get("fields") or {})
        if not ident or "|" not in ident or not fields:
            continue
        kursnr, start_time = ident.split("|", 1)
        kursnr = kursnr.strip()
        start_time = start_time.strip()
        if not kursnr or not start_time:
            continue
        try:
            fields["kursnr"] = kursnr
            fields["start_time"] = start_time
            supabase.table("kurs_termine").upsert(fields, on_conflict="kursnr,start_time").execute()
        except Exception as e:
            print(f"Override kurs_termine fehlgeschlagen ({ident}): {e}")

    # unisport_locations by name
    for item in (data.get("unisport_locations") or []):
        name = item.get("identifier")
        fields = _safe_fields(item.get("fields") or {})
        if not name or not fields:
            continue
        try:
            fields["name"] = name
            supabase.table("unisport_locations").upsert(fields, on_conflict="name").execute()
        except Exception as e:
            print(f"Override unisport_locations fehlgeschlagen ({name}): {e}")

def generate_missing_info_csv(supabase) -> List[Dict[str, str]]:
    """Detect missing fields across main tables and merge into overrides.

    The function inspects multiple tables for missing important fields
    (e.g. missing ``image_url`` on ``sportangebote``) and ensures that a
    corresponding entry exists in the ``missing_overrides.json`` file so
    that maintainers can provide the missing information.
    """
    rows: List[Dict[str, str]] = []

    # sport offers: missing image_url, missing description
    try:
        sa1 = supabase.table("sportangebote").select("href,name").is_("image_url", "null").execute()
        sa2 = supabase.table("sportangebote").select("href,name").eq("image_url", "").execute()
        sa3 = supabase.table("sportangebote").select("href,name").is_("description", "null").execute()
        sa4 = supabase.table("sportangebote").select("href,name").eq("description", "").execute()
        def _append_sa(data, field):
            for r in (data.data or []):
                rows.append({
                    "table_name": "sportangebote",
                    "identifier": r.get("href") or "",
                    "missing_field": field,
                    "context1": r.get("name") or "",
                    "context2": "",
                })
        _append_sa(sa1, "image_url")
        _append_sa(sa2, "image_url")
        _append_sa(sa3, "description")
        _append_sa(sa4, "description")
    except Exception:
        pass

    # sportkurse: missing offer_href, missing zeitraum_href
    try:
        sk1 = supabase.table("sportkurse").select("kursnr,details,preis").is_("offer_href", "null").execute()
        sk2 = supabase.table("sportkurse").select("kursnr,details,preis").eq("offer_href", "").execute()
        sk3 = supabase.table("sportkurse").select("kursnr,details,preis").is_("zeitraum_href", "null").execute()
        sk4 = supabase.table("sportkurse").select("kursnr,details,preis").eq("zeitraum_href", "").execute()
        def _append_sk(data, field):
            for r in (data.data or []):
                rows.append({
                    "table_name": "sportkurse",
                    "identifier": r.get("kursnr") or "",
                    "missing_field": field,
                    "context1": (r.get("details") or ""),
                    "context2": (r.get("preis") or ""),
                })
        _append_sk(sk1, "offer_href")
        _append_sk(sk2, "offer_href")
        _append_sk(sk3, "zeitraum_href")
        _append_sk(sk4, "zeitraum_href")
    except Exception:
        pass

    # kurs_termine: missing ort_href, location_name, end_time
    try:
        kt1 = supabase.table("kurs_termine").select("kursnr,start_time").is_("ort_href", "null").execute()
        kt2 = supabase.table("kurs_termine").select("kursnr,start_time").eq("ort_href", "").execute()
        kt3 = supabase.table("kurs_termine").select("kursnr,start_time").is_("location_name", "null").execute()
        kt4 = supabase.table("kurs_termine").select("kursnr,start_time").eq("location_name", "").execute()
        kt5 = supabase.table("kurs_termine").select("kursnr,start_time").is_("end_time", "null").execute()
        def _append_kt(data, field):
            for r in (data.data or []):
                identifier = f"{r.get('kursnr') or ''}|{(r.get('start_time') or '')[:19]}"
                rows.append({
                    "table_name": "kurs_termine",
                    "identifier": identifier,
                    "missing_field": field,
                    "context1": r.get("kursnr") or "",
                    "context2": (r.get("start_time") or "")[:19],
                })
        _append_kt(kt1, "ort_href")
        _append_kt(kt2, "ort_href")
        _append_kt(kt3, "location_name")
        _append_kt(kt4, "location_name")
        _append_kt(kt5, "end_time")
    except Exception:
        pass

    # unisport_locations: missing lat, lng, ort_href, spid
    try:
        ul1 = supabase.table("unisport_locations").select("name").is_("lat", "null").execute()
        ul2 = supabase.table("unisport_locations").select("name").is_("lng", "null").execute()
        ul3 = supabase.table("unisport_locations").select("name").is_("ort_href", "null").execute()
        ul4 = supabase.table("unisport_locations").select("name").eq("ort_href", "").execute()
        ul5 = supabase.table("unisport_locations").select("name").is_("spid", "null").execute()
        ul6 = supabase.table("unisport_locations").select("name").eq("spid", "").execute()
        def _append_ul(data, field):
            for r in (data.data or []):
                rows.append({
                    "table_name": "unisport_locations",
                    "identifier": r.get("name") or "",
                    "missing_field": field,
                    "context1": "",
                    "context2": "",
                })
        _append_ul(ul1, "lat")
        _append_ul(ul2, "lng")
        _append_ul(ul3, "ort_href")
        _append_ul(ul4, "ort_href")
        _append_ul(ul5, "spid")
        _append_ul(ul6, "spid")
    except Exception:
        pass

    # Merge missing entries directly into missing_overrides.json (CSV no longer needed)
    try:
        _merge_missing_into_overrides(rows)
        print(f"missing_overrides.json aktualisiert (Missing-Merge) mit {len(rows)} Einträgen")
    except Exception as e:
        print(f"Fehler beim Aktualisieren von missing_overrides.json: {e}")
    return rows


def _load_overrides_json() -> Dict[str, object]:
    overrides_path = os.path.join(os.path.dirname(__file__), "missing_overrides.json")
    if not os.path.exists(overrides_path):
        return {}
    try:
        with open(overrides_path, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def _build_ignore_set_from_overrides(overrides: Dict[str, object]) -> set:
    ignore: set = set()
    # Each section is a list of { identifier, fields, ignore_valueerror? }
    for section in [
        ("sportangebote", "href"),
        ("sportkurse", "kursnr"),
        ("kurs_termine", "composite"),
        ("unisport_locations", "name"),
    ]:
        key = section[0]
        items = (overrides.get(key) or []) if isinstance(overrides, dict) else []
        for it in items:  # type: ignore
            try:
                if it.get("ignore_valueerror") is True:
                    ident = (it.get("identifier") or "").strip()
                    if ident:
                        ignore.add((key, ident))
            except Exception:
                continue
    return ignore


def _save_overrides_json(data: Dict[str, object]) -> None:
    """Persist the overrides JSON atomically to disk.

    Writes to a temporary file and replaces the original file to avoid
    partial writes.
    """
    overrides_path = os.path.join(os.path.dirname(__file__), "missing_overrides.json")
    tmp_path = overrides_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp_path, overrides_path)


def _ensure_ignore_flags(data: Dict[str, object]) -> None:
    """Ensure every override item has an ``ignore_valueerror`` boolean key.

    Existing ``true`` values remain unchanged; missing keys are set to
    ``False`` by default so callers can respect the explicit ignore flag.
    """
    for key in [
        "sportangebote",
        "sportkurse",
        "kurs_termine",
        "unisport_locations",
    ]:
        items = data.get(key)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and ("ignore_valueerror" not in it):
                    it["ignore_valueerror"] = False


def _merge_missing_into_overrides(rows: List[Dict[str, str]]) -> None:
    """Merge detected missing identifiers into ``missing_overrides.json``.

    Adds entries for identifiers that are not yet present and ensures the
    file structure contains the expected per-table lists.
    """
    data = _load_overrides_json() or {}

    # Make sure the four main lists exist
    for key in ["sportangebote", "sportkurse", "kurs_termine", "unisport_locations"]:
        if key not in data or not isinstance(data.get(key), list):
            data[key] = []

    # Fast lookup per area: identifier -> item
    def _index_by_identifier(items: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
        idx: Dict[str, Dict[str, object]] = {}
        for it in items:
            if isinstance(it, dict):
                ident = (it.get("identifier") or "").strip()
                if ident:
                    idx[ident] = it
        return idx

    indexes = {
        "sportangebote": _index_by_identifier(data["sportangebote"]),
        "sportkurse": _index_by_identifier(data["sportkurse"]),
        "kurs_termine": _index_by_identifier(data["kurs_termine"]),
        "unisport_locations": _index_by_identifier(data["unisport_locations"]),
    }

    for r in rows:
        table = (r.get("table_name") or "").strip()
        identifier = (r.get("identifier") or "").strip()
        if not table or not identifier:
            continue
        if table not in data:
            continue

        idx = indexes.get(table) or {}
        existing = idx.get(identifier)
        if existing is None:
            # Create new
            new_item: Dict[str, object] = {
                "identifier": identifier,
                "fields": {},
                "ignore_valueerror": False,
            }
            data[table].append(new_item)  # type: ignore[arg-type]
            idx[identifier] = new_item
        else:
            # Add flag by default; once true, it stays true
            if "ignore_valueerror" not in existing:
                existing["ignore_valueerror"] = False

    # Globally ensure that all items have the flag
    _ensure_ignore_flags(data)
    _save_overrides_json(data)


def send_missing_info_email_if_needed(rows: List[Dict[str, str]]) -> None:
    """Optionally send an email notification about missing overrides.

    Sends a transactional email via the Loops API when there are missing
    entries (after honoring ignore flags). Requires ``ADMIN_EMAIL`` and
    ``LOOPS_API_KEY`` environment variables.
    """
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
    loops_api_key = os.environ.get("LOOPS_API_KEY", "").strip()
    transactional_id = "cmhaf9k8f988i060i0tsb79io"
    if not admin_email or not loops_api_key:
        print("Hinweis: ADMIN_EMAIL oder LOOPS_API_KEY nicht gesetzt – überspringe E-Mail.")
        return

    # Optionally load ignore_valueerror from overrides
    overrides = _load_overrides_json()
    ignore_set = _build_ignore_set_from_overrides(overrides)

    # Filter entries that should be ignored (by table + identifier)
    filtered = [r for r in rows if (r.get("table_name"), r.get("identifier")) not in ignore_set]
    if len(filtered) <= 0:
        print("Keine fehlenden Einträge (nach Ignorieren) – keine E-Mail.")
        return

    # build JSON-Text
    try:
        missing_json_text = json.dumps(filtered, ensure_ascii=False, indent=2)
    except Exception:
        missing_json_text = str(filtered)

    # Send HTTP POST to Loops
    try:
        import requests
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.post(
            "https://app.loops.so/api/v1/transactional",
            headers={
                "Authorization": f"Bearer {loops_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "transactionalId": transactional_id,
                "email": admin_email,
                "dataVariables": {
                    "MissingValues": missing_json_text
                }
            },
            timeout=30,
        )
        print(f"Loops API status: {resp.status_code} – {resp.text[:200]}")
    except Exception as e:
        print(f"Warnung: Konnte Loops-Transaktionsmail nicht senden: {e}")


def main() -> None:
    # 1) Load environment variables from .env (if present).
    #    This keeps credentials out of source control.
    load_dotenv()
    # 2) Use the live offers index page as the canonical source
    html_source = "https://www.sportprogramm.unisg.ch/unisg/angebote/aktueller_zeitraum/index.html"
    offers = extract_offers(html_source)  # list of {name, href}

    # 3) Connect to Supabase using environment credentials
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("Please set SUPABASE_URL and SUPABASE_KEY in the environment.")
        return
    supabase = create_client(supabase_url, supabase_key)  # DB connection

    # 4) First, we write the offers into the "sportangebote" table.
    #    Upsert means: if an entry already exists (same key), it will be updated.
    #    The key here is the "href" column (the link to the offer page).
    # Idempotent: same href → will be updated instead of duplicated
    supabase.table("sportangebote").upsert(offers, on_conflict="href").execute()
    print(f"Supabase: {len(offers)} Angebote upserted (idempotent).")

    # 4b) Extract image URL and description text from each offer page
    #     and update the entries in the database
    updated_count = 0
    for offer in offers:
        metadata = extract_offer_metadata(offer)
        if metadata:
            # Prepare update: href + name + new fields
            update_data = {
                "href": offer["href"],
                "name": offer["name"]
            }
            if "image_url" in metadata:
                update_data["image_url"] = metadata["image_url"]
            if "description" in metadata:
                update_data["description"] = metadata["description"]
            # Upsert with the new fields
            supabase.table("sportangebote").upsert(update_data, on_conflict="href").execute()
            updated_count += 1
    print(f"Supabase: Bild-URL und Beschreibungen aktualisiert für {updated_count} Angebote.")

    # 5) Next, we collect all courses for all offers.
    #    For this, we visit the detail page of each offer and read the course table.
    all_courses: List[Dict[str, str]] = []
    for off in offers:  # jede Angebotsseite besuchen
        all_courses.extend(extract_courses_for_offer(off))
    #    Then we write all courses into the "sportkurse" table.
    #    The key is the course number ("kursnr").
    # Clean up temporary fields (_leitung) before the upsert
    courses_for_db = [
        {k: v for k, v in course.items() if not k.startswith("_")}
        for course in all_courses
    ]
    
    # Idempotent: same kursnr → will be updated
    supabase.table("sportkurse").upsert(courses_for_db, on_conflict="kursnr").execute()
    print(f"Supabase: {len(courses_for_db)} Kurse upserted (idempotent).")

    # 5b) Extract trainer names from all courses and store them
    trainer_to_courses: Dict[str, List[str]] = {}  # trainer_name -> [kursnr, kursnr, ...]
    
    for course in all_courses:
        leitung = course.get("_leitung", "").strip() if course.get("_leitung") else ""
        if leitung:
            trainer_names = extract_trainer_names(leitung)
            for trainer_name in trainer_names:
                # Track which courses each trainer teaches
                if trainer_name not in trainer_to_courses:
                    trainer_to_courses[trainer_name] = []
                trainer_to_courses[trainer_name].append(course["kursnr"])
    
    # Deduplicate trainer list (trainer_name -> rating dict)
    all_trainers: List[Dict[str, object]] = [
        {"name": trainer_name, "rating": 3}
        for trainer_name in trainer_to_courses.keys()
    ]
    
    # Save trainers into the trainer table (idempotent)
    if all_trainers:
        supabase.table("trainer").upsert(all_trainers, on_conflict="name").execute()
        print(f"Supabase: {len(all_trainers)} Trainer upserted (idempotent).")
    
    # Save relationships in the kurs_trainer table
    kurs_trainer_rows: List[Dict[str, object]] = []
    for trainer_name, kursnrs in trainer_to_courses.items():
        for kursnr in kursnrs:
            kurs_trainer_rows.append({"kursnr": kursnr, "trainer_name": trainer_name})
    
    if kurs_trainer_rows:
        # Lösche vorhandene Verknüpfungen für diese Kurse zuerst, um Duplikate zu vermeiden
        kursnrs_to_update = [course["kursnr"] for course in all_courses]
        for kursnr in kursnrs_to_update:
            supabase.table("kurs_trainer").delete().eq("kursnr", kursnr).execute()
        # Insert new relationships
        supabase.table("kurs_trainer").insert(kurs_trainer_rows).execute()
        print(f"Supabase: {len(kurs_trainer_rows)} Kurs-Trainer-Verknüpfungen gespeichert.")

    # 6) Now we handle the exact dates for each course.
    #    For each course there is a link (zeitraum_href) to a subpage with all scheduled dates.
    all_dates: List[Dict[str, str]] = []
    for c in all_courses:  # Termine-Seite pro Kurs besuchen
        if c.get("zeitraum_href") and c.get("kursnr"):
            all_dates.extend(extract_course_dates(c["kursnr"], c["zeitraum_href"]))
        # Delete existing relationships for these courses first to avoid duplicates
    if all_dates:
        # Before upsert: clean invalid location_name (set to NULL if not in unisport_locations)
        loc_resp = supabase.table("unisport_locations").select("name").execute()  # erlaubte Standorte holen
        valid_names = { (r.get("name") or "").strip() for r in (loc_resp.data or []) if r.get("name") }
        for row in all_dates:
            ln = (row.get("location_name") or "").strip()
            if not ln or (valid_names and ln not in valid_names):
                row["location_name"] = None
        # MERGE strategy: the canceled flag is NOT overwritten, only set if it is not already set
        # Load existing canceled status for all dates in a single query
        kursnrs_with_dates = [(row["kursnr"], row["start_time"]) for row in all_dates]
        existing_canceled = {}
        
    #    We write these dates back into "kurs_termine" (legacy table), now with a location_name link.
        if kursnrs_with_dates:
            # Fetch all existing canceled values
            kursnrs_set = set(kr[0] for kr in kursnrs_with_dates)
            for kursnr in kursnrs_set:
                resp = supabase.table("kurs_termine").select("kursnr, start_time, canceled").eq("kursnr", kursnr).execute()
                for term in resp.data or []:
                    existing_canceled[(term["kursnr"], term["start_time"])] = term.get("canceled", False)
        
        # Set canceled only if it does not already exist
        for row in all_dates:
            key = (row["kursnr"], row["start_time"])
            if key in existing_canceled:
                # Keep the existing canceled status
                row["canceled"] = existing_canceled[key]
            else:
                # New date, canceled = false
                row["canceled"] = False
        
        supabase.table("kurs_termine").upsert(all_dates, on_conflict="kursnr,start_time").execute()  # Idempotent pro (kursnr, start_time)
        print(f"Supabase: {len(all_dates)} Termine upserted (kurs_termine, idempotent, canceled Status behalten).")
    else:
        print("Hinweis: Keine Termine gefunden.")

    # Log ETL run
    try:
        supabase.table("etl_runs").insert({"component": "scrape_sportangebote"}).execute()
    except Exception:
        pass

    # Note: The logic for detecting and marking training cancellations
    #       has been moved to update_cancellations.py so that both
    #       scripts can run independently.

    # 7) Update missing info in missing_overrides.json and optionally send an email
    try:
        # 7a) Apply optional overrides if the file exists
        apply_overrides(supabase)
        # 7b) Then determine missing entries and merge them into missing_overrides.json (no more CSV)
        rows = generate_missing_info_csv(supabase)
        # 7c) If missing entries exist, send an email to the admin
        send_missing_info_email_if_needed(rows)
    except Exception as e:
        print(f"Warnung: Missing-Info konnte nicht aktualisiert/versendet werden: {e}")


if __name__ == "__main__":
    main()

# Note (Academic Integrity): The tool "Cursor" was used as a supporting aid
# in the creation of this file.
