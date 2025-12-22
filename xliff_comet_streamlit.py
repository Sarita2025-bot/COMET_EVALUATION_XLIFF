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
from pathlib import Path
from io import BytesIO

# Import from the working XLIFF parser module
from mqxliff_comet_to_xlsx import (
    parse_mqxliff,
    COMET_MODEL_NAME
)

# Import COMET functions directly (not through wrapper that might have input())
from comet import download_model, load_from_checkpoint  # type: ignore

# Try to load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Page configuration
st.set_page_config(
    page_title="COMET XLIFF Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

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


@st.cache_resource
def get_comet_model():
    """
    Load COMET model with caching.
    
    This function is cached so the model is only loaded once per session,
    making subsequent evaluations much faster.
    
    IMPORTANT: Model loading happens here, not at import time, to avoid blocking.
    
    Returns:
        Loaded COMET model
    """
    try:
        if os.getenv("HF_TOKEN"):
            # Token is available, proceed with model loading
            pass
        else:
            # Note: This won't block, just inform the user
            pass
            
        model_path = download_model(COMET_MODEL_NAME)
        model = load_from_checkpoint(model_path)
        return model
    except Exception as e:
        st.error(f"Error loading COMET model: {str(e)}")
        st.info("Make sure you're logged into Hugging Face: `hf auth login` or set HF_TOKEN in .env file")
        return None


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
    # Check if password is configured in Streamlit secrets
    if "APP_PASSWORD" not in st.secrets:
        # No password configured -> no gate
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

# Optional password gate (remove if not needed)
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
    hf_token = st.text_input(
        "Hugging Face Token (optional)",
        type="password",
        help="Set HF_TOKEN here or use .env file or 'hf auth login'"
    )
    
    if hf_token:
        os.environ['HF_TOKEN'] = hf_token
        st.success("Token set!")

# Main content area
st.header("📁 Upload XLIFF File")

uploaded_file = st.file_uploader(
    "Choose a memoQ XLIFF file (.mqxliff or .xliff)",
    type=['mqxliff', 'xliff', 'xlf'],
    help="Upload a memoQ XLIFF file containing translation units"
)

# Batch size configuration
batch_size = st.number_input(
    "Batch size for COMET evaluation",
    min_value=1,
    max_value=64,
    value=8,
    help="Adjust based on available memory. Larger batches are faster but use more memory."
)

if uploaded_file is not None:
    # Display file info
    st.success(f"✅ File uploaded: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")
    
    # Process button
    if st.button("🚀 Evaluate Translation Quality", type="primary", use_container_width=True):
        # Load model (cached) - only when button is clicked
        with st.spinner("Loading COMET model (this may take a few minutes on first run)..."):
            model = get_comet_model()
        
        if model is None:
            st.error("❌ Could not load COMET model. Please check authentication.")
            st.stop()
        
        # Create temporary file for parsing
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = Path(tmp_file.name)
        
        try:
            # Parse XLIFF file
            with st.spinner("Parsing XLIFF file..."):
                try:
                    extracted_data, source_lang, target_lang = parse_mqxliff(tmp_path)
                except Exception as e:
                    st.error(f"Error parsing XLIFF file: {str(e)}")
                    st.info("Please check that the file is a valid memoQ XLIFF file.")
                    st.stop()
            
            if not extracted_data:
                st.warning("No valid translation units found in the XLIFF file.")
                st.info("Make sure the file contains trans-units with:")
                st.info("- mq:status='ManuallyConfirmed'")
                st.info("- Source, target, and mq:insertedmatch elements with MT data")
                st.stop()
            
            # Convert to DataFrame
            df = pd.DataFrame(extracted_data)
            
            # Add language codes
            if source_lang:
                df['source_language'] = source_lang
            if target_lang:
                df['target_language'] = target_lang
            
            # Prepare data for COMET
            data = []
            for _, row in df.iterrows():
                data.append({
                    "src": str(row['source']),
                    "mt": str(row['mt']),
                    "ref": str(row['ref'])
                })
            
            # Compute COMET scores
            with st.spinner(f"Computing COMET scores for {len(data)} translation units..."):
                try:
                    model_output = model.predict(data, batch_size=int(batch_size), gpus=0)
                    scores = model_output['scores']
                except Exception as e:
                    st.error(f"Error computing COMET scores: {str(e)}")
                    st.stop()
            
            # Add scores to DataFrame
            df['comet_score'] = scores
            
            # Calculate statistics
            stats = {
                'total_units': len(df),
                'avg_score': sum(scores) / len(scores),
                'min_score': min(scores),
                'max_score': max(scores),
                'source_lang': source_lang,
                'target_lang': target_lang
            }
            
            # Display results
            st.success("✅ Evaluation Complete!")
            
            # Statistics section
            st.header("📈 Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Units", stats['total_units'])
            
            with col2:
                st.metric("Average Score", f"{stats['avg_score']:.4f}")
            
            with col3:
                st.metric("Min Score", f"{stats['min_score']:.4f}")
            
            with col4:
                st.metric("Max Score", f"{stats['max_score']:.4f}")
            
            # Language pair info
            if source_lang and target_lang:
                st.info(f"🌐 Language Pair: **{source_lang}** → **{target_lang}**")
            
            # Data preview
            st.header("📋 Results Preview")
            # Select columns to display (handle both old and new column sets)
            preview_cols = ['source', 'mt', 'ref', 'comet_score']
            if 'trans_unit_id' in df.columns:
                preview_cols.insert(0, 'trans_unit_id')
            if 'mt_provider' in df.columns:
                preview_cols.insert(-1, 'mt_provider')
            
            st.dataframe(
                df[preview_cols].head(10),
                use_container_width=True,
                hide_index=True
            )
            
            if len(df) > 10:
                st.caption(f"Showing first 10 of {len(df)} translation units")
            
            # Score distribution
            st.header("📊 Score Distribution")
            st.bar_chart(df['comet_score'])
            
            # Download section
            st.header("💾 Download Results")
            
            # Create Excel file in memory
            output_filename = f"{Path(uploaded_file.name).stem}_comet_scores.xlsx"
            xlsx_bytes = df_to_xlsx_bytes(df)
            
            # Download button
            st.download_button(
                label="📥 Download Excel File",
                data=xlsx_bytes,
                file_name=output_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            # Full data table (expandable)
            with st.expander("📊 View Full Results Table"):
                st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Store in session state for potential future use
            st.session_state['results_df'] = df
            st.session_state['stats'] = stats
            
        finally:
            # Clean up temporary file
            if tmp_path.exists():
                os.unlink(tmp_path)
else:
    st.info("👆 Upload a memoQ XLIFF file to begin evaluation.")

# Note: NO if __name__ == "__main__" block - Streamlit imports and runs this file directly
