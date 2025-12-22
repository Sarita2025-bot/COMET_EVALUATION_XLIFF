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
    batch_size = st.number_input("Batch size", min_value=1, max_value=64, value=8)

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
tmp_path = None
try:
    apply_hf_token_from_secrets_or_env()

    with st.spinner("Loading COMET model (first run may take a few minutes)..."):
        model = get_comet_model_cached()

    # Save upload to a temp path for ElementTree parsing
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = Path(tmp_file.name)

    with st.spinner("Parsing XLIFF..."):
        extracted_data, source_lang, target_lang = parse_mqxliff(tmp_path)

    if not extracted_data:
        st.warning("No valid translation units extracted.")
        st.info("Check that the file contains mq:status='ManuallyConfirmed' and MT in mq:insertedmatch.")
        st.stop()

    df = pd.DataFrame(extracted_data)
    if source_lang:
        df["source_language"] = source_lang
    if target_lang:
        df["target_language"] = target_lang

    data = [{"src": r["source"], "mt": r["mt"], "ref": r["ref"]} for r in df.to_dict("records")]

    with st.spinner(f"Scoring {len(data)} segments with COMET..."):
        model_output = model.predict(data, batch_size=int(batch_size), gpus=0)

    df["comet_score"] = model_output["scores"]

    # Stats
    scores = df["comet_score"].tolist()
    st.success("✅ Evaluation complete!")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Units", len(df))
    c2.metric("Avg", f"{(sum(scores)/len(scores)):.4f}")
    c3.metric("Min", f"{min(scores):.4f}")
    c4.metric("Max", f"{max(scores):.4f}")

    if source_lang and target_lang:
        st.info(f"🌐 Language pair: **{source_lang} → {target_lang}**")

    st.subheader("Preview")
    preview_cols = ["source", "mt", "ref", "comet_score"]
    for extra in ["trans_unit_id", "mt_provider", "segmentguid"]:
        if extra in df.columns and extra not in preview_cols:
            preview_cols.insert(0, extra)

    st.dataframe(df[preview_cols].head(20), use_container_width=True, hide_index=True)

    st.subheader("Download")
    out_name = f"{Path(uploaded_file.name).stem}_comet_scores.xlsx"
    xlsx_bytes = df_to_xlsx_bytes(df)

    st.download_button(
        "📥 Download Excel",
        data=xlsx_bytes,
        file_name=out_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

except Exception:
    st.error("🚨 The app crashed during processing. Full traceback:")
    st.code(traceback.format_exc())
    st.stop()

finally:
    if tmp_path and tmp_path.exists():
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
