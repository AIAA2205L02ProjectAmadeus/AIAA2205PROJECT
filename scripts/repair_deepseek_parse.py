#!/usr/bin/env python3
"""尝试修复 deepseek-ai/DeepSeek-V2.5 的 parse_error 条目。

功能：
- 读取 results/structured_results.dedup.jsonl
- 对 model_raw_output 做清洗（去除 ```json code fences、strip 前后空白、提取第一个 {...}）
- 尝试 json.loads，若成功则记录为 repaired
- 输出修复尝试的详细 JSONL 到 results/deepseek_parse_repair.jsonl
- 输出汇总到 results/deepseek_parse_repair_summary.json

此脚本不会修改原始数据文件，仅写入新的报告文件供人工审核。
"""
import json
import re
from pathlib import Path


def clean_output(text: str) -> str:
    if text is None:
        return ''
    s = text
    # Remove common markdown code fences like ```json ... ``` or ``` ... ```
    s = re.sub(r"^\s*```(?:json)?\s*", '', s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```\s*$", '', s)
    s = s.strip()
    return s


def extract_first_json(s: str) -> str:
    # Try to find the first {...} block. Use a simple balanced scan to find matching braces.
    start = s.find('{')
    if start == -1:
        return ''
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    # fallback: regex non-greedy (may fail on nested braces)
    m = re.search(r"(\{.*?\})", s, flags=re.DOTALL)
    return m.group(1) if m else ''


def try_load(s: str):
    import json
    try:
        return json.loads(s)
    except Exception:
        pass
    # try decoding unicode escapes
    try:
        return json.loads(s.encode('utf-8').decode('unicode_escape'))
    except Exception:
        pass
    return None


def main():
    repo_root = Path(__file__).resolve().parents[1]
    dedup_path = repo_root / 'results' / 'structured_results.dedup.jsonl'
    out_path = repo_root / 'results' / 'deepseek_parse_repair.jsonl'
    summary_path = repo_root / 'results' / 'deepseek_parse_repair_summary.json'

    total = 0
    repaired = 0
    repaired_examples = []
    failed_examples = []
    parse_error_msgs = {}

    if not dedup_path.exists():
        print('dedup file not found:', dedup_path)
        return

    with dedup_path.open('r', encoding='utf-8') as fr, out_path.open('w', encoding='utf-8') as fw:
        for line in fr:
            line = line.rstrip('\n')
            if not line:
                continue
            try:
                j = json.loads(line)
            except Exception:
                continue
            model = j.get('model','') or ''
            if not model.lower().startswith('deepseek'):
                continue
            if not j.get('parse_error'):
                continue
            total += 1
            msg = j.get('parse_error_msg') or '<none>'
            parse_error_msgs[msg] = parse_error_msgs.get(msg,0) + 1

            raw = j.get('model_raw_output') or ''
            cleaned = clean_output(raw)

            parsed = try_load(cleaned)
            method = 'clean_strip'
            if parsed is None:
                # try extract first JSON block
                candidate = extract_first_json(cleaned)
                if candidate:
                    parsed = try_load(candidate)
                    method = 'extract_first_json'
            record = {
                'file': j.get('file'),
                'row_index': j.get('row_index'),
                'original_parse_error_msg': msg,
                'repair_method': method,
                'repaired': bool(parsed),
            }
            if parsed:
                repaired += 1
                record['parsed'] = parsed
                repaired_examples.append(record)
            else:
                # include a short snippet for debugging
                record['model_raw_output_snippet'] = (raw or '')[:1000]
                failed_examples.append(record)
            fw.write(json.dumps(record, ensure_ascii=False) + '\n')

    summary = {
        'total_deepseek_parse_error': total,
        'repaired_count': repaired,
        'failed_count': total - repaired,
        'top_parse_error_msgs': sorted(parse_error_msgs.items(), key=lambda x: -x[1])[:20],
    }
    with summary_path.open('w', encoding='utf-8') as sf:
        json.dump(summary, sf, ensure_ascii=False, indent=2)

    print('TOTAL_DEEPSEEK_PARSE_ERROR=', total)
    print('REPAIRED=', repaired)
    print('FAILED=', total - repaired)
    print('SUMMARY written to', summary_path)
    print('DETAILED records written to', out_path)


if __name__ == '__main__':
    main()
