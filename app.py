import os
import subprocess
import streamlit as st
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

# --- BRANDING & PAGE SETUP (Change "TraceLens" to any name you want) ---
APP_NAME = "DeepSight"
st.set_page_config(page_title=f"{APP_NAME} — Intelligence Dashboard", page_icon="🔎", layout="wide")

st.title(f"🔎 {APP_NAME} — Automated Intelligence Investigations")
st.markdown("Enter an email address to run multi-agent footprint mapping and web reconnaissance.")

# --- SIDEBAR: SETTINGS & API KEY ---
with st.sidebar:
    st.header("⚙️ System Settings")
    api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    st.info("Your API key is only used in memory for this session and is never stored.")
    
    st.divider()
    st.subheader("Investigation Agents")
    st.markdown("- **Footprint Scanner:** Checks 100+ platforms via Holehe")
    st.markdown("- **Web Researcher:** Searches public web mentions & records")
    st.markdown("- **Intelligence Analyst:** Verifies & writes the final report")

# --- DEFINE OSINT TOOLS ---
@tool("Email Footprint Scanner")
def scan_email(email: str) -> str:
    """Checks where an email address is registered across 100+ websites using Holehe."""
    try:
        result = subprocess.run(
            ["holehe", email, "--only-used"],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout if result.stdout else "No public registrations found."
    except Exception as e:
        return f"Error running email scan: {str(e)}"

@tool("Web & Public Records Search")
def web_search(query: str) -> str:
    """Searches the open web for public mentions, social profiles, and records."""
    search = DuckDuckGoSearchRun()
    return search.run(query)

# --- INVESTIGATION ENGINE ---
def run_investigation(target_email: str):
    footprint_agent = Agent(
        role="Digital Footprint Specialist",
        goal="Discover online accounts and services linked to the target email.",
        backstory="Expert investigator mapping digital footprints using automated reconnaissance tools.",
        tools=[scan_email],
        verbose=False
    )

    web_agent = Agent(
        role="Open Web & Records Researcher",
        goal="Find public mentions, social profiles, and background context on the target.",
        backstory="Specialist in search engine dorking and public records discovery.",
        tools=[web_search],
        verbose=False
    )

    analyst_agent = Agent(
        role="Lead Intelligence Analyst",
        goal="Cross-reference findings, filter false positives, and write a clean report.",
        backstory="Synthesizes raw intelligence data into structured, source-linked reports.",
        verbose=False
    )

    task1 = Task(
        description=f"Scan '{target_email}' with Email Footprint Scanner to find registered platforms.",
        expected_output="A clean list of websites and services where the email is registered.",
        agent=footprint_agent
    )

    task2 = Task(
        description=f"Search the web for '{target_email}' and any usernames derived from it. Look for social profiles, forums, or public records.",
        expected_output="A summary of web mentions, links, and potential names or locations.",
        agent=web_agent
    )

    task3 = Task(
        description=f"Combine all findings for '{target_email}' into a structured Markdown intelligence report with sections: Executive Summary, Registered Accounts, Web & Social Mentions, and Confidence Assessment.",
        expected_output="A complete, well-formatted Markdown report.",
        agent=analyst_agent
    )

    crew = Crew(
        agents=[footprint_agent, web_agent, analyst_agent],
        tasks=[task1, task2, task3],
        process=Process.sequential
    )

    result = crew.kickoff()
    return str(result)

# --- MAIN DASHBOARD INTERFACE ---
col1, col2 = st.columns([3, 1])
with col1:
    target_input = st.text_input("Target Identifier (Email Address)", placeholder="target@example.com")
with col2:
    st.write("")
    st.write("")
    launch_btn = st.button("🚀 Start Scan", use_container_width=True, type="primary")

if launch_btn:
    if not api_key:
        st.error("Please enter your OpenAI API Key in the left sidebar first.")
    elif not target_input or "@" not in target_input:
        st.warning("Please enter a valid target email address.")
    else:
        os.environ["OPENAI_API_KEY"] = api_key
        
        with st.status("🔎 Deploying AI Agents...", expanded=True) as status:
            st.write("🔍 **Agent 1 (Footprint):** Scanning platform registrations...")
            st.write("🌐 **Agent 2 (Web Research):** Searching open web and public records...")
            st.write("🧠 **Agent 3 (Lead Analyst):** Cross-referencing data and writing report...")
            
            try:
                final_report = run_investigation(target_input)
                status.update(label="✅ Investigation Complete!", state="complete", expanded=False)
                
                st.divider()
                st.subheader(f"📄 {APP_NAME} Report: {target_input}")
                st.markdown(final_report)
                
                st.download_button(
                    label="📥 Download Report (.md)",
                    data=final_report,
                    file_name=f"{APP_NAME.lower()}_report_{target_input}.md",
                    mime="text/markdown"
                )
            except Exception as e:
                status.update(label="❌ Investigation Failed", state="error")
                st.error(f"An error occurred: {str(e)}")
