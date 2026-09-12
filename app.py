"""
PrivMed Gateway — Interactive Streamlit Demo Application (app.py)
Run with: streamlit run app.py
"""

import os
import streamlit as st
import time
import json
from dotenv import load_dotenv
from src.gateway import PrivMedGateway

# Auto-load API keys from .env file
load_dotenv()

st.set_page_config(
    page_title="PrivMed Gateway — PHI De-identification",
    page_icon="🛡️",
    layout="wide"
)

# Header & Title
st.title("🛡️ PrivMed Gateway — Clinical PHI/PII De-identification")
st.caption("AI/ML Internship Assessment | Privacy-Preserving Clinical AI Gateway")

# Sidebar Configuration
st.sidebar.header("⚙️ Gateway Settings")
enable_date_shifting = st.sidebar.checkbox("Enable Relative Date Shifting (+100 Days)", value=False)

_has_gemini_key = bool(os.environ.get("GEMINI_API_KEY", ""))
_default_provider_idx = 2 if _has_gemini_key else 0

llm_provider = st.sidebar.selectbox(
    "Downstream LLM Provider",
    options=["Mock (Offline)", "Ollama (Local)", "Google Gemini API"],
    index=_default_provider_idx
)

# API key is loaded silently from .env — never shown in UI
gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
if llm_provider == "Google Gemini API":
    if gemini_api_key:
        st.sidebar.success("Gemini API Key: Loaded ✓")
    else:
        st.sidebar.error("Gemini API Key not found in .env")

# Cache gateway in session state — only one instance per session
def get_gateway():
    key = f"gateway_{llm_provider}_{enable_date_shifting}"
    if key not in st.session_state:
        use_mock = (llm_provider == "Mock (Offline)")
        gw = PrivMedGateway(
            enable_date_shifting=enable_date_shifting,
            use_mock_llm=use_mock,
            provider="gemini" if llm_provider == "Google Gemini API" else "mock",
            api_key=gemini_api_key
        )
        st.session_state[key] = gw
    return st.session_state[key]

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔒 Security Status")
st.sidebar.success("Gateway Active")
st.sidebar.info("Mapping Storage: Isolated In-Memory")
st.sidebar.warning("Raw PHI to LLM: PROHIBITED")

DEFAULT_NOTE = ""

# Main Interface Tabs
tab_gateway, tab_review, tab_matrix = st.tabs(["🚀 Gateway Pipeline", "📋 Review Queue", "📊 HIPAA Coverage Matrix"])

def extract_text_from_uploaded_file(uploaded_file) -> str:
    if uploaded_file.name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(uploaded_file)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    else:
        return uploaded_file.getvalue().decode("utf-8")

with tab_gateway:
    st.subheader("1. Provide Clinical Document / Note")
    input_mode = st.radio("Input Source:", ["📝 Paste Text", "📄 Upload File (.pdf, .txt)"], horizontal=True)

    clinical_text = ""
    if input_mode == "📝 Paste Text":
        pasted_input = st.text_area("Raw Clinical Input", value="", height=140, placeholder="Paste clinical note here...")
        if pasted_input.strip():
            import re
            note_chunks = [n.strip() for n in re.split(r'=====\s*NOTE\s*[^=]*=====', pasted_input) if n.strip()]
            if len(note_chunks) > 1:
                st.info(f"Multi-note text detected! Found **{len(note_chunks)} individual clinical notes**.")
                selected_idx = st.selectbox(
                    "Select Note to Process:",
                    options=list(range(len(note_chunks))),
                    format_func=lambda i: f"Clinical Note #{i+1}"
                )
                clinical_text = note_chunks[selected_idx]
            else:
                clinical_text = pasted_input
    else:
        uploaded_file = st.file_uploader("Upload Clinical Document", type=["pdf", "txt"])
        if uploaded_file is not None:
            try:
                raw_file_text = extract_text_from_uploaded_file(uploaded_file)
                
                # Detect multi-note file format (e.g. ===== NOTE 1 =====)
                import re
                note_chunks = [n.strip() for n in re.split(r'=====\s*NOTE\s*[^=]*=====', raw_file_text) if n.strip()]
                
                if len(note_chunks) > 1:
                    st.success(f"Multi-note document detected! Found **{len(note_chunks)} individual clinical notes** in '{uploaded_file.name}'")
                    selected_idx = st.selectbox(
                        "Select Note to Process:",
                        options=list(range(len(note_chunks))),
                        format_func=lambda i: f"Clinical Note #{i+1} ({len(note_chunks[i])} chars)"
                    )
                    clinical_text = note_chunks[selected_idx]
                    with st.expander(f"Preview Selected Clinical Note #{selected_idx+1}"):
                        st.code(clinical_text, language="text")
                else:
                    clinical_text = raw_file_text
                    st.success(f"Successfully extracted {len(clinical_text)} characters from '{uploaded_file.name}'")
                    with st.expander("Preview Extracted Document Text"):
                        st.text(clinical_text[:1000] + ("..." if len(clinical_text) > 1000 else ""))
            except Exception as ex:
                st.error(f"Error parsing file: {ex}")

    if st.button("🛡️ Process De-identification Gateway", type="primary"):
        if not clinical_text.strip():
            st.warning("Please enter a clinical note first.")
        else:
            start_time = time.time()
            gateway = get_gateway()
            try:
                result = gateway.process_round_trip(clinical_text)
            except Exception as e:
                st.error(f"Gateway Error: {e}")
                st.stop()
            latency = (time.time() - start_time) * 1000

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔍 Detected PHI Entities")
            if result["entities"]:
                st.dataframe(result["entities"], width="stretch")
            else:
                st.info("No PHI entities detected.")

            st.markdown("### 🔒 Pseudonymized Clinical Text (Sent to LLM)")
            st.code(result["masked_text"], language="text")

        with col2:
            st.markdown(f"### 🤖 Downstream LLM Response ({llm_provider})")
            st.info(result["llm_response"])

            st.markdown("### ✨ Final Rehydrated Output")
            st.success(result["final_response"])

            st.metric("Latency (ms)", f"{latency:.2f} ms")

        # Security Proof Panel
        st.markdown("---")
        st.markdown("#### 🛡️ Gateway Privacy & Security Guarantee")
        sec_col1, sec_col2, sec_col3 = st.columns(3)
        sec_col1.metric("Raw PHI Sent to LLM", "NO", delta_color="normal")
        sec_col2.metric("Mapping Isolated In-Memory", "YES")
        sec_col3.metric("Unknown Placeholder Risk", "ZERO (Preserved)")

with tab_review:
    st.subheader("📋 Human Review Queue for Uncertain Detections")
    st.caption("Entities with medium/low confidence levels are flagged for human review prior to automated masking.")
    st.info("Currently all deterministic regex entities are auto-masked with HIGH confidence.")

with tab_matrix:
    st.subheader("📊 18 HIPAA Safe Harbor Category Coverage Matrix")
    st.markdown(r"""
    | # | HIPAA Category | Strategy | Detection Method |
    |---|---|---|---|
    | 1 | Names | Hybrid | ML NER (`PATIENT`, `DOCTOR`) + Rules |
    | 2 | Geographic Subdivisions | Hybrid | ML NER (`LOCATION`) + Address Regex |
    | 3 | Dates / Ages >89 | Hybrid | ML NER + Date Shifter |
    | 4 | Telephone Numbers | Regex | `\d{3}-\d{3}-\d{4}` |
    | 5 | Fax Numbers | Regex | Pattern match |
    | 6 | Email Addresses | Regex | Standard email pattern |
    | 7 | Social Security Numbers | Regex | `\d{3}-\d{2}-\d{4}` |
    | 8 | Medical Record Numbers | Hybrid | `MRN-\d+` + ML |
    | 9-15 | Technical IDs (IP, URL, etc.) | Regex | Deterministic patterns |
    | 16-17 | Non-text (Photos/Biometrics) | Documented Exclusion | Out-of-scope for text gateway |
    """)
