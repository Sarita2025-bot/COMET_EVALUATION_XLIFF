# Python Version Compatibility Note

## Issue
Python 3.14 introduced breaking changes that `unbabel-comet` hasn't adapted to yet. Specifically:
- `_HashedSeq` was removed from `functools` module in Python 3.14
- `unbabel-comet` still uses this internal function

## Solution: Use Python 3.12 or 3.13

Python 3.12 or 3.13 are recommended as they:
- Are fully supported and stable
- Have pre-built wheels for all required packages (including numpy)
- Are compatible with `unbabel-comet`
- Are still very recent (released in 2023-2024)

## Quick Setup with Python 3.12/3.13

### Step 1: Install Python 3.12 or 3.13
- Download Python 3.12: https://www.python.org/downloads/release/python-3120/
- Or Python 3.13: https://www.python.org/downloads/release/python-3130/
- During installation, check "Add Python to PATH"

### Step 2: Create Virtual Environment
```powershell
# For Python 3.12:
py -3.12 -m venv .venv

# Or for Python 3.13:
py -3.13 -m venv .venv
```

### Step 3: Activate and Install
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 4: Run Evaluation
```powershell
python run_comet_evaluation.py
```

## Alternative: Keep Python 3.14 and Wait
If you prefer to keep Python 3.14, you'll need to wait for `unbabel-comet` to release a version compatible with Python 3.14, or use an alternative MT evaluation metric.



