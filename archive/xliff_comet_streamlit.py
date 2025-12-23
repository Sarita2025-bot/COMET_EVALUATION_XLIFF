"""
Streamlit UI for COMET MT Evaluation of memoQ XLIFF Files

- Upload memoQ mqxliff/xliff
- Parse source / MT / ref
- Score with COMET
- Download XLSX

Notes:
- Streamlit Cloud free tier often has ~1GB RAM. wmt22-comet-da can OOM.
  If it crashes during model load, use a smaller model like wmt20-comet-da.
"""

from __future__ import annotations

import os
import tempfile
import traceback
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

# --------- IMPORTANT: choose a smaller model for Streamlit Cloud ----------
# Try this first on Streamlit Cloud:
COMET_MODEL_NAME = "Unbabel/wmt20-comet-da"  # smaller, more deployable
# If you have enough RAM elsewhere, you can switch back:
# COMET_MODEL_NAME = "Unbabel/wmt22-comet-da"


# Import your parser (must NOT load COMET at import time)
from mqxliff_comet_to_xlsx import parse_mqxliff  # noqa: E402


# Must be the first Streamlit command
st.set_page_config(
    page_title="COMET XLIFF Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 COMET XLIFF Evaluator")
st.caption(f"Model: `{COMET_MODEL_NAME}`")


def df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="COMET_Scores")
    return buf.getvalue()


def _apply_hf_token_from_secrets_or_env() -> None:
    # Streamlit Secrets -> env var
    if "HF_TOKEN" in st.secrets and st.secrets["HF_TOKEN"]:
        os.environ["HF_TOKEN"] = st.secrets["HF_TOKEN"]


@st.cache_resource(show_spinner=False)
def get_comet_model_cached(model_name: str):
    """
    Load COMET model ONCE per app process.
    Import COMET inside the function so it doesn't load torch at import time.
    """
    from comet import download_model, load_from_checkpoint  # type: ignore

    print(f"MODEL LOAD: starting download/load for {model_name}")
    model_path = download_model(model_name)
    print(f"MODEL LOAD: downloaded to {model_path}")
    model = load_from_checkpoint(model_path)
    print("MODEL LOAD: load_from_checkpoint done")
    return model


with st.sidebar:
    st.header("🔐 Auth")
    st.write("HF token is required if the model is gated.")
    token_ok = False
    if "HF_TOKEN" in st.secrets and st.secrets["HF_TOKEN"]:
        st.success("✅ HF_TOKEN found in Streamlit Secrets")
        token_ok = True
    elif os.getenv("HF_TOKEN"):
        st.success("✅ HF_TOKEN found in environment")
        token_ok = True
    else:
        st.warning("⚠️ No HF_TOKEN found (may still work if model is public).")

    hf_token_manual = st.text_input(
        "HF_TOKEN (manual override)",
        type="password",
        help="Only needed if the model requires authentication.",
    )
    if hf_token_manual:
        os.environ["HF_TOKEN"] = hf_token_manual
        token_ok = True
        st.success("✅ Token set from manual input")

    st.header("⚙️ Settings")
    batch_size = st.number_input(
        "Batch size",
        min_value=1,
        max_value=64,
        value=4,  # lower by default to reduce memory spikes
        help="Lower batch size = less memory usage.",
    )

st.header("📁 Upload XLIFF")
uploaded_file = st.file_uploader(
    "Upload a memoQ XLIFF (.mqxliff / .xliff / .xlf)",
    type=["mqxliff", "xliff", "xlf"],
)

if uploaded_file is None:
    st.info("Upload a file to begin.")
    st.stop()

st.success(f"Uploaded: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")

# Button
if st.button("🚀 Evaluate", type="primary", use_container_width=True):
    try:
        print("STEP 0: button clicked")
        _apply_hf_token_from_secrets_or_env()
        print("STEP 1: HF_TOKEN applied (if present)")

        # Save upload to temp file
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = Path(tmp.name)

        try:
            print("STEP 2: parsing mqxliff")
            with st.spinner("Parsing XLIFF..."):
                extracted_data, source_lang, target_lang = parse_mqxliff(tmp_path)

            if not extracted_data:
                st.error("No valid translation units found.")
                st.stop()

            df = pd.DataFrame(extracted_data)
            if source_lang:
                df["source_language"] = source_lang
            if target_lang:
                df["target_language"] = target_lang

            # Prepare COMET input
            data = [{"src": r["source"], "mt": r["mt"], "ref": r["ref"]} for r in extracted_data]
            print(f"STEP 3: prepared {len(data)} rows for COMET")

            # Load model (cached)
            print("STEP 4: loading COMET model (cached)")
            with st.spinner("Loading COMET model (first time can be heavy)..."):
                model = get_comet_model_cached(COMET_MODEL_NAME)

            print("STEP 5: scoring")
            with st.spinner("Scoring..."):
                # CPU scoring; keep batch size conservative
                model_out = model.predict(data, batch_size=int(batch_size), gpus=0)

            scores = model_out["scores"]
            df["comet_score"] = scores

            st.success("✅ Done!")
            st.write(f"Language pair: {source_lang} → {target_lang}" if source_lang and target_lang else "Language pair: (not found)")

            st.dataframe(df.head(20), use_container_width=True, hide_index=True)

            out_name = f"{Path(uploaded_file.name).stem}_comet_scores.xlsx"
            st.download_button(
                "📥 Download XLSX",
                data=df_to_xlsx_bytes(df),
                file_name=out_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        finally:
            try:
                if tmp_path.exists():
                    os.unlink(tmp_path)
            except Exception:
                pass

    except Exception as e:
        st.error("🚨 App crashed with an exception:")
        st.code(traceback.format_exc())
        st.error(f"Error: {e}")
        raise
