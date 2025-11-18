import os
import re
import pandas as pd

KEYWORD_TO_LABEL = {
    'quantitative': 'Q',
    '定量': 'Q',
    'logical': 'L',
    '逻辑': 'L',
    'commonsense': 'C',
    '常识': 'C'
}
LABEL_ORDER = ['Q', 'L', 'C']
ALLOWED_PATTERN = re.compile(r'^(Q|L|C)(?:&(Q|L|C))*$')


def extract_labels(text: str):
    if not isinstance(text, str):
        return None
    text_l = text.lower()
    found = set()
    for kw, lab in KEYWORD_TO_LABEL.items():
        if kw in text_l:
            found.add(lab)
    # letters
    for ch in ['q', 'l', 'c']:
        if re.search(rf"\b{ch}\b", text_l):
            found.add(ch.upper())
    if not found:
        return None
    ordered = [lab for lab in LABEL_ORDER if lab in found]
    return '&'.join(ordered)


def sanitize_model_response(text: str, max_len=2000):
    if not isinstance(text, str):
        return ''
    # Replace newlines and excessive whitespace
    s = re.sub(r"\s+", ' ', text).strip()
    # remove internal CSV-unfriendly quotes
    s = s.replace('\n', ' ').replace('\r', ' ')
    # Truncate if too long
    if len(s) > max_len:
        s = s[:max_len] + '...'
    return s


def normalize_category_value(val):
    if not isinstance(val, str):
        return None
    v = val.strip()
    if not v:
        return None
    # If already allowed pattern and components are unique and ordered, return ordered version
    parts = re.split(r'[&,;/\\|\s]+', v)
    parts = [p.strip().upper().replace('COMMONSENSE', 'C').replace('LOGICAL', 'L').replace('QUANTITATIVE', 'Q') for p in parts if p.strip()]
    # map Chinese words
    mapped = []
    for p in parts:
        if p in ['Q','L','C']:
            mapped.append(p)
        else:
            # map from keywords
            lbl = extract_labels(p)
            if lbl:
                mapped.extend(lbl.split('&'))
    # deduplicate while preserving LABEL_ORDER
    final = [lab for lab in LABEL_ORDER if lab in mapped]
    if not final:
        return None
    return '&'.join(final)


def clean_file(path):
    try:
        df = pd.read_csv(path, dtype=str)
    except Exception as e:
        print(f"Failed to read {path}: {e}")
        return

    # Drop unnamed index columns
    drop_cols = [c for c in df.columns if re.match(r'^Unnamed: 0', c) or c.lower() in ['index']]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    # Ensure expected columns exist
    cols = list(df.columns)
    # If ModelResponse not present, create empty
    if 'ModelResponse' not in df.columns:
        df['ModelResponse'] = ''
    # If Category_raw not present, set from existing Category
    if 'Category_raw' not in df.columns:
        if 'Category' in df.columns:
            df['Category_raw'] = df['Category'].fillna('')
        else:
            df['Category_raw'] = ''

    # Normalize Category by preferring Category_raw then Category then ModelResponse
    normalized = []
    for idx, row in df.iterrows():
        raw = str(row.get('Category_raw', '') or '')
        cur = str(row.get('Category', '') or '')
        mr = str(row.get('ModelResponse', '') or '')
        val = None
        # try normalize raw
        if raw:
            val = normalize_category_value(raw)
        if not val and cur:
            val = normalize_category_value(cur)
        if not val and mr:
            val = extract_labels(mr)
        if not val:
            val = 'UNKNOWN'
        normalized.append(val)

    df['Category'] = normalized

    # sanitize ModelResponse
    df['ModelResponse'] = df['ModelResponse'].apply(lambda x: sanitize_model_response(x))

    # Reorder columns if possible
    desired = ['Question','A','B','C','D','Answer','Category','ModelResponse','Category_raw']
    present = [c for c in desired if c in df.columns]
    other_cols = [c for c in df.columns if c not in present]
    new_order = present + other_cols
    df = df[new_order]

    # save
    try:
        df.to_csv(path, index=False, encoding='utf-8')
        print(f"Cleaned and saved {path}")
    except Exception as e:
        print(f"Failed to save {path}: {e}")


def main():
    roots = [os.path.join('data','dev_labeled'), os.path.join('data_en_baidu','dev_labeled')]
    for root in roots:
        if not os.path.isdir(root):
            continue
        files = [f for f in os.listdir(root) if f.endswith('.csv')]
        for f in files:
            path = os.path.join(root, f)
            clean_file(path)

if __name__ == '__main__':
    main()
