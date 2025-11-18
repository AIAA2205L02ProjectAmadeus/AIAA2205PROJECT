# 评测整理与分析报告（自动草稿）

日期：2025-11-17

本文为对当前使用 `llm-cot-siliconflow-py` 项目生成的结构化评测结果的整理与初步分析报告。该仓库的评测结果存放在 `results/structured_results.jsonl`，本报告依赖该文件作为权威输入。

## 研究目标
- 使用统一 prompt 模板与严格 JSON 格式 ({choice, reason, self_judgment}) 对一组基线模型（如 Qwen2-7B、THUDM/GLM-4-9B-0414、deepseek-ai/DeepSeek-V2.5 等）进行横向比较。
- 评估模型在不同语言（zh/en）、不同策略（zero_shot, few_shot 等）下的表现并统计常见失败模式（parse_error / api_error / JSON 解析异常等）。

## 数据与方法
- 原始评测结果：`results/structured_results.jsonl`（追加写入，append-only）。
- 去重规则：基于 (sample_id 或 question hash, model, strategy, language) 的键去重（详见 `scripts/summarize_results.py`）。
- 输出：去重后的 `results/structured_results.dedup.jsonl`，自动摘要 `results/structured_summary.auto.csv`（兼有 `.xlsx` 详情），并生成简单图表 `results/plots`。

## 快速摘要（自动化脚本可刷新）
- 原始记录条数（样本）：请使用 `python3 scripts/summarize_results.py` 生成精确信息；脚本会打印读入条数与去重后条数。

## 主要发现（半自动化/草稿）
- 发现大量 parse_error：常见原因包括模型返回的 JSON 被代码块（```）包裹、或在文本中包含额外说明导致 JSON 无法直接解析。建议在 prompt 中明确要求“只返回纯 JSON 且不要带代码块或多余引导语”。
- 存在间歇性 API 错误（500/502/timeout），这些会在结果中以 `api_error` 或空输出体现，应增加重试与 request-id 追踪以便与提供方日志核对。
- 去重后统计可揭示：每个模型的样本覆盖、选项（choice）分布与错误占比（parse_vs_api_vs_ok）。

## 错误示例（从恢复日志与结果样本中抽取）
- parse_error 样例：模型输出像 "```json\n{\"choice\": \"A\", ... }\n```"，导致直接 JSON 解码失败。
- api_error 样例：返回以 "API_ERROR:" 开头或直接空响应。

## 建议（可立即执行）
1. 在 prompt 中再强调：“不要用代码块、不要带注释、纯 JSON 响应；字段必须存在：choice、reason、self_judgment”，并做一轮 small-batch 验证。
2. 将 siliconflow 客户端增加 per-request 审计日志：记录时间戳、请求 payload、provider 返回的 request-id 与响应头（便于与平台日志核对）。我可以准备该补丁并提交到 `llm-cot-siliconflow-py/src/siliconflow_client.py`（需要重启评测以生效）。
3. 持久化当前正在写入的日志（若你希望我现在操作，我可以把正在运行进程的 stdout/stderr 读出并追加到 `evaluation.log`）。

## 如何复现/生成最终报告
1. 安装依赖：
```
pip install pandas matplotlib openpyxl
```
2. 运行：
```
python3 scripts/summarize_results.py
```
3. 打开结果：
- `results/structured_results.dedup.jsonl`
- `results/structured_summary.auto.csv` 与 `results/structured_summary.auto.xlsx`
- `results/plots/choices_bar.png`, `results/plots/errors_pie.png`

## 后续工作（研究性建议）
- 用更多自动化的 prompt-robustness 检测（例如：检测返回中是否包含代码块、额外非 JSON 文本、或多余字段）。
- 将评测结果与 provider 的 request-id 对齐，以核实计费差异。建议一次性做单次带 trace_id 的请求进行对账。
- 撰写学术版报告（含表格与图），并把 `results/structured_summary.auto.xlsx` 中的数据整合为论文图表（需要你决定目标期刊/格式）。

---
（本文件为草稿，已生成脚本 `scripts/summarize_results.py` 可用于刷新数字与图表；需要我现在运行脚本并把图/CSV 写到 `results/` 吗？）
