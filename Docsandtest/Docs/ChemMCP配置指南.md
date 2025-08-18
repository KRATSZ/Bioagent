# ChemMCP 配置与安装指南

## 🎯 配置建议

基于测试结果，我们提供三种ChemMCP集成方案，**推荐方案2**用于生产环境。

---

## 方案1：直接安装 ChemMCP 模块 

### 适用场景
- 快速集成
- 简单部署
- 不需要定制化

### 安装步骤
```bash
# 激活虚拟环境
& .\.venv\Scripts\Activate.ps1

# 安装ChemMCP
pip install git+https://github.com/OSU-NLP-Group/ChemMCP.git

# 测试安装
python -m chemmcp --help
```

### 配置文件
```yaml
# mcp_config.yaml
chemmcp:
  enabled: true
  command: ["python", "-m", "chemmcp"]
  env:
    CHEMSPACE_API_KEY: "${CHEMSPACE_API_KEY}"
    RXN4CHEM_API_KEY: "${RXN4CHEM_API_KEY}"
    TAVILY_API_KEY: "${TAVILY_API_KEY}"
    LLM_MODEL_NAME: "${LLM_MODEL_NAME}"
    OPENAI_API_KEY: "${OPENAI_API_KEY}"
```

### 优点
- ✅ 安装简单
- ✅ 配置简洁
- ✅ 自动依赖管理

### 缺点
- ❌ 可能与现有依赖冲突
- ❌ 更新困难
- ❌ 定制化有限

---

## 方案2：独立仓库 + uv 运行 (🏆 推荐)

### 适用场景
- 生产环境
- 需要定制化
- 要求隔离性
- 多项目复用

### 安装步骤
```bash
# 创建独立目录
cd D:\LLM\
git clone https://github.com/OSU-NLP-Group/ChemMCP.git
cd ChemMCP

# 使用uv设置环境
uv sync
uv pip install -e . --no-build-isolation

# 测试运行
uv run -m chemmcp --help
```

### 配置文件
```yaml
# mcp_config.yaml
chemmcp:
  enabled: true
  command: ["uv", "--directory", "D:\\LLM\\ChemMCP", "run", "-m", "chemmcp"]
  env:
    CHEMSPACE_API_KEY: "${CHEMSPACE_API_KEY}"
    RXN4CHEM_API_KEY: "${RXN4CHEM_API_KEY}"
    TAVILY_API_KEY: "${TAVILY_API_KEY}"
    LLM_MODEL_NAME: "${LLM_MODEL_NAME}"
    OPENAI_API_KEY: "${OPENAI_API_KEY}"
```

### 优点
- ✅ 环境完全隔离
- ✅ 易于更新和维护
- ✅ 支持定制化开发
- ✅ 多版本并存
- ✅ 生产环境稳定

### 缺点
- ❌ 需要额外的磁盘空间
- ❌ 配置稍复杂

---

## 方案3：暂时禁用（快速上线）

### 适用场景
- 快速演示
- 主要使用BioMCP
- 后续再集成ChemMCP

### 配置文件
```yaml
# mcp_config.yaml
chemmcp:
  enabled: false  # 禁用ChemMCP
```

### 优点
- ✅ 无需安装
- ✅ 系统立即可用
- ✅ 避免依赖问题

### 缺点
- ❌ 缺少化学工具支持
- ❌ 功能不完整

---

## 🔧 必需的API密钥

### ChemSpace API
```bash
# 获取地址: https://chem-space.com/
$env:CHEMSPACE_API_KEY = "your_chemspace_key"
```

### IBM RXN4Chem API  
```bash
# 获取地址: https://rxn.res.ibm.com/
$env:RXN4CHEM_API_KEY = "your_rxn4chem_key"
```

### Tavily API
```bash
# 获取地址: https://tavily.com/
$env:TAVILY_API_KEY = "your_tavily_key"
```

### LLM配置
```bash
$env:LLM_MODEL_NAME = "openai/gpt-4o"  # LiteLLM格式
$env:OPENAI_API_KEY = "your_openai_key"
```

---

## 🚀 快速启用 ChemMCP

如果您已准备好API密钥，推荐使用**方案2**：

```bash
# 1. 克隆ChemMCP
cd D:\LLM\
git clone https://github.com/OSU-NLP-Group/ChemMCP.git
cd ChemMCP
uv sync
uv pip install -e . --no-build-isolation

# 2. 修改BioAgent配置
cd D:\LLM\BioAgent

# 3. 编辑 mcp_config.yaml，启用ChemMCP:
# enabled: true
# command: ["uv", "--directory", "D:\\LLM\\ChemMCP", "run", "-m", "chemmcp"]

# 4. 设置环境变量
$env:CHEMSPACE_API_KEY = "your_key"
$env:RXN4CHEM_API_KEY = "your_key"  
$env:TAVILY_API_KEY = "your_key"
$env:LLM_MODEL_NAME = "openai/gpt-4o"

# 5. 测试运行
$env:VENV_PATH = (Resolve-Path .\.venv).Path
& "$env:VENV_PATH\Scripts\python.exe" test_backend.py
```

---

## 📋 验证清单

- [ ] ChemMCP源码已下载
- [ ] uv环境配置完成
- [ ] API密钥已配置
- [ ] mcp_config.yaml已更新
- [ ] 测试脚本运行成功
- [ ] ChemMCP工具已发现

---

## 🔍 故障排除

### 问题1: "No module named chemmcp"
**解决方案：** 确保按方案2安装，或使用方案3暂时禁用

### 问题2: uv命令未找到
**解决方案：** 
```bash
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 问题3: Docker相关错误
**解决方案：** 
- 安装Docker Desktop
- 或在ChemMCP配置中禁用PythonExecutor工具

### 问题4: API调用失败
**解决方案：** 
- 检查API密钥是否正确
- 确认网络连接
- 查看环境变量是否设置

---

🎉 **完成配置后，您将拥有一个集成了BioMCP + ChemMCP的强大生物化学助手！**

