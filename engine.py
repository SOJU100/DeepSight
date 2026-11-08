import base64, io, re, subprocess
from concurrent.futures import ThreadPoolExecutor
import dns.resolver, phonenumbers
from phonenumbers import geocoder, carrier, timezone
from geopy.geocoders import Nominatim
from PIL import Image, ExifTags
from groq import Groq
from langchain_community.tools import DuckDuckGoSearchRun

def web_search(query: str) -> str:
    try:
        return DuckDuckGoSearchRun().run(query)
    except Exception as e:
        return f"Search note: {str(e)}"

def geocode_location(loc_text: str):
    if not loc_text or loc_text.strip().upper() == "NONE":
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
        return "Skipped (not an email)."
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
    s1 = web_search(f'"{raw}" OR "{h}" site:facebook.com OR site:instagram.com OR site:tiktok.com OR site:x.com OR site:threads.net')
    s2 = web_search(f'"{raw}" OR "{h}" site:linkedin.com OR site:youtube.com OR site:reddit.com OR site:github.com OR site:t.me')
    return f"MAIGRET:\n{m_out[:1200]}\nSOCIALS:\n{s1[:1000]}\n{s2[:1000]}"

def agent_phone(target: str) -> str:
    digits = re.sub(r"[^\d+]", "", target)
    if len(digits) < 7:
        return "No phone number in target."
    meta = f"Raw: {digits}"
    try:
        p = phonenumbers.parse(digits if digits.startswith("+") else f"+{digits}", None)
        if phonenumbers.is_valid_number(p):
            meta = f"Number: {phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.INTERNATIONAL)} | Region: {geocoder.description_for_number(p, 'en')} | Carrier: {carrier.name_for_number(p, 'en') or 'Unknown'} | TZ: {', '.join(timezone.time_zones_for_number(p))}"
    except Exception:
        pass
    dork = web_search(f'"{target}" OR "{digits}" "owner" OR "caller" OR "address" OR site:truecaller.com OR site:whitepages.com')
    return f"{meta}\nDIRECTORY:\n{dork[:1200]}"

def agent_people_criminal(target: str, handle: str) -> str:
    addr = web_search(f'"{target}" OR "{handle}" "address" OR "relatives" OR site:spokeo.com OR site:beenverified.com OR site:truepeoplesearch.com')
    crim = web_search(f'"{target}" OR "{handle}" "court" OR "docket" OR "criminal" OR "arrest" OR "warrant" OR "lawsuit" OR site:judiciary.gov.ph OR site:courtlistener.com')
    return f"PEOPLE & ADDRESS:\n{addr[:1300]}\nCOURT & CRIMINAL:\n{crim[:1300]}"

def agent_breach_dns(target: str, handle: str) -> str:
    leak = web_search(f'"{target}" OR "{handle}" "breach" OR "leaked" OR "database" OR "password" OR site:pastebin.com')
    dns_info = ""
    if "@" in target:
        dom = target.split("@").lower()
        try:
            mx = [str(r.exchange) for r in dns.resolver.resolve(dom, "MX")]
            dns_info = f"Domain: {dom} | MX: {', '.join(mx)}"
        except Exception:
            dns_info = f"Domain: {dom}"
    return f"{dns_info}\nBREACHES:\n{leak[:1200]}"

def run_text_investigation(target: str, mode: str, api_key: str) -> dict:
    client = Groq(api_key=api_key.strip())
    target = target.strip()
    handle = target.split("@") if "@" in target else target.lstrip("@")
    with ThreadPoolExecutor(max_workers=5) as ex:
        f1 = ex.submit(agent_email, target)
        f2 = ex.submit(agent_socials, handle, target)
        f3 = ex.submit(agent_phone, target)
        f4 = ex.submit(agent_people_criminal, target, handle)
        f5 = ex.submit(agent_breach_dns, target, handle)
        r1, r2, r3, r4, r5 = f1.result(), f2.result(), f3.result(), f4.result(), f5.result()

    prompt = f"""
    Chief Intelligence Officer for DeepSight. Synthesize all reconnaissance on '{target}' (Mode: {mode}).
    On the VERY FIRST LINE output ONLY: LOCATION: <City, Country or Street Address or NONE>
    --- EMAIL ---\n{r1}\n--- SOCIALS ---\n{r2}\n--- PHONE ---\n{r3}\n--- PEOPLE & CRIMINAL ---\n{r4}\n--- BREACH & DNS ---\n{r5}
    After LOCATION, format with Markdown headers:
    ### 1. Executive Identity Summary (Country, Location & Confidence)
    ### 2. Contact Intelligence (Phone Numbers, Carriers, Emails & Physical Addresses)
    ### 3. Complete Social Media & Online Footprint
    ### 4. Open Criminal, Court & Legal Records
    ### 5. Breaches, Relatives & Recommended Follow-Up Dorks
    """
    comp = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}])
    raw_text = comp.choices.message.content
    detected_loc, clean_lines = None, []
    for line in raw_text.splitlines():
        if line.strip().startswith("LOCATION:"):
            detected_loc = geocode_location(line.split("LOCATION:", 1).strip())
        else:
            clean_lines.append(line)
    if not detected_loc and any(k in target.lower() for k in ["street", "st.", "ave", "road", "city", "davao", "manila"]):
        detected_loc = geocode_location(target)
    return {"report": "\n".join(clean_lines).strip(), "map_data": detected_loc}

def run_photo_investigation(uploaded_image, context_notes: str, api_key: str) -> dict:
    client = Groq(api_key=api_key.strip())
    raw_img = Image.open(uploaded_image)
    exif_str = "No EXIF metadata."
    try:
        ex = raw_img._getexif()
        if ex:
            tags = [f"- **{ExifTags.TAGS.get(k, k)}:** {v}" for k, v in ex.items() if ExifTags.TAGS.get(k, k) in ["Make", "Model", "DateTimeOriginal", "Software", "GPSInfo"]]
            if tags:
                exif_str = "\n".join(tags)
    except Exception:
        pass
    img = raw_img.convert("RGB")
    img.thumbnail((512, 512))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    prompt = f"Senior OSINT Visual Analyst. First line ONLY: LOCATION: <City, Country or NONE>\nEXIF:\n{exif_str}\nContext: {context_notes}\nSections: ### 1. EXIF & Assessment ### 2. Visual Forensics ### 3. Geolocation Clues ### 4. Reverse-Search Dorks"
    v_rep = ""
    for m in ["qwen/qwen3.8-27b", "meta-llama/llama-4-maverick-17b-128e-instruct"]:
        try:
            c = client.chat.completions.create(model=m, messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}])
            v_rep = c.choices.message.content
            break
        except Exception as e:
            v_rep = f"LOCATION: NONE\n⚠️ Vision note: {str(e)}"
    detected_loc, clean_lines = None, []
    for line in v_rep.splitlines():
        if line.strip().startswith("LOCATION:"):
            detected_loc = geocode_location(line.split("LOCATION:", 1).strip())
        else:
            clean_lines.append(line)
    links = "\n---\n### 🔗 One-Click Reverse Image Search\n* **[Google Lens](https://google.com)** | **[Yandex Images](https://yandex.com)** | **[TinEye](https://tineye.com)**"
    return {"report": "\n".join(clean_lines).strip() + links, "map_data": detected_loc}
