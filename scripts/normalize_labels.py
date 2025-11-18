import os
import re
import pandas as pd

# Define mapping keywords to short labels
KEYWORD_TO_LABEL = {
    'quantitative': 'Q',
    '定量': 'Q',
    'logical': 'L',
    '逻辑': 'L',
    'commonsense': 'C',
    '常识': 'C'
}

# Desired order of labels when combining
LABEL_ORDER = ['Q', 'L', 'C']


def extract_labels(text: str):
    """Extract allowed labels from free text and return ordered combination like 'Q&C' or single 'L'."""
    if not isinstance(text, str):
        return None
    text_l = text.lower()
    found = set()
    # find english keywords
    for kw, lab in KEYWORD_TO_LABEL.items():
        if kw in text_l:
            found.add(lab)
    # also try to find letters Q/L/C directly
    for ch in ['q', 'l', 'c']:
        if re.search(rf"\b{ch}\b", text_l):
            found.add(ch.upper())
    if not found:
        return None
    # produce ordered combo
    ordered = [lab for lab in LABEL_ORDER if lab in found]
    return '&'.join(ordered)


def normalize_file(path):
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Failed to read {path}: {e}")
        return

    if 'Category' not in df.columns:
        print(f"No 'Category' column in {path}, skipping.")
        return

    # Keep raw
    if 'Category_raw' not in df.columns:
        df['Category_raw'] = df['Category']

    # Normalize
    normalized = []
    for v in df['Category_raw'].fillna(''):
        lab = extract_labels(str(v))
        if lab is None:
            lab = 'UNKNOWN'
        normalized.append(lab)

    df['Category'] = normalized

    # Save back
    backup = path + '.bak'
    try:
        if not os.path.exists(backup):
            df.to_csv(path, index=False, encoding='utf-8')
        else:
            # if backup exists, just overwrite file
            df.to_csv(path, index=False, encoding='utf-8')
        print(f"Normalized and saved {path}")
    except Exception as e:
        print(f"Failed to save {path}: {e}")


def main():
    roots = [
        os.path.join('data', 'dev_labeled'),
        os.path.join('data_en_baidu', 'dev_labeled')
    ]
    for root in roots:
        if not os.path.isdir(root):
            continue
        files = [f for f in os.listdir(root) if f.endswith('.csv')]
        for f in files:
            path = os.path.join(root, f)
            normalize_file(path)

if __name__ == '__main__':
    main()
