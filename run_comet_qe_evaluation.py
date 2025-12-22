"""
COMET-QE (COMET-Kiwi) MT Quality Estimation Script

This script evaluates machine translation quality using COMET-QE/Kiwi models WITHOUT needing reference translations.
It processes Excel files containing source and MT translations, and adds quality scores to each row.

COMET-QE (COMET Quality Estimation) is a reference-free neural metric that evaluates translation quality
by analyzing only the source text and machine translation output. No human reference translation is required.

This script uses the Unbabel/wmt22-cometkiwi-da model, which is:
- Reference-free (only needs source + MT)
- Best correlation with human DA (Direct Assessment) scores
- Works on classic NMT and modern LLM translations
- Provides segment-level scoring
- Fully free (Apache-style research license)

Documentation: https://huggingface.co/Unbabel/wmt22-cometkiwi-da
"""

import pandas as pd
# Import COMET from unbabel-comet package (installed as 'unbabel-comet' but imported as 'comet')
# Note: If IDE shows import error, ensure it's using the .venv Python interpreter
from comet import download_model, load_from_checkpoint  # type: ignore
from pathlib import Path
import os

# Load environment variables from .env file if it exists
# This allows you to store your Hugging Face token in a .env file
# The unbabel-comet library will automatically use the HF_TOKEN environment variable
try:
    from dotenv import load_dotenv
    load_dotenv()  # Loads variables from .env file into environment
except ImportError:
    # python-dotenv not installed - that's okay, user can use environment variables directly
    pass

# Define the input and output directories
# Input files are in the RAW_MT folder
INPUT_DIR = Path("./RAW_MT")
OUTPUT_DIR = Path("./RAW_MT/OUTPUT")

# Create output directory if it doesn't exist
# This ensures we have a place to save the results
OUTPUT_DIR.mkdir(exist_ok=True)

# Define the COMET-QE model to use
# wmt22-cometkiwi-da is a reference-free quality estimation model (2022 version - most stable)
# Alternative: "Unbabel/wmt23-cometkiwi" (2023 version - slightly better, newer)
# We use the 2022 version for maximum stability as recommended
COMET_MODEL_NAME = "Unbabel/wmt22-cometkiwi-da"

# List of Excel files to process
# These files should contain columns: source, mt (NO 'ref' column needed!)
EXCEL_FILES = [
    "Globalese-COMET-KIWI-eval-EN-FR.xlsx"
]


def load_comet_model():
    """
    Download and load the COMET-QE/Kiwi model.
    
    The model is downloaded on first use and cached for subsequent runs.
    This is a reference-free model, so it doesn't need reference translations.
    
    Authentication options (choose one):
    1. Use .env file: Create .env file with HF_TOKEN=your_token_here
    2. Use environment variable: Set HF_TOKEN in your environment
    3. Use hf auth login: Run 'hf auth login' command (stores token in Hugging Face config)
    
    Get your token from: https://huggingface.co/settings/tokens
    
    Returns:
        Loaded COMET model ready for quality estimation predictions
    """
    print(f"Loading COMET-QE model: {COMET_MODEL_NAME}")
    print("Note: Model will be downloaded on first run (this may take a few minutes)...")
    
    # Check if HF_TOKEN is available (either from .env file or environment variable)
    # The unbabel-comet library automatically uses this token for authentication
    if os.getenv('HF_TOKEN'):
        print("      Using HF_TOKEN from environment/.env file")
    else:
        print("      Authentication: Use 'hf auth login' OR set HF_TOKEN in .env file")
        print("      Get token from: https://huggingface.co/settings/tokens")
    
    # Download the model checkpoint (cached after first download)
    # This requires Hugging Face authentication for the model license
    model_path = download_model(COMET_MODEL_NAME)
    
    # Load the model from the checkpoint
    model = load_from_checkpoint(model_path)
    
    print("Model loaded successfully!")
    
    return model


def process_excel_file(model, input_file_path, output_file_path):
    """
    Process a single Excel file: read data, compute COMET-QE scores, and save results.
    
    This function:
    1. Reads the Excel file with source and mt columns (reference-free!)
    2. Prepares data in the format expected by COMET-QE (only src + mt, no ref)
    3. Computes quality scores for all rows
    4. Adds scores as a new column
    5. Saves the result to a new Excel file
    
    Args:
        model: Loaded COMET-QE model
        input_file_path: Path to input Excel file
        output_file_path: Path where output Excel file will be saved
    """
    print(f"\nProcessing: {input_file_path}")
    
    # Read the Excel file into a pandas DataFrame
    # This handles the Excel file format and loads all columns
    df = pd.read_excel(input_file_path)
    
    # Display basic info about the file
    print(f"  - Found {len(df)} rows")
    print(f"  - Columns: {list(df.columns)}")
    
    # Verify required columns exist
    # COMET-QE only needs source and MT output (NO reference needed - that's the advantage!)
    required_columns = ['source', 'mt']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}. "
            f"File must contain: source, mt (reference-free - no 'ref' column needed!)"
        )
    
    # Prepare data for COMET-QE prediction
    # COMET-QE expects a list of dictionaries with 'src' and 'mt' keys only
    # Unlike COMET-DA, this model doesn't need 'ref' because it's quality estimation, not comparison
    data = []
    for index, row in df.iterrows():
        data.append({
            "src": str(row['source']),  # Source language text
            "mt": str(row['mt'])         # Machine translation output
            # Note: No 'ref' key needed - this is reference-free quality estimation!
        })
    
    print(f"  - Computing COMET-QE scores (reference-free)...")
    
    # Compute COMET-QE scores for all rows
    # batch_size=8 processes 8 examples at a time (adjust based on available memory)
    # gpus=0 uses CPU (change to gpus=1 if you have a compatible GPU available)
    model_output = model.predict(data, batch_size=8, gpus=0)
    
    # Extract scores from model output
    # COMET-QE scores range from 0 to 1, where 1 indicates perfect translation quality
    scores = model_output['scores']
    
    # Add COMET-QE scores as a new column to the DataFrame
    # This preserves all original data and adds the quality estimation scores
    df['comet_qe_score'] = scores
    
    # Save the DataFrame to a new Excel file
    # index=False prevents saving the row index as a column
    df.to_excel(output_file_path, index=False)
    
    # Display summary statistics
    print(f"  - Scores computed successfully!")
    print(f"  - Score range: {min(scores):.4f} - {max(scores):.4f}")
    print(f"  - Average score: {sum(scores)/len(scores):.4f}")
    print(f"  - Output saved to: {output_file_path}")


def main():
    """
    Main function to orchestrate the COMET-QE evaluation process.
    
    This function:
    1. Loads the COMET-QE model (downloads if needed, requires Hugging Face login)
    2. Processes each Excel file in the list
    3. Saves results with COMET-QE scores added
    
    Note: This is reference-free evaluation - no reference translations needed!
    """
    print("=" * 60)
    print("COMET-QE (COMET-Kiwi) MT Quality Estimation")
    print("=" * 60)
    print("Reference-free evaluation - no reference translations needed!")
    print("=" * 60)
    
    # Load the COMET-QE model once (reused for all files)
    # This is more efficient than loading it for each file
    model = load_comet_model()
    
    # Process each Excel file
    for excel_file in EXCEL_FILES:
        # Construct full paths for input and output files
        input_path = INPUT_DIR / excel_file
        
        # Check if input file exists
        if not input_path.exists():
            print(f"\nWarning: File not found: {input_path}")
            print("  Skipping this file...")
            continue
        
        # Create output filename by adding '_qe_scores' before the extension
        # This distinguishes QE results from regular COMET-DA results
        output_filename = excel_file.replace('.xlsx', '_qe_scores.xlsx')
        output_path = OUTPUT_DIR / output_filename
        
        # Process the file: read, compute scores, save
        try:
            process_excel_file(model, input_path, output_path)
        except Exception as e:
            print(f"\nError processing {excel_file}: {str(e)}")
            print("  Please check the file format and try again.")
            print("  Remember: COMET-QE only needs 'source' and 'mt' columns (no 'ref' needed!)")
            continue
    
    print("\n" + "=" * 60)
    print("Quality Estimation complete!")
    print(f"Results saved in: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    # Run the main function when script is executed
    main()

