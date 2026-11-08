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
    [data-testid="stPopover"] > button { background-color: #3b82f6 !important; color: #fff !important; border: none !important; border-radius: 6px !important; font-weight: 800 !important; padding: 10px 18px !important; width: 100%; }
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
    .bv-header { background-color: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 20px; margin-bottom: 12px; }
    .bv-name { font-size: 24px; font-weight: 800; color: #f8fafc; }
    .bv-loc { font-size: 14px; color: #3b82f6; font-weight: 600; margin-top: 4px; }
    .bv-lbl { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .bv-val { font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

if "investigations" not in st.session_state:
    st.session_state.investigations = []

def render_case_dossier(case: dict, key_prefix: str):
    p = case.get("profile")
    if p:
        aliases = ", ".join(p.get("aliases", [])) or "None listed"
        st.markdown(f'<div class="bv-header"><div class="bv-name">{p.get("full_name", case["target"])}</div><div class="bv-loc">📍 {p.get("location", "Location Unknown")}</div></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='bv-lbl'>Age</div><div class='bv-val'>{p.get('age', 'Unknown')}</div><div class='bv-lbl'>Date of Birth</div><div class='bv-val'>{p.get('dob', 'Unknown')}</div><div class='bv-lbl'>Aliases</div><div class='bv-val'>{aliases}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='bv-lbl'>Primary Address</div><div class='bv-val'>{p.get('primary_address', 'Not found')}</div><div class='bv-lbl'>Primary Phone</div><div class='bv-val'>{p.get('primary_phone', 'Not found')}</div><div class='bv-lbl'>Primary Email</div><div class='bv-val'>{p.get('primary_email', 'Not found')}</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='bv-lbl'>Job</div><div class='bv-val'>{p.get('job', 'No job found')}</div><div class='bv-lbl'>Education</div><div class='bv-val'>{p.get('education', 'Unknown')}</div>", unsafe_allow_html=True)
        if case.get("map_data"):
            st.map(pd.DataFrame([{"lat": case["map_data"]["lat"], "lon": case["map_data"]["lon"]}]), zoom=11)
        addrs = [str(a) if not isinstance(a, dict) else ", ".join(str(v) for v in a.values() if v) for a in p.get("addresses", [])]
        phones = [str(ph) if not isinstance(ph, dict) else ", ".join(str(v) for v in ph.values() if v) for ph in p.get("phones", [])]
        emails = p.get("emails", [])
        socials = p.get("social_profiles", [])
        unames = [str(u) for u in p.get("usernames", [])]
        rels = [str(r) if not isinstance(r, dict) else ", ".join(str(v) for v in r.values() if v) for r in p.get("relatives", [])]
        crim = [str(c) for c in p.get("criminal_records", [])]

        with st.expander(f"🏠 Addresses ({len(addrs)})", expanded=True):
            st.write(" · ".join(addrs) if addrs else p.get("primary_address", "None found"))
        with st.expander(f"📞 Phones ({len(phones)})", expanded=True):
            st.write(" · ".join(phones) if phones else p.get("primary_phone", "None found"))
        with st.expander(f"✉️ Emails ({len(emails)})", expanded=True):
            for em in emails:
                st.markdown(f"- **{em.get('email', em) if isinstance(em, dict) else em}**")
            if not emails:
                st.write(p.get("primary_email", "None found"))
        with st.expander(f"🌐 Social Profiles ({len(socials)})", expanded=True):
            for sp in socials:
                st.markdown(f"- **{sp.get('platform', 'Link')}:** [{sp.get('url', '')}]({sp.get('url', '')})" if isinstance(sp, dict) else f"- {sp}")
            if not socials:
                st.write("No direct social links confirmed.")
        with st.expander(f"🆔 Usernames ({len(unames)})"):
            st.write(", ".join(unames) if unames else "None found")
        with st.expander(f"👨‍👩‍👧‍👦 Family & Relatives ({len(rels)})"):
            st.write(" · ".join(rels) if rels else "None listed")
        with st.expander(f"⚖️ Criminal & Court Records ({len(crim)})", expanded=True):
            for item in crim:
                st.markdown(f"- {item}")
        if p.get("summary_markdown"):
            with st.expander("📋 Analyst Notes & Follow-Up Dorks"):
                st.markdown(p["summary_markdown"])
    else:
        if case.get("map_data"):
            st.info(f"📍 **Geolocated Position:** {case['map_data']['address']}")
            st.map(pd.DataFrame([{"lat": case["map_data"]["lat"], "lon": case["map_data"]["lon"]}]), zoom=11)
        st.markdown(case.get("report", ""))
    st.download_button("📥 Download Full Dossier (.md)", data=str(case.get("report", "")), file_name=f"deepsight_{case['target']}.md", mime="text/markdown", key=key_prefix)

with st.sidebar:
    st.image("logo.png", use_container_width=True)
    st.caption("INTELLIGENCE PLATFORM")
    
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

@st.dialog("🚀 Launch Investigation", width="large")
def open_modal(selected_mode="Full Investigation"):
    st.caption(f"// ACTIVE OPERATION TYPE: {selected_mode.upper()}")
    if selected_mode == "Start From a Photo":
        uploaded_file = st.file_uploader("Upload Target Image (JPG, PNG)", type=["jpg", "jpeg", "png"])
        ctx = st.text_input("Optional Context / Suspected Name or City", placeholder="e.g., Davao City or Marleen R. Avey...")
        if st.button("🛰️ Run Visual & Social Scan", type="primary", use_container_width=True):
            if api_key and uploaded_file:
                with st.status("Scanning image fingerprint & social media...", expanded=True):
                    res = run_photo_investigation(uploaded_file, ctx, api_key)
                    if isinstance(res, str):
                        res = {"profile": None, "report": res, "map_data": None}
                    st.session_state.investigations.append({"time": datetime.now().strftime("%H:%M"), "mode": "Photo Intel", "target": uploaded_file.name, "profile": res.get("profile"), "report": res.get("report", ""), "map_data": res.get("map_data")})
                    st.rerun()
    else:
        target = st.text_input("Target Identifier (Full Name, Email, Phone, or Address)", placeholder="e.g., Marleen R. Avey, dsdet35@hotmail.com, or (815) 335-0010")
        if st.button("🛰️ Deploy Intelligence Agents", type="primary", use_container_width=True):
            if api_key and target:
                os.environ["GEMINI_API_KEY"] = api_key
                with st.status(f"⚡ Working on it — Running DeepSight multi-agent sweep on '{target}'...", expanded=True):
                    res = run_text_investigation(target, selected_mode, api_key)
                    if isinstance(res, str):
                        res = {"profile": None, "report": res, "map_data": None}
                    st.session_state.investigations.append({"time": datetime.now().strftime("%H:%M"), "mode": selected_mode, "target": target, "profile": res.get("profile"), "report": res.get("report", ""), "map_data": res.get("map_data")})
                    st.rerun()

if nav == "🔑 API & Settings":
    st.markdown('<div class="section-header">// SYSTEM ARCHITECTURE</div>', unsafe_allow_html=True)
    st.info("Active Modules: Identity Resolution | Address & Map Geocoder | Phone Carrier Intel | Email & Social Profiles | Family & Relatives | Criminal & Court Dockets | Look-Alike Photo Intel")
elif nav == "🔍 Investigations":
    st.markdown('<div class="section-header">// CASE ARCHIVE & REPORTS</div>', unsafe_allow_html=True)
    for idx, case in enumerate(reversed(st.session_state.investigations)):
        with st.expander(f"📁 [{case['time']}] {case['mode']} — {case['target']}", expanded=(idx == 0)):
            render_case_dossier(case, f"arch_{idx}")
else:
    top_l, top_r = st.columns(2)
    with top_l:
        st.markdown("## // OPERATIONS")
        st.caption("Command center — live intelligence overview")
    with top_r:
        st.write("")
        with st.popover("➕ NEW INVESTIGATION"):
            st.markdown('<div style="font-size:11px; font-weight:700; color:#64748b; margin-bottom:8px;">// SELECT OPERATION TYPE</div>', unsafe_allow_html=True)
            st.markdown('<div class="menu-item-box"><div class="menu-title">➕ FULL INVESTIGATION</div><div class="menu-sub">Age, DOB, Aliases, Addresses + Map, Phones, Emails, Socials, Family & Court Records.</div><div class="menu-badge">● 7 AGENTS READY</div></div>', unsafe_allow_html=True)
            if st.button("Launch Full Investigation", key="p1", use_container_width=True):
                open_modal("Full Investigation")
            st.markdown('<div class="menu-item-box" style="margin-top:8px;"><div class="menu-title">📷 START FROM A PHOTO</div><div class="menu-sub">Scan Facebook & social networks + look-alike facial search links.</div><div class="menu-badge">● VISION + SOCIAL ACTIVE</div></div>', unsafe_allow_html=True)
            if st.button("Launch Photo Scan", key="p2", use_container_width=True):
                open_modal("Start From a Photo")
            st.markdown('<div class="menu-item-box" style="margin-top:8px;"><div class="menu-title">👤 SOCIAL PROFILE SEARCH</div><div class="menu-sub">Find social profiles & usernames tied to an email, phone, or handle.</div><div class="menu-badge">● 200+ PLATFORMS</div></div>', unsafe_allow_html=True)
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
        st.markdown('<div class="mode-card"><div class="mode-title">➕ FULL INVESTIGATION</div><div class="mode-desc">Structured profile: Age, DOB, Aliases, Addresses + Map, Phones, Emails, Socials, Family & Criminal Records.</div></div>', unsafe_allow_html=True)
        if st.button("Select Full Investigation", key="c1", use_container_width=True):
            open_modal("Full Investigation")
    with m2:
        st.markdown('<div class="mode-card"><div class="mode-title">🖼️ START FROM A PHOTO</div><div class="mode-desc">Scan Facebook & social networks + look-alike facial recognition links.</div></div>', unsafe_allow_html=True)
        if st.button("Select Photo Intel", key="c2", use_container_width=True):
            open_modal("Start From a Photo")
    with m3:
        st.markdown('<div class="mode-card"><div class="mode-title">👤 SOCIAL PROFILE SEARCH</div><div class="mode-desc">Find social media accounts & usernames across 200+ platforms.</div></div>', unsafe_allow_html=True)
        if st.button("Select Social Search", key="c3", use_container_width=True):
            open_modal("Social Profile Search")

    st.markdown('<div class="section-header">// RECENT INVESTIGATIONS</div>', unsafe_allow_html=True)
    if not st.session_state.investigations:
        with st.container(border=True):
            st.markdown("<div style='text-align:center; padding: 25px; color: #64748b;'><b>NO INVESTIGATIONS YET</b><br><span style='font-size:12px;'>Enter a Full Name, Email, Phone Number, or Address to build a complete profile dossier.</span></div>", unsafe_allow_html=True)
    else:
        for idx, case in enumerate(reversed(st.session_state.investigations)):
            with st.expander(f"✅ [{case['time']}] {case['mode']} — {case['target']}", expanded=(idx == 0)):
                render_case_dossier(case, f"d_{idx}")
        
