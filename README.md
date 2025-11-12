# LLM 思维链 (CoT) 中文推理分析项目

## 项目背景
本项目旨在利用 Siliconflow API 实现 LLM 思维链 (CoT) 的中文推理分析。通过构建不同的提示策略，我们希望能够探索和比较模型在处理多样化问题时的表现。

## 项目结构
```
llm-cot-siliconflow-py
├── src
│   ├── main.py                # 项目的主入口
│   ├── siliconflow_client.py   # 封装与 Siliconflow API 的交互
│   └── prompts.py             # 定义提示策略函数
├── data
│   └── sample_questions.json   # 示例问题数据集
├── notebooks
│   └── exploratory_analysis.ipynb # 数据探索和可视化分析
├── .env                        # 存储环境变量
├── requirements.txt            # 项目所需的 Python 库
└── README.md                   # 项目文档
```

## 使用方法
1. **环境配置**  
   在项目根目录下创建一个 `.env` 文件，并添加您的 Siliconflow API 密钥：
   ```
   SILICONFLOW_API_KEY=your_api_key_here
   ```

2. **安装依赖**  
   使用以下命令安装项目所需的依赖：
   ```
   pip install -r requirements.txt
   ```

3. **运行项目**  
   使用以下命令启动项目：
   ```
   python src/main.py
   ```

## 数据集说明
`data/sample_questions.json` 文件包含了多样化的示例问题，按照任务类型和难度等级组织，旨在为模型提供丰富的推理场景。

## 可视化结果
在 `notebooks/exploratory_analysis.ipynb` 中，您可以找到数据探索和可视化分析的结果，展示不同提示策略和模型性能的比较。

## 贡献
欢迎任何形式的贡献！请提交问题或拉取请求以帮助改进本项目。

## 许可证
本项目遵循 MIT 许可证。