#!/usr/bin/env python3
"""尝试修复所有模型的 parse_error 条目。

输出:
- results/parse_repair_all.jsonl
- results/parse_repair_all_summary.json

该脚本不会修改源文件，仅写入修复尝试报告。
"""
import json
import re
from pathlib import Path


def clean_output(text: str) -> str:
    if text is None:
        return ''
    s = text
    s = re.sub(r"^\s*```(?:json)?\s*", '', s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```\s*$", '', s)
    return s.strip()


def extract_first_json(s: str) -> str:
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
    m = re.search(r"(\{.*?\})", s, flags=re.DOTALL)
    return m.group(1) if m else ''


def try_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        pass
    try:
        return json.loads(s.encode('utf-8').decode('unicode_escape'))
    except Exception:
        pass
    return None


def main():
    repo_root = Path(__file__).resolve().parents[1]
    dedup_path = repo_root / 'results' / 'structured_results.dedup.jsonl'
    out_path = repo_root / 'results' / 'parse_repair_all.jsonl'
    summary_path = repo_root / 'results' / 'parse_repair_all_summary.json'

    if not dedup_path.exists():
        print('dedup file not found:', dedup_path)
        return

    total = 0
    repaired = 0
    failed = 0
    parse_error_msgs = {}
    repaired_examples = []

    with dedup_path.open('r', encoding='utf-8') as fr, out_path.open('w', encoding='utf-8') as fw:
        for line in fr:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if not r.get('parse_error'):
                continue
            total += 1
            msg = r.get('parse_error_msg') or '<none>'
            parse_error_msgs[msg] = parse_error_msgs.get(msg, 0) + 1

            raw = r.get('model_raw_output') or ''
            cleaned = clean_output(raw)
            parsed = try_load(cleaned)
            method = 'clean_strip'
            if parsed is None:
                candidate = extract_first_json(cleaned)
                if candidate:
                    parsed = try_load(candidate)
                    method = 'extract_first_json'

            out = {
                'file': r.get('file'),
                'row_index': r.get('row_index'),
                'model': r.get('model'),
                'strategy': r.get('strategy'),
                'language': r.get('language'),
                'original_parse_error_msg': msg,
                'repair_method': method,
                'repaired': bool(parsed),
            }
            if parsed:
                repaired += 1
                out['parsed'] = parsed
                repaired_examples.append(out)
            else:
                failed += 1
                out['model_raw_output_snippet'] = (raw or '')[:1000]
            fw.write(json.dumps(out, ensure_ascii=False) + '\n')

    summary = {
        'total_parse_error': total,
        'repaired_count': repaired,
        'failed_count': failed,
        'top_parse_error_msgs': sorted(parse_error_msgs.items(), key=lambda x: -x[1])[:20],
    }
    with summary_path.open('w', encoding='utf-8') as sf:
        json.dump(summary, sf, ensure_ascii=False, indent=2)

    print('TOTAL_PARSE_ERROR=', total)
    print('REPAIRED=', repaired)
    print('FAILED=', failed)
    print('Wrote details to', out_path)
    print('Wrote summary to', summary_path)


if __name__ == '__main__':
    main()
