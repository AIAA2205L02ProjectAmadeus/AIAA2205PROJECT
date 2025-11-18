import os
import pandas as pd
import time
import re

# Try to import SiliconflowClient if available
try:
    from llm_cot_siliconflow_py.src.siliconflow_client import SiliconflowClient
    HAVE_SILICONFLOW = True
except Exception:
    HAVE_SILICONFLOW = False

# If the project package isn't installed as a package we can still import via path
if not HAVE_SILICONFLOW:
    import sys
    project_client_path = os.path.join(os.path.dirname(__file__), '..', 'llm-cot-siliconflow-py', 'src')
    project_client_path = os.path.abspath(project_client_path)
    if os.path.isdir(project_client_path):
        sys.path.insert(0, project_client_path)
        try:
            from siliconflow_client import SiliconflowClient
            HAVE_SILICONFLOW = True
        except Exception:
            HAVE_SILICONFLOW = False


def heuristic_category(question: str) -> str:
    """A simple keyword-based fallback classifier."""
    q = question.lower()
    # quantitative hints
    if re.search(r"\d|多少|几|平方|百分比|公里|米|小时|分钟|分钟|加|减|乘|除|速度|速度为|速度是", q):
        return "Quantitative"
    # logical hints
    if re.search(r"如果|则|那么|前提|结论|逻辑|能否推断|是否可以推出|蕴含", q):
        return "Logical"
    # commonsense default
    return "Commonsense"


def classify_file_with_model(source_csv: str, target_csv: str, client=None, max_examples=None):
    df = pd.read_csv(source_csv)
    if max_examples:
        df = df.head(max_examples)

    if 'Category' in df.columns:
        print(f"Category column already in {source_csv}, skipping model classification.")
        df.to_csv(target_csv, index=False, encoding='utf-8')
        return

    categories = []
    if client:
        print("Using SiliconflowClient for classification...")
        for idx, row in df.iterrows():
            question = str(row.get('Question', ''))
            prompt = (
                "请将下面的问题归类为三类之一：\n"
                "1) Commonsense（常识推理）\n"
                "2) Logical（逻辑推理）\n"
                "3) Quantitative（定量推理）\n"
                "仅输出类别名称之一（Commonsense/Logical/Quantitative）和一句最多五个字的简短说明，不要输出其它文本。\n\n"
                f"问题: {question}\n"
                "请在下一行输出:"
            )
            try:
                out = client.generate(prompt)
                # Take first token that matches known labels
                label = None
                for candidate in ['Commonsense', 'Logical', 'Quantitative', '常识', '逻辑', '定量']:
                    if candidate.lower() in out.lower():
                        if candidate == '常识':
                            label = 'Commonsense'
                        elif candidate == '逻辑':
                            label = 'Logical'
                        elif candidate == '定量':
                            label = 'Quantitative'
                        else:
                            label = candidate
                        break
                if not label:
                    # fallback: attempt to parse first word
                    first_word = out.strip().split()[0]
                    if first_word.lower() in ['commonsense', 'logical', 'quantitative']:
                        label = first_word.capitalize()
                    else:
                        label = heuristic_category(question)
                categories.append(label)
            except Exception as e:
                print(f"Model classification failed for index {idx}: {e}")
                categories.append(heuristic_category(question))
            time.sleep(0.3)
    else:
        print("No Siliconflow client available; using heuristic classifier.")
        for _, row in df.iterrows():
            question = str(row.get('Question', ''))
            categories.append(heuristic_category(question))

    df['Category'] = categories
    os.makedirs(os.path.dirname(target_csv), exist_ok=True)
    df.to_csv(target_csv, index=False, encoding='utf-8')
    print(f"Saved labeled file to {target_csv}")


def main():
    source_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'dev')
    target_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'dev_labeled')
    os.makedirs(target_dir, exist_ok=True)

    client = None
    if HAVE_SILICONFLOW:
        try:
            client = SiliconflowClient(model_name="Qwen/Qwen2-7B-Instruct")
        except Exception as e:
            print(f"Siliconflow client init failed: {e}")
            client = None

    files = [f for f in os.listdir(source_dir) if f.endswith('.csv')]
    for f in files:
        src = os.path.join(source_dir, f)
        tgt = os.path.join(target_dir, f)
        print(f"\nProcessing {src} -> {tgt}")
        # For quick testing, we can limit max_examples; by default None
        classify_file_with_model(src, tgt, client=client, max_examples=None)


if __name__ == '__main__':
    main()
