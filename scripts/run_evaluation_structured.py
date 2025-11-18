import os
import sys
import time
import json
import random
import logging
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

# try to import prompts.get_prompt from project
try:
    from prompts import get_prompt
except Exception:
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

# Structured JSON instruction template
JSON_INSTRUCTION_TEMPLATE = (
    "你需要以严格的 JSON 格式返回答案，且只能返回 JSON，对其它任何文本都不允许。\n"
    "返回的 JSON 结构必须包含三个字段：\n"
    "  - choice: 一个字符，代表模型选择的选项（A/B/C/D），若无法确定请返回空字符串 \"\"。\n"
    "  - reason: 字符串，简短的逐步推理或一句话解释（最多 200 字）。\n"
    "  - self_judgment: 字符串，模型自我判断该选择是否正确，值必须是 'correct' 或 'incorrect'（小写）。\n"
    "例如： {\"choice\": \"A\", \"reason\": \"因为...\", \"self_judgment\": \"correct\"}\n"
    "注意：只允许输出 JSON，不要包含任何额外的文字或说明。"
)

JSON_INSTRUCTION_TEMPLATE_EN = (
    "Return ONLY a strict JSON object (no extra text). The JSON must contain exactly three fields:\n"
    "  - choice: string, one of \"A\" / \"B\" / \"C\" / \"D\"; if unsure, return an empty string \"\".\n"
    "  - reason: string, a short step-by-step rationale or one-sentence explanation (max 200 characters).\n"
    "  - self_judgment: string, model's self-assessment, MUST be either \"correct\" or \"incorrect\" (lowercase).\n"
    "Example: {\"choice\":\"A\", \"reason\":\"Because...\", \"self_judgment\":\"correct\"}\n"
    "Note: Output only JSON, do NOT include any other text."
)

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
            # collect option texts if present
            a = str(r.get('A','') or '')
            b = str(r.get('B','') or '')
            c = str(r.get('C','') or '')
            d = str(r.get('D','') or '')
            rows.append({'file':f,'row_index':int(idx),'question':q,'answer':ans,'category':cat,'A':a,'B':b,'C':c,'D':d})
    if not rows:
        return []
    random.shuffle(rows)
    return rows[:max_samples]


def parse_model_json(output):
    """Try to parse model output as JSON. Return dict with fields or None and error."""
    out = output.strip()
    try:
        parsed = json.loads(out)
        # Ensure keys exist
        choice = parsed.get('choice','') if isinstance(parsed.get('choice',''), str) else ''
        reason = parsed.get('reason','') if isinstance(parsed.get('reason',''), str) else ''
        self_judgment = parsed.get('self_judgment','') if isinstance(parsed.get('self_judgment',''), str) else ''
        return {'choice': choice.strip().upper(), 'reason': reason.strip(), 'self_judgment': self_judgment.strip().lower()}, None
    except Exception as e:
        return None, str(e)


def normalize_choice(c):
    if not isinstance(c, str):
        return ''
    c = c.strip().upper()
    if c in ['A','B','C','D']:
        return c
    # sometimes models return like 'Option A' or 'A.' etc.
    import re
    m = re.search(r"\b([ABCD])\b", c)
    if m:
        return m.group(1)
    return ''


def call_with_retries(client, prompt, max_retries=5, base_delay=1.0, max_delay=60.0):
    """Call client's generate(prompt) with bounded retries, exponential backoff and jitter.
    Returns the string output on success or raises the last exception on failure.
    """
    attempts = 0
    while True:
        try:
            attempts += 1
            return client.generate(prompt)
        except Exception as e:
            # if we've reached the allowed number of attempts, re-raise
            if attempts >= max_retries:
                logging.exception("Exceeded max_retries calling client.generate")
                raise
            # exponential backoff with jitter
            sleep_base = min(max_delay, base_delay * (2 ** (attempts - 1)))
            jitter = random.uniform(0, sleep_base * 0.1)
            sleep_time = sleep_base + jitter
            logging.warning(f"client.generate failed (attempt {attempts}/{max_retries}): {e}; retrying in {sleep_time:.2f}s")
            time.sleep(sleep_time)


def run_structured_eval(models, strategies, languages, samples_per_lang=10, delay=0.8, resume=False, processed_set=None):
    results_dir = os.path.join('results')
    os.makedirs(results_dir, exist_ok=True)
    results_file = os.path.join(results_dir, 'structured_results.jsonl')
    summary_csv = os.path.join(results_dir, 'structured_summary.csv')

    records = []

    for lang in languages:
        data_dir = os.path.join('data','dev_labeled') if lang == 'zh' else os.path.join('data_en_baidu','dev_labeled')
        samples = collect_samples(data_dir, samples_per_lang)
        print(f"Language {lang}: collected {len(samples)} samples from {data_dir}")

        for model_name in models:
            client = SiliconflowClient(model_name=model_name)
            for strategy in strategies:
                print(f"Running: model={model_name}, lang={lang}, strategy={strategy}, samples={len(samples)}")
                for s in tqdm(samples, desc=f"{model_name}-{lang}-{strategy}"):
                    # If resuming, skip any sample already processed for this model/strategy/lang
                    if resume and processed_set is not None:
                        key = (model_name, lang, strategy, s.get('file'), int(s.get('row_index')))
                        if key in processed_set:
                            # skip already processed
                            continue
                    # Build prompt: include original prompt, explicit ABCD options, and JSON instruction
                    base_prompt = get_prompt(strategy=strategy, question=s['question'], task_type='quantitative')
                    options_text = f"选项：\nA. {s.get('A','')}\nB. {s.get('B','')}\nC. {s.get('C','')}\nD. {s.get('D','')}\n\n请仅从 A/B/C/D 四个选项中选择一个。\n"
                    prompt = base_prompt + "\n\n" + options_text + JSON_INSTRUCTION_TEMPLATE
                    # Safety check: ensure we are not accidentally including the standard answer
                    # in the prompt in common explicit forms (e.g. '答案: A', 'Answer: A', '标准答案').
                    # This is to prevent accidental leakage of ground-truth to the evaluated model.
                    ground_truth = s['answer'].strip().upper() if isinstance(s['answer'], str) else ''
                    lower_prompt = prompt.lower()
                    leak_indicators = [
                        '标准答案', 'standard_answer', 'standard answer', '参考答案',
                        '答案:' , '答案：', 'answer:'
                    ]
                    for token in leak_indicators:
                        if token in lower_prompt:
                            # If the prompt contains an explicit '答案:' or similar, check whether
                            # the ground-truth letter itself appears directly after that token.
                            # This avoids false positives from few-shot examples that contain answers
                            # but not the current sample's ground truth.
                            import re
                            # look for patterns like '答案: A' or 'answer: A'
                            pattern = re.escape(token) + r"\s*[:：]?\s*([A-Da-d])"
                            m = re.search(pattern, prompt, re.IGNORECASE)
                            if m:
                                found = m.group(1).upper()
                                if ground_truth and found == ground_truth:
                                    raise RuntimeError(f"Detected possible leakage of ground-truth into prompt for file {s['file']} row {s['row_index']}. Token='{token}' matched with '{found}'. Prompt snippet: {prompt[max(0, m.start()-80):m.end()+80]}")
                            # also detect literal tokens like 'standard_answer' being present
                            if token in ['standard_answer', 'standard answer', '标准答案', '参考答案'] and token in lower_prompt:
                                raise RuntimeError(f"Detected token '{token}' in prompt which may indicate leakage (file {s['file']} row {s['row_index']}).")
                    try:
                        out = call_with_retries(client, prompt, max_retries=5, base_delay=1.0, max_delay=60.0)
                    except Exception as e:
                        # If retries exhausted, capture the error string for record and continue
                        out = f"API_ERROR: {e}"

                    parsed, err = parse_model_json(out)
                    parse_error = False
                    parse_error_msg = ''
                    predicted_choice = ''
                    predicted_reason = ''
                    predicted_self_judgment = ''
                    if parsed is None:
                        parse_error = True
                        parse_error_msg = err or 'parse_failed'
                        # fallback: extract single letter
                        import re
                        m = re.search(r"\b([ABCD])\b", out.upper())
                        predicted_choice = m.group(1) if m else ''
                    else:
                            predicted_choice = normalize_choice(parsed.get('choice',''))
                            predicted_reason = parsed.get('reason','')
                            # truncate reason to max 200 chars
                            if isinstance(predicted_reason, str) and len(predicted_reason) > 200:
                                predicted_reason = predicted_reason[:200]
                            predicted_self_judgment = parsed.get('self_judgment','').lower()

                    # script computed correctness
                    ground_truth = s['answer'].strip().upper() if isinstance(s['answer'], str) else ''
                    is_correct = (predicted_choice == ground_truth) if predicted_choice else False

                    reason_length = len(predicted_reason) if predicted_reason else 0
                    rec = {
                        'model': model_name,
                        'language': lang,
                        'strategy': strategy,
                        'file': s['file'],
                        'row_index': s['row_index'],
                        'question': s['question'],
                        'standard_answer': ground_truth,
                        'model_raw_output': out,
                        'parse_error': parse_error,
                        'parse_error_msg': parse_error_msg,
                        'predicted_choice': predicted_choice,
                        'predicted_reason': predicted_reason,
                        'predicted_self_judgment': predicted_self_judgment,
                        'reason_length': reason_length,
                        'is_correct': is_correct,
                        'category': s['category']
                    }

                    records.append(rec)
                    with open(results_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + '\n')

                    time.sleep(delay)

    # write summary
    df = pd.DataFrame(records)
    if not df.empty:
        df.to_csv(summary_csv, index=False, encoding='utf-8-sig')
    print(f"Structured evaluation finished. Results: {results_file}, Summary: {summary_csv}")
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=10, help='samples per language')
    parser.add_argument('--delay', type=float, default=0.8, help='delay between API calls (seconds)')
    parser.add_argument('--resume', action='store_true', help='resume from existing results/structured_results.jsonl and skip already-processed items')
    parser.add_argument('--models', type=str, default=None, help='comma-separated list of models to test (overrides project main.py)')
    args = parser.parse_args()

    # If --models provided on the command line, use it (comma-separated list).
    if args.models:
        models_to_test = [m.strip() for m in args.models.split(',') if m.strip()]
    else:
        # otherwise try to load models from project main if possible
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

    print(f"Models: {models_to_test}\nStrategies: {strategies}\nLanguages: {languages}\nSamples per language: {args.samples}\nResume mode: {args.resume}")
    # Load processed set if resume requested
    processed = set()
    results_file = os.path.join('results', 'structured_results.jsonl')
    if args.resume and os.path.exists(results_file):
        try:
            with open(results_file, 'r', encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        j = json.loads(line)
                        key = (j.get('model'), j.get('language'), j.get('strategy'), j.get('file'), int(j.get('row_index')))
                        processed.add(key)
                    except Exception:
                        continue
            print(f"Loaded {len(processed)} processed records from {results_file}")
        except Exception as e:
            print(f"Failed to load existing results for resume: {e}")

    try:
        records = run_structured_eval(models=models_to_test, strategies=strategies, languages=languages, samples_per_lang=args.samples, delay=args.delay, resume=args.resume, processed_set=processed)
    except KeyboardInterrupt:
        print("Run interrupted by user (KeyboardInterrupt). Partial results have been saved to results/structured_results.jsonl")
        sys.exit(1)

    if records:
        print('\nFive example structured records:')
        for r in records[:5]:
            print(json.dumps(r, ensure_ascii=False, indent=2))
