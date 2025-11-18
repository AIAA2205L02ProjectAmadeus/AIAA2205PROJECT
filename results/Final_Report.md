# 结构化评测报告（基于当前统计）

日期：2025-11-16

本文基于 `results/structured_results.jsonl` 的汇总（经去重后写入 `results/structured_summary.csv`）和分析脚本输出的统计文件，侧重量化指标、主要发现与可执行建议。目标读者为数据工程/模型评测平台维护者与研究人员。

## 一、执行摘要（要点）

- 样本规模：去重后共有 2680 条记录（模型/语言/策略/样本组合）。
- 总体表现（以 `is_correct` 为准）：
  - 英文（en）样本：1340 条，准确率 ~51.3%。
  - 中文（zh）样本：1340 条，准确率 ~73.9%。
- 自评/一致性（来自分析文件）：英文自评一致率约 55.1%，中文自评一致率约 76.3%（分析表 `analysis_overall_by_model_lang.csv`）。
- 解析失败（parse_error）：共 33 条（约 1.23%）；英文 parse_error 率略高（约 1.94% vs 中文 0.52%）。
- 模型未输出选择（predicted_choice 为空）：161 条（约 6.0%）。
- 原因长度（reason_length）：总体均值约 43.9 字，英文均值约 48.4，中文均值约 39.4。

结论要点：模型在中文语境下表现明显优于英文；知识类/常识类（C）题的准确率普遍高于计量/推理题（Q）；CoT（chain-of-thought）提示显著增加 `reason_length`，但对准确率的提升并非始终稳定，且在英文样本上更容易引入解析错误或空选项。

## 二、关键定量指标（摘选）

（来源：`results/analysis_overall_by_model_lang.csv` 与 `results/analysis_summary_by_group.csv`，以及对 `results/structured_summary.csv` 的补充统计）

- 按语言总体：
  - en: samples=1340, accuracy=0.513, self_judgment_agreement≈0.551, parse_err≈1.94%，empty_choice≈6.42%，avg_reason_len≈48.4
  - zh: samples=1340, accuracy=0.739, self_judgment_agreement≈0.763, parse_err≈0.52%，empty_choice≈5.60%，avg_reason_len≈39.4

- 按策略/类别（选取若干代表性行，自 `analysis_summary_by_group.csv`）：
  - 对于类别 C（知识/事实类，zh）: zero_shot accuracy≈0.798, few_shot_cot≈0.789，均接近 79%–80%。
  - 对于类别 Q（定量/计算类，en）: 所有策略普遍较低，典型 accuracy 在 0.34–0.40 区间。
  - few_shot 与 zero_shot 在不同类别表现并无绝对优劣，CoT（*_cot）显著拉长 reason_length（例如 zero_shot_cot/en avg_reason_length≈52.7），但对准确率的提升有条件（在某些 zh/Q 组合可见提升，在 en/Q 中反而无益）。

## 三、细节洞察与可疑模式

1. 语言依赖性强
   - 模型在中文数据上表现显著好于英文（约 +22.6 百分点）。原因可能包括：训练与指令理解对中文更友好、few-shot 示例/提示主要为中文或中英翻译质量影响、或模型本身在中文指令下更稳定。

2. 类别差异明显
   - 知识类（C）平均准确率最高，说明模型在事实回忆/词汇知识上较为可靠。
   - 逻辑/推理（L）中等；定量题（Q）最脆弱，尤其在英文下准确率很低，且产生 parse_error 与空选项的概率更高（暗示模型在数值/符号细节和格式约束时容易失败）。

3. CoT（chain-of-thought）带来的权衡
   - CoT 策略显著拉长输出的 reason（平均增长 10–30 字），并在某些情形下提高准确率与自评一致性（尤其是 zh 的 L/Q 组合）。
   - 但在英文数据上，CoT 常带来更多解析失败或未规范输出（导致空选或 parse_error），这可能是因为 JSON 强制约束下模型在给出长推理时更容易脱离格式。

4. JSON 结构与解析失败
   - parse_error 总数虽低（1.23%），但当发生时会导致该条无法自动计分（需要人工或基于启发式的后处理）。解析失败常见原因：
     - 模型输出多余文本或尾随注释
     - 引号或转义问题（例如在理由文本中出现未转义的引号）
     - 返回非 JSON 或包含注释的 'JSON+' 格式
   - 建议：在模型 prompt 中加入更强的“仅输出 JSON”的约束，并在客户端增加更鲁棒的后处理（针对常见非标准输出做清洗与提取 letter 的启发式规则）。

5. 空选（empty choice）现象
   - ~6% 的记录没有返回 A/B/C/D，该类样本的 is_correct 显然为 False（或需人工判断）。它们主要集中在：
     - 问题表述不充分或需要额外背景（模型自评 often = "incorrect"）
     - 数学/符号题（Q）——模型给出解释但不做明确选择
   - 建议：对空选项单独分类并采样复查，考虑二次询问（follow-up prompt）或在 prompt 中强制“如果无法判断请选择一个最可能的字母”。

6. 中英文翻译质量可能影响
   - 你曾使用百度翻译生成英文副本；翻译过程中术语或数量表达的偏差会影响模型判断，特别是 Q 类问题（参数/符号敏感）。建议在关键定量题上优先使用原文（中文）或人工校对的翻译。

## 四、代表性失败案例（示例抽样、供人工审查）

- parse_error 示例（摘自日志）: 含有未转义的反斜杠或 LaTeX 片段导致 JSON 解析失败（见 structured_summary.csv 中 `parse_error_msg` 字段）。
- 空选示例: 在多项选择的定量题中模型输出了完整推理但没有提供最终 letter（需要策略调整）。
- 错选但理由合理：模型有时能给出正确的理由却选择错误字母，这说明评分应结合理由做弱监督（例如 judge LLM），而非只看 predicted_choice。

（注：如需，我可以从 `results/structured_results.jsonl` 中抽取 10 个典型失败样本并保存为 `results/failure_samples.jsonl` 以便人工复查。）

## 五、可执行建议（优先级排序）

1. 提升解析健壮性（优先级：高）
   - 在客户端增加更强的后处理：对常见非标准 JSON 输出用正则清洗（先找第一个 "{" 到最后一个 "}"），然后尝试 json.loads；若仍失败，使用启发式提取 A/B/C/D。
   - 增加二次尝试策略：当 parse_error 或 empty_choice 时，自动给模型发一条简短的“请仅返回 A/B/C/D”（或给出最可能选项）作为补救（最多一次）。

2. 针对定量题（Q）设计专门提示（优先级：高）
   - 对需要计算/符号敏感的问题，使用不强制输出长 CoT 的简短计算路径或要求“最后一行只输出 A/B/C/D”。
   - 或者先请求简短答案（choice），再单独请求理由作为可选步骤。

3. 语言与翻译策略（优先级：中）
   - 对关键定量题优先使用中文原题；若必须使用英文，先人工或半自动校验翻译是否保留数值/单位/符号。
   - 在提示中明确声明“选项文字已包含在下方，务必只从 A/B/C/D 中选一个”。

4. 策略选择与成本权衡（优先级：中）
   - CoT 可用于需要推理的复杂 L/Q 问题，但在英文样本上需谨慎使用（会增加 parse 风险与 token 费用）。建议采用按需 CoT：仅对被分类为 L/Q 的样本打开 CoT 模式。

5. 进一步实验建议（优先级：中）
   - 运行小规模的 A/B 实验：对照（1）强 JSON 约束 + 精简 CoT，（2）宽松 CoT + 后处理，比较解析失败率、准确率与自评一致性。
   - 考虑使用专门的 judge LLM 对模型理由与选择做二次判定，以减少单纯字母匹配带来的误判。

6. 日志与监控（优先级：低）
   - 在长期运行中记录 parse_error 的示例片段与原始模型输出，按错误类型做统计，逐步减少常见失败模式。

## 六、可选下一步（我可以代为执行）

- 重新运行分析脚本 `scripts/analyze_results.py`（基于现有去重后的数据）并将图表更新到 `results/plots/`，同时把关键信息自动写入 `results/Final_Report.md`（我可以把本报告进一步丰富为带图版）。
- 从当前结果中抽取并保存 10–30 个代表性失败样本（parse_error、empty_choice、reason/correct 冲突）以便人工审查。
- 按建议在 `scripts/run_evaluation_structured.py` 中加入：
  - parse 强化后处理示例代码（先取最内层 JSON，再 fallback 正则提取），
  - 对 parse_error/empty_choice 的自动二次询问逻辑（限制重试次数）。

---

报告已保存为 `results/Final_Report.md`（同时在此会话中展示）。如需我现在：

- A：重新运行图表生成并把带图的报告写入（需要 matplotlib/seaborn，已经在仓库中）。
- B：抽取失败样本到 `results/failure_samples.jsonl` 并把前 10 条粘贴到聊天中供快速审阅。
- C：直接在 `scripts/run_evaluation_structured.py` 中实现更鲁棒的 JSON 后处理与自动补救逻辑并做小规模 smoke-test（--samples 5）。

请选择一项或告诉我你希望先推进哪个动作。