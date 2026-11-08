import os
import subprocess
from datetime import datetime
import streamlit as st
from PIL import Image
import google.generativeai as genai
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

APP_NAME = "DeepSight"
st.set_page_config(page_title=f"{APP_NAME} — Intelligence Platform", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    [data-testid="stSidebar"] { background-color: #0f1523; border-right: 1px solid #1e293b; }
    .kpi-card { background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 18px 20px; margin-bottom: 10px; }
    .kpi-label { font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px; }
    .kpi-value-blue { font-size: 28px; font-weight: 800; color: #3b82f6; }
    .kpi-value-orange { font-size: 28px; font-weight: 800; color: #f59e0b; }
    .kpi-value-green { font-size: 28px; font-weight: 800; color: #10b981; }
    .kpi-value-white { font-size: 28px; font-weight: 800; color: #f8fafc; }
    .kpi-sub { font-size: 12px; color: #64748b; margin-top: 2px; }
    .mode-card { background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; height: 135px; }
    .mode-title { font-size: 13px; font-weight: 700; letter-spacing: 0.5px; color: #f8fafc; margin-bottom: 6px; }
    .mode-desc { font-size: 12px; color: #94a3b8; line-height: 1.4; }
    .section-header { font-size: 12px; font-weight: 700; letter-spacing: 1.2px; color: #64748b; text-transform: uppercase; margin-top: 20px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

if "investigations" not in st.session_state:
    st.session_state.investigations = []
if "active_mode" not in st.session_state:
    st.session_state.active_mode = "Full Investigation"

with st.sidebar:
    st.markdown(f"### 🛡️ {APP_NAME}")
    st.caption("INTELLIGENCE PLATFORM")
    st.divider()

    nav = st.radio("NAVIGATION", ["📊 Dashboard", "🔍 Investigations", "🔑 API & Settings"], label_visibility="collapsed")
    st.divider()

    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("● API ACTIVE (Encrypted Vault)")
    else:
        api_key = st.text_input("Google Gemini API Key (Free)", type="password", placeholder="Paste Gemini key...")
        if api_key:
            st.success("● API ACTIVE")
        else:
            st.warning("● API INACTIVE — Add key in Secrets")

@tool("Email Footprint Scanner")
def scan_email(email: str) -> str:
    """Checks where an email address is registered across 100+ websites using Holehe."""
    try:
        result = subprocess.run(["holehe", email, "--only-used"], capture_output=True, text=True, timeout=60)
        return result.stdout if result.stdout else "No public registrations found."
    except Exception as e:
        return f"Scan note: {str(e)}"

@tool("Web & Public Records Search")
def web_search(query: str) -> str:
    """Searches the open web for public mentions, social profiles, and records."""
    search = DuckDuckGoSearchRun()
    return search.run(query)

def run_text_investigation(target: str, mode: str, gemini_key: str) -> str:
    gemini_llm = LLM(model="gemini/gemini-2.5-flash", api_key=gemini_key)

    footprint_agent = Agent(
        role="Digital Footprint Specialist",
        goal="Discover online accounts, handles, and services linked to the target.",
        backstory="Senior OSINT analyst mapping digital footprints across platforms.",
        tools=[scan_email],
        llm=gemini_llm,
        verbose=False
    )

    web_agent = Agent(
        role="Open Web & Records Researcher",
        goal="Find public mentions, social profiles, and background context on the target.",
        backstory="Specialist in search engine dorking and public records discovery.",
        tools=[web_search],
        llm=gemini_llm,
        verbose=False
    )

    analyst_agent = Agent(
        role="Lead Intelligence Analyst",
        goal="Compile findings into a structured, high-confidence intelligence dossier.",
        backstory="Synthesizes raw intelligence into clean, source-linked operational reports.",
        llm=gemini_llm,
        verbose=False
    )

    t1 = Task(
        description=f"Scan '{target}' using Email Footprint Scanner to uncover registered platforms.",
        expected_output="List of registered websites and services.",
        agent=footprint_agent
    )
    t2 = Task(
        description=f"Search the open web for '{target}', associated usernames, social profiles, and public records.",
        expected_output="Detailed summary of web mentions, links, and identity clues.",
        agent=web_agent
    )
    t3 = Task(
        description=f"Generate a formal Markdown Intelligence Dossier for '{target}' (Mode: {mode}). Include: Executive Summary, Verified Accounts, Open Web Intelligence, and Confidence Score.",
        expected_output="Structured Markdown intelligence dossier.",
        agent=analyst_agent
    )

    crew = Crew(agents=[footprint_agent, web_agent, analyst_agent], tasks=[t1, t2, t3], process=Process.sequential)
    return str(crew.kickoff())

def run_photo_investigation(uploaded_image, context_notes: str, gemini_key: str) -> str:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    img = Image.open(uploaded_image)
    prompt = f"""
    You are an expert OSINT Geolocation and Visual Intelligence Analyst.
    Analyze this image thoroughly for open-source intelligence clues:
    1. **Geolocation & Environment Clues:** Architecture, signage, language, vegetation, weather, road markings, or landmarks.
    2. **Identifying Details:** Logos, uniforms, badges, license plate formats, or device models.
    3. **Recommended Reverse-Search Queries:** Exact search terms and visual dorks to run next.
    Additional Investigator Context: {context_notes if context_notes else 'None provided'}
    Format the output as a clean, structured Markdown Intelligence Report.
    """
    response = model.generate_content([prompt, img])
    return response.text

if nav == "🔑 API & Settings":
    st.markdown('<div class="section-header">// API ACCESS & CONFIGURATION</div>', unsafe_allow_html=True)
    st.info("Your API key is managed securely via Streamlit Secrets or the left sidebar.")
    st.markdown("- **Engine Model:** `gemini-2.5-flash`\n- **Footprint Scanner:** `Holehe`\n- **Web Dorking:** `DuckDuckGo Search`\n- **Visual OSINT:** `Gemini Multimodal Vision`")

elif nav == "🔍 Investigations":
    st.markdown('<div class="section-header">// CASE ARCHIVE & REPORTS</div>', unsafe_allow_html=True)
    if not st.session_state.investigations:
        st.info("No completed investigations in this session yet. Launch one from the Dashboard.")
    else:
        for idx, case in enumerate(reversed(st.session_state.investigations)):
            with st.expander(f"📁 [{case['time']}] {case['mode']} — Target: {case['target']}", expanded=(idx == 0)):
                st.markdown(case["report"])
                st.download_button("📥 Export Markdown Dossier", data=case["report"], file_name=f"deepsight_{case['target']}.md", mime="text/markdown", key=f"dl_{idx}")

else:
    top_l, top_r = st.columns([3, 1])
    with top_l:
        st.markdown("## // OPERATIONS")
        st.caption("Command center — live intelligence overview")
    with top_r:
        st.write("")
        if st.button("➕ NEW INVESTIGATION", use_container_width=True, type="primary"):
            st.session_state.active_mode = "Full Investigation"

    total_cases = len(st.session_state.investigations)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">YOUR TOTAL</div><div class="kpi-value-blue">{total_cases}</div><div class="kpi-sub">investigations</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown('<div class="kpi-card"><div class="kpi-label">LIVE QUEUE</div><div class="kpi-value-orange">0</div><div class="kpi-sub">active agents</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">ORG TOTAL</div><div class="kpi-value-green">{total_cases}</div><div class="kpi-sub">all analysts</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">TODAY</div><div class="kpi-value-white">{total_cases}</div><div class="kpi-sub">new cases</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">// SELECT INVESTIGATION MODULE</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown('<div class="mode-card"><div class="mode-title">➕ FULL INVESTIGATION</div><div class="mode-desc">Deep multi-source sweep across registered accounts, public records, and open web mentions.</div></div>', unsafe_allow_html=True)
        if st.button("Select Full Investigation", use_container_width=True):
            st.session_state.active_mode = "Full Investigation"
    with m2:
        st.markdown('<div class="mode-card"><div class="mode-title">🖼️ START FROM A PHOTO</div><div class="mode-desc">Analyze an image for geolocation clues, landmarks, signage, and reverse-search leads.</div></div>', unsafe_allow_html=True)
        if st.button("Select Photo Intel", use_container_width=True):
            st.session_state.active_mode = "Start From a Photo"
    with m3:
        st.markdown('<div class="mode-card"><div class="mode-title">👤 SOCIAL PROFILE SEARCH</div><div class="mode-desc">Find social media accounts and online handles tied to an email address or username.</div></div>', unsafe_allow_html=True)
        if st.button("Select Social Search", use_container_width=True):
            st.session_state.active_mode = "Social Profile Search"

