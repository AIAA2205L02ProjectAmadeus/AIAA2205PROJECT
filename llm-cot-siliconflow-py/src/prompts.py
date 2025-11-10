# 示例问题，用于 Few-shot 和 Few-shot CoT
FEW_SHOT_EXAMPLES = {
    "quantitative": """示例1:
问题: 一个篮子里有5个苹果，又放进去了3个，后来吃掉了2个，篮子里还剩几个苹果？
答案: 6个

示例2:
问题: 一辆车以60公里/小时的速度行驶了2小时，它行驶了多少公里？
答案: 120公里""",
    "logical": """示例1:
问题: 前提A：所有的人都会死。前提B：苏格拉底是人。结论是什么？
答案: 苏格拉底会死。

示例2:
问题: 如果今天是星期三，那么后天是星期几？
答案: 星期五"""
}

FEW_SHOT_COT_EXAMPLES = {
    "quantitative": """示例1:
问题: 一个篮子里有5个苹果，又放进去了3个，后来吃掉了2个，篮子里还剩几个苹果？
思考过程: 初始有5个苹果。放进去3个后，苹果总数是 5 + 3 = 8个。然后吃掉了2个，所以剩下的苹果是 8 - 2 = 6个。
答案: 6个

示例2:
问题: 一辆车以60公里/小时的速度行驶了2小时，它行驶了多少公里？
思考过程: 距离等于速度乘以时间。速度是60公里/小时，时间是2小时。所以总距离是 60 * 2 = 120公里。
答案: 120公里""",
    "logical": """示例1:
问题: 前提A：所有的人都会死。前提B：苏格拉底是人。结论是什么？
思考过程: 这是一个三段论推理。大前提是“所有的人都会死”，小前提是“苏格拉底是人”。根据逻辑规则，可以得出结论“苏格拉底会死”。
答案: 苏格拉底会死。

示例2:
问题: 如果今天是星期三，那么后天是星期几？
思考过程: 今天是星期三。明天是星期四。后天就是星期五。
答案: 星期五"""
}


def get_prompt(strategy: str, question: str, task_type: str = "quantitative") -> str:
    """
    根据不同的策略生成相应的提示。
    """
    if strategy == "zero_shot":
        return f"请回答以下问题，只输出最终答案：\n问题: {question}"
    
    elif strategy == "few_shot":
        examples = FEW_SHOT_EXAMPLES.get(task_type, FEW_SHOT_EXAMPLES["quantitative"])
        return f"{examples}\n\n请回答:\n问题: {question}\n答案:"

    elif strategy == "zero_shot_cot":
        return f"请回答以下问题，逐步思考，最后给出答案。\n问题: {question}"

    elif strategy == "few_shot_cot":
        examples = FEW_SHOT_COT_EXAMPLES.get(task_type, FEW_SHOT_COT_EXAMPLES["quantitative"])
        return f"{examples}\n\n请回答:\n问题: {question}\n思考过程:"
    
    else:
        raise ValueError(f"未知的策略: {strategy}")