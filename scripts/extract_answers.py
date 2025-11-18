import os
import pandas as pd
import sys

def extract_answers(source_path, target_path):
    """
    Reads a CSV file, extracts the 'Answer' column, and saves it to a new CSV file.
    """
    try:
        # Read the source CSV
        df = pd.read_csv(source_path)

        # Check if 'Answer' column exists
        if 'Answer' in df.columns:
            # Create a new DataFrame with only the Answer column
            answer_df = df[['Answer']].copy()
            
            # Ensure the target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Save the answers to the target file
            answer_df.to_csv(target_path, index=False, header=True)
            print(f"  - Successfully extracted answers to {target_path}")
        else:
            print(f"  - Warning: 'Answer' column not found in {source_path}. Skipping.")

    except Exception as e:
        print(f"  - An error occurred while processing {source_path}: {e}")

def main():
    """
    Main function to find and process all relevant datasets in the dev directory.
    """
    source_base = 'data/dev'
    target_base = 'data_answers/dev'
    
    print("Starting answer extraction process...")
    print(f"Source: '{source_base}', Target: '{target_base}'")

    # Check if the source directory exists
    if not os.path.isdir(source_base):
        print(f"Error: Source directory '{source_base}' not found. Exiting.")
        sys.exit(1)

    # Walk through the source directory structure
    for filename in os.listdir(source_base):
        if filename.endswith('.csv'):
            source_file = os.path.join(source_base, filename)
            target_file = os.path.join(target_base, filename)
            
            print(f"\nProcessing file: {source_file}")
            
            # Check if the answer file already exists
            if os.path.exists(target_file):
                print(f"  - Skipping, answer file already exists: {target_file}")
                continue
            
            extract_answers(source_file, target_file)

    print("\nAnswer extraction process finished.")

if __name__ == "__main__":
    # Before running, ensure you have pandas installed:
    # pip install pandas
    main()
