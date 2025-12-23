"""
Streamlit UI for COMET MT Evaluation of memoQ XLIFF Files
"""

import os
import gc
import traceback
import tempfile
from pathlib import Path
from io import BytesIO

import streamlit as st
import pandas as pd

import torch
from comet import download_model, load_from_checkpoint  # type: ignore

from mqxliff_comet_to_xlsx import (
    parse_mqxliff,
    COMET_MODEL_NAME,
)

# ----------------- Page config (MUST be before other Streamlit calls) -----------------
st.set_page_config(
    page_title="COMET XLIFF Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.write("App started ✅")  # heartbeat


def apply_hf_token_from_secrets_or_env() -> None:
    """
    Ensure HF_TOKEN is set in environment.
    Priority: Streamlit secrets -> already-set env var -> manual UI input (sidebar)
    """
    if "HF_TOKEN" in st.secrets and st.secrets["HF_TOKEN"]:
        os.environ["HF_TOKEN"] = st.secrets["HF_TOKEN"]


@st.cache_resource(show_spinner=False)
def get_comet_model_cached():
    """
    Load COMET model once per Streamlit server process.
    This MUST be light on CPU/RAM to avoid Cloud kills.
    """
    print("MODEL: start load", flush=True)

    # Reduce CPU thrash and memory spikes
    torch.set_num_threads(1)
    torch.set_grad_enabled(False)

    model_path = download_model(COMET_MODEL_NAME)
    model = load_from_checkpoint(model_path)
    model.eval()

    # Encourage garbage collection
    gc.collect()

    print("MODEL: loaded OK", flush=True)
    return model


def df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="COMET_Scores")
    return buf.getvalue()


# ---------------- UI ----------------
st.markdown("## 📊 COMET XLIFF Evaluator")
st.markdown("Upload a memoQ `.mqxliff` / `.xliff` file and score MT vs post-edited reference using COMET.")

with st.sidebar:
    st.header("🔐 Hugging Face Auth")

    if "HF_TOKEN" in st.secrets and st.secrets["HF_TOKEN"]:
        st.success("✅ HF_TOKEN found in Streamlit Secrets")
    elif os.getenv("HF_TOKEN"):
        st.success("✅ HF_TOKEN found in environment variables")
    else:
        st.warning("⚠️ No HF_TOKEN detected yet")
        st.info("Add HF_TOKEN in Streamlit Cloud → Settings → Secrets")

    manual_token = st.text_input("HF_TOKEN (manual, optional)", type="password")
    if manual_token:
        os.environ["HF_TOKEN"] = manual_token
        st.success("Token set for this session ✅")

    st.header("⚙️ Safety settings")
    default_batch = st.number_input("Batch size (lower = safer)", min_value=1, max_value=32, value=1)
    max_segments = st.number_input("Max segments to score (0 = no cap)", min_value=0, max_value=20000, value=1500)

uploaded_file = st.file_uploader(
    "Choose a memoQ XLIFF file (.mqxliff / .xliff / .xlf)",
    type=["mqxliff", "xliff", "xlf"],
)

if uploaded_file is None:
    st.info("👆 Upload a file to begin.")
    st.stop()

st.success(f"✅ Uploaded: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")

run = st.button("🚀 Evaluate Translation Quality", type="primary", use_container_width=True)
if not run:
    st.stop()

tmp_path = None
try:
    print("STEP 0: button clicked", flush=True)

    apply_hf_token_from_secrets_or_env()
    print("STEP 1: HF_TOKEN applied", flush=True)

    # Load model ONLY after click
    with st.spinner("Loading COMET model (first run can take a few minutes)..."):
        print("STEP 2: loading COMET model", flush=True)
        model = get_comet_model_cached()
        print("STEP 3: COMET model loaded", flush=True)

    # Write upload to temp file for XML parsers
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    print(f"STEP 4: temp file written: {tmp_path}", flush=True)

    with st.spinner("Parsing mqxliff..."):
        print("STEP 5: parsing started", flush=True)
        extracted_data, src_lang, tgt_lang = parse_mqxliff(tmp_path)
        print(f"STEP 6: parsing done, rows={len(extracted_data)}", flush=True)

    if not extracted_data:
        st.warning("No valid translation units extracted.")
        st.stop()

    df = pd.DataFrame(extracted_data)
    if src_lang:
        df["source_language"] = src_lang
    if tgt_lang:
        df["target_language"] = tgt_lang

    # Prepare COMET input
    data = [{"src": r["source"], "mt": r["mt"], "ref": r["ref"]} for r in df.to_dict("records")]
    print(f"STEP 7: prepared comet input rows={len(data)}", flush=True)

    # Optional cap to prevent Cloud OOM
    if int(max_segments) > 0 and len(data) > int(max_segments):
        st.warning(f"⚠️ Capping scoring to first {int(max_segments)} segments (safety setting).")
        data = data[: int(max_segments)]
        df = df.iloc[: int(max_segments)].copy()

    with st.spinner(f"Scoring {len(data)} segments..."):
        print("STEP 8: predict() start", flush=True)
        out = model.predict(data, batch_size=int(default_batch), gpus=0)
        print("STEP 9: predict() done", flush=True)

    df["comet_score"] = out["scores"]

    st.success("✅ Done!")
    if src_lang and tgt_lang:
        st.info(f"🌐 Language pair: **{src_lang} → {tgt_lang}**")

    st.metric("Segments scored", len(df))
    st.metric("Average COMET", f"{df['comet_score'].mean():.4f}")

    st.dataframe(df.head(20), use_container_width=True, hide_index=True)

    xlsx_bytes = df_to_xlsx_bytes(df)
    out_name = f"{Path(uploaded_file.name).stem}_comet_scores.xlsx"
    st.download_button(
        "📥 Download Excel",
        data=xlsx_bytes,
        file_name=out_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

except Exception:
    st.error("🚨 App crashed — traceback below")
    st.code(traceback.format_exc())
    raise

finally:
    if tmp_path and tmp_path.exists():
        try:
            os.unlink(tmp_path)
            print("CLEANUP: temp file removed", flush=True)
        except Exception:
            pass
