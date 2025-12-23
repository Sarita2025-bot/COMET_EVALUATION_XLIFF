# Archived: Streamlit Implementation

This directory contains the Streamlit web UI implementation that was archived due to deployment issues on Streamlit Cloud.

## Archived Files

- **`xliff_comet_streamlit.py`** - Streamlit web application for COMET XLIFF evaluation
- **`STREAMLIT_README.md`** - Documentation for the Streamlit app
- **`STREAMLIT_DEPLOYMENT.md`** - Deployment guide for Streamlit Cloud
- **`.streamlit/config.toml`** - Streamlit configuration file

## Status

**Archived:** The Streamlit app was not working reliably on Streamlit Cloud (likely due to memory/CPU constraints with the COMET model). The CLI scripts remain functional and are the recommended way to use this tool.

## Alternative: Use CLI Scripts

The working CLI alternatives are:
- `run_comet_evaluation.py` - COMET-DA evaluation with Excel files
- `run_comet_qe_evaluation.py` - COMET-QE/Kiwi evaluation (reference-free)

## Future

If you want to revisit the Streamlit implementation later, consider:
- Using a smaller COMET model (e.g., `wmt20-comet-da` instead of `wmt22-comet-da`)
- Deploying on a platform with more resources (paid Streamlit Cloud tier or other hosting)
- Using a serverless function approach (e.g., AWS Lambda, Google Cloud Functions)

---

**Archive Date:** January 2025
**Reason:** Streamlit Cloud deployment issues

