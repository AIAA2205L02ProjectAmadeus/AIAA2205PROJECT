import os
import pandas as pd
import requests
import random
import hashlib
import time
import sys

# --- Baidu Translate API Configuration ---
BAIDU_APP_ID = '20251116002499033'
BAIDU_APP_KEY = 'OzkJp91V9sXCjjh0lTCh'
BAIDU_API_URL = 'http://api.fanyi.baidu.com/api/trans/vip/translate'

def translate_text_with_baidu(text, dest_lang='en', src_lang='zh'):
    """
    Translates text using the Baidu Translate API.
    """
    if not isinstance(text, str) or not text.strip():
        return text

    salt = random.randint(32768, 65536)
    sign_str = BAIDU_APP_ID + text + str(salt) + BAIDU_APP_KEY
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {
        'q': text,
        'from': src_lang,
        'to': dest_lang,
        'appid': BAIDU_APP_ID,
        'salt': salt,
        'sign': sign
    }

    try:
        # Add a small delay to avoid overwhelming the API
        time.sleep(1) # Baidu API has a 1 QPS limit for the free tier
        response = requests.post(BAIDU_API_URL, params=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        if 'trans_result' in result:
            return result['trans_result'][0]['dst']
        else:
            error_msg = result.get('error_msg', 'Unknown error')
            print(f"    - Baidu API Error: {error_msg}")
            return f"TRANSLATION_ERROR: {text}"
            
    except requests.exceptions.RequestException as e:
        print(f"    - HTTP Request failed: {e}")
        return f"TRANSLATION_ERROR: {text}"
    except Exception as e:
        print(f"    - An unexpected error occurred: {e}")
        return f"TRANSLATION_ERROR: {text}"

def translate_csv(source_path, target_path, columns_to_translate, dest_lang='en', src_lang='zh'):
    """
    Reads a CSV, translates specified columns using Baidu API, and saves it.
    """
    try:
        df = pd.read_csv(source_path)
        
        print(f"  - Translating {len(df)} rows...")
        for col in columns_to_translate:
            if col in df.columns:
                print(f"    - Translating column: {col}")
                # Apply Baidu translation to each cell in the column
                df[col] = df[col].apply(lambda x: translate_text_with_baidu(x, dest_lang, src_lang))
            else:
                print(f"    - Warning: Column '{col}' not found in {source_path}.")
        
        # Ensure the target directory exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        df.to_csv(target_path, index=False, encoding='utf-8')
        print(f"  - Successfully saved translated file to {target_path}")

    except Exception as e:
        print(f"  - An error occurred while processing {source_path}: {e}")

def main():
    """
    Main function to find and translate all relevant datasets.
    """
    source_base = 'data'
    target_base = 'data_en_baidu' # Using a new directory for Baidu translations
    columns_to_translate = ['Question', 'A', 'B', 'C', 'D']
    
    print("Starting dataset translation process with Baidu Translate API...")
    print(f"Source: '{source_base}', Target: '{target_base}'")

    # Check if the source directory exists
    if not os.path.isdir(source_base):
        print(f"Error: Source directory '{source_base}' not found. Exiting.")
        sys.exit(1)

    # Walk through the source directory structure
    for dirpath, _, filenames in os.walk(source_base):
        for filename in filenames:
            if filename.endswith('.csv'):
                source_file = os.path.join(dirpath, filename)
                
                # Construct the corresponding target path
                relative_path = os.path.relpath(source_file, source_base)
                target_file = os.path.join(target_base, relative_path)
                
                print(f"\nProcessing file: {source_file}")
                
                # Check if the translated file already exists
                if os.path.exists(target_file):
                    print(f"  - Skipping, translated file already exists: {target_file}")
                    continue
                
                translate_csv(source_file, target_file, columns_to_translate)

    print("\nTranslation process finished.")

if __name__ == "__main__":
    # Before running, ensure you have the necessary libraries installed:
    # pip install pandas requests
    main()
