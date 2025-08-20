/**
 * 集中化配置管理
 * 从环境变量读取配置，提供合理的默认值
 */

export const config = {
  // API 配置
  api: {
    // Opentrons 机器人默认端口
    robotPort: parseInt(process.env.OPENTRONS_ROBOT_PORT) || 31950,
    
    // 默认机器人 IP (如果环境变量中有设置)
    defaultRobotIP: process.env.OPENTRONS_DEFAULT_ROBOT_IP || null,
    
    // API 版本头
    opentronApiVersion: process.env.OPENTRONS_API_VERSION || '*',
    
    // HTTP 请求超时时间 (毫秒)
    requestTimeout: parseInt(process.env.HTTP_REQUEST_TIMEOUT) || 30000,
    
    // 短超时 (用于错误报告获取等)
    shortTimeout: parseInt(process.env.HTTP_SHORT_TIMEOUT) || 10000
  },

  // 错误修复配置
  errorFixer: {
    // 错误报告服务器
    errorReportServer: process.env.ERROR_REPORT_SERVER || 'http://192.168.0.145:8080',
    
    // 默认错误报告文件名
    defaultErrorReportFile: process.env.DEFAULT_ERROR_REPORT_FILE || 'error_report_20250622_124746.json',
    
    // 默认协议文件路径
    defaultProtocolPath: process.env.DEFAULT_PROTOCOL_PATH || '/Users/gene/Developer/failed-protocol-5.py',
    
    // Anthropic API 配置
    anthropicApiKey: process.env.ANTHROPIC_API_KEY,
    anthropicApiUrl: process.env.ANTHROPIC_API_URL || 'https://api.anthropic.com/v1/messages',
    anthropicModel: process.env.ANTHROPIC_MODEL || 'claude-3-5-sonnet-20240620',
    anthropicMaxTokens: parseInt(process.env.ANTHROPIC_MAX_TOKENS) || 4000,
    anthropicApiVersion: process.env.ANTHROPIC_API_VERSION || '2023-06-01'
  },

  // 协议模拟配置
  simulation: {
    // Python 脚本路径 (相对于项目根目录)
    simulationScriptPath: process.env.SIMULATION_SCRIPT_PATH || 'simulate_helper.py',
    
    // 默认输出格式
    defaultOutputFormat: process.env.SIMULATION_OUTPUT_FORMAT || 'summary',
    
    // 临时文件前缀
    tempFilePrefix: process.env.TEMP_FILE_PREFIX || 'temp_protocol_'
  },

  // 文件上传配置
  upload: {
    // 默认协议类型
    defaultProtocolKind: process.env.DEFAULT_PROTOCOL_KIND || 'standard',
    
    // 文件内容类型
    fileContentType: process.env.FILE_CONTENT_TYPE || 'application/octet-stream'
  },

  // 服务器配置
  server: {
    // MCP 服务器名称
    name: process.env.MCP_SERVER_NAME || 'opentrons-mcp',
    
    // 版本信息
    version: process.env.MCP_SERVER_VERSION || '1.0.23'
  },

  // 调试配置
  debug: {
    // 是否启用详细日志
    verbose: process.env.DEBUG_VERBOSE === 'true',
    
    // 是否显示执行的命令
    showCommands: process.env.DEBUG_SHOW_COMMANDS !== 'false'
  }
};

/**
 * 获取完整的 API URL
 * @param {string} robotIP - 机器人 IP 地址
 * @param {string} endpoint - API 端点路径
 * @returns {string} 完整的 URL
 */
export function getApiUrl(robotIP, endpoint = '') {
  const ip = robotIP || config.api.defaultRobotIP;
  if (!ip) {
    throw new Error('Robot IP address is required');
  }
  
  const baseUrl = `http://${ip}:${config.api.robotPort}`;
  return endpoint ? `${baseUrl}/${endpoint.replace(/^\//, '')}` : baseUrl;
}

/**
 * 获取默认的 HTTP 请求头
 * @param {Object} additionalHeaders - 额外的请求头
 * @returns {Object} 请求头对象
 */
export function getDefaultHeaders(additionalHeaders = {}) {
  return {
    'Opentrons-Version': config.api.opentronApiVersion,
    ...additionalHeaders
  };
}

/**
 * 验证必需的配置项
 * @throws {Error} 如果缺少必需的配置
 */
export function validateConfig() {
  const errors = [];
  
  // 检查 Anthropic API 密钥 (如果使用错误修复功能)
  if (!config.errorFixer.anthropicApiKey) {
    errors.push('ANTHROPIC_API_KEY environment variable is not set (required for error fixing)');
  }
  
  if (errors.length > 0) {
    console.warn('Configuration warnings:');
    errors.forEach(error => console.warn(`- ${error}`));
  }
}

// 在导入时进行配置验证
validateConfig(); 