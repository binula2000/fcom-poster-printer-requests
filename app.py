import streamlit as st
import fitz  # PyMuPDF
import base64
import requests
import json

# 1. Page Configuration
st.set_page_config(page_title="FCOM Poster Print Request", layout="wide")

# 2. Belmont Branding CSS (Dark Mode)
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #FFFFFF !important; }
    h1, h2, h3, h4, h5, h6 { color: #FFFFFF !important; }
    div[data-testid="stAlert"] { background-color: #1D4289 !important; color: #FFFFFF !important; border: none; }
    div[data-testid="stForm"] { background-color: #3D3D3D; border: 2px solid #6AB3E7; border-radius: 8px; padding: 20px; color: #FFFFFF !important; }
    .stMarkdown, .stText, label { color: #FFFFFF !important; }
    div.stButton > button:first-child, div[data-testid="stFormSubmitButton"] > button {
        background-color: #862633 !important; color: #FFFFFF !important; border: none; border-radius: 4px; font-weight: bold;
    }
    div.stButton > button:first-child:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #6AB3E7 !important; color: #121212 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Session State Initialization
if 'submission_status' not in st.session_state:
    st.session_state.submission_status = "intake" # intake, preview, success

# 4. Helper Function for Webhook
def send_to_power_automate(name, email_addr, filename, file_bytes, option_text):
    try:
        # Pulls from Streamlit Cloud Advanced Settings -> Secrets
        webhook_url = st.secrets["POWER_AUTOMATE_URL"]
    except:
        st.error("Secrets Error: 'POWER_AUTOMATE_URL' not found.")
        return False
        
    file_b64 = base64.b64encode(file_bytes).decode('utf-8')
    payload = {
        "submitterName": name, "submitterEmail": email_addr, 
        "chosenOption": option_text, "fileName": filename, "fileBase64": file_b64
    }
    try:
        resp = requests.post(webhook_url, json=payload)
        return resp.status_code in [200, 202]
    except Exception:
        return False

# --- SCREEN 1: INTAKE FORM ---
if st.session_state.submission_status == "intake":
    st.title("FCOM Office of Academic Affairs")
    st.subheader("Poster Print Request")
    st.info("Poster requests typically require a minimum of one week (5 business days) of lead time.")
    st.caption("Contact: binula.illukpitiya@belmont.edu | Approval: jamaine.davis@belmont.edu")

    with st.form("intake_form"):
        col1, col2 = st.columns(2)
        with col1:
            f_name = st.text_input("1. First Name *")
        with col2:
            l_name = st.text_input("2. Last Name *")

        college = st.selectbox("3. Belmont College Affiliation *", [
            "Thomas F. Frist, Jr. College of Medicine", "College of Pharmacy & Health Sciences", "College of Sciences & Mathematics",
            "O'More College of Architecture & Design", "Watkins College of Art", "Jack C. Massey College of Business",
            "College of Education", "Mike Curb College of Entertainment & Music Business", "Gordon E. Inman College of Nursing",
            "College of Law", "College of Liberal Arts & Social Sciences", "College of Music & Performing Arts"
        ])

        role = st.radio("4. Role *", ["Faculty", "Staff", "Student"], horizontal=True)
        use_case = st.selectbox("5. Use Case *", ["FCOM Student Research Day", "SPARK Symposium", "External Conference", "Other"])
        purpose = st.text_area("6. Poster Purpose *")
        email = st.text_input("8. Email Address *")
        uploaded_file = st.file_uploader("9. Poster Upload (PDF) *", type=["pdf"])

        submitted = st.form_submit_button("Calculate Print Options")

    if submitted:
        if not (f_name and l_name and purpose and email and uploaded_file):
            st.error("Please fill all required fields.")
        else:
            # Store data and move to next screen
            st.session_state.submission_status = "preview"
            st.session_state.pdf_bytes = uploaded_file.read()
            st.session_state.file_name = uploaded_file.name
            st.session_state.user_info = {"name": f"{f_name} {l_name}", "email": email}
            st.rerun()

# --- SCREEN 2: PREVIEW & SELECTION ---
elif st.session_state.submission_status == "preview":
    st.title("Step 2: Select Scaling Option")
    st.write(f"Reviewing poster for: **{st.session_state.user_info['name']}**")
    
    # Process PDF for this screen
    doc = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
    page = doc[0]
    w_in, h_in = page.rect.width / 72.0, page.rect.height / 72.0
    img_src = f"data:image/png;base64,{base64.b64encode(page.get_pixmap(dpi=72).tobytes('png')).decode('utf-8')}"
    
    # Scaling Math
    opt_a_h = h_in * (36.0 / w_in)
    opt_b_w = w_in * (36.0 / h_in)
    display_scale = 350.0 / max(36.0, opt_a_h, opt_b_w, 36.0)

    st.success(f"Original Dimensions: {w_in:.1f}\" x {h_in:.1f}\"")
    
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Option A: Fit Width")
        st.write(f"**Final Size: 36.0\" x {opt_a_h:.1f}\"**")
        px_w, px_h = 36.0 * display_scale, opt_a_h * display_scale
        st.markdown(f'''<div style="height: 400px; display: flex; justify-content: center; align-items: center;"><div style="position: relative; width: {px_w}px; height: {px_h}px;"><div style="position: absolute; top: -25px; width: 100%; text-align: center; color: white; font-weight: bold;">36.0"</div><div style="position: absolute; left: -45px; top: 50%; transform: translateY(-50%); color: white; font-weight: bold;">{opt_a_h:.1f}"</div><img src="{img_src}" style="width: 100%; height: 100%; border: 2px solid #862633;"></div></div>''', unsafe_allow_html=True)
        if st.button("Submit Option A", key="final_a"):
            with st.spinner("Uploading to SharePoint..."):
                if send_to_power_automate(st.session_state.user_info["name"], st.session_state.user_info["email"], st.session_state.file_name, st.session_state.pdf_bytes, f"Option A (36x{opt_a_h:.1f})"):
                    st.session_state.submission_status = "success"
                    st.rerun()

    with colB:
        st.subheader("Option B: Fit Length")
        st.write(f"**Final Size: {opt_b_w:.1f}\" x 36.0\"**")
        px_w, px_h = opt_b_w * display_scale, 36.0 * display_scale
        st.markdown(f'''<div style="height: 400px; display: flex; justify-content: center; align-items: center;"><div style="position: relative; width: {px_w}px; height: {px_h}px;"><div style="position: absolute; top: -25px; width: 100%; text-align: center; color: white; font-weight: bold;">{opt_b_w:.1f}"</div><div style="position: absolute; left: -45px; top: 50%; transform: translateY(-50%); color: white; font-weight: bold;">36.0"</div><img src="{img_src}" style="width: 100%; height: 100%; border: 2px solid #862633;"></div></div>''', unsafe_allow_html=True)
        if st.button("Submit Option B", key="final_b"):
            with st.spinner("Uploading to SharePoint..."):
                if send_to_power_automate(st.session_state.user_info["name"], st.session_state.user_info["email"], st.session_state.file_name, st.session_state.pdf_bytes, f"Option B ({opt_b_w:.1f}x36)"):
                    st.session_state.submission_status = "success"
                    st.rerun()

    st.divider()
    if st.button("← Go Back & Edit Form"):
        st.session_state.submission_status = "intake"
        st.rerun()

# --- SCREEN 3: SUCCESS CONFIRMATION ---
elif st.session_state.submission_status == "success":
    st.balloons()
    st.markdown("""
        <div style="text-align: center; padding: 100px 40px; background-color: #3D3D3D; border-radius: 15px; border: 4px solid #6AB3E7; margin-top: 50px;">
            <h1 style="color: #6AB3E7 !important; font-size: 48px;">Success!</h1>
            <p style="font-size: 22px; color: white;">Your poster has been routed to <b>Dr. Jamaine Davis</b> for approval.</p>
            <p style="color: white; opacity: 0.8;">You may close this window or click below to submit another poster.</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Submit Another Poster Request"):
        st.session_state.submission_status = "intake"
        st.rerun()
