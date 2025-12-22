"""
COMET MT Evaluation Script

This script evaluates machine translation quality using the Unbabel/wmt22-comet-da model.
It processes Excel files containing source, MT, and reference translations,
and adds COMET scores to each row.

COMET (Crosslingual Optimized Metric for Evaluation of Translation) is a neural metric
that evaluates translation quality by comparing MT output against a reference translation.
"""

import pandas as pd
# Import COMET from unbabel-comet package (installed as 'unbabel-comet' but imported as 'comet')
# Note: If IDE shows import error, ensure it's using the .venv Python interpreter
from comet import download_model, load_from_checkpoint  # type: ignore
import os
from pathlib import Path

# Define the input and output directories
# Input files are in the RAW_MT folder
INPUT_DIR = Path("./RAW_MT")
OUTPUT_DIR = Path("./RAW_MT/OUTPUT")

# Create output directory if it doesn't exist
# This ensures we have a place to save the results
OUTPUT_DIR.mkdir(exist_ok=True)

# Define the COMET model to use
# wmt22-comet-da is a reference-free metric that uses source, MT, and reference
COMET_MODEL_NAME = "Unbabel/wmt22-comet-da"

# List of Excel files to process
# These files should contain columns: source, mt, ref
EXCEL_FILES = [
    "Globalese-COMET-eval-EN-FR.xlsx"
]


def load_comet_model():
    """
    
    Download and load the COMET model.
    
    The model is downloaded on first use and cached for subsequent runs.
    This function handles the model initialization which is needed before
    computing any scores.
    
    Returns:
        Loaded COMET model ready for prediction
    """
    print(f"Loading COMET model: {COMET_MODEL_NAME}")
    print("Note: Model will be downloaded on first run (this may take a few minutes)...")
    
    # Download the model checkpoint (cached after first download)
    model_path = download_model(COMET_MODEL_NAME)
    
    # Load the model from the checkpoint
    model = load_from_checkpoint(model_path)
    
    print("Model loaded successfully!")
    
    return model


def process_excel_file(model, input_file_path, output_file_path):
    """
    Process a single Excel file: read data, compute COMET scores, and save results.
    
    This function:
    1. Reads the Excel file with source, mt, and ref columns
    2. Prepares data in the format expected by COMET
    3. Computes scores for all rows
    4. Adds scores as a new column
    5. Saves the result to a new Excel file
    
    Args:
        model: Loaded COMET model
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
    # COMET needs source, MT output, and reference translation
    required_columns = ['source', 'mt', 'ref']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}. "
            f"File must contain: source, mt, ref"
        )
    
    # Prepare data for COMET prediction
    # COMET expects a list of dictionaries with 'src', 'mt', and 'ref' keys
    data = []
    for index, row in df.iterrows():
        data.append({
            "src": str(row['source']),  # Source language text
            "mt": str(row['mt']),        # Machine translation output
            "ref": str(row['ref'])       # Reference (human) translation
        })
    
    print(f"  - Computing COMET scores...")
    
    # Compute COMET scores for all rows
    # batch_size=8 processes 8 examples at a time (adjust based on available memory)
    # gpus=1 uses GPU if available, otherwise falls back to CPU
    model_output = model.predict(data, batch_size=8, gpus=0)
    
    # Extract scores from model output
    # COMET scores range from 0 to 1, where 1 indicates perfect translation
    scores = model_output['scores']
    
    # Add COMET scores as a new column to the DataFrame
    # This preserves all original data and adds the evaluation scores
    df['comet_score'] = scores
    
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
    Main function to orchestrate the COMET evaluation process.
    
    This function:
    1. Loads the COMET model (downloads if needed)
    2. Processes each Excel file in the list
    3. Saves results with COMET scores added
    """
    print("=" * 60)
    print("COMET MT Evaluation")
    print("=" * 60)
    
    # Load the COMET model once (reused for all files)
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
        
        # Create output filename by adding '_with_scores' before the extension
        # This preserves the original filename while indicating it has scores
        output_filename = excel_file.replace('.xlsx', '_with_scores.xlsx')
        output_path = OUTPUT_DIR / output_filename
        
        # Process the file: read, compute scores, save
        try:
            process_excel_file(model, input_path, output_path)
        except Exception as e:
            print(f"\nError processing {excel_file}: {str(e)}")
            print("  Please check the file format and try again.")
            continue
    
    print("\n" + "=" * 60)
    print("Evaluation complete!")
    print(f"Results saved in: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    # Run the main function when script is executed
    main()

