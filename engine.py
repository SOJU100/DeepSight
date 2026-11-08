import base64, io, json, re, subprocess
from concurrent.futures import ThreadPoolExecutor
import dns.resolver, phonenumbers, imagehash
from phonenumbers import geocoder, carrier, timezone
from geopy.geocoders import Nominatim
from PIL import Image, ExifTags
from groq import Groq
from langchain_community.tools import DuckDuckGoSearchRun

def web_search(query: str) -> str:
    try:
        return DuckDuckGoSearchRun().run(query)
    except Exception:
        return ""

def geocode_location(loc_text: str):
    if not loc_text or loc_text.strip().upper() in ["NONE", "UNKNOWN", "N/A", "NOT FOUND"]:
        return None
    try:
        loc = Nominatim(user_agent="deepsight_osint").geocode(loc_text.strip(), timeout=10)
        if loc:
            return {"lat": loc.latitude, "lon": loc.longitude, "address": loc.address}
    except Exception:
        pass
    return None

def agent_email(target: str) -> str:
    if "@" not in target:
        return "Not an email input."
    try:
        res = subprocess.run(["holehe", target, "--only-used"], capture_output=True, text=True, timeout=40)
        return res.stdout or "No registrations found."
    except Exception as e:
        return f"Holehe note: {str(e)}"

def agent_socials(handle: str, raw: str) -> str:
    h = handle.lstrip("@").strip()
    try:
        res = subprocess.run(["maigret", h, "--timeout", "8", "--top-sites", "150", "--print-not-found", "False"], capture_output=True, text=True, timeout=45)
        m_out = res.stdout or "No Maigret hits."
    except Exception as e:
        m_out = f"Maigret note: {str(e)}"
    s1 = web_search(f'"{raw}" OR "{h}" site:facebook.com OR site:instagram.com OR site:tiktok.com OR site:x.com')
    s2 = web_search(f'"{raw}" OR "{h}" site:linkedin.com OR site:youtube.com OR site:reddit.com OR site:github.com')
    return f"MAIGRET:\n{m_out[:1200]}\nSOCIALS:\n{s1[:1000]}\n{s2[:1000]}"

def agent_phone_people(target: str, handle: str) -> str:
    digits = re.sub(r"[^\d+]", "", target)
    meta = ""
    if len(digits) >= 7:
        try:
            p = phonenumbers.parse(digits if digits.startswith("+") else f"+{digits}", None)
            if phonenumbers.is_valid_number(p):
                meta = f"Number: {phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.INTERNATIONAL)} | Region: {geocoder.description_for_number(p, 'en')} | Carrier: {carrier.name_for_number(p, 'en') or 'Unknown'}"
        except Exception:
            pass
    addr = web_search(f'"{target}" OR "{handle}" "address" OR "phone" OR "age" OR "born" OR "relatives" OR site:spokeo.com OR site:beenverified.com OR site:truepeoplesearch.com')
    edu_job = web_search(f'"{target}" OR "{handle}" "University" OR "College" OR "Education" OR "worked at" OR "employed" OR site:linkedin.com')
    crim = web_search(f'"{target}" OR "{handle}" "court" OR "docket" OR "criminal" OR "arrest" OR "warrant" OR site:judiciary.gov.ph OR site:courtlistener.com')
    return f"{meta}\nPEOPLE & ADDRESS:\n{addr[:1300]}\nJOB & EDUCATION:\n{edu_job[:1000]}\nCOURT & CRIMINAL:\n{crim[:1200]}"

def parse_json_profile(raw_text: str, fallback_name: str) -> dict:
    try:
        clean = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(clean[start:end])
    except Exception:
        pass
    return {
        "full_name": fallback_name,
        "location": "Unknown",
        "age": "Unknown",
        "dob": "Unknown",
        "aliases": [],
        "primary_address": "Not found in public records",
        "primary_phone": "Not found",
        "primary_email": fallback_name if "@" in fallback_name else "Not found",
        "job": "No job found",
        "education": "Not found",
        "addresses": [],
        "phones": [],
        "emails": [],
        "social_profiles": [],
        "usernames": [],
        "relatives": [],
        "criminal_records": ["No open court or criminal records found in public web index."],
        "summary_markdown": raw_text
    }

def run_text_investigation(target: str, mode: str, api_key: str) -> dict:
    client = Groq(api_key=api_key.strip())
    target = target.strip()
    handle = target.split("@", 1) if "@" in target else target.lstrip("@")
    with ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(agent_email, target)
        f2 = ex.submit(agent_socials, handle, target)
        f3 = ex.submit(agent_phone_people, target, handle)
        r1, r2, r3 = f1.result(), f2.result(), f3.result()

    prompt = f"""
    You are DeepSight's Identity Resolution Engine. Extract all verified details for target '{target}' from the OSINT data below and return ONLY valid JSON matching this exact schema (use "Unknown" or empty lists [] if a field is not found—never invent fake facts):
    {{
      "full_name": "Full Name or Target",
      "location": "City, State/Country",
      "age": "Age or Unknown",
      "dob": "Month Year or Unknown",
      "aliases": ["Alias 1", "Alias 2"],
      "primary_address": "Best Street Address, City, State Zip",
      "primary_phone": "Best Phone Number",
      "primary_email": "Best Email Address",
      "job": "Current/Past Job Title & Company or No job found",
      "education": "University/School or Unknown",
      "addresses": ["Address 1", "Address 2"],
      "phones": ["Phone 1", "Phone 2"],
      "emails": [{{"email": "user@domain.com", "tag": "Personal or Work"}}],
      "social_profiles": [{{"platform": "LinkedIn", "url": "https://..."}}],
      "usernames": ["username1", "username2"],
      "relatives": ["Relative Name 1", "Relative Name 2"],
      "criminal_records": ["Court/Docket summary or No open criminal records found"],
      "summary_markdown": "Detailed analyst notes and follow-up dorks in Markdown"
    }}

    --- EMAIL DATA ---\n{r1}\n--- SOCIAL DATA ---\n{r2}\n--- PEOPLE, PHONE & CRIMINAL DATA ---\n{r3}
    """
    comp = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}])
    raw_text = next(iter(comp.choices)).message.content
    profile = parse_json_profile(raw_text, target)

    loc_query = profile.get("primary_address") if profile.get("primary_address") not in ["", "Unknown", "Not found in public records"] else profile.get("location")
    detected_loc = geocode_location(loc_query)
    if not detected_loc and any(k in target.lower() for k in ["street", "st.", "ave", "road", "city", "davao", "manila", "il", "ca", "tx", "ny"]):
        detected_loc = geocode_location(target)

    return {"profile": profile, "report": profile.get("summary_markdown", ""), "map_data": detected_loc}

def run_photo_investigation(uploaded_image, context_notes: str, api_key: str) -> dict:
    client = Groq(api_key=api_key.strip())
    raw_img = Image.open(uploaded_image)
    w, h = raw_img.size
    phash = str(imagehash.phash(raw_img))
    fname = uploaded_image.name
    origin = "Meta CDN (Facebook/Instagram)" if re.search(r"^\d+_\d+_\d+_n\.(jpg|png)", fname.lower()) else "Standard Image File"
    exif_str = f"- **Dimensions:** {w}x{h} px\n- **Visual Fingerprint (pHash):** `{phash}`\n- **Origin:** {origin}"

    search_seed = context_notes.strip() if context_notes else fname.rsplit(".", 1)
    with ThreadPoolExecutor(max_workers=2) as ex:
        fb_fut = ex.submit(web_search, f'"{search_seed}" site:facebook.com OR site:instagram.com OR site:tiktok.com')
        soc_fut = ex.submit(web_search, f'"{search_seed}" site:x.com OR site:linkedin.com OR site:youtube.com')
        fb_hits, soc_hits = fb_fut.result(), soc_fut.result()

    prompt = f"""
    DeepSight Social & Visual OSINT Lead Analyst. First line ONLY: LOCATION: <City, Country or NONE>
    FILE FORENSICS:\n{exif_str}\nCONTEXT: {context_notes}\nFACEBOOK/IG/TIKTOK:\n{fb_hits[:1400]}\nOTHER SOCIALS:\n{soc_hits[:1200]}
    Sections: ### 1. Image Origin & Visual Fingerprint ### 2. Look-Alike Facial Matching Strategy ### 3. Facebook & Social Media Matches ### 4. Geolocation & Search Dorks
    """
    c = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}])
    v_rep = next(iter(c.choices)).message.content
    detected_loc, clean_lines = None, []
    for line in v_rep.splitlines():
        if line.strip().startswith("LOCATION:"):
            _, loc_part = line.split("LOCATION:", 1)
            detected_loc = geocode_location(loc_part.strip())
        else:
            clean_lines.append(line)
    if not detected_loc and context_notes:
        detected_loc = geocode_location(context_notes)

    links = "\n---\n### 👤 Look-Alike & Social Facial Search Engines\n* **[Yandex Images](https://yandex.com)** — Look-alike faces & matching social profile photos.\n* **[FaceCheck.ID](https://facecheck.id)** — Scans Facebook, Instagram, TikTok, X, LinkedIn & YouTube for matching faces.\n* **[PimEyes](https://pimeyes.com)** — Deep facial similarity scanner for look-alike individuals.\n* **[Google Lens](https://google.com)** — Matches exact reposts, clothing, backgrounds & locations."
    return {"profile": None, "report": "\n".join(clean_lines).strip() + "\n" + links, "map_data": detected_loc}
