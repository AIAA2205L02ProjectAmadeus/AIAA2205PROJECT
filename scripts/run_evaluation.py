import os
import sys
import time
import json
import random
import argparse
import pandas as pd
from tqdm import tqdm

# Ensure siliconflow client is importable
project_client_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'llm-cot-siliconflow-py', 'src'))
if project_client_path not in sys.path:
    sys.path.insert(0, project_client_path)

try:
    from siliconflow_client import SiliconflowClient
except Exception as e:
    print(f"Failed to import SiliconflowClient: {e}")
    raise

# Import get_prompt from project prompts
prompts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'llm-cot-siliconflow-py', 'src'))
if prompts_path not in sys.path:
    sys.path.insert(0, prompts_path)
try:
    from prompts import get_prompt
except Exception:
    # Fallback: simple prompt generator
    def get_prompt(strategy, question, task_type='quantitative'):
        if strategy == 'zero_shot':
            return f"请回答以下问题，只输出最终答案：\n问题: {question}"
        if strategy == 'few_shot':
            return f"示例...\n请回答:\n问题: {question}\n答案:"
        if strategy == 'zero_shot_cot':
            return f"请回答以下问题，逐步思考，最后给出答案。\n问题: {question}"
        if strategy == 'few_shot_cot':
            return f"示例...\n请回答:\n问题: {question}\n思考过程:"
        return question


DEFAULT_STRATEGIES = ["zero_shot","few_shot","zero_shot_cot","few_shot_cot"]


def collect_samples(language_dir, max_samples):
    rows = []
    files = [f for f in os.listdir(language_dir) if f.endswith('.csv')]
    for f in files:
        path = os.path.join(language_dir, f)
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception as e:
            print(f"Failed to read {path}: {e}")
            continue
        for idx, r in df.iterrows():
            q = str(r.get('Question',''))
            ans = str(r.get('Answer',''))
            cat = str(r.get('Category',''))
            rows.append({'file':f,'row_index':int(idx),'question':q,'answer':ans,'category':cat})
    if not rows:
        return []
    random.shuffle(rows)
    return rows[:max_samples]


def extract_choice_from_output(output):
    if not isinstance(output, str):
        return ''
    # Try to find patterns like 'A', '(A)', 'Answer: A', '答案: A'
    out = output.upper()
    # common choices A/B/C/D
    m = None
    for token in ['(A)','(B)','(C)','(D)',' A.',' B.',' C.',' D.',' A)',' B)',' C)',' D)','答案: A','答案：A','ANSWER: A','SO THE ANSWER IS A']:
        if token in out:
            # return single letter present
            if 'A' in token:
                return 'A'
            if 'B' in token:
                return 'B'
            if 'C' in token:
                return 'C'
            if 'D' in token:
                return 'D'
    # fallback: regex find single letter A/B/C/D as a standalone token
    import re
    m = re.search(r"\b([ABCD])\b", out)
    if m:
        return m.group(1)
    return ''


def run_evaluation(models, strategies, languages, samples_per_lang=50, delay=0.6):
    results_dir = os.path.join('results')
    os.makedirs(results_dir, exist_ok=True)
    results_jsonl = os.path.join(results_dir, 'results.jsonl')
    summary_csv = os.path.join(results_dir, 'summary.csv')

    all_records = []

    for lang in languages:
        if lang == 'zh':
            data_dir = os.path.join('data','dev_labeled')
        else:
            data_dir = os.path.join('data_en_baidu','dev_labeled')
        samples = collect_samples(data_dir, samples_per_lang)
        print(f"Language {lang}: collected {len(samples)} samples from {data_dir}")

        for model_name in models:
            client = SiliconflowClient(model_name=model_name)
            for strategy in strategies:
                print(f"Running: model={model_name}, lang={lang}, strategy={strategy}, samples={len(samples)}")
                for s in tqdm(samples, desc=f"{model_name}-{lang}-{strategy}"):
                    prompt = get_prompt(strategy=strategy, question=s['question'], task_type='quantitative')
                    # Safety check: prevent accidental leakage of ground-truth into prompt
                    ground_truth = s['answer'].strip().upper() if isinstance(s['answer'], str) else ''
                    lower_prompt = prompt.lower()
                    leak_indicators = ['标准答案', 'standard_answer', 'standard answer', '参考答案', '答案:', '答案：', 'answer:']
                    for token in leak_indicators:
                        if token in lower_prompt:
                            import re
                            pattern = re.escape(token) + r"\s*[:：]?\s*([A-Da-d])"
                            m = re.search(pattern, prompt, re.IGNORECASE)
                            if m:
                                found = m.group(1).upper()
                                if ground_truth and found == ground_truth:
                                    raise RuntimeError(f"Detected possible leakage of ground-truth into prompt for file {s['file']} row {s['row_index']}. Token='{token}' matched with '{found}'.")
                            if token in ['standard_answer', 'standard answer', '标准答案', '参考答案'] and token in lower_prompt:
                                raise RuntimeError(f"Detected token '{token}' in prompt which may indicate leakage (file {s['file']} row {s['row_index']}).")
                    try:
                        out = client.generate(prompt)
                    except Exception as e:
                        out = f"API_ERROR: {e}"
                    extracted = extract_choice_from_output(out)
                    rec = {
                        'model': model_name,
                        'language': lang,
                        'strategy': strategy,
                        'file': s['file'],
                        'row_index': s['row_index'],
                        'question': s['question'],
                        'standard_answer': s['answer'],
                        'model_output': out,
                        'predicted_choice': extracted,
                        'category': s['category']
                    }
                    all_records.append(rec)
                    # write incrementally
                    with open(results_jsonl, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    time.sleep(delay)

    # write summary csv
    df = pd.DataFrame(all_records)
    if not df.empty:
        df.to_csv(summary_csv, index=False, encoding='utf-8-sig')
    print(f"Evaluation finished. JSONL: {results_jsonl}, Summary CSV: {summary_csv}")
    return all_records


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=50, help='samples per language')
    parser.add_argument('--delay', type=float, default=0.6, help='delay between API calls (seconds)')
    args = parser.parse_args()

    # read models from llm-cot-siliconflow-py/src/main.py if possible
    try:
        mf = os.path.join(os.path.dirname(__file__), '..', 'llm-cot-siliconflow-py', 'src', 'main.py')
        g = {}
        with open(mf, 'r', encoding='utf-8') as fh:
            code = fh.read()
        exec(code, g)
        models_to_test = g.get('MODELS_TO_TEST', ["Qwen/Qwen2-7B-Instruct"])
    except Exception:
        models_to_test = ["Qwen/Qwen2-7B-Instruct"]

    strategies = DEFAULT_STRATEGIES
    languages = ['zh','en']

    print(f"Models: {models_to_test}\nStrategies: {strategies}\nLanguages: {languages}\nSamples per language: {args.samples}")
    records = run_evaluation(models=models_to_test, strategies=strategies, languages=languages, samples_per_lang=args.samples, delay=args.delay)

    # show 5 examples
    if records:
        print('\nFive example records:')
        for r in records[:5]:
            print(json.dumps(r, ensure_ascii=False, indent=2))
