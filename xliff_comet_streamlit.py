"""
Streamlit UI for COMET MT Evaluation of memoQ XLIFF Files

This Streamlit application provides a user-friendly web interface for:
- Uploading memoQ XLIFF files
- Parsing and extracting translation data
- Computing COMET quality scores
- Viewing results and downloading Excel output files
"""

import streamlit as st
import pandas as pd
import tempfile
import os
from pathlib import Path
import io
from mqxliff_comet_to_xlsx import (
    load_comet_model,
    parse_mqxliff,
    COMET_MODEL_NAME
)

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
    
    Returns:
        Loaded COMET model
    """
    with st.spinner("Loading COMET model (this may take a few minutes on first run)..."):
        try:
            model = load_comet_model()
            return model
        except Exception as e:
            st.error(f"Error loading COMET model: {str(e)}")
            st.info("Make sure you're logged into Hugging Face: `hf auth login` or set HF_TOKEN in .env file")
            return None


def process_xliff_with_streamlit(model, uploaded_file):
    """
    Process uploaded XLIFF file and return results.
    
    Args:
        model: Loaded COMET model
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Tuple of (DataFrame with scores, source_lang, target_lang, stats_dict)
    """
    # Create temporary file to save uploaded content
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mqxliff') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Parse XLIFF file
        with st.spinner("Parsing XLIFF file..."):
            try:
                # Use parse_mqxliff from mqxliff_comet_to_xlsx.py
                extracted_data, source_lang, target_lang = parse_mqxliff(Path(tmp_path))
            except Exception as e:
                st.error(f"Error parsing XLIFF file: {str(e)}")
                st.info("Please check that the file is a valid memoQ XLIFF file.")
                return None, None, None, None
        
        if not extracted_data:
            st.warning("No valid translation units found in the XLIFF file.")
            st.info("Make sure the file contains trans-units with:")
            st.info("- mq:status='ManuallyConfirmed'")
            st.info("- Source, target, and mq:insertedmatch elements with MT data")
            return None, None, None, None
        
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
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text(f"Computing COMET scores for {len(data)} translation units...")
        progress_bar.progress(0.5)
        
        try:
            model_output = model.predict(data, batch_size=8, gpus=0)
            scores = model_output['scores']
        except Exception as e:
            st.error(f"Error computing COMET scores: {str(e)}")
            return None, None, None, None
        
        progress_bar.progress(1.0)
        status_text.text("Scores computed successfully!")
        
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
        
        return df, source_lang, target_lang, stats
        
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    """Main Streamlit application."""
    
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
    
    if uploaded_file is not None:
        # Display file info
        st.success(f"✅ File uploaded: **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")
        
        # Load model (cached)
        model = get_comet_model()
        
        if model is None:
            st.error("❌ Could not load COMET model. Please check authentication.")
            st.stop()
        
        # Process button
        if st.button("🚀 Evaluate Translation Quality", type="primary", use_container_width=True):
            # Process the file
            df, source_lang, target_lang, stats = process_xliff_with_streamlit(model, uploaded_file)
            
            if df is not None:
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
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='COMET_Scores')
                
                output.seek(0)
                
                # Download button
                st.download_button(
                    label="📥 Download Excel File",
                    data=output,
                    file_name=f"{Path(uploaded_file.name).stem}_comet_scores.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
                # Full data table (expandable)
                with st.expander("📊 View Full Results Table"):
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Store in session state for potential future use
                st.session_state['results_df'] = df
                st.session_state['stats'] = stats


if __name__ == "__main__":
    main()

