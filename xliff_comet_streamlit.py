"""
Streamlit UI for COMET MT Evaluation of memoQ XLIFF Files

This Streamlit application provides a user-friendly web interface for:
- Uploading memoQ XLIFF files
- Parsing and extracting translation data
- Computing COMET quality scores
- Viewing results and downloading Excel output files

IMPORTANT: This file must be "pure Streamlit" - no input(), no CLI-style main()
"""

import streamlit as st
import pandas as pd
import tempfile
import os
import traceback
from pathlib import Path
from io import BytesIO

# Import from the working XLIFF parser module
from mqxliff_comet_to_xlsx import (
    parse_mqxliff,
    COMET_MODEL_NAME
)

# Import COMET functions directly
from comet import download_model, load_from_checkpoint  # type: ignore


# ✅ MUST be the first Streamlit call (before any st.write/st.markdown/etc.)
st.set_page_config(
    page_title="COMET XLIFF Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ========== CRASH CATCHER: Wrap entire app in try/except ==========
try:
    # Heartbeat - confirms app started successfully
    st.write("App started ✅")  # safe now (after set_page_config)

    # ========== Handle HF_TOKEN from Streamlit Secrets (Cloud-friendly) ==========
    # Priority order: Streamlit Secrets > Environment Variable > Manual input
    hf_token_set = False
    if "HF_TOKEN" in st.secrets:
        os.environ["HF_TOKEN"] = st.secrets["HF_TOKEN"]
        hf_token_set = True
    elif os.getenv("HF_TOKEN"):
        hf_token_set = True

    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            margin-bottom: 1rem;
        }
        .info-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f0f2f6;
            margin: 1rem 0;
        }
        .success-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            margin: 1rem 0;
        }
        </style>
    """, unsafe_allow_html=True)


    # ✅ Cached model loader MUST be "pure": no st.* calls inside cached function
    @st.cache_resource
    def get_comet_model():
        model_path = download_model(COMET_MODEL_NAME)
        return load_from_checkpoint(model_path)


    def df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
        """Convert DataFrame to Excel file bytes."""
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="COMET_Scores")
        return buf.getvalue()


    def require_password():
        """
        Optional password gate for the application.
        Remove this function call if you don't want password protection.
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


    # ---------------- UI starts here ----------------

    # Optional password gate (uncomment if you want it)
    # require_password()

    # Header
    st.markdown('<div class="main-header">📊 COMET XLIFF Evaluator</div>', unsafe_allow_html=True)
    st.markdown("Evaluate machine translation quality from memoQ XLIFF files using COMET metrics")

    # Sidebar with information
    with st.sidebar:
        st.header("ℹ️ Information")
        st.markdown("""
        **What is COMET?**

        COMET (Crosslingual Optimized Metric for Evaluation of Translation)
        is a neural metric that evaluates translation quality by comparing
        MT output against reference translations.

        **Requirements:**
        - memoQ XLIFF files with `mq:status="ManuallyConfirmed"`
        - Source, target, and MT data in `mq:insertedmatch` elements
        - Hugging Face authentication (HF_TOKEN or `hf auth login`)

        **Model:** `Unbabel/wmt22-comet-da`
        """)

        st.header("🔐 Authentication")

        token_from_secrets = "HF_TOKEN" in st.secrets
        token_from_env = bool(os.getenv("HF_TOKEN"))

        if token_from_secrets:
            st.success("✅ HF_TOKEN found in Streamlit Secrets")
        elif token_from_env:
            st.success("✅ HF_TOKEN found in environment variables")
        else:
            st.warning("⚠️ No HF_TOKEN configured")
            st.info("""
            **For Streamlit Cloud:**
            1. Go to Settings > Secrets
            2. Add: `HF_TOKEN = "your_token_here"`

            **For local development:**
            - Set environment variable: `$env:HF_TOKEN="your_token"`
            - Or enter token manually below
            """)

        hf_token = st.text_input(
            "Hugging Face Token (manual entry - if not in Secrets)",
            type="password",
            help="Enter token here if not set in Streamlit Secrets."
        )

        if hf_token:
            os.environ["HF_TOKEN"] = hf_token
            st.success("Token set via manual input!")

    # Main content area
    st.header("📁 Upload XLIFF File")

    uploaded_file = st.file_uploader(
        "Choose a memoQ XLIFF file (.mqxliff or .xliff)",
        type=["mqxliff", "xliff", "xlf"],
        help="Upload a memoQ XLIFF file containing translation units"
    )

    batch_size = st.number_input(
        "Batch size for COMET evaluation",
        min_value=1,
        max_value=64,
        value=8,
        help="Larger batches are faster but use more memory."
    )

    if uploaded_file is not None:
        st.success(f"✅ File uploaded: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")

        if st.button("🚀 Evaluate Translation Quality", type="primary", use_container_width=True):
            # ✅ Load model only when button clicked
            with st.spinner("Loading COMET model (first run can take a while)..."):
                try:
                    model = get_comet_model()
                except Exception as e:
                    st.error(f"Error loading COMET model: {e}")
                    st.code(traceback.format_exc())
                    st.stop()

            # Create temporary file for parsing
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = Path(tmp_file.name)

            try:
                with st.spinner("Parsing XLIFF file..."):
                    try:
                        extracted_data, source_lang, target_lang = parse_mqxliff(tmp_path)
                    except Exception as e:
                        st.error(f"Error parsing XLIFF file: {e}")
                        st.code(traceback.format_exc())
                        st.stop()

                if not extracted_data:
                    st.warning("No valid translation units found in the XLIFF file.")
                    st.info("Expected trans-units with mq:status='ManuallyConfirmed' and MT in mq:insertedmatch.")
                    st.stop()

                df = pd.DataFrame(extracted_data)

                if source_lang:
                    df["source_language"] = source_lang
                if target_lang:
                    df["target_language"] = target_lang

                data = [
                    {"src": str(r["source"]), "mt": str(r["mt"]), "ref": str(r["ref"])}
                    for r in df.to_dict("records")
                ]

                with st.spinner(f"Computing COMET scores for {len(data)} translation units..."):
                    try:
                        model_output = model.predict(data, batch_size=int(batch_size), gpus=0)
                        scores = model_output["scores"]
                    except Exception as e:
                        st.error(f"Error computing COMET scores: {e}")
                        st.code(traceback.format_exc())
                        st.stop()

                df["comet_score"] = scores

                stats = {
                    "total_units": len(df),
                    "avg_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "source_lang": source_lang,
                    "target_lang": target_lang
                }

                st.success("✅ Evaluation Complete!")

                st.header("📈 Statistics")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Units", stats["total_units"])
                col2.metric("Average Score", f"{stats['avg_score']:.4f}")
                col3.metric("Min Score", f"{stats['min_score']:.4f}")
                col4.metric("Max Score", f"{stats['max_score']:.4f}")

                if source_lang and target_lang:
                    st.info(f"🌐 Language Pair: **{source_lang}** → **{target_lang}**")

                st.header("📋 Results Preview")
                preview_cols = ["source", "mt", "ref", "comet_score"]
                if "trans_unit_id" in df.columns:
                    preview_cols.insert(0, "trans_unit_id")
                if "mt_provider" in df.columns:
                    preview_cols.insert(-1, "mt_provider")

                st.dataframe(df[preview_cols].head(10), use_container_width=True, hide_index=True)

                if len(df) > 10:
                    st.caption(f"Showing first 10 of {len(df)} translation units")

                st.header("📊 Score Distribution")
                st.bar_chart(df["comet_score"])

                st.header("💾 Download Results")
                output_filename = f"{Path(uploaded_file.name).stem}_comet_scores.xlsx"
                xlsx_bytes = df_to_xlsx_bytes(df)

                st.download_button(
                    label="📥 Download Excel File",
                    data=xlsx_bytes,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

                with st.expander("📊 View Full Results Table"):
                    st.dataframe(df, use_container_width=True, hide_index=True)

                st.session_state["results_df"] = df
                st.session_state["stats"] = stats

            finally:
                # Clean up temp file
                if "tmp_path" in locals() and tmp_path.exists():
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

    else:
        st.info("👆 Upload a memoQ XLIFF file to begin evaluation.")

# ========== CRASH CATCHER: Display full exception if app crashes ==========
except Exception as e:
    st.error("🚨 App crashed with an exception:")
    st.code(traceback.format_exc())
    st.error(f"**Error message:** {str(e)}")
    raise
