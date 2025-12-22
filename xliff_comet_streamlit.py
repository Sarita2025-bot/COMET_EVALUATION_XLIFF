"""
Streamlit UI for COMET MT Evaluation of memoQ XLIFF Files

Upload memoQ mqxliff/xlf/xliff, extract source/mt/ref, score with COMET,
and download an Excel with results.

IMPORTANT:
- st.set_page_config() MUST be the first Streamlit call.
- Do NOT use input() / CLI main().
- Do NOT call st.* inside @st.cache_* functions.
"""

import os
import tempfile
import traceback
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from comet import download_model, load_from_checkpoint  # type: ignore
from mqxliff_comet_to_xlsx import parse_mqxliff, COMET_MODEL_NAME


# ✅ MUST be the first Streamlit call (before any st.write/st.markdown/etc.)
st.set_page_config(
    page_title="COMET XLIFF Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- Auth / Secrets ----------
def apply_hf_token_from_secrets_or_env():
    """
    Ensures HF_TOKEN is available in os.environ before model download.
    Priority: Streamlit Secrets > existing env var.
    """
    if "HF_TOKEN" in st.secrets:
        os.environ["HF_TOKEN"] = st.secrets["HF_TOKEN"]


def require_password():
    """
    Optional password gate.
    Configure in Streamlit Secrets:
      APP_PASSWORD = "your_password"
    """
    if "APP_PASSWORD" not in st.secrets:
        return

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if st.session_state.auth_ok:
        return

    st.title("🔐 Login Required")
    pwd = st.text_input("Password", type="password")

    if st.button("Enter"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth_ok = True
            st.rerun()
        else:
            st.error("Wrong password")

    st.stop()


# ---------- COMET model (cached) ----------
@st.cache_resource
def get_comet_model_cached():
    """
    Cached COMET model loader.
    IMPORTANT: Must be "pure" (no st.* calls inside).
    """
    model_path = download_model(COMET_MODEL_NAME)
    return load_from_checkpoint(model_path)


# ---------- Excel helper ----------
def df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="COMET_Scores")
    return buf.getvalue()


# ---------------- UI ----------------
apply_hf_token_from_secrets_or_env()
# require_password()  # <- Uncomment if you want the password gate

st.markdown(
    """
    <style>
    .main-header { font-size: 2.2rem; font-weight: 700; margin-bottom: .25rem; }
    .subheader { color: #555; margin-bottom: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-header">📊 COMET XLIFF Evaluator</div>', unsafe_allow_html=True)
st.markdown('<div class="subheader">Upload memoQ XLIFF and download COMET scores as Excel.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔐 Hugging Face token")
    if "HF_TOKEN" in st.secrets:
        st.success("✅ HF_TOKEN found in Streamlit Secrets")
    elif os.getenv("HF_TOKEN"):
        st.success("✅ HF_TOKEN found in environment variables")
    else:
        st.warning("⚠️ No HF_TOKEN found")
        st.info('Add it in Streamlit Cloud → App settings → Secrets:  HF_TOKEN = "hf_..."')

    st.header("⚙️ Settings")
    batch_size = st.number_input("Batch size", min_value=1, max_value=500, value=8)

st.header("📁 Upload XLIFF file")
uploaded_file = st.file_uploader(
    "Choose a memoQ XLIFF file (.mqxliff / .xlf / .xliff)",
    type=["mqxliff", "xlf", "xliff"],
)

if uploaded_file is None:
    st.info("👆 Upload a memoQ XLIFF file to begin.")
    st.stop()

st.success(f"✅ Uploaded: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")

run = st.button("🚀 Evaluate Translation Quality", type="primary", use_container_width=True)

if not run:
    st.stop()

# ---- Everything below is inside the button action, with explicit crash reporting ----
# ---- Everything below is inside the button action, with explicit crash reporting ----
tmp_path = None
try:
    print("STEP 0: button clicked", flush=True)

    apply_hf_token_from_secrets_or_env()
    print("STEP 1: HF_TOKEN applied", flush=True)

    with st.spinner("Loading COMET model (first run may take a few minutes)..."):
        print("STEP 2: loading COMET model", flush=True)
        model = get_comet_model_cached()
        print("STEP 3: COMET model loaded", flush=True)

    # Save upload to a temp path for ElementTree parsing
    suffix = Path(uploaded_file.name).suffix
    print("STEP 4: creating temp file", flush=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = Path(tmp_file.name)

    print(f"STEP 5: temp file written to {tmp_path}", flush=True)

    with st.spinner("Parsing XLIFF..."):
        print("STEP 6: parsing mqxliff", flush=True)
        extracted_data, source_lang, target_lang = parse_mqxliff(tmp_path)
        print(f"STEP 7: parsed rows = {len(extracted_data)}", flush=True)

    if not extracted_data:
        st.warning("No valid translation units extracted.")
        st.stop()

    df = pd.DataFrame(extracted_data)
    print("STEP 8: dataframe created", flush=True)

    data = [
        {"src": r["source"], "mt": r["mt"], "ref": r["ref"]}
        for r in df.to_dict("records")
    ]
    print(f"STEP 9: prepared COMET input ({len(data)} rows)", flush=True)

    with st.spinner(f"Scoring {len(data)} segments with COMET..."):
        print("STEP 10: starting COMET predict()", flush=True)
        model_output = model.predict(data, batch_size=int(batch_size), gpus=0)
        print("STEP 11: COMET predict() finished", flush=True)

    df["comet_score"] = model_output["scores"]
    print("STEP 12: scores attached to dataframe", flush=True)

    st.success("✅ Evaluation complete!")

except Exception:
    st.error("🚨 The app crashed during processing. Full traceback:")
    st.code(traceback.format_exc())
    st.stop()

finally:
    if tmp_path and tmp_path.exists():
        try:
            os.unlink(tmp_path)
            print("STEP 13: temp file cleaned up", flush=True)
        except Exception:
            pass

