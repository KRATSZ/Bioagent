Momentum LLM Control (LangGraph + MCP + MomentumPyClient)

快速开始（Windows PowerShell）：

1) 创建虚拟环境并安装依赖

```powershell
cd D:\LLM\LLMpyMomentum
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e MomentumPyClient
python -m pip install -r requirements.txt
```

### 项目结构

```
LLMpyMomentum/
├─ app/
│  ├─ http_api.py              # FastAPI 入口，暴露 /health、/chat 等
│  ├─ graph.py                 # LangGraph 状态图（GraphState、agent 节点）
│  ├─ intent.py                # 意图解析（LLM + 规则），run_process 参数抽取增强
│  ├─ momentum_client.py       # Momentum 客户端工厂与 MockMomentum（无设备可用）
│  ├─ config.py                # 配置加载（.env），含 LLM 与 Momentum 连接参数
│  ├─ llm.py                   # OpenAI 兼容接口封装
│  ├─ mcp_server.py            # MCP 工具服务（可选）
│  ├─ analyze_data_strategies.py / adjust_fluorescence_data.py  # 数据分析示例脚本
│  └─ cli.py                   # 预留 CLI
│
├─ MomentumPyClient/          # 可编辑安装的子包（封装 Momentum Web Services）
│  └─ src/MomentumPyClient/{ws.py, ui.py, __init__.py}
│
├─ tests/                     # 测试用例
│  ├─ conftest.py             # 测试环境准备（加载 .env 等）
│  ├─ test_intent.py          # 意图解析用例（覆盖 run_process 参数抽取）
│  └─ test_llm.py             # 实时 LLM 测试（可跳过）
│
├─ requirements.txt           # 运行与测试依赖
├─ README.md                  # 使用说明（本文件）
├─ pytest.ini                 # pytest 配置
└─ .venv/                     # 虚拟环境（本地）
```

关键点：
- `app/intent.py` 支持在无 LLM 时通过规则解析提取 `run_process` 的参数（中英双语），字段包括：`process_name`、`variables`、`iterations`、`append`、`minimum_delay`、`workunit_name`、`dry_run`。
- `app/momentum_client.py` 会根据 `.env` 中 `MOMENTUM_MOCK` 自动选择 Mock 或真实客户端。
- 通过 `uvicorn app.http_api:app --reload` 启动本地服务后，可访问 `http://127.0.0.1:8000/docs` 查看交互式 API 文档。

**Linux/macOS 快速开始（bash）：**

```bash
cd /path/to/LLMpyMomentum
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e MomentumPyClient
python -m pip install -r requirements.txt
```

2) 配置 .env（无设备可用 mock）

在项目根目录创建 `.env` 并填入：

```
MOMENTUM_URL="https://localhost/api/"
MOMENTUM_USER="webuser1"
MOMENTUM_PASSWD="password"
MOMENTUM_VERIFY=false
MOMENTUM_TIMEOUT=5
MOMENTUM_MOCK=1

AI190_API_KEY="sk-Fbf6T3Gd8o3srcifmRyfUa3PfKmtbNuYgNzind0j92h2sV3n"
AI190_BASE_URL="https://api.ai190.com/v1"
AI190_MODEL="gemini-2.5-pro"
```

3) 运行 HTTP API（本地）

```powershell
uvicorn app.http_api:app --host 127.0.0.1 --port 8000 --reload
```

健康检查：`GET http://127.0.0.1:8000/health`

**API 文档（Swagger/OpenAPI）：**
运行后访问 `http://127.0.0.1:8000/docs`

**对话接口：**

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -Body (@{text='start system'} | ConvertTo-Json) -ContentType 'application/json'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -Body (@{text='status'} | ConvertTo-Json) -ContentType 'application/json'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -Body (@{text='仿真启动'} | ConvertTo-Json) -ContentType 'application/json'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -Body (@{text='show devices'} | ConvertTo-Json) -ContentType 'application/json'
```

**dry-run 模式（只计划不执行）：**

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -Body (@{text='run process X'; dry_run=$true} | ConvertTo-Json) -ContentType 'application/json'
```

**意图解析端点：**

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/intent -Body (@{text='运行进程 Alpha variables: a=1;b=2'} | ConvertTo-Json) -ContentType 'application/json'
```

4) 运行 MCP 服务器（可选）

```powershell
python -m app.mcp_server
```

架构说明

- LangGraph：轻量对话工作流（节点 `agent`），根据自然语言触发 Momentum 控制（start/simulate/stop/status 等）。
- MomentumPyClient：封装对 Momentum Web Services 的访问。无设备时启用 `MockMomentum`。
- MCP：导出工具（status/start/simulate/stop/devices），供支持 MCP 的客户端调用。
- FastAPI：对外暴露 `/chat` 接口，便于从任意语言/环境调用。

5) 运行测试（可选）

```powershell
python -m pytest tests/ -v
```

**后续可扩展**

- 基于 LLM 准确意图解析与参数抽取（LangGraph 工具调用/提示工程）。
- Worklist/Process 参数收集表单与执行回传。
- 安全控制、审计日志、多租户。
- 数据分析工具集成（如 `app/adjust_fluorescence_data.py`）。

