# COMET MT Evaluation Setup Guide

This guide will help you set up Python 3.11 and run the COMET evaluation script.

## Step 1: Install Python 3.11

If Python 3.11 is not installed on your system:

1. **Download Python 3.11:**
   - Visit: https://www.python.org/downloads/
   - Download Python 3.11.x (latest 3.11 version)
   - Or use direct link: https://www.python.org/downloads/release/python-3110/

2. **Install Python:**
   - Run the installer
   - **IMPORTANT:** Check the box "Add Python to PATH" during installation
   - Choose "Install Now" or "Customize installation"
   - Complete the installation

3. **Verify Installation:**
   - Open a new PowerShell window
   - Run: `python --version` or `py -3.11 --version`
   - You should see: `Python 3.11.x`

## Step 2: Set Up Virtual Environment

### Option A: Using the Setup Script (Recommended)

Run the PowerShell setup script:

```powershell
.\setup_venv.ps1
```

This script will:
- Check for Python 3.11
- Create a virtual environment (`.venv`)
- Install all required dependencies
- Activate the virtual environment

### Option B: Manual Setup

If the script doesn't work, set up manually:

1. **Create virtual environment:**
   ```powershell
   python -m venv .venv
   ```
   Or if using py launcher:
   ```powershell
   py -3.11 -m venv .venv
   ```

2. **Activate virtual environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   
   **Note:** If you get an execution policy error, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

## Step 3: Run COMET Evaluation

Once the virtual environment is activated (you'll see `(.venv)` in your prompt):

```powershell
python run_comet_evaluation.py
```

The script will:
- Download the COMET model on first run (may take a few minutes)
- Process both Excel files:
  - `RAW_MT/Globalese-COMET-eval-EN-DE.xlsx`
  - `RAW_MT/Globalese-COMET-eval-EN-ES.xlsx`
- Save results to `OUTPUT/` folder with `_with_scores.xlsx` suffix

## Troubleshooting

### Issue: "python is not recognized"
- **Solution:** Python is not in PATH. Reinstall Python and check "Add Python to PATH", or add Python manually to your system PATH.

### Issue: Execution Policy Error when activating venv
- **Solution:** Run this command:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### Issue: Virtual environment activation fails
- **Solution:** Make sure you're in the correct directory and the `.venv` folder exists. Try:
  ```powershell
  cd "C:\Users\SaritaVasquez\PeterandClark\PandC - Documents\DATA\_TECH\_LES_projects\MT\MT_EVALUATIONS\COMET_EVAL"
  .\.venv\Scripts\Activate.ps1
  ```

### Issue: COMET model download fails
- **Solution:** Check your internet connection. The model is downloaded from Hugging Face on first use.

## Files Created

- `run_comet_evaluation.py` - Main evaluation script
- `requirements.txt` - Python dependencies
- `setup_venv.ps1` - Automated setup script
- `OUTPUT/` - Folder containing results with COMET scores

## Output

The script creates new Excel files in the `OUTPUT/` folder:
- `Globalese-COMET-eval-EN-DE_with_scores.xlsx`
- `Globalese-COMET-eval-EN-ES_with_scores.xlsx`

Each file contains the original columns (source, mt, ref) plus a new `comet_score` column with values between 0 and 1 (1 = perfect translation).

