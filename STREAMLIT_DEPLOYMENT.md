# Streamlit Community Cloud Deployment Guide

This repository is organized according to [Streamlit Community Cloud file organization guidelines](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization).

## Repository Structure

```
COMET_EVAL/
├── .streamlit/              # Streamlit configuration (required at root)
│   └── config.toml         # App configuration (error details, upload limits, theme)
├── requirements.txt        # Python dependencies (required for Cloud deployment)
├── xliff_comet_streamlit.py  # Main Streamlit app entrypoint (at root)
├── mqxliff_comet_to_xlsx.py  # Helper module (imported by Streamlit app)
│
├── README.md               # Project documentation
├── STREAMLIT_README.md     # Streamlit-specific documentation
├── ENV_SETUP.md           # Environment setup instructions
│
├── run_comet_evaluation.py      # CLI script (not used by Streamlit)
├── run_comet_qe_evaluation.py   # CLI script (not used by Streamlit)
│
└── [other files...]       # Documentation, data files, etc.
```

## Streamlit Cloud Deployment

### Entrypoint
- **File**: `xliff_comet_streamlit.py` (at repository root)
- **Command**: Streamlit Cloud automatically runs `streamlit run xliff_comet_streamlit.py` from root

### Configuration
- **Location**: `.streamlit/config.toml` (required at root)
- **Purpose**: Error details, file upload limits, theme customization

### Dependencies
- **File**: `requirements.txt` (at repository root)
- **Purpose**: All Python packages needed by the Streamlit app

### Working Directory
On Streamlit Community Cloud, the working directory is **always the repository root**. All paths in the code must be relative to root.

## Deployment Steps

1. **Push to GitHub**: Ensure all files are committed and pushed
2. **Connect to Streamlit Cloud**: 
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect your GitHub repository
   - Select branch: `main`
   - Main file path: `xliff_comet_streamlit.py`

3. **Configure Secrets**:
   - In Streamlit Cloud, go to Settings > Secrets
   - Add: `HF_TOKEN = "your_huggingface_token_here"`
   - Get token from: https://huggingface.co/settings/tokens

4. **Deploy**: Click "Deploy" and wait for the app to build and launch

## Local Testing

To test locally and ensure consistency with Cloud:

```powershell
# From repository root (important!)
cd "C:\Users\SaritaVasquez\OneDrive - PeterandClark\Desktop\COMET_EVAL"

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run from root (matches Cloud behavior)
streamlit run xliff_comet_streamlit.py
```

**Important**: Always run `streamlit run` from the repository root, not from a subdirectory, to match Streamlit Cloud's behavior.

## Notes

- The IDE import error for `streamlit` is just a linter warning - it won't affect deployment since `streamlit` is in `requirements.txt`
- All paths in the code use relative paths (e.g., `./RAW_MT`) or `Path` objects, ensuring compatibility with Cloud
- The app does not depend on `.env` files - it uses Streamlit Secrets for `HF_TOKEN` (Cloud-friendly)

