# Streamlit UI for COMET XLIFF Evaluation

A user-friendly web interface for evaluating machine translation quality from memoQ XLIFF files using COMET metrics.

## Features

- 📁 **Easy File Upload**: Drag and drop or browse for XLIFF files
- 📊 **Real-time Processing**: See progress as files are parsed and evaluated
- 📈 **Visual Statistics**: View score distributions and summary statistics
- 💾 **Download Results**: Export results as Excel files
- 🔐 **Secure Authentication**: Enter Hugging Face token directly in the UI

## Installation

1. **Install Streamlit** (if not already installed):
   ```powershell
   pip install streamlit
   ```

2. **Or install all requirements**:
   ```powershell
   pip install -r requirements.txt
   ```

## Running the Application

1. **Activate your virtual environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Run Streamlit**:
   ```powershell
   streamlit run xliff_comet_streamlit.py
   ```

3. **Open your browser**: Streamlit will automatically open your default browser, or navigate to the URL shown in the terminal (usually `http://localhost:8501`)

## Usage

1. **Set Authentication** (in sidebar):
   - Option 1: Enter your Hugging Face token in the sidebar
   - Option 2: Use `.env` file with `HF_TOKEN=your_token`
   - Option 3: Run `hf auth login` before starting Streamlit

2. **Upload XLIFF File**:
   - Click "Browse files" or drag and drop your `.mqxliff` or `.xliff` file
   - Supported formats: `.mqxliff`, `.xliff`, `.xlf`

3. **Evaluate**:
   - Click "🚀 Evaluate Translation Quality" button
   - Wait for processing (model loads on first run, may take a few minutes)

4. **View Results**:
   - See statistics (average, min, max scores)
   - Preview results table
   - View score distribution chart
   - Download Excel file with all results

## Requirements

- Python 3.8+
- Virtual environment with dependencies installed
- Hugging Face account and token (for model access)
- memoQ XLIFF files with:
  - `mq:status="ManuallyConfirmed"` trans-units
  - Source, target, and `mq:insertedmatch` elements

## Troubleshooting

**Model won't load:**
- Check Hugging Face authentication
- Verify token is correct
- Try running `hf auth login` in terminal

**No translation units found:**
- Verify XLIFF file has `mq:status="ManuallyConfirmed"` trans-units
- Check that source, target, and MT data are present
- Ensure `mq:insertedmatch` elements have `matchtype="1"` and `source` containing "MT /"

**Streamlit won't start:**
- Make sure virtual environment is activated
- Verify Streamlit is installed: `pip install streamlit`
- Check port 8501 is not in use

## Tips

- The COMET model is cached after first load, so subsequent evaluations are faster
- Large files may take longer to process
- Results are stored in session state, so you can download multiple times
- Use the sidebar to set your token if you prefer not to use `.env` file

