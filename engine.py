import base64
import io
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
import dns.resolver
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from geopy.geocoders import Nominatim
from PIL import Image, ExifTags
from groq import Groq
from langchain_community.tools import DuckDuckGoSearchRun

def web_search(query: str) -> str:
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        return f"Search note: {str(e)}"

def geocode_location(location_text: str):
    """Converts a city, region, or street address into latitude/longitude for the map."""
    if not location_text or location_text.strip().upper() == "NONE":
        return None
    try:
        geolocator = Nominatim(user_agent="deepsight_osint_app")
        loc = geolocator.geocode(location_text.strip(), timeout=10)
        if loc:
            return {"lat": loc.latitude, "lon": loc.longitude, "address": loc.address}
    except Exception:
        pass
    return None

# --- AGENT 1: ACCOUNT REGISTRATION SCANNER ---
def agent_account_registrations(target: str) -> str:
    if "@" not in target:
        return "Skipped (target is not an email address)."
    try:
        result = subprocess.run(["holehe", target, "--only-used"], capture_output=True, text=True, timeout=45)
        return result.stdout if result.stdout else "No public registrations detected."
    except Exception as e:
        return f"Holehe note: {str(e)}"

# --- AGENT 2: COMPREHENSIVE SOCIAL MEDIA & HANDLE MAPPER ---
def agent_social_handles(handle: str, raw_target: str) -> str:
    clean_handle = handle.lstrip("@").strip()
    try:
        result = subprocess.run(
            ["maigret", clean_handle, "--timeout", "8", "--top-sites", "200", "--print-not-found", "False"],
            capture_output=True,
            text=True,
            timeout=50
        )
        maigret_out = result.stdout if result.stdout else "No direct Maigret hits."
    except Exception as e:
        maigret_out = f"Maigret note: {str(e)}"

    s1 = web_search(f'"{raw_target}" OR "{clean_handle}" site:facebook.com OR site:instagram.com OR site:tiktok.com OR site:x.com OR site:threads.net')
    s2 = web_search(f'"{raw_target}" OR "{clean_handle}" site:linkedin.com OR site:youtube.com OR site:reddit.com OR site:github.com OR site:t.me OR site:pinterest.com')
    return f"MAIGRET 200-SITE SCAN:\n{maigret_out[:1400]}\n\nMAJOR SOCIAL PLATFORMS:\n{s1[:1200]}\n\nPROFESSIONAL & COMMUNITY PLATFORMS:\n{s2[:1200]}"

# --- AGENT 3: PHONE NUMBER & CARRIER INTELLIGENCE ---
def agent_phone_intel(target: str) -> str:
    digits = re.sub(r"[^\d+]", "", target)
    if len(digits) < 7:
        return "No phone number detected in primary target."
    
    phone_meta = ""
    try:
        parsed = phonenumbers.parse(digits if digits.startswith("+") else f"+{digits}", None)
        if phonenumbers.is_valid_number(parsed):
            region = geocoder.description_for_number(parsed, "en")
            net_carrier = carrier.name_for_number(parsed, "en")
            tz = ", ".join(timezone.time_zones_for_number(parsed))
            intl_fmt = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            phone_meta = f"Valid Number: {intl_fmt} | Country/Region: {region} | Carrier: {net_carrier or 'Unknown'} | Timezone: {tz}"
    except Exception:
        phone_meta = f"Raw Number String: {digits}"

    phone_dork = web_search(f'"{target}" OR "{digits}" "owner" OR "caller" OR "address" OR "directory" OR site:truecaller.com OR site:sync.me OR site:whitepages.com')
    return f"TELECOM METADATA:\n{phone_meta}\n\nPUBLIC DIRECTORY & CALLER-ID MENTIONS:\n{phone_dork[:1500]}"

# --- AGENT 4: PEOPLE-SEARCH & PHYSICAL ADDRESS BROKER ---
def agent_people_records(target: str, handle: str) -> str:
    q1 = web_search(f'"{target}" OR "{handle}" "address" OR "street" OR "city" OR "phone" OR "email" OR "relatives" OR "associates"')
    q2 = web_search(f'"{target}" OR "{handle}" site:whitepages.com OR site:spokeo.com OR site:beenverified.com OR site:truepeoplesearch.com OR site:fastpeoplesearch.com OR site:radaris.com')
    return f"PEOPLE-SEARCH AGGREGATORS:\n{q2[:1500]}\n\nADDRESS, PHONE & EMAIL CORRELATIONS:\n{q1[:1500]}"

# --- AGENT 5: OPEN CRIMINAL, COURT & LEGAL RECORDS ---
def agent_criminal_court_records(target: str, handle: str) -> str:
    q1 = web_search(f'"{target}" OR "{handle}" "court" OR "docket" OR "case no" OR "criminal" OR "arrest" OR "warrant" OR "conviction" OR "lawsuit"')
    q2 = web_search(f'"{target}" OR "{handle}" site:judiciary.gov.ph OR site:courtlistener.com OR site:justia.com OR site:unicourt.com OR "police blotter" OR "inmate"')
    return f"OPEN COURT & CRIMINAL DOCKET SEARCH:\n{q1[:1500]}\n\nJUDICIAL & PUBLIC LEGAL DATABASES:\n{q2[:1500]}"

# --- AGENT 6: BREACH & CREDENTIAL LEAK HUNTER ---
def agent_breach_intelligence(target: str, handle: str) -> str:
    q1 = web_search(f'"{target}" "breach" OR "leaked" OR "database" OR "dump" OR "password" OR "pwned"')
    q2 = web_search(f'"{target}" OR "{handle}" site:pastebin.com OR site:github.com OR site:://github.com')
    return f"BREACH MENTIONS:\n{q1[:1200]}\n\nPASTE & CODE EXPOSURES:\n{q2[:1200]}"

# --- AGENT 7: DOMAIN & TECHNICAL INFRASTRUCTURE ---
def agent_domain_infra(target: str) -> str:
    if "@" not in target:
        return "No email domain provided."
    domain = target.split("@").lower()
    free_providers = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "proton.me"}
    if domain in free_providers:
        return f"Standard consumer email provider ({domain})."
    try:
        answers = dns.resolver.resolve(domain, "MX")
        mx = [str(r.exchange) for r in answers]
    except Exception:
        mx = ["No MX records"]
    return f"Custom Domain: {domain} | MX Servers: {', '.join(mx)}"

def get_best_text_model(client: Groq) -> str:
    preferred = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
    try:
        available = [m.id for m in client.models.list().data]
        for p in preferred:
            if p in available:
                return p
    except Exception:
        pass
    return "openai/gpt-oss-120b"

def run_text_investigation(target: str, mode: str, api_key: str) -> dict:
    client = Groq(api_key=api_key.strip())
    model_id = get_best_text_model(client)
    target = target.strip()
    derived_handle = target.split("@") if "@" in target else target.lstrip("@")

    # Run all 7 OSINT agents simultaneously
    with ThreadPoolExecutor(max_workers=7) as executor:
        f1 = executor.submit(agent_account_registrations, target)
        f2 = executor.submit(agent_social_handles, derived_handle, target)
        f3 = executor.submit(agent_phone_intel, target)
        f4 = executor.submit(agent_people_records, target, derived_handle)
        f5 = executor.submit(agent_criminal_court_records, target, derived_handle)
        f6 = executor.submit(agent_breach_intelligence, target, derived_handle)
        f7 = executor.submit(agent_domain_infra, target)

        r1, r2, r3, r4, r5, r6, r7 = f1.result(), f2.result(), f3.result(), f4.result(), f5.result(), f6.result(), f7.result()

    prompt = f"""
    You are the Chief Intelligence Officer for DeepSight. Seven specialized OSINT agents just completed a parallel sweep on target: '{target}' (Mode: {mode}).
    Compile ALL discovered details—country, physical addresses, phone numbers, emails, every social media profile, breach mentions, and open court/criminal records—into a comprehensive Markdown dossier.

    First, on the VERY FIRST LINE of your response, output ONLY the single best-known physical address, city, or country discovered for this target in this exact format (or write LOCATION: NONE if unknown):
    LOCATION: <City, Country or Street Address>

    --- AGENT 1 (EMAIL REGISTRATIONS) ---
    {r1}

    --- AGENT 2 (ALL SOCIAL MEDIA PROFILES) ---
    {r2}

    --- AGENT 3 (PHONE & CARRIER INTEL) ---
    {r3}

    --- AGENT 4 (PEOPLE RECORDS & ADDRESSES) ---
    {r4}

    --- AGENT 5 (OPEN COURT & CRIMINAL RECORDS) ---
    {r5}

    --- AGENT 6 (BREACH & LEAK EXPOSURE) ---
    {r6}

    --- AGENT 7 (DOMAIN INFRASTRUCTURE) ---
    {r7}

    After the LOCATION line, format the rest of the report with these exact Markdown sections:
    ### 1. Executive Identity Summary (Name, Country, Location & Confidence Level)
    ### 2. Contact Intelligence (Phone Numbers, Carriers, Emails & Physical Addresses)
    ### 3. Complete Social Media & Online Footprint (List every discovered account & URL)
    ### 4. Open Criminal, Court & Public Legal Records
    ### 5. Security Exposure, Breaches & Relatives/Associates
    ### 6. Recommended Follow-Up OSINT Queries
    """
    completion = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}]
    )
    raw_text = completion.choices.message.content

    # Extract LOCATION line for map rendering
    lines = raw_text.splitlines()
    detected_loc = None
    clean_lines = []
    for line in lines:
        if line.strip().startswith("LOCATION:"):
            loc_val = line.split("LOCATION:", 1).strip()
            detected_loc = geocode_location(loc_val)
        else:
            clean_lines.append(line)

    # Fallback: if target itself is a street address, geocode it directly
    if not detected_loc and any(k in target.lower() for k in ["street", "st.", "ave", "road", "rd", "city", "davao", "manila", "blvd"]):
        detected_loc = geocode_location(target)

    return {"report": "\n".join(clean_lines).strip(), "map_data": detected_loc}

def extract_exif_metadata(img: Image.Image) -> str:
    try:
        exif_raw = img._getexif()
        if not exif_raw:
            return "No embedded EXIF metadata found."
        parsed = []
        for tag_id, val in exif_raw.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
