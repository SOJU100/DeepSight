import subprocess
from PIL import Image
import google.generativeai as genai
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

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
    a1 = Agent(role="Footprint Specialist", goal="Find accounts linked to target.", backstory="OSINT footprint analyst.", tools=[scan_email], llm=gemini_llm, verbose=False)
    a2 = Agent(role="Web Researcher", goal="Find web mentions and records.", backstory="Open-web OSINT researcher.", tools=[web_search], llm=gemini_llm, verbose=False)
    a3 = Agent(role="Lead Analyst", goal="Write a structured Markdown dossier.", backstory="Senior intelligence analyst.", llm=gemini_llm, verbose=False)
    t1 = Task(description=f"Scan '{target}' with Email Footprint Scanner.", expected_output="List of registered platforms.", agent=a1)
    t2 = Task(description=f"Search web for '{target}' profiles and public records.", expected_output="Web mentions and clues.", agent=a2)
    t3 = Task(description=f"Write a Markdown Intelligence Dossier for '{target}' ({mode}) with Executive Summary, Verified Accounts, Web Intelligence, and Confidence Score.", expected_output="Markdown report.", agent=a3)
    return str(Crew(agents=[a1, a2, a3], tasks=[t1, t2, t3], process=Process.sequential).kickoff())

def run_photo_investigation(uploaded_image, context_notes: str, gemini_key: str) -> str:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    img = Image.open(uploaded_image)
    prompt = f"Analyze this image as an OSINT geolocation & visual analyst (landmarks, signage, environment, logos, reverse-search leads). Context: {context_notes}. Output clean Markdown."
    return model.generate_content([prompt, img]).text

