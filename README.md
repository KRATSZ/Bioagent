# 一、BioAgent - 快速入门
## 1. 克隆仓库
```
git clone https://github.com/JiangtaoXu-AI/BioAgent.git
cd BioAgent
```

## 2. 创建虚拟环境
```
conda create -n bioagent3.10 python=3.10 -y
conda activate bioagent3.10
pip install -r requirements.txt
```

## 3. 配置 API 密钥
```python
os.environ["OPENAI_API_KEY"] = "你的API密钥"
os.environ["OPENAI_API_BASE"] = "https://api.deepseek.com/v1"
model = "deepseek-chat"
```
## 4. 运行
```
python main.py
```

### 可选：新增能力依赖（质谱/实验设计/HTTP）
- CFM-ID 质谱预测：`pip install cfm-id`
- DoE 优化（可选）：`pip install pyDOE2`
- mzML 解析：`pip install pymzml pyteomics`
- HTTP 调用（requests 已内置于 requirements）
# 二、工具添加
## 第一步：工具实现

- 工具的实现应放在 `bioagent/tools` 文件夹下。
- 每一类工具可以单独创建一个 `.py` 文件，例如 `my_tool.py`。
- 模仿别的工具格式，在该文件内编写工具的核心逻辑。

## 第二步：工具导入

在 `bioagent/agents/tools.py` 文件中，将工具导入并注册到工具集合中。
```python
all_tools += [
    KnowledgeGraphSearch(llm=llm),
    SMILESToBiosyntheticPathway(),
    AddReactantsToBionavi(memory),
    SMILESToPredictedSynthesisInfo(llm=llm,memory=memory),
    GenomeCollectorTool(),
    GenomeQueryTool()
]
```
# 三、工具测试

## 方法一：在实现文件内测试

- 可以直接在实现文件中添加 `__main__` 代码块进行简单测试。
- 适合本地调试和单元测试使用。
```python
if __name__ == "__main__":
    result = example_tool("apple")
    print(result)  # 输出：Processed apple
```
## 方法二：在 Agent 系统中测试
- 启动 agent对话框（参考1快速开始python main.py）
- 在对话框输入触发工具的用户需求
- 测试结果







## 四、项目结构（最新文件树）

```text
BioAgent/
├─ app.py                     # Gradio 前端（本地聊天界面）
├─ main.py                    # 命令行入口（快速验证）
├─ mcp_config.yaml            # MCP 服务器配置
├─ requirements.txt
├─ README.md
├─ results/
│  ├─ genome_classification.txt
│  ├─ GGGPS_query_ID.txt
│  └─ Plsc_genome_ID.txt
├─ Docs&test/
│  ├─ Docs/
│  │  ├─ PROGRESS.txt
│  │  ├─ background.txt
│  │  ├─ BioAgent_测试报告.md
│  │  └─ ChemMCP配置指南.md
│  └─ Test/
│     ├─ test_backend.py
│     ├─ test_chemmcp.py
│     └─ test_report_*.json
└─ bioagent/
   ├─ __init__.py
   ├─ utils.py
   ├─ version.py
   ├─ agents/
   │  ├─ bioagent.py          # 构建 LLM Agent（记忆、工具、执行器）
   │  ├─ mcp_tools.py         # 发现/封装 MCP 工具（STDIO）
   │  ├─ tools.py             # 汇总并注册所有工具（本地 + MCP + Biomni）
   │  └─ prompts.py
   ├─ tools/
   │  ├─ biomni_wrappers.py   # 动态封装 Biomni 函数为 LangChain 工具
   │  ├─ Genome.py            # 基因组采集/查询工具
   │  ├─ PathPrediction.py    # 逆合成/路径预测工具（BioNavi-NP 相关）
   │  ├─ search.py            # 知识图谱/检索相关
   │  ├─ analysis_tools.py    # LCMSParser/MzMLParser/CFMIDPredictor/HypothesisVerifier
   │  ├─ doe_planner.py       # DoE 实验设计（全因子/简化LHS）
   │  ├─ literature_processor.py # Biomni biorxiv 抽取封装
   │  ├─ kg_write.py          # Neo4j 写入（add_node/add_edge）
   │  ├─ sop_generator.py     # 本地 Otcoder 协议生成链封装
   │  ├─ otcoder_http.py      # Otcoder FastAPI 的 HTTP 调用工具
   │  ├─ human_tool.py        # 人在回路（HITL）占位工具
   │  └─ prompts.py
   ├─ Biomni/                 # 外部“生物领域工具集”源码（已内嵌）
   │  └─ biomni/tool/...      # database、literature、biochemistry、genetics 等
   └─ ChemMCP/                # 外部“化学 MCP 服务器”源码（独立运行）
      └─ src/chemmcp/...      # tools、tool_utils、utils
```

## 五、模块简介

- **总体定位**: 这是一个“生物逆合成 + 知识图谱 + 工具增强”的智能体（Agent）项目，支持本地工具与 MCP 远程工具协同工作。

- **前端与入口**
  - `app.py`: 使用 Gradio 提供网页聊天界面，便于交互式测试。
  - `main.py`: 命令行方式快速跑通核心 Agent。

- **Agent 核心（bioagent/agents）**
  - `bioagent.py`: 构建对话式智能体。基于 LangChain 的 ChatZeroShotAgent + Retry 执行器，加入对话记忆，支持多轮对话与工具调用。
  - `tools.py`: 注册并汇总所有可用工具，包含本地工具、MCP 工具、以及 Biomni 封装的工具。
    - 本地核心工具包括：`KnowledgeGraphSearch`、`SMILESToBiosyntheticPathway`、`AddReactantsToBionavi`、`SMILESToPredictedSynthesisInfo`、`GenomeCollectorTool`、`GenomeQueryTool`。
  - `mcp_tools.py`: 读取 `mcp_config.yaml`，通过 STDIO 启动 MCP 服务器（如 BioMCP、ChemMCP），自动发现其提供的工具并封装为 LangChain Tool（Windows 友好）。

- **本地工具（bioagent/tools）**
  - `biomni_wrappers.py`: 动态扫描并封装 `Biomni` 模块中的函数为可调用工具（按白名单模块过滤）。
  - `Genome.py`: 基因组采集与数据库查询相关能力。
  - `PathPrediction.py`: 生物逆合成路径预测相关（与 BioNavi-NP 链路打通）。
  - `search.py` 与 `prompts.py`: 检索与提示模板辅助。

- **外部能力（已集成源码）**
  - `bioagent/Biomni/`: 面向生物医学各子领域的大量工具集合（database、literature、biochemistry、genetics 等）。
  - `bioagent/ChemMCP/`: 化学工具的 MCP 服务器实现，通常以 `uv` 独立环境启动后由 MCP 客户端调用。

- **文档与测试（Docs&test）**
  - `Docs/PROGRESS.txt`: 项目进度与交接要点。
  - `Docs/background.txt`: 研究背景草稿与方法说明。
  - `Test/test_backend.py`、`Test/test_chemmcp.py`: 回归测试与工具连通性测试。

## 六、如何运行（Windows PowerShell）

```powershell
# 1) 可选：在当前会话设置环境变量
$env:OPENAI_API_BASE = "XXX"
$env:OPENAI_API_KEY  = "<你的key>"
$env:MCP_CONFIG      = ".\mcp_config.yaml"

# 2) 命令行快速验证
python .\main.py

# 3) 启动 Gradio 前端（默认 7860 端口）
python .\app.py
# 或使用虚拟环境 Python：
.\.venv\Scripts\python.exe .\app.py

# 4) 运行后端测试
.\.venv\Scripts\python.exe .\Docs&test\Test\test_backend.py

# 5) 新增工具冒烟测试
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python .\Docsandtest\Test\test_smoke_new_tools.py
```

### 新增工具快速试用（对话输入示例）
- DoE 设计: 调用 `DoEPlanner`，输入 `{ "factors": {"temp":[20,30], "pH":[6,7,8]}, "mode": "full" }`
- SOP/代码生成: 调用 `SOPGenerator`，输入 `{ "hardware_config": "Robot Model: OT-2\nAPI Version: 2.19", "user_goal": "96孔板移液稀释", "action": "code" }`
- LC-MS 解析: 调用 `LCMSParser`，输入 `{ "csv_path":"path/to/mrm.csv", "transitions":[{"precursor_mz":707,"product_mz":425,"ppm":10}] }`
- CFM-ID 预测: 调用 `CFMIDPredictor`，输入 `{ "smiles": "C[C@H](O)C(=O)O" }`
- 假设验证: 调用 `HypothesisVerifier`，输入 `{ "hypothesis":"...", "observations":{...}}`
- 文献处理: 调用 `LiteratureProcessor`，输入 `{ "subject":"bioinformatics", "limit":10 }`
- 图谱写入: 调用 `KGWrite`，输入 `{ "op":"add_edge", "data": {"head":"A","tail":"B","type":"REL","props":{"source":"exp"}} }`
- HITL：调用 `HumanInTheLoop`，输入 `{ "title":"本体确认", "payload":{...} }`（工具会返回带 `HITL_REQUEST` 的结构化提示，直接在聊天中粘贴确认后的 JSON 即可继续）

### Otcoder FastAPI（可选，HTTP 正向验证）
```powershell
# 启动 Otcoder FastAPI（默认 127.0.0.1:8000）
.\.venv\Scripts\python -m uvicorn bioagent.OTcoder.api_server:app --host 127.0.0.1 --port 8000

# 在另一窗口运行冒烟脚本或在 Agent 中调用 `OtcoderHTTP` 进行 generate_sop/generate_code/simulate
```

## 七、更多文档

- 项目进度与交接说明：`Docs&test/Docs/PROGRESS.txt`
- 研究背景草稿：`Docs&test/Docs/background.txt`

