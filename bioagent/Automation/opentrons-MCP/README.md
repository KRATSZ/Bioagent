# Opentrons MCP Server

一个为 Opentrons 机器人自动化和 API 文档设计的模型上下文协议 (MCP) 服务器。此工具为 Opentrons Flex 和 OT-2 机器人提供全面的 API 文档查询和直接的机器人控制能力。

## ✨ 项目重构总结

此项目经历了一次彻底的重构，从一个包含近 2000 行代码的单体 `index.js` 文件，演变成一个高度模块化、可配置、易于维护的现代化架构。

**关键改进：**
-   **代码行数减少 96%**: 主文件 `index.js` 从 1882 行减少到 66 行。
-   **模块化**: 所有核心功能被拆分到独立的、单一职责的模块中。
-   **移除外部依赖**: 完全用纯 Node.js (Axios, form-data) 替代了 `curl` 调用。
-   **集中化配置**: 所有硬编码值被提取到 `config/index.js` 中，可通过环境变量进行配置。
-   **可扩展的工具分发器**: 使用映射表替换了庞大的 `switch` 语句，使添加新工具变得简单。

## 🏛️ 项目架构


```
opentrons-MCP/
├── config/index.js          # 集中化配置管理
├── src/
│   ├── modules/             # 核心功能模块
│   │   ├── apiExplorer.js     # API 探索
│   │   ├── robotController.js # 机器人硬件控制
│   │   ├── protocolManager.js # 协议上传与模拟
│   │   └── errorFixer.js      # AI 错误修复
│   └── toolDispatcher.js    # 工具调用分发器
├── apiEndpoints.js          # (数据) 所有 API 端点定义
├── toolSchemas.js           # (数据) 所有工具的 MCP 模式定义
├── package.json
└── index.js                 # (主文件) 服务器入口，仅 66 行
```

**优势**:
-   **高可维护性**: 修改或修复功能时，只需关注特定模块。
-   **易于扩展**: 添加新功能有清晰的模式可循。
-   **关注点分离**: 业务逻辑、数据和配置完全解耦。
-   **灵活性**: 可通过环境变量轻松调整应用行为，无需修改代码。


## ⚙️ 配置

### 服务器端 (环境变量)

应用的行为可以通过环境变量进行配置。您可以在启动服务器前设置它们，或者将它们写入一个 `.env` 文件 (需要 `dotenv` 包支持)。

**常用配置项:**
-   `OPENTRONS_DEFAULT_ROBOT_IP`: 设置默认的机器人 IP 地址。
-   `ANTHROPIC_API_KEY`: 使用 AI 错误修复功能所需的 Anthropic API 密钥。
-   `HTTP_REQUEST_TIMEOUT`: 全局 HTTP 请求超时时间 (毫秒)。
-   `DEBUG_SHOW_COMMANDS=true`: 在控制台打印执行的外部命令 (如协议模拟)。

所有可配置项及其默认值都在 `config/index.js` 中定义。

### 客户端 (MCP JSON)

要让您的 MCP 客户端 (如 Cursor) 连接到此服务器，请更新您的 MCP JSON 配置文件。

## 🚀 安装

### From npm (推荐)
```bash
npm install -g opentrons-mcp
```

### From source
```bash
git clone https://github.com/yerbymatey/opentrons-mcp.git
cd opentrons-mcp
npm install
```
**全局安装:**
```json
{
  "mcpServers": {
    "opentrons": {
      "command": "opentrons-mcp",
      "args": []
    }
  }
}
```

**本地开发 (从源码运行,当前的版本):**
```json
{
  "mcpServers": {
    "opentrons-local": {
      "command": "node",
      "args": [
        "D:/path/to/opentrons-MCP/index.js" 
      ]
    }
  }
}
```
*请务必将路径替换为您机器上 `index.js` 的 **绝对路径**。*

## 🛠️ 使用与开发

1.  **启动本地服务器**:
    在项目根目录运行 `npm start`。这将直接使用 `node` 运行您本地的 `index.js`，确保所有代码更改生效。

2.  **重启与刷新**:
    -   **修改代码后**: 使用 `Ctrl+C` 停止并重新运行 `npm start`。
    -   **客户端**: 完全重启您的 MCP 客户端是确保它重新连接并获取最新工具列表的最可靠方法。

## 🧰 可用工具

### 文档工具

#### search_endpoints
按功能、方法、路径或关键字搜索 Opentrons HTTP API 端点。

#### get_endpoint_details
获取特定 API 端点的详细信息。

#### list_by_category
列出特定功能类别中的所有端点。

#### get_api_overview
获取 Opentrons HTTP API 结构和功能的高级概述。

### 自动化工具

#### upload_protocol
上传协议文件到 Opentrons 机器人。
-   `robot_ip` (required)
-   `file_path` (required)
-   `support_files` (optional): 支持文件路径数组。
-   `protocol_kind` (optional): "standard" 或 "quick-transfer"。
-   `run_time_parameters` (optional): 运行时参数值。

#### get_protocols
列出机器人上存储的所有协议。

#### create_run
创建一个新的协议运行。

#### control_run
控制运行执行 (play, pause, stop, resume)。

#### get_runs
列出机器人上的所有运行。

#### get_run_status
获取特定运行的详细状态。

#### robot_health
检查机器人的健康状况和连接性。

#### control_lights
打开或关闭机器人灯光。

#### home_robot
归位机器人轴或特定移液器。

#### simulate_protocol
使用 `opentrons.simulate` 模块模拟 Opentrons 协议，无需物理机器人。
-   `protocol_path` 或 `protocol_code` (required)
-   `output_format` (optional): "summary", "detailed", 或 "json"。

### AI 工具

#### poll_error_endpoint_and_fix
获取错误报告并使用 AI 生成修复后的协议。
-   `json_filename` (optional): 错误报告的 JSON 文件名 (从配置中获取默认值)。
-   `original_protocol_path` (optional): 原始协议文件的路径 (从配置中获取默认值)。


## 🤝 如何贡献 (添加新工具)

得益于模块化架构，添加新工具非常简单：

1.  **添加核心逻辑**:
    -   在 `src/modules/` 中选择一个合适的模块 (如 `robotController.js`) 并添加您的新方法。
    -   如果功能完全独立，可以创建一个新的模块文件。

2.  **定义工具模式**:
    -   在 `toolSchemas.js` 文件中，为您的新工具添加一个 MCP 模式定义，描述其名称、用途和参数。

3.  **注册工具**:
    -   在 `src/toolDispatcher.js` 的 `createToolDispatcher` 函数中，将新工具的名称和处理函数添加到 `Map` 中。

4.  **(可选) 添加配置**:
    -   如果您的工具需要配置项 (如 API 密钥、默认值)，请将它们添加到 `config/index.js` 中，并确保可以从环境变量加载。

5.  **更新文档**:
    -   最后，将您的新工具添加到本 `README.md` 文件的 "可用工具" 部分。

##  troubleshooting

### 无法连接到机器人
-   确认机器人 IP 地址正确。
-   确保机器人已开机并连接到网络。
-   检查端口 31950 是否可访问。

### 协议上传失败
-   确认文件路径存在且可读。
-   确保协议文件是有效的 Python (.py) 或 JSON 格式。
-   检查机器人上的可用磁盘空间。

有问题请联系gaoyuanbio@qq.com
## 📄 License

This project is licensed under the **MIT License**.

