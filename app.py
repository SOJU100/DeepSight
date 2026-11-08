import os
from datetime import datetime
import streamlit as st
from engine import run_text_investigation, run_photo_investigation

APP_NAME = "DeepSight"
st.set_page_config(page_title=f"{APP_NAME} — Intelligence Platform", page_icon="🛡️", layout="wide")

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

with st.sidebar:
    st.markdown(f"### 🛡️ {APP_NAME}")
    st.caption("INTELLIGENCE PLATFORM")
    if api_key:
    st.success("● API ACTIVE (Encrypted Vault)")
else:
    st.warning("● API INACTIVE")
    nav = st.radio("NAVIGATION", ["📊 Dashboard", "🔍 Investigations", "🔑 API & Settings"], label_visibility="collapsed")
    st.divider()
    api_key = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else st.text_input("Gemini API Key", type="password")
    st.success("● API ACTIVE (Encrypted Vault)") if api_key else st.warning("● API INACTIVE")

@st.dialog("🚀 Launch Investigation", width="large")
def open_modal(selected_mode="Full Investigation"):
    st.caption(f"// ACTIVE OPERATION TYPE: {selected_mode.upper()}")
    if selected_mode == "Start From a Photo":
        uploaded_file = st.file_uploader("Upload Target Image (JPG, PNG)", type=["jpg", "jpeg", "png"])
        ctx = st.text_input("Optional Context", placeholder="e.g., Taken near a coastal highway...")
        if st.button("🛰️ Run Visual Intelligence Scan", type="primary", use_container_width=True):
            if api_key and uploaded_file:
                with st.status("Analyzing image clues...", expanded=True):
                    report = run_photo_investigation(uploaded_file, ctx, api_key)
                    st.session_state.investigations.append({"time": datetime.now().strftime("%H:%M"), "mode": "Photo Intel", "target": uploaded_file.name, "report": report})
                    st.rerun()
    else:
        target = st.text_input("Target Identifier", placeholder="target@example.com")
        if st.button("🛰️ Deploy AI Agents", type="primary", use_container_width=True):
            if api_key and target:
                os.environ["GEMINI_API_KEY"] = api_key
                with st.status(f"Deploying {selected_mode} Agents...", expanded=True):
                    report = run_text_investigation(target, selected_mode, api_key)
                    st.session_state.investigations.append({"time": datetime.now().strftime("%H:%M"), "mode": selected_mode, "target": target, "report": report})
                    st.rerun()

if nav == "🔑 API & Settings":
    st.markdown('<div class="section-header">// API ACCESS & CONFIGURATION</div>', unsafe_allow_html=True)
    st.info("Engine: `gemini-2.5-flash` | Footprint: `Holehe` | Web: `DuckDuckGo` | Vision: `Gemini Multimodal`")

elif nav == "🔍 Investigations":
    st.markdown('<div class="section-header">// CASE ARCHIVE & REPORTS</div>', unsafe_allow_html=True)
    for idx, case in enumerate(reversed(st.session_state.investigations)):
        with st.expander(f"📁 [{case['time']}] {case['mode']} — {case['target']}", expanded=(idx == 0)):
            st.markdown(case["report"])

else:
    top_l, top_r = st.columns(2)
    with top_l:
        st.markdown("## // OPERATIONS")
        st.caption("Command center — live intelligence overview")
    with top_r:
        st.write("")
        with st.popover("➕ NEW INVESTIGATION"):
            st.markdown('<div style="font-size:11px; font-weight:700; color:#64748b; margin-bottom:8px;">// SELECT OPERATION TYPE</div>', unsafe_allow_html=True)
            st.markdown('<div class="menu-item-box"><div class="menu-title">➕ FULL INVESTIGATION</div><div class="menu-sub">Deep multi-source sweep across accounts, records, and web mentions.</div><div class="menu-badge">● FREE TIER READY</div></div>', unsafe_allow_html=True)
            if st.button("Launch Full Investigation", key="p1", use_container_width=True):
                open_modal("Full Investigation")
            st.markdown('<div class="menu-item-box" style="margin-top:8px;"><div class="menu-title">📷 START FROM A PHOTO</div><div class="menu-sub">Identify a subject or location from a photo using visual intel.</div><div class="menu-badge">● VISION ENGINE ACTIVE</div></div>', unsafe_allow_html=True)
            if st.button("Launch Photo Scan", key="p2", use_container_width=True):
                open_modal("Start From a Photo")
            st.markdown('<div class="menu-item-box" style="margin-top:8px;"><div class="menu-title">👤 SOCIAL PROFILE SEARCH</div><div class="menu-sub">Find social profiles registered to an email or handle.</div><div class="menu-badge">● 100+ PLATFORMS</div></div>', unsafe_allow_html=True)
            if st.button("Launch Social Search", key="p3", use_container_width=True):
                open_modal("Social Profile Search")

    total = len(st.session_state.investigations)
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="kpi-card"><div class="kpi-label">YOUR TOTAL</div><div class="kpi-value-blue">{total}</div><div class="kpi-sub">investigations</div></div>', unsafe_allow_html=True)
    k2.markdown('<div class="kpi-card"><div class="kpi-label">LIVE QUEUE</div><div class="kpi-value-orange">0</div><div class="kpi-sub">active agents</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="kpi-card"><div class="kpi-label">ORG TOTAL</div><div class="kpi-value-green">{total}</div><div class="kpi-sub">all analysts</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="kpi-card"><div class="kpi-label">TODAY</div><div class="kpi-value-white">{total}</div><div class="kpi-sub">new cases</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">// SELECT INVESTIGATION MODULE</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown('<div class="mode-card"><div class="mode-title">➕ FULL INVESTIGATION</div><div class="mode-desc">Deep multi-source sweep across registered accounts, public records, and open web mentions.</div></div>', unsafe_allow_html=True)
        if st.button("Select Full Investigation", key="c1", use_container_width=True):
            open_modal("Full Investigation")
    with m2:
        st.markdown('<div class="mode-card"><div class="mode-title">🖼️ START FROM A PHOTO</div><div class="mode-desc">Analyze an image for geolocation clues, landmarks, signage, and reverse-search leads.</div></div>', unsafe_allow_html=True)
        if st.button("Select Photo Intel", key="c2", use_container_width=True):
            open_modal("Start From a Photo")
    with m3:
        st.markdown('<div class="mode-card"><div class="mode-title">👤 SOCIAL PROFILE SEARCH</div><div class="mode-desc">Find social media accounts and online handles tied to an email address or username.</div></div>', unsafe_allow_html=True)
        if st.button("Select Social Search", key="c3", use_container_width=True):
            open_modal("Social Profile Search")

    st.markdown('<div class="section-header">// RECENT INVESTIGATIONS</div>', unsafe_allow_html=True)
    if not st.session_state.investigations:
        with st.container(border=True):
            st.markdown("<div style='text-align:center; padding: 25px; color: #64748b;'><b>NO INVESTIGATIONS YET</b><br><span style='font-size:12px;'>Click '+ NEW INVESTIGATION' at the top right to select an operation type.</span></div>", unsafe_allow_html=True)
    else:
        for idx, case in enumerate(reversed(st.session_state.investigations)):
            with st.expander(f"✅ [{case['time']}] {case['mode']} — {case['target']}", expanded=(idx == 0)):
                st.markdown(case["report"])
                st.download_button("📥 Download Dossier (.md)", data=case["report"], file_name=f"deepsight_{case['target']}.md", mime="text/markdown", key=f"d_{idx}")
