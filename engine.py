import base64, hashlib, io, json, os, re, subprocess, requests
from concurrent.futures import ThreadPoolExecutor
import dns.resolver, phonenumbers, imagehash
from phonenumbers import geocoder, carrier, timezone
from geopy.geocoders import Nominatim
from PIL import Image
from groq import Groq
import streamlit as st
from tavily import TavilyClient

def deep_web_search(query: str, max_res: int = 6) -> str:
    tavily_key = st.secrets.get("TAVILY_API_KEY", os.environ.get("TAVILY_API_KEY", ""))
    if not tavily_key:
        return ""
    try:
        client = TavilyClient(api_key=tavily_key.strip())
        res = client.search(query=query, search_depth="advanced", max_results=max_res)
        return "\n".join([f"- {r.get('title', '')} ({r.get('url', '')}): {r.get('content', '')}" for r in res.get("results", [])])
    except Exception:
        return ""

def geocode_location(loc_text: str):
    if not loc_text or loc_text.strip().upper() in ["NONE", "UNKNOWN", "N/A", "NOT FOUND"]:
        return None
    try:
        loc = Nominatim(user_agent="deepsight_osint_v3").geocode(loc_text.strip(), timeout=10)
        if loc:
            return {"lat": loc.latitude, "lon": loc.longitude, "address": loc.address}
    except Exception:
        pass
    return None

def agent_1_pentester_breaches(target: str) -> dict:
    breaches, details = [], []
    if "@" in target:
        try:
            r = requests.get(f"https://xposedornot.com{target}", timeout=12)
            if r.status_code == 200:
                exposed = r.json().get("ExposedBreaches", {}).get("breaches_details", [])
                for b in exposed:
                    b_name = b.get("breach", "Unknown")
                    b_date = b.get("xposed_date", "")
                    b_data = b.get("xposed_data", "")
                    breaches.append(f"{b_name} ({b_date}) — Exposed: {b_data}")
                    details.append(f"Breach: {b_name} | Date: {b_date} | Data: {b_data}")
        except Exception:
            pass
        try:
            hr = requests.get(f"https://hudsonrock.com{target}", timeout=10)
            if hr.status_code == 200 and hr.json().get("stealers"):
                stealers = str(hr.json().get("stealers"))[:800]
                breaches.append(f"Infostealer Log Detected: {stealers}")
                details.append(f"INFOSTEALER: {stealers}")
        except Exception:
            pass
    return {"breach_list": breaches, "raw": "\n".join(details)}

def agent_2_connected_accounts(target: str) -> dict:
    accounts, identity_clues, social_links = [], [], []
    if "@" not in target:
        return {"accounts": [], "clues": "", "socials": []}
    try:
        res = subprocess.run(["holehe", target, "--only-used", "--no-color"], capture_output=True, text=True, timeout=45)
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        clean_out = ansi_escape.sub("", res.stdout or "")
        for line in clean_out.splitlines():
            if "[+]" in line:
                _, after_plus = line.split("[+]", 1)
                site, _, _ = after_plus.strip().partition(" ")
                if site and "." in site:
                    accounts.append(site)
    except Exception:
        pass
    try:
        md5_hash = hashlib.md5(target.strip().lower().encode("utf-8")).hexdigest()
        gr = requests.get(f"https://gravatar.com{md5_hash}.json", timeout=8)
        if gr.status_code == 200:
            entry = next(iter(gr.json().get("entry", [])), {})
            if entry.get("displayName"):
                identity_clues.append(f"Gravatar Name: {entry.get('displayName')}")
            if entry.get("currentLocation"):
                identity_clues.append(f"Gravatar Location: {entry.get('currentLocation')}")
            if entry.get("aboutMe"):
                identity_clues.append(f"Gravatar Bio: {entry.get('aboutMe')}")
            for u in entry.get("urls", []):
                social_links.append({"platform": u.get("title", "Profile"), "url": u.get("value", "")})
    except Exception:
        pass
    try:
        gh = requests.get(f"https://github.com{target}", timeout=8)
        if gh.status_code == 200 and gh.json().get("items"):
            user_login = next(iter(gh.json()["items"])).get("login")
            if user_login:
                u_det = requests.get(f"https://github.com{user_login}", timeout=8).json()
                identity_clues.append(f"GitHub Name: {u_det.get('name')} | Location: {u_det.get('location')} | Bio: {u_det.get('bio')} | Username: {user_login}")
                social_links.append({"platform": "GitHub", "url": f"https://github.com{user_login}"})
    except Exception:
        pass
    return {"accounts": sorted(list(set(accounts))), "clues": "\n".join(identity_clues), "socials": social_links}

def agent_3_web_and_people(target: str, handle: str) -> str:
    q1 = deep_web_search(f'"{target}" OR "{handle}" site:linkedin.com OR site:github.com OR site:chess.com OR site:duolingo.com OR site:facebook.com OR site:instagram.com', 7)
    q2 = deep_web_search(f'"{target}" address phone age relatives education employer OR site:spokeo.com OR site:beenverified.com OR site:truepeoplesearch.com', 6)
    q3 = deep_web_search(f'"{target}" court docket criminal arrest lawsuit OR site:courtlistener.com OR site:judiciary.gov.ph', 4)
    return f"WEB PROFILES:\n{q1[:2000]}\nPEOPLE & ADDRESS:\n{q2[:1500]}\nCOURT RECORDS:\n{q3[:1000]}"

def parse_json_profile(raw_text: str, fallback_name: str) -> dict:
    try:
        clean = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)
        start, end = clean.find("{"), clean.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(clean[start:end])
    except Exception:
        pass
    return {"full_name": fallback_name, "location": "Unknown", "age": "Unknown", "dob": "Unknown", "aliases": [], "primary_address": "Not found", "primary_phone": "Not found", "primary_email": fallback_name if "@" in fallback_name else "Not found", "job": "No job found", "education": "Not found", "addresses": [], "phones": [], "emails": [], "social_profiles": [], "usernames": [], "relatives": [], "criminal_records": ["No open court records found."], "summary_markdown": raw_text}

def run_text_investigation(target: str, mode: str, api_key: str) -> dict:
    client = Groq(api_key=api_key.strip())
    target = target.strip()
    handle, _, _ = target.lstrip("@").partition("@")

    with ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(agent_1_pentester_breaches, target)
        f2 = ex.submit(agent_2_connected_accounts, target)
        f3 = ex.submit(agent_3_web_and_people, target, handle)
        b_res, a_res, w_res = f1.result(), f2.result(), f3.result()

    prompt = f"""
    DeepSight Chief Intelligence Officer. Synthesize all findings for '{target}' into ONLY valid JSON matching the exact schema below. Use the Gravatar/GitHub/Web clues to fill in full_name, location, job, education, and social_profiles whenever found (never invent fake details):
    {{"full_name": "", "location": "City, Region/Country", "age": "Unknown", "dob": "Unknown", "aliases": [], "primary_address": "Not found", "primary_phone": "Not found", "primary_email": "{target if '@' in target else 'Not found'}", "job": "No job found", "education": "Not found", "addresses": [], "phones": [], "emails": [{{"email": "{target}", "tag": "Primary"}}], "social_profiles": [], "usernames": ["{handle}"], "relatives": [], "criminal_records": ["No open court records found."], "summary_markdown": "Detailed AI risk assessment and summary in Markdown"}}
    --- DIRECT IDENTITY CLUES ---\n{a_res['clues']}
    --- CONNECTED ACCOUNTS ({len(a_res['accounts'])} PLATFORMS) ---\n{', '.join(a_res['accounts'])}
    --- BREACH EXPOSURE RECORDS ({len(b_res['breach_list'])} FOUND) ---\n{b_res['raw']}
    --- OPEN WEB & PEOPLE SEARCH ---\n{w_res}
    """
    comp = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}])
    profile = parse_json_profile(next(iter(comp.choices)).message.content, target)

    existing_urls = {s.get("url") for s in profile.get("social_profiles", []) if isinstance(s, dict)}
    for s in a_res["socials"]:
        if s["url"] and s["url"] not in existing_urls:
            profile.setdefault("social_profiles", []).append(s)
    for acc in a_res["accounts"]:
        profile.setdefault("social_profiles", []).append({"platform": f"Registered Account ({acc})", "url": f"https://{acc}"})
    if b_res["breach_list"]:
        profile["criminal_records"] = [f"⚠️ BREACH EXPOSURE: {b}" for b in b_res["breach_list"]] + profile.get("criminal_records", [])

    loc_query = profile.get("primary_address") if profile.get("primary_address") not in ["", "Unknown", "Not found"] else profile.get("location")
    detected_loc = geocode_location(loc_query)
    return {"profile": profile, "report": profile.get("summary_markdown", ""), "map_data": detected_loc}

def run_photo_investigation(uploaded_image, context_notes: str, api_key: str) -> dict:
    client = Groq(api_key=api_key.strip())
    raw_img = Image.open(uploaded_image)
    w, h = raw_img.size
    phash = str(imagehash.phash(raw_img))
    fname = uploaded_image.name
    origin = "Meta CDN (Facebook/Instagram)" if re.search(r"^\d+_\d+_\d+_n\.(jpg|png)", fname.lower()) else "Standard Image File"
    exif_str = f"- **Dimensions:** {w}x{h} px\n- **Visual Fingerprint (pHash):** `{phash}`\n- **Origin:** {origin}"
    search_seed = context_notes.strip() if context_notes else fname.rpartition(".")
    soc_hits = deep_web_search(f'"{search_seed}" site:facebook.com OR site:instagram.com OR site:tiktok.com OR site:linkedin.com OR site:x.com', 7)

    prompt = f"""
    DeepSight Visual & Social Analyst. First line ONLY: LOCATION: <City, Country or NONE>
    FILE FORENSICS:\n{exif_str}\nCONTEXT: {context_notes}\nLIVE SOCIAL WEB MATCHES:\n{soc_hits[:2500]}
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
