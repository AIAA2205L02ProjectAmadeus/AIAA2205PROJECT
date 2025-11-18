#!/usr/bin/env python3
"""Apply parse repairs to dedup records and produce a refreshed summary and plots.

Writes:
- results/structured_results.repaired.dedup.jsonl
- results/structured_summary.repaired.auto.csv
- results/structured_summary.repaired.auto.xlsx
- results/plots_repaired/
"""
import json
from pathlib import Path
from collections import Counter

try:
    import pandas as pd
    import matplotlib.pyplot as plt
except Exception:
    print('请先安装依赖: pip install pandas matplotlib openpyxl')
    raise


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
DEDUP = RESULTS / 'structured_results.dedup.jsonl'
REPAIRS = RESULTS / 'parse_repair_all.jsonl'
OUT_DEDUP = RESULTS / 'structured_results.repaired.dedup.jsonl'
SUMMARY_CSV = RESULTS / 'structured_summary.repaired.auto.csv'
SUMMARY_XLSX = RESULTS / 'structured_summary.repaired.auto.xlsx'
PLOTS_DIR = RESULTS / 'plots_repaired'
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def load_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def key_from_rec(r):
    return (r.get('file'), r.get('row_index'), r.get('model'), r.get('strategy'), r.get('language'))


def normalize_choice(c):
    if c is None:
        return ''
    return str(c).strip().upper()


def main():
    if not DEDUP.exists():
        print('找不到去重文件:', DEDUP)
        return
    repairs_map = {}
    if REPAIRS.exists():
        for r in load_jsonl(REPAIRS):
            k = (r.get('file'), r.get('row_index'), r.get('model'), r.get('strategy'), r.get('language'))
            repairs_map[k] = r

    records = list(load_jsonl(DEDUP))
    out_records = []
    applied = 0
    for r in records:
        if r.get('parse_error'):
            k = key_from_rec(r)
            repair = repairs_map.get(k)
            if repair and repair.get('repaired') and repair.get('parsed'):
                parsed = repair['parsed']
                # Map parsed fields
                choice = parsed.get('choice') or parsed.get('predicted_choice')
                reason = parsed.get('reason') or parsed.get('predicted_reason')
                sj = parsed.get('self_judgment') or parsed.get('predicted_self_judgment')
                if choice is not None:
                    r['predicted_choice'] = choice
                if reason is not None:
                    r['predicted_reason'] = reason
                if sj is not None:
                    r['predicted_self_judgment'] = sj
                # mark parse_error cleared
                r['parse_error'] = False
                r['parse_error_msg'] = ''
                # update reason_length
                r['reason_length'] = len(r.get('predicted_reason') or '')
                # recompute is_correct if standard_answer exists
                std = r.get('standard_answer')
                if std is not None and r.get('predicted_choice') is not None:
                    r['is_correct'] = normalize_choice(r.get('predicted_choice')) == normalize_choice(std)
                applied += 1
        out_records.append(r)

    # write repaired dedup
    with OUT_DEDUP.open('w', encoding='utf-8') as fw:
        for r in out_records:
            fw.write(json.dumps(r, ensure_ascii=False) + '\n')

    print(f'Applied repairs to {applied} records. Wrote {OUT_DEDUP}')

    # Summarize
    total = len(out_records)
    parse_errors = sum(1 for r in out_records if r.get('parse_error') is True)
    api_errors = sum(1 for r in out_records if r.get('model_raw_output','').lower().startswith('api_error') or r.get('api_error') is True)
    models = Counter(r.get('model') for r in out_records)
    choices = Counter(r.get('predicted_choice') or r.get('choice') or '' for r in out_records)

    stats = {
        'total_records': total,
        'parse_errors': parse_errors,
        'api_errors': api_errors,
        'unique_models': len(models),
    }

    # write xlsx summary
    df_models = pd.DataFrame([{'model': m, 'count': c} for m, c in models.items()])
    df_choices = pd.DataFrame([{'choice': k, 'count': v} for k, v in choices.items()])
    with pd.ExcelWriter(SUMMARY_XLSX) as ew:
        df_models.sort_values('count', ascending=False).to_excel(ew, sheet_name='models', index=False)
        df_choices.sort_values('count', ascending=False).to_excel(ew, sheet_name='choices', index=False)
        pd.DataFrame([stats]).to_excel(ew, sheet_name='summary', index=False)

    # CSV summary
    pd.DataFrame(list(stats.items()), columns=['metric','value']).to_csv(SUMMARY_CSV, index=False)

    # plots
    choices_items = sorted(choices.items(), key=lambda x: x[1], reverse=True)
    if choices_items:
        labels, vals = zip(*choices_items[:20])
        plt.figure(figsize=(8,4))
        plt.bar(labels, vals)
        plt.title('Top choices (repaired)')
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'choices_bar_repaired.png')
        plt.close()

    err_counts = {'parse_error': stats['parse_errors'], 'api_error': stats['api_errors'], 'ok': stats['total_records'] - stats['parse_errors'] - stats['api_errors']}
    plt.figure(figsize=(6,6))
    plt.pie(list(err_counts.values()), labels=list(err_counts.keys()), autopct='%1.1f%%')
    plt.title('Error breakdown (repaired)')
    plt.savefig(PLOTS_DIR / 'errors_pie_repaired.png')
    plt.close()

    print('Wrote repaired summary CSV/XLSX and plots to', PLOTS_DIR)


if __name__ == '__main__':
    main()
