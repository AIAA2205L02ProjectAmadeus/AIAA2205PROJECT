#!/usr/bin/env python3
"""
scripts/summarize_results.py

读入 `results/structured_results.jsonl`，做去重与统计，输出：
- results/structured_results.dedup.jsonl
- results/structured_summary.auto.csv
- results/plots/choices_bar.png
- results/plots/errors_pie.png

依赖: pandas, matplotlib
用法: python3 scripts/summarize_results.py
"""
import os
import json
from collections import Counter
from pathlib import Path

try:
    import pandas as pd
    import matplotlib.pyplot as plt
except Exception:
    print("请先安装依赖: pip install pandas matplotlib")
    raise

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SRC = RESULTS / "structured_results.jsonl"
DEDUP = RESULTS / "structured_results.dedup.jsonl"
SUMMARY_CSV = RESULTS / "structured_summary.auto.csv"
PLOTS_DIR = RESULTS / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                # 尽量跳过无法解析的行
                continue


def dedupe_records(records):
    seen = set()
    out = []
    for r in records:
        # 构造健值: 尝试使用 sample id / model / strategy / language
        sid = r.get("sample_id") or r.get("id")
        if sid is None:
            sample = r.get("question") or r.get("sample") or ""
            sid = hash(sample[:200])
        key = (sid, r.get("model"), r.get("strategy"), r.get("language"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def summarize(records):
    total = len(records)
    parse_errors = sum(1 for r in records if r.get("parse_error") is True)
    api_errors = sum(1 for r in records if r.get("model_raw_output", "").lower().startswith("api_error") or r.get("api_error") is True)
    models = Counter(r.get("model") for r in records)
    choices = Counter(r.get("predicted_choice") or r.get("choice") or "" for r in records)
    # 分类占比
    categories = Counter(r.get("category") for r in records)

    stats = {
        "total_records": total,
        "parse_errors": parse_errors,
        "api_errors": api_errors,
        "unique_models": len(models),
    }
    return stats, models, choices, categories


def main():
    if not SRC.exists():
        print(f"找不到 {SRC}; 请确认评测结果已写入此文件。")
        return

    print("读取原始 JSONL ...")
    records = list(load_jsonl(SRC))
    print(f"读入记录: {len(records)} 条")

    print("开始去重...（基于 sample/model/strategy/language）")
    deduped = dedupe_records(records)
    print(f"去重后记录: {len(deduped)} 条")

    print("写入去重文件...", DEDUP)
    with open(DEDUP, "w", encoding="utf-8") as f:
        for r in deduped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("统计摘要...")
    stats, models, choices, categories = summarize(deduped)
    # 写 CSV 汇总
    print("生成 CSV 汇总...", SUMMARY_CSV)
    df_models = pd.DataFrame([{"model": m, "count": c} for m, c in models.items()])
    df_choices = pd.DataFrame([{"choice": k, "count": v} for k, v in choices.items()])
    # 合并为总表
    with pd.ExcelWriter(SUMMARY_CSV.with_suffix('.xlsx')) as ew:
        df_models.sort_values('count', ascending=False).to_excel(ew, sheet_name='models', index=False)
        df_choices.sort_values('count', ascending=False).to_excel(ew, sheet_name='choices', index=False)
        pd.DataFrame([stats]).to_excel(ew, sheet_name='summary', index=False)

    # 也写一个简洁的 CSV（summary 样式）
    summary_rows = [
        ("total_records", stats["total_records"]),
        ("parse_errors", stats["parse_errors"]),
        ("api_errors", stats["api_errors"]),
        ("unique_models", stats["unique_models"]),
    ]
    pd.DataFrame(summary_rows, columns=["metric","value"]).to_csv(SUMMARY_CSV, index=False)

    # 绘图：choice 分布与错误占比
    print("绘图...")
    choices_items = sorted(choices.items(), key=lambda x: x[1], reverse=True)
    if choices_items:
        labels, vals = zip(*choices_items[:20])
        plt.figure(figsize=(8,4))
        plt.bar(labels, vals)
        plt.title('Top choices')
        plt.xlabel('choice')
        plt.ylabel('count')
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'choices_bar.png')
        plt.close()

    # 错误饼图
    err_counts = {'parse_error': stats['parse_errors'], 'api_error': stats['api_errors'], 'ok': stats['total_records'] - stats['parse_errors'] - stats['api_errors']}
    plt.figure(figsize=(6,6))
    plt.pie(list(err_counts.values()), labels=list(err_counts.keys()), autopct='%1.1f%%')
    plt.title('Error breakdown')
    plt.savefig(PLOTS_DIR / 'errors_pie.png')
    plt.close()

    print("完成。输出文件：")
    print(" -", DEDUP)
    print(" -", SUMMARY_CSV)
    print(" -", PLOTS_DIR)


if __name__ == '__main__':
    main()
