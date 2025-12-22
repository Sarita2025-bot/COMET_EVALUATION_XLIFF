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

# Import COMET functions directly (not through wrapper that might have input())
from comet import download_model, load_from_checkpoint  # type: ignore

# ========== CRASH CATCHER: Wrap entire app in try/except ==========
try:
    # Heartbeat - confirms app started successfully
    st.write("App started ✅")  # Keep this at the top as a heartbeat
    
    # ========== Handle HF_TOKEN from Streamlit Secrets (Cloud-friendly) ==========
    # Priority order: Streamlit Secrets > Environment Variable > Manual input
    # On Streamlit Cloud, set HF_TOKEN in: Settings > Secrets > Add secret
    # Do NOT use .env file (gitignored, won't work in Cloud)
    hf_token_set = False
    if "HF_TOKEN" in st.secrets:
        os.environ["HF_TOKEN"] = st.secrets["HF_TOKEN"]
        hf_token_set = True
    elif os.getenv("HF_TOKEN"):
        # Environment variable might be set by Streamlit Cloud or system
        hf_token_set = True
    
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
        
        IMPORTANT: This function is ONLY called when user clicks the button,
        NOT at import time or during startup. This prevents health-check kills.
        
        Token is obtained from (in order):
        1. Streamlit Secrets (st.secrets["HF_TOKEN"])
        2. Environment variable (os.getenv("HF_TOKEN"))
        3. Manual input from sidebar (handled in UI)
        
        Returns:
            Loaded COMET model or None if error
        """
        try:
            # Check for token - don't warn here, let the UI handle it
            # Token should be set from secrets or environment before calling this
            
            # Download and load model
            model_path = download_model(COMET_MODEL_NAME)
            model = load_from_checkpoint(model_path)
            return model
        except Exception as e:
            st.error(f"Error loading COMET model: {str(e)}")
            st.info("""
            **Troubleshooting:**
            - Set HF_TOKEN in Streamlit Cloud: Settings > Secrets
            - Or set as environment variable in Streamlit Cloud settings
            - Or enter token manually in the sidebar
            - Get token from: https://huggingface.co/settings/tokens
            """)
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
        
        # Check token status (from secrets or environment)
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
        
        # Allow manual token entry as fallback (for local dev or if secrets not set)
        hf_token = st.text_input(
            "Hugging Face Token (manual entry - if not in Secrets)",
            type="password",
            help="Enter token here if not set in Streamlit Secrets. Get token from: https://huggingface.co/settings/tokens"
        )
        
        if hf_token:
            os.environ['HF_TOKEN'] = hf_token
            st.success("Token set via manual input!")
    
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
        
        # Process button - MODEL LOADS HERE ONLY, NOT AT STARTUP
        if st.button("🚀 Evaluate Translation Quality", type="primary", use_container_width=True):
            # Load model (cached) - ONLY when button is clicked, not at startup
            # This prevents health-check timeouts on Streamlit Cloud
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
                # NOTE: We do NOT cache parsing results (they can be large and cause memory issues)
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
                # NOTE: We do NOT cache this DataFrame (it can be large)
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
                # NOTE: Session state is fine for this (it's per-session, not cached across reruns)
                st.session_state['results_df'] = df
                st.session_state['stats'] = stats
                
            finally:
                # Clean up temporary file
                if tmp_path.exists():
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass  # Ignore cleanup errors
    else:
        st.info("👆 Upload a memoQ XLIFF file to begin evaluation.")
    
    # Note: NO if __name__ == "__main__" block - Streamlit imports and runs this file directly

# ========== CRASH CATCHER: Display full exception if app crashes ==========
except Exception as e:
    st.error("🚨 App crashed with an exception:")
    st.code(traceback.format_exc())
    st.error(f"**Error message:** {str(e)}")
    st.info("""
    **Troubleshooting:**
    - Check that all dependencies are installed
    - Verify Hugging Face token is set (Streamlit Secrets or .env)
    - Ensure the XLIFF file is valid
    - Check Streamlit logs for more details
    """)
    # Re-raise so it also appears in logs
    raise
