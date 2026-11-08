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
        return "⚠️ TAVILY_API_KEY missing in Streamlit Secrets."
    try:
        client = TavilyClient(api_key=tavily_key.strip())
        res = client.search(query=query, search_depth="advanced", max_results=max_res)
        snippets = [f"- {r.get('title', '')} ({r.get('url', '')}): {r.get('content', '')}" for r in res.get("results", [])]
        return "\n".join(snippets) if snippets else "No web results."
    except Exception as e:
        return f"Search error: {str(e)}"

def geocode_location(loc_text: str):
    if not loc_text or loc_text.strip().upper() in ["NONE", "UNKNOWN", "N/A", "NOT FOUND"]:
        return None
    try:
        loc = Nominatim(user_agent="deepsight_osint_v2").geocode(loc_text.strip(), timeout=10)
        if loc:
            return {"lat": loc.latitude, "lon": loc.longitude, "address": loc.address}
    except Exception:
        pass
    return None

def agent_1_breaches(target: str, handle: str) -> str:
    out = []
    if "@" in target:
        try:
            r = requests.get(f"https://xposedornot.com{target}", timeout=10)
            if r.status_code == 200:
                out.append(f"XPOSEDORNOT BREACHES: {r.json().get('breaches', [])}")
        except Exception:
            pass
        try:
            hr = requests.get(f"https://hudsonrock.com{target}", timeout=10)
            if hr.status_code == 200 and hr.json().get("stealers"):
                out.append(f"INFOSTEALER LOGS: {hr.json().get('stealers')}")
        except Exception:
            pass
    leak_web = deep_web_search(f'"{target}" OR "{handle}" "breach" OR "leaked" OR "database" OR "password" OR "combo" OR site:pastebin.com', 5)
    out.append(f"WEB LEAK MENTIONS:\n{leak_web[:1400]}")
    return "\n".join(out)

def agent_2_accounts_gravatar(target: str) -> str:
    if "@" not in target:
        return "Target is not an email."
    out = []
    try:
        md5_hash = hashlib.md5(target.strip().lower().encode("utf-8")).hexdigest()
        gr = requests.get(f"https://gravatar.com{md5_hash}.json", timeout=8)
        if gr.status_code == 200:
            entry = next(iter(gr.json().get("entry", [])), {})
            out.append(f"GRAVATAR IDENTITY: Name={entry.get('displayName')} | Location={entry.get('currentLocation')} | About={entry.get('aboutMe')} | URLs={entry.get('urls')}")
    except Exception:
        pass
    try:
        res = subprocess.run(["holehe", target, "--only-used"], capture_output=True, text=True, timeout=35)
        if res.stdout:
            out.append(f"HOLEHE REGISTRATIONS:\n{res.stdout[:1200]}")
    except Exception:
        pass
    return "\n".join(out) if out else "No direct email registrations."

def agent_3_people_brokers(target: str, handle: str) -> str:
    q1 = deep_web_search(f'"{target}" site:spokeo.com OR site:beenverified.com OR site:whitepages.com OR site:truepeoplesearch.com OR site:fastpeoplesearch.com OR site:radaris.com OR site:clustrmaps.com', 7)
    q2 = deep_web_search(f'"{target}" "address" "phone" "age" OR "born" OR "relatives" OR "associates"', 6)
    return f"PEOPLE DIRECTORIES:\n{q1[:1800]}\nRESIDENTIAL & RELATIVE CLUES:\n{q2[:1500]}"

def agent_4_social_graph(target: str, handle: str) -> str:
    h = handle.lstrip("@").strip()
    s1 = deep_web_search(f'"{target}" OR "{h}" site:facebook.com OR site:instagram.com OR site:tiktok.com OR site:x.com OR site:threads.net', 7)
    s2 = deep_web_search(f'"{target}" OR "{h}" site:linkedin.com OR site:github.com OR site:reddit.com OR site:youtube.com OR site:t.me OR site:pinterest.com', 7)
    return f"MAJOR SOCIALS:\n{s1[:1800]}\nPROFESSIONAL & FORUMS:\n{s2[:1600]}"

def agent_5_career_edu(target: str, handle: str) -> str:
    q = deep_web_search(f'"{target}" OR "{handle}" "University" OR "College" OR "Education" OR "Experience" OR "CEO" OR "Founder" OR "Manager" OR site:opencorporates.com', 6)
    return f"CAREER, EDUCATION & CORPORATE:\n{q[:1600]}"

def agent_6_criminal_court(target: str, handle: str) -> str:
    q = deep_web_search(f'"{target}" OR "{handle}" "court" OR "docket" OR "criminal" OR "arrest" OR "warrant" OR "lawsuit" OR "defendant" OR site:courtlistener.com OR site:judiciary.gov.ph OR site:unicourt.com', 6)
    return f"COURT & CRIMINAL RECORDS:\n{q[:1600]}"

def agent_8_infra_telecom(target: str) -> str:
    digits = re.sub(r"[^\d+]", "", target)
    out = []
    if len(digits) >= 7:
        try:
            p = phonenumbers.parse(digits if digits.startswith("+") else f"+{digits}", None)
            if phonenumbers.is_valid_number(p):
                out.append(f"TELECOM INTEL: {phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.INTERNATIONAL)} | Region: {geocoder.description_for_number(p, 'en')} | Carrier: {carrier.name_for_number(p, 'en') or 'Unknown'} | TZ: {', '.join(timezone.time_zones_for_number(p))}")
        except Exception:
            pass
    if "@" in target:
        _, dom = target.split("@", 1)
        dom = dom.lower()
        if dom not in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}:
            try:
                mx = [str(r.exchange) for r in dns.resolver.resolve(dom, "MX")]
                out.append(f"CUSTOM DOMAIN: {dom} | MX: {', '.join(mx)}")
            except Exception:
                pass
            try:
                crt = requests.get(f"https://crt.sh%.{dom}&output=json", timeout=8)
                if crt.status_code == 200:
                    subs = list({item.get("name_value", "") for item in crt.json()[:10]})
                    out.append(f"SSL SUBDOMAINS (crt.sh): {', '.join(subs[:8])}")
            except Exception:
                pass
    return "\n".join(out) if out else "Standard infrastructure."

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

    with ThreadPoolExecutor(max_workers=7) as ex:
        f1 = ex.submit(agent_1_breaches, target, handle)
        f2 = ex.submit(agent_2_accounts_gravatar, target)
        f3 = ex.submit(agent_3_people_brokers, target, handle)
        f4 = ex.submit(agent_4_social_graph, target, handle)
        f5 = ex.submit(agent_5_career_edu, target, handle)
        f6 = ex.submit(agent_6_criminal_court, target, handle)
        f8 = ex.submit(agent_8_infra_telecom, target)
        r1, r2, r3, r4, r5, r6, r8 = f1.result(), f2.result(), f3.result(), f4.result(), f5.result(), f6.result(), f8.result()

    wave1_blob = f"{r1}\n{r2}\n{r3}\n{r4}\n{r5}"
    found_emails = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", wave1_blob)))
    found_phones = list(set(re.findall(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", wave1_blob)))
    pivot_queries = [e for e in found_emails if e.lower() != target.lower()][:2] + found_phones[:2]
    r7_pivot = ""
    if pivot_queries:
        pivot_results = [deep_web_search(f'"{pq}"', 4) for pq in pivot_queries]
        r7_pivot = f"PIVOTED ON CLUES {pivot_queries}:\n" + "\n".join(pivot_results)[:1800]

    prompt = f"""
    DeepSight Chief Intelligence Officer. Synthesize all 8 OSINT agents into ONLY valid JSON matching the exact schema below. Include every real URL, address, phone number, email, username, relative, breach, and court record found (never invent fake details; use "Unknown" or [] if absent):
    {{"full_name": "", "location": "City, State/Country", "age": "", "dob": "", "aliases": [], "primary_address": "", "primary_phone": "", "primary_email": "", "job": "", "education": "", "addresses": [], "phones": [], "emails": [{{"email": "", "tag": "Personal/Work"}}], "social_profiles": [{{"platform": "", "url": ""}}], "usernames": [], "relatives": [], "criminal_records": [], "summary_markdown": "Comprehensive Markdown report covering all 8 agents, breach details, and source links"}}
    --- AGENT 1 (BREACHES & INFOSTEALERS) ---\n{r1}
    --- AGENT 2 (GRAVATAR & REGISTRATIONS) ---\n{r2}
    --- AGENT 3 (PEOPLE BROKERS & ADDRESSES) ---\n{r3}
    --- AGENT 4 (SOCIAL GRAPH) ---\n{r4}
    --- AGENT 5 (CAREER & EDUCATION) ---\n{r5}
    --- AGENT 6 (COURT & CRIMINAL) ---\n{r6}
    --- AGENT 7 (AUTOMATED CLUE PIVOT) ---\n{r7_pivot}
    --- AGENT 8 (TELECOM & DOMAIN RECON) ---\n{r8}
    """
    comp = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}])
    profile = parse_json_profile(next(iter(comp.choices)).message.content, target)
    loc_query = profile.get("primary_address") if profile.get("primary_address") not in ["", "Unknown", "Not found"] else profile.get("location")
    detected_loc = geocode_location(loc_query) or (geocode_location(target) if any(k in target.lower() for k in ["street", "st.", "ave", "road", "city", "davao", "manila", "il", "ca", "tx", "ny"]) else None)
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
