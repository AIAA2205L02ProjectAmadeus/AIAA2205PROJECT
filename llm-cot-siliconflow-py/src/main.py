import json
import pandas as pd
from tqdm import tqdm
import os

from siliconflow_client import SiliconflowClient
from prompts import get_prompt

# --- 配置 ---
MODELS_TO_TEST = [
    "Qwen/Qwen2-7B-Instruct",
    # "deepseek-ai/deepseek-coder-6.7b-instruct",
    # "meta-llama/Llama-2-13b-chat-hf",
    # "Qwen/Qwen-72B-Chat" # 如果可用
]

STRATEGIES_TO_TEST = [
    "zero_shot",
    "few_shot",
    "zero_shot_cot",
    "few_shot_cot"
]

# 获取脚本所在目录的绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(script_dir, "..", "data", "sample_questions.json")
RESULTS_OUTPUT_PATH = os.path.join(script_dir, "..", "results.csv")

def run_experiments():
    """
    加载数据集，遍历模型和策略，运行实验并保存结果。
    """
    # 加载数据集
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    all_results = []

    # 使用 tqdm 创建总进度条
    total_iterations = sum(len(questions) for questions in dataset.values()) * len(MODELS_TO_TEST) * len(STRATEGIES_TO_TEST)
    with tqdm(total=total_iterations, desc="总进度") as pbar:
        for model_name in MODELS_TO_TEST:
            print(f"\n--- 正在测试模型: {model_name} ---")
            client = SiliconflowClient(model_name=model_name)
            
            for task_type, questions in dataset.items():
                for question_data in questions:
                    for strategy in STRATEGIES_TO_TEST:
                        prompt = get_prompt(
                            strategy=strategy,
                            question=question_data["question"],
                            task_type=task_type.split('_')[0] # e.g., "quantitative_reasoning" -> "quantitative"
                        )
                        
                        # 调用 API 获取模型输出
                        model_output = client.generate(prompt)
                        
                        # 记录结果
                        result_entry = {
                            "model": model_name,
                            "task_type": task_type,
                            "question_id": question_data["id"],
                            "question": question_data["question"],
                            "standard_answer": question_data["answer"],
                            "strategy": strategy,
                            "prompt": prompt,
                            "model_output": model_output
                        }
                        all_results.append(result_entry)
                        pbar.update(1)

    # 保存结果到 CSV
    df = pd.DataFrame(all_results)
    df.to_csv(RESULTS_OUTPUT_PATH, index=False, encoding='utf-8-sig')
    print(f"\n实验完成！结果已保存到 {RESULTS_OUTPUT_PATH}")


if __name__ == "__main__":
    run_experiments()