import base64
import io
import subprocess
from PIL import Image
from groq import Groq
from langchain_community.tools import DuckDuckGoSearchRun

def scan_email(email: str) -> str:
    try:
        result = subprocess.run(["holehe", email, "--only-used"], capture_output=True, text=True, timeout=45)
        return result.stdout if result.stdout else "No public registrations found."
    except Exception as e:
        return f"Footprint scan note: {str(e)}"

def web_search(query: str) -> str:
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        return f"Web search note: {str(e)}"

def get_best_text_model(client: Groq) -> str:
    preferred = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.1-8b-instant"]
    try:
        available = [m.id for m in client.models.list().data]
        for p in preferred:
            if p in available:
                return p
        for m in available:
            if "whisper" not in m and "guard" not in m and "orpheus" not in m:
                return m
    except Exception:
        pass
    return "openai/gpt-oss-20b"

def run_text_investigation(target: str, mode: str, api_key: str) -> str:
    client = Groq(api_key=api_key.strip())
    model_id = get_best_text_model(client)
    
    footprint_data = scan_email(target) if "@" in target else "Username target — skipping email-only scan."
    web_data = web_search(f'"{target}"')
    social_data = web_search(f'"{target}" site:linkedin.com OR site:instagram.com OR site:x.com OR site:github.com')

    prompt = f"""
    You are a Lead OSINT Intelligence Analyst. Compile the raw reconnaissance data below into a structured, high-confidence Markdown Intelligence Dossier for target: '{target}' (Operation Mode: {mode}).

    RAW FOOTPRINT DATA (Holehe):
    {footprint_data[:2500]}

    RAW OPEN WEB MENTIONS:
    {web_data[:2500]}

    RAW SOCIAL PROFILE MENTIONS:
    {social_data[:2500]}

    Format your report with these exact Markdown sections:
    ### 1. Executive Summary
    ### 2. Verified Accounts & Registrations
    ### 3. Social Media & Open Web Footprint
    ### 4. Confidence Assessment & Next Steps
    """
    completion = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

def run_photo_investigation(uploaded_image, context_notes: str, api_key: str) -> str:
    client = Groq(api_key=api_key.strip())
    
    img = Image.open(uploaded_image).convert("RGB")
    img.thumbnail((512, 512))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    prompt = f"""
    You are an expert OSINT Geolocation and Visual Intelligence Analyst.
    Analyze this image for geolocation clues, landmarks, signage, environment, logos, and reverse-search leads.
    Additional Context: {context_notes if context_notes else 'None provided'}
    Format the output as a clean Markdown Intelligence Report.
    """
    for model_id in ["qwen/qwen3.8-27b", "meta-llama/llama-4-maverick-17b-128e-instruct"]:
        try:
            completion = client.chat.completions.create(
                model=model_id,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }]
            )
            return completion.choices[0].message.content
        except Exception as e:
            last_err = str(e)
            continue
    return f"⚠️ Vision scan notice: {last_err}"
