import os
from datetime import datetime
import pandas as pd
import streamlit as st
from engine import run_text_investigation, run_photo_investigation

APP_NAME = "DeepSight"
page_icon = "logo.png" if os.path.exists("logo.png") else "🛡️"
st.set_page_config(page_title=f"{APP_NAME} — Intelligence Platform", page_icon=page_icon, layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    [data-testid="stSidebar"] { background-color: #0f1523; border-right: 1px solid #1e293b; }
    [data-testid="stPopover"] > button { background-color: #3b82f6 !important; color: #fff !important; border: none !important; border-radius: 6px !important; font-weight: 700 !important; padding: 10px 18px !important; width: 100%; }
    [data-testid="stPopoverBody"] { background-color: #0f1523 !important; border: 1px solid #1e293b !important; border-radius: 10px !important; padding: 16px !important; min-width: 320px !important; }
    .kpi-card { background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 18px 20px; margin-bottom: 10px; }
    .kpi-label { font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px; }
    .kpi-value-blue { font-size: 28px; font-weight: 800; color: #3b82f6; }
    .kpi-value-orange { font-size: 28px; font-weight: 800; color: #f59e0b; }
    .kpi-value-green { font-size: 28px; font-weight: 800; color: #10b981; }
    .kpi-value-white { font-size: 28px; font-weight: 800; color: #f8fafc; }
    .kpi-sub { font-size: 12px; color: #64748b; margin-top: 2px; }
    .mode-card { background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; height: 130px; margin-bottom: 8px; }
    .mode-title { font-size: 13px; font-weight: 700; color: #f8fafc; margin-bottom: 6px; }
    .mode-desc { font-size: 12px; color: #94a3b8; line-height: 1.4; }
    .section-header { font-size: 12px; font-weight: 700; letter-spacing: 1.2px; color: #64748b; text-transform: uppercase; margin-top: 20px; margin-bottom: 10px; }
    .menu-item-box { background-color: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; margin-bottom: 6px; }
    .menu-title { font-size: 13px; font-weight: 800; color: #f8fafc; }
    .menu-sub { font-size: 11px; color: #94a3b8; margin-top: 3px; }
    .menu-badge { font-size: 10px; font-weight: 700; color: #10b981; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

if "investigations" not in st.session_state:
    st.session_state.investigations = []

def render_case_dossier(case: dict, key_prefix: str):
    if case.get("map_data"):
        md = case["map_data"]
        st.info(f"📍 **Geolocated Position:** {md['address']} (`{md['lat']:.4f}, {md['lon']:.4f}`)")
        st.map(pd.DataFrame([{"lat": md["lat"], "lon": md["lon"]}]), zoom=11)
    st.markdown(case["report"])
    st.download_button("📥 Download Full Dossier (.md)", data=case["report"], file_name=f"deepsight_{case['target']}.md", mime="text/markdown", key=key_prefix)

with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown(f"### 🛡️ {APP_NAME}")
    st.caption("INTELLIGENCE PLATFORM")
    st.divider()
    nav = st.radio("NAVIGATION", ["📊 Dashboard", "🔍 Investigations", "🔑 API & Settings"], label_visibility="collapsed")
    st.divider()
    api_key = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else st.text_input("API Key", type="password")
    if api_key:
        st.success("● API ACTIVE (Encrypted Vault)")
    else:
        st.warning("● API INACTIVE")

@st.dialog("🚀 Launch 7-Agent Investigation", width="large")
def open_modal(selected_mode="Full Investigation"):
    st.caption(f"// ACTIVE OPERATION TYPE: {selected_mode.upper()}")
    if selected_mode == "Start From a Photo":
        uploaded_file = st.file_uploader("Upload Target Image (JPG, PNG)", type=["jpg", "jpeg", "png"])
        ctx = st.text_input("Optional Context", placeholder="e.g., Suspect seen near a coastal highway...")
        if st.button("🛰️ Run Visual Intelligence Scan", type="primary", use_container_width=True):
            if api_key and uploaded_file:
                with st.status("Analyzing EXIF & visual geolocation clues...", expanded=True):
                    res = run_photo_investigation(uploaded_file, ctx, api_key)
                    st.session_state.investigations.append({"time": datetime.now().strftime("%H:%M"), "mode": "Photo Intel", "target": uploaded_file.name, "report": res["report"], "map_data": res["map_data"]})
                    st.rerun()
    else:
        target = st.text_input("Target Identifier (Email, Phone +CountryCode, Full Name, or Address)", placeholder="e.g., +639171234567, john@domain.com, or 'Juan Dela Cruz'")
        if st.button("🛰️ Deploy All 7 Intelligence Agents", type="primary", use_container_width=True):
            if api_key and target:
                os.environ["GEMINI_API_KEY"] = api_key
                with st.status(f"Deploying 7 Parallel Agents on '{target}'...", expanded=True):
                    st.write("🔍 **Agents 1 & 2:** Scanning emails, 200+ social networks & handles...")
                    st.write("📞 **Agents 3 & 4:** Running phone carrier lookup, address & people directories...")
                    st.write("⚖️ **Agents 5, 6 & 7:** Checking open court/criminal dockets, breaches & DNS...")
                    res = run_text_investigation(target, selected_mode, api_key)
                    st.session_state.investigations.append({"time": datetime.now().strftime("%H:%M"), "mode": selected_mode, "target": target, "report": res["report"], "map_data": res["map_data"]})
                    st.rerun()

if nav == "🔑 API & Settings":
    st.markdown('<div class="section-header">// 7-AGENT SYSTEM ARCHITECTURE</div>', unsafe_allow_html=True)
    st.info("Active Modules: Holehe | Maigret (200 Sites) | PhoneNumbers Telecom | Nominatim Map Geocoder | People Directories | Court & Criminal Dockets | Breach & DNS Recon")

elif nav == "🔍 Investigations":
    st.markdown('<div class="section-header">// CASE ARCHIVE & REPORTS</div>', unsafe_allow_html=True)
    if not st.session_state.investigations:
        st.info("No completed investigations yet.")
    for idx, case in enumerate(reversed(st.session_state.investigations)):
        with st.expander(f"📁 [{case['time']}] {case['mode']} — {case['target']}", expanded=(idx == 0)):
            render_case_dossier(case, f"arch_{idx}")

else:
    top_l, top_r = st.columns(2)
    with top_l:
        st.markdown("## // OPERATIONS")
        st.caption("Command center — 7-agent parallel intelligence suite")
    with top_r:
        st.write("")
        with st.popover("➕ NEW INVESTIGATION"):
            st.markdown('<div style="font-size:11px; font-weight:700; color:#64748b; margin-bottom:8px;">// SELECT OPERATION TYPE</div>', unsafe_allow_html=True)
            st.markdown('<div class="menu-item-box"><div class="menu-title">➕ FULL INVESTIGATION</div><div class="menu-sub">7-agent sweep: Phone, Address + Map, Email, All Socials & Court Records.</div><div class="menu-badge">● 7 AGENTS READY</div></div>', unsafe_allow_html=True)
            if st.button("Launch Full Investigation", key="p1", use_container_width=True):
                open_modal("Full Investigation")
            st.markdown('<div class="menu-item-box" style="margin-top:8px;"><div class="menu-title">📷 START FROM A PHOTO</div><div class="menu-sub">Extract EXIF metadata, geolocate clues on a map & generate reverse searches.</div><div class="menu-badge">● VISION + MAP ACTIVE</div></div>', unsafe_allow_html=True)
            if st.button("Launch Photo Scan", key="p2", use_container_width=True):
                open_modal("Start From a Photo")
            st.markdown('<div class="menu-item-box" style="margin-top:8px;"><div class="menu-title">👤 SOCIAL PROFILE SEARCH</div><div class="menu-sub">Deep 200-platform handle & social media account sweep.</div><div class="menu-badge">● 200+ PLATFORMS</div></div>', unsafe_allow_html=True)
            if st.button("Launch Social Search", key="p3", use_container_width=True):
                open_modal("Social Profile Search")

    total = len(st.session_state.investigations)
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="kpi-card"><div class="kpi-label">YOUR TOTAL</div><div class="kpi-value-blue">{total}</div><div class="kpi-sub">investigations</div></div>', unsafe_allow_html=True)
    k2.markdown('<div class="kpi-card"><div class="kpi-label">ACTIVE AGENTS</div><div class="kpi-value-orange">7</div><div class="kpi-sub">parallel engines</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="kpi-card"><div class="kpi-label">ORG TOTAL</div><div class="kpi-value-green">{total}</div><div class="kpi-sub">all analysts</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="kpi-card"><div class="kpi-label">TODAY</div><div class="kpi-value-white">{total}</div><div class="kpi-sub">new cases</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">// SELECT INVESTIGATION MODULE</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown('<div class="mode-card"><div class="mode-title">➕ FULL INVESTIGATION</div><div class="mode-desc">Phone lookup, street address map, email, social media accounts & open criminal records.</div></div>', unsafe_allow_html=True)
        if st.button("Select Full Investigation", key="c1", use_container_width=True):
            open_modal("Full Investigation")
    with m2:
        st.markdown('<div class="mode-card"><div class="mode-title">🖼️ START FROM A PHOTO</div><div class="mode-desc">Analyze an image for geolocation clues, landmarks, EXIF data & map coordinates.</div></div>', unsafe_allow_html=True)
        if st.button("Select Photo Intel", key="c2", use_container_width=True):
                        open_modal("Start From a Photo")
    with m3:
        st.markdown('<div class="mode-card"><div class="mode-title">👤 SOCIAL PROFILE SEARCH</div><div class="mode-desc">Find social media accounts across 200+ networks tied to an email, phone, or handle.</div></div>', unsafe_allow_html=True)
        if st.button("Select Social Search", key="c3", use_container_width=True):
            open_modal("Social Profile Search")

    st.markdown('<div class="section-header">// RECENT INVESTIGATIONS</div>', unsafe_allow_html=True)
    if not st.session_state.investigations:
        with st.container(border=True):
            st.markdown("<div style='text-align:center; padding: 25px; color: #64748b;'><b>NO INVESTIGATIONS YET</b><br><span style='font-size:12px;'>Enter a phone number (+63...), street address, email, or name to deploy all 7 agents.</span></div>", unsafe_allow_html=True)
    else:
        for idx, case in enumerate(reversed(st.session_state.investigations)):
            with st.expander(f"✅ [{case['time']}] {case['mode']} — {case['target']}", expanded=(idx == 0)):
                render_case_dossier(case, f"d_{idx}")

