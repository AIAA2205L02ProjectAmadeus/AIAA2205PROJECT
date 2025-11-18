#!/usr/bin/env python3
"""Deduplicate results/structured_results.jsonl.

Policy: keep the latest record for each unique key (model, language, strategy, file, row_index).
Produces a timestamped backup and overwrites the original JSONL. Also regenerates results/structured_summary.csv.
"""
import os
import sys
import json
import shutil
from datetime import datetime
import pandas as pd

RESULTS_FILE = os.path.join('results', 'structured_results.jsonl')
SUMMARY_CSV = os.path.join('results', 'structured_summary.csv')


def load_records(path):
    recs = []
    if not os.path.exists(path):
        print(f"No results file at {path}")
        return recs
    with open(path, 'r', encoding='utf-8') as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception as e:
                print(f"Skipping invalid JSON line {i}: {e}")
    return recs


def dedup_keep_latest(records):
    # key -> record (later records overwrite earlier ones)
    d = {}
    order = []
    for rec in records:
        try:
            key = (rec.get('model'), rec.get('language'), rec.get('strategy'), rec.get('file'), int(rec.get('row_index')))
        except Exception:
            # if row_index missing/invalid, fallback to using raw index
            key = (rec.get('model'), rec.get('language'), rec.get('strategy'), rec.get('file'), rec.get('row_index'))
        d[key] = rec
    # Return list of records (we'll sort for determinism)
    out = list(d.values())
    # sort by model, language, strategy, file, row_index
    def sort_key(r):
        try:
            return (r.get('model') or '', r.get('language') or '', r.get('strategy') or '', r.get('file') or '', int(r.get('row_index') or 0))
        except Exception:
            return (r.get('model') or '', r.get('language') or '', r.get('strategy') or '', r.get('file') or '', 0)
    out.sort(key=sort_key)
    return out


def write_jsonl(path, records):
    with open(path, 'w', encoding='utf-8') as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    recs = load_records(RESULTS_FILE)
    if not recs:
        print('No records to process. Exiting.')
        sys.exit(0)
    before = len(recs)
    deduped = dedup_keep_latest(recs)
    after = len(deduped)

    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    bak_path = RESULTS_FILE + f'.bak.{ts}'
    shutil.copy2(RESULTS_FILE, bak_path)
    print(f'Backed up original {RESULTS_FILE} -> {bak_path}')

    write_jsonl(RESULTS_FILE, deduped)
    print(f'Wrote deduplicated results to {RESULTS_FILE} (before={before}, after={after})')

    # regenerate summary csv
    try:
        df = pd.DataFrame(deduped)
        if not df.empty:
            df.to_csv(SUMMARY_CSV, index=False, encoding='utf-8-sig')
            print(f'Wrote summary CSV to {SUMMARY_CSV} (rows={len(df)})')
    except Exception as e:
        print(f'Failed to write summary CSV: {e}')

    print('Done.')
