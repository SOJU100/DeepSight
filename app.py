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
    [data-testid="stPopover"] > button {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        padding: 10px 18px !important;
        width: 100%;
    }
    [data-testid="stPopoverBody"] {
        background-color: #0f1523 !important;
        border: 1px solid #1e293b !important;
        border-radius: 10px !important;
        padding: 16px !important;
        min-width: 320px !important;
    }
    .kpi-card { background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 18px 20px; margin-bottom: 10px; }
    .kpi-label { font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px; }
    .kpi-value-blue { font-size: 28px; font-weight: 800; color: #3b82f6; }
    .kpi-value-orange { font-size: 28px; font-weight: 800; color: #f59e0b; }
    .kpi-value-green { font-size: 28px; font-weight: 800; color: #10b981; }
    .kpi-value-white { font-size: 28px; font-weight: 800; color: #f8fafc; }
    .kpi-sub { font-size: 12px; color: #64748b; margin-top: 2px; }
    .mode-card { background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; height: 130px; margin-bottom: 8px; }
    .mode-title { font-size: 13px; font-weight: 700; letter-spacing: 0.5px; color: #f8fafc; margin-bottom: 6px; }
    .mode-desc { font-size: 12px; color: #94a3b8; line-height: 1.4; }
    .section-header { font-size: 12px; font-weight: 700; letter-spacing: 1.2px; color: #64748b; text-transform: uppercase; margin-top: 20px; margin-bottom: 10px; }
    .menu-item-box { background-color: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; margin-bottom: 6px; }
    .menu-title { font-size: 13px; font-weight: 800; color: #f8fafc; }
    .menu-sub { font-size: 11px; color: #94a3b8; margin-top: 3px; line-height: 1.3; }
    .menu-badge { font-size: 10px; font-weight: 700; color: #10b981; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

if "investigations" not in st.session_state:
    st.session_state.investigations = []

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

@st.dialog("🚀 Launch Investigation", width="large")
def open_investigation_modal(selected_mode="Full Investigation"):
    st.caption(f"// ACTIVE OPERATION TYPE: {selected_mode.upper()}")

    if selected_mode == "Start From a Photo":
        uploaded_file = st.file_uploader("Upload Target Image (JPG, PNG)", type=["jpg", "jpeg", "png"])
        photo_context = st.text_input("Optional Context", placeholder="e.g., Taken near a coastal highway...")
        if st.button("🛰️ Run Visual Intelligence Scan", type="primary", use_container_width=True):
            if not api_key:
                st.error("API key missing. Add GEMINI_API_KEY in Streamlit Secrets.")
            elif not uploaded_file:
                st.warning("Please upload an image first.")
            else:
                with st.status("Analyzing image clues...", expanded=True) as status:
                    try:
                        report = run_photo_investigation(uploaded_file, photo_context, api_key)
                        st.session_state.investigations.append({"time": datetime.now().strftime("%H:%M"), "mode": "Photo Intel", "target": uploaded_file.name, "report": report})
                        status.update(label="✅ Complete!", state="complete")
                        st.rerun()
                    except Exception as e:
                        status.update(label="❌ Failed", state="error")
                        st.error(f"Error: {str(e)}")
    else:
        placeholder = "target@example.com" if selected_mode == "Full Investigation" else "target@example.com or @username"
        target_input = st.text_input("Target Identifier", placeholder=placeholder)
        if st.button("🛰️ Deploy AI Agents", type="primary", use_container_width=True):
            if not api_key:
                st.error("API key missing. Add GEMINI_API_KEY in Streamlit Secrets.")
            elif not target_input:
                st.warning("Please enter a target email or username.")
            else:
                os.environ["GEMINI_API_KEY"] = api_key
                with st.status(f"Deploying {selected_mode} Agents...", expanded=True) as status:
                    st.write("🔍 **Footprint Scanner:** Checking platform registrations...")
                    st.write("🌐 **Web Researcher:** Querying open web & public records...")
                    st.write("🧠 **Lead Analyst:** Compiling final intelligence dossier...")
                    try:
                        report = run_text_investigation(target_input, selected_mode, api_key)
                        st.session_state.investigations.append({"time": datetime.now().strftime("%H:%M"), "mode": selected_mode, "target": target_input, "report": report})
                        status.update(label="✅ Investigation Complete!", state="complete")
                        st.rerun()
                    except Exception as e:
