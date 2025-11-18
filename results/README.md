# results/ 说明

此目录包含评测输出与自动生成的分析产物。

重要文件：
- `structured_results.jsonl`：主结果（append-only），用于断点重跑/恢复。
- `structured_results.dedup.jsonl`：去重后结果（由 `scripts/summarize_results.py` 生成）。
- `structured_summary.auto.csv` / `.xlsx`：脚本生成的摘要表格。
- `plots/`：脚本生成的图像（choices 分布、错误占比等）。
- `evaluation.log.recovered`：若误删原 `evaluation.log`，本文件为最近一次通过 /proc/<pid>/fd 恢复的快照（如果存在）。

如何把正在运行进程的 stdout/stderr 安全追加到持久日志（不停止进程）：

1. 找到 PID（假设 PID 为 3946408）：
```
tail -f /proc/3946408/fd/1 >> evaluation.log &
tail -f /proc/3946408/fd/2 >> evaluation.log 2>&1 &
```
注意：如果进程随后重定向了 stdout/stderr 到新的文件，这个 tail 需要重新建立。

2. 另一种更保险的策略是在启动评测时就使用 `nohup` 或 `tee` 将输出写到持久文件：
```
nohup python3 scripts/run_evaluation_structured.py --resume --models ... > evaluation.log 2>&1 &
```

运行汇总脚本：
```
pip install pandas matplotlib openpyxl
python3 scripts/summarize_results.py
```

如果需要，我可以：
- 现在运行 `scripts/summarize_results.py` 并把生成的 CSV/图像上传到 `results/`（注意：会使用当前工作区的 Python 环境），或
- 修改 `siliconflow_client.py` 增加 per-request 审计日志并提交补丁（需重启评测以生效）。
