import json
import re
from typing import Dict, Any
from src.siliconflow_client import SiliconflowClient

# 使用一个高性能的模型作为裁判
JUDGE_MODEL = "Qwen/Qwen3-32B"

# 为裁判LLM设计的提示模板
JUDGE_PROMPT_TEMPLATE = """
你是一个严谨的逻辑分析师和AI评估员。你的任务是评估一个AI模型针对给定问题的“思维链”（CoT）推理过程是否正确。

你需要根据以下标准进行评估，并严格按照指定的JSON格式输出你的判断：

1.  **分析推理过程**: 仔细阅读AI模型的“思维链输出”，判断其中的每一步推理是否合乎逻辑、计算是否准确、是否遗漏了关键信息。
2.  **评估步骤正确性**: 以分数形式评估推理步骤的正确性。例如，如果一个推理包含5个步骤，其中4个是正确的，则得分为 "4/5"。如果整个过程完全正确，则为 "1/1" 或 "5/5"。如果完全错误，则为 "0/N"。
3.  **识别错误类型**: 如果推理过程中存在错误，请从以下类别中选择最主要的一个错误类型：
    *   `arithmetic_error`: 计算错误（例如，加减乘除错误）。
    *   `logical_fallacy`: 逻辑谬误（例如，前提和结论不匹配，错误的因果关系）。
    *   `premise_omission`: 遗漏了问题中的关键前提或信息。
    *   `hallucination`: 引入了问题中不存在的虚假信息。
    *   `incomplete_reasoning`: 推理链条不完整，未能得出最终结论。
    *   `correct`: 推理过程完全正确。
    *   `other`: 其他类型的错误。

---
**待评估信息**:

**问题**:
{question}

**标准答案**:
{standard_answer}

**AI模型的思维链输出**:
{model_cot_output}

---
**你的评估结果 (请严格以JSON格式输出)**:
```json
{{
  "step_correctness": "在此处填写步骤正确性得分，格式为 'X/Y'",
  "error_type": "在此处填写最主要的错误类型"
}}
```
"""

class JudgeLLM:
    """
    使用一个强大的LLM作为裁判，评估其他模型的CoT输出。
    """
    def __init__(self):
        self.client = SiliconflowClient(model_name=JUDGE_MODEL)

    def evaluate_cot_path(self, question: str, standard_answer: str, model_cot_output: str) -> Dict[str, Any]:
        """
        评估一个CoT推理路径。

        :param question: 原始问题。
        :param standard_answer: 标准答案。
        :param model_cot_output: 待评估的模型CoT输出。
        :return: 一个包含评估结果的字典。
        """
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            question=question,
            standard_answer=standard_answer,
            model_cot_output=model_cot_output
        )

        # 调用API
        raw_output = self.client.generate(prompt, max_tokens=512, temperature=0.1)

        # 解析JSON输出
        try:
            # 使用正则表达式从可能包含额外文本的输出中提取JSON块
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                # 如果正则匹配失败，尝试直接解析
                return json.loads(raw_output)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"无法解析裁判LLM的JSON输出: {e}")
            print(f"原始输出: {raw_output}")
            return {
                "step_correctness": "parse_error",
                "error_type": "parse_error"
            }

if __name__ == '__main__':
    # 示例用法
    judge = JudgeLLM()
    
    test_question = "一个篮子里有5个苹果，又放进去了3个，后来吃掉了4个，篮子里还剩几个苹果？"
    test_answer = "4个"
    
    # 正确的CoT
    correct_cot = "思考过程: 初始有5个苹果。放进去3个后，总数是 5 + 3 = 8个。然后吃掉了4个，所以剩下 8 - 4 = 4个。答案: 4个"
    
    # 错误的CoT (计算错误)
    incorrect_cot = "思考过程: 初始有5个苹果。放进去3个后，总数是 5 + 3 = 7个。然后吃掉了4个，所以剩下 7 - 4 = 3个。答案: 3个"

    print("--- 评估正确CoT ---")
    evaluation_correct = judge.evaluate_cot_path(test_question, test_answer, correct_cot)
    print(evaluation_correct)

    print("\n--- 评估错误CoT ---")
    evaluation_incorrect = judge.evaluate_cot_path(test_question, test_answer, incorrect_cot)
    print(evaluation_incorrect)
