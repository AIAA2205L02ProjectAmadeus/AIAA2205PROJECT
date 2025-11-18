import os
import pandas as pd

src_en = os.path.join('data_en_baidu','dev')
tgt_en = os.path.join('data_en_baidu','dev_labeled')
src_zh_labeled = os.path.join('data','dev_labeled')

os.makedirs(tgt_en, exist_ok=True)

if not os.path.isdir(src_en):
    print(f"Source English dir not found: {src_en}")
else:
    files = [f for f in os.listdir(src_en) if f.endswith('.csv')]
    for f in files:
        en_path = os.path.join(src_en, f)
        tgt_path = os.path.join(tgt_en, f)
        zh_label_path = os.path.join(src_zh_labeled, f)
        try:
            en_df = pd.read_csv(en_path, dtype=str)
        except Exception as e:
            print(f"Failed to read {en_path}: {e}")
            continue
        # default empty Category
        en_df['Category'] = ''
        en_df['Category_raw'] = ''
        # if zh label exists, copy Category
        if os.path.exists(zh_label_path):
            try:
                zh_df = pd.read_csv(zh_label_path, dtype=str)
                # align by index positions up to min length
                minlen = min(len(en_df), len(zh_df))
                en_df.loc[:minlen-1, 'Category'] = zh_df.loc[:minlen-1, 'Category'].values
                en_df.loc[:minlen-1, 'Category_raw'] = zh_df.loc[:minlen-1, 'Category_raw'].values if 'Category_raw' in zh_df.columns else zh_df.loc[:minlen-1, 'Category'].values
            except Exception as e:
                print(f"Failed to merge labels from {zh_label_path}: {e}")
        # Ensure ModelResponse exists
        if 'ModelResponse' not in en_df.columns:
            en_df['ModelResponse'] = ''
        # Save
        try:
            en_df.to_csv(tgt_path, index=False, encoding='utf-8')
            print(f"Generated {tgt_path}")
        except Exception as e:
            print(f"Failed to save {tgt_path}: {e}")
