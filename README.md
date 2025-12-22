# COMET Evaluation for Machine Translation

A comprehensive toolkit for evaluating machine translation quality using COMET metrics, supporting both Excel files and memoQ XLIFF files.

## Features

- 📊 **COMET-DA Evaluation**: Reference-based evaluation using `Unbabel/wmt22-comet-da`
- 🔍 **COMET-QE Evaluation**: Reference-free quality estimation using `Unbabel/wmt22-cometkiwi-da`
- 📁 **Excel File Support**: Process Excel files with source, MT, and reference columns
- 📄 **XLIFF File Support**: Parse memoQ XLIFF files and extract translation data
- 🖥️ **Streamlit Web UI**: User-friendly web interface for XLIFF evaluation
- 🌐 **Multi-language Support**: Works with any language pair supported by COMET models

## Quick Start

### 1. Setup

```powershell
# Clone the repository
git clone https://github.com/Sarita2025-bot/COMET_EVALUATION_XLIFF.git
cd COMET_EVALUATION_XLIFF

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Authentication

You need a Hugging Face token to access the COMET models:

**Option 1: Use .env file** (Recommended)
```powershell
# Create .env file with:
HF_TOKEN=your_huggingface_token_here
```

**Option 2: Use Hugging Face CLI**
```powershell
hf auth login
```

**Option 3: Environment Variable**
```powershell
$env:HF_TOKEN="your_token_here"
```

Get your token from: https://huggingface.co/settings/tokens

### 3. Run Evaluations

#### Excel Files (COMET-DA)
```powershell
python run_comet_evaluation.py
```

#### Excel Files (COMET-QE - Reference-free)
```powershell
python run_comet_qe_evaluation.py
```

#### XLIFF Files (Streamlit UI)
```powershell
streamlit run xliff_comet_streamlit.py
```

#### XLIFF Files (Command Line)
```powershell
python mqxliff_comet_to_xlsx.py path/to/file.mqxliff
```

## Scripts Overview

### `run_comet_evaluation.py`
Evaluates MT quality using COMET-DA (requires reference translations).
- **Input**: Excel files with `source`, `mt`, and `ref` columns
- **Output**: Excel files with `comet_score` column added
- **Model**: `Unbabel/wmt22-comet-da`

### `run_comet_qe_evaluation.py`
Evaluates MT quality using COMET-QE (reference-free).
- **Input**: Excel files with `source` and `mt` columns (no `ref` needed!)
- **Output**: Excel files with `comet_qe_score` column added
- **Model**: `Unbabel/wmt22-cometkiwi-da`

### `xliff_comet_streamlit.py`
Web-based UI for evaluating memoQ XLIFF files.
- **Features**: File upload, real-time processing, visualizations, Excel download
- **Run**: `streamlit run xliff_comet_streamlit.py`

### `mqxliff_comet_to_xlsx.py`
Command-line tool for processing memoQ XLIFF files.
- **Input**: memoQ XLIFF files (`.mqxliff` or `.xliff`)
- **Output**: Excel files with extracted translation data and COMET scores
- **Extracts**: Source, MT (from `mq:insertedmatch`), Reference (from `target` with `mq:status="ManuallyConfirmed"`)

## File Formats

### Excel Input Format

**For COMET-DA** (`run_comet_evaluation.py`):
| source | mt | ref |
|--------|----|----|
| Hello | Hola | Hola |
| World | Mundo | Mundo |

**For COMET-QE** (`run_comet_qe_evaluation.py`):
| source | mt |
|--------|----|
| Hello | Hola |
| World | Mundo |

### XLIFF File Requirements

memoQ XLIFF files must contain:
- `<trans-unit>` elements with `mq:status="ManuallyConfirmed"`
- `<source>` elements with source text
- `<target>` elements with post-edited translation (reference)
- `<mq:insertedmatch>` elements with `matchtype="1"` and `source` containing "MT /" (for MT extraction)

## Requirements

- Python 3.8 or higher
- Virtual environment (recommended)
- Hugging Face account and token
- See `requirements.txt` for full dependency list

## Documentation

- **Setup Guide**: `README_SETUP.md`
- **Environment Setup**: `ENV_SETUP.md`
- **Streamlit UI**: `STREAMLIT_README.md`
- **Python Version Notes**: `PYTHON_VERSION_NOTE.md`

## Project Structure

```
COMET_EVALUATION_XLIFF/
├── run_comet_evaluation.py          # COMET-DA for Excel files
├── run_comet_qe_evaluation.py       # COMET-QE for Excel files
├── xliff_comet_streamlit.py         # Streamlit UI for XLIFF
├── mqxliff_comet_to_xlsx.py         # CLI tool for XLIFF
├── requirements.txt                 # Python dependencies
├── setup_venv.ps1                   # Virtual environment setup script
├── RAW_MT/                          # Sample Excel files
│   └── OUTPUT/                      # Output directory
└── README.md                        # This file
```

## COMET Models

### COMET-DA (Reference-based)
- **Model**: `Unbabel/wmt22-comet-da`
- **Requires**: Source, MT, and Reference translations
- **Use Case**: When you have human reference translations for comparison

### COMET-QE (Reference-free)
- **Model**: `Unbabel/wmt22-cometkiwi-da`
- **Requires**: Source and MT only (no reference needed!)
- **Use Case**: Quality estimation without reference translations

## License

This project uses COMET models which have their own licenses. Please review:
- [COMET License](https://github.com/Unbabel/COMET)
- [Hugging Face Model Cards](https://huggingface.co/Unbabel)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues or questions:
1. Check the documentation files in this repository
2. Review [COMET Documentation](https://github.com/Unbabel/COMET)
3. Open an issue on GitHub

## Acknowledgments

- [Unbabel COMET](https://github.com/Unbabel/COMET) - COMET metric implementation
- [Hugging Face](https://huggingface.co/) - Model hosting and distribution
- [Streamlit](https://streamlit.io/) - Web UI framework

