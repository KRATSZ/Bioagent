/**
 * 工具调用分发器
 * 使用映射表管理工具名称到处理函数的关系
 */

/**
 * 创建工具分发器映射表
 * @param {Object} modules - 包含所有模块实例的对象
 * @returns {Map} 工具名称到处理函数的映射
 */
export function createToolDispatcher(modules) {
  const { apiExplorer, robotController, protocolManager, errorFixer } = modules;
  
  return new Map([
    // API 探索工具
    ['search_endpoints', apiExplorer.searchEndpoints.bind(apiExplorer)],
    ['get_endpoint_details', apiExplorer.getEndpointDetails.bind(apiExplorer)],
    ['list_by_category', apiExplorer.listByCategory.bind(apiExplorer)],
    ['get_api_overview', apiExplorer.getApiOverview.bind(apiExplorer)],
    
    // 协议管理工具
    ['upload_protocol', protocolManager.uploadProtocol.bind(protocolManager)],
    ['get_protocols', protocolManager.getProtocols.bind(protocolManager)],
    ['simulate_protocol', protocolManager.simulateProtocol.bind(protocolManager)],
    
    // 机器人控制工具
    ['create_run', robotController.createRun.bind(robotController)],
    ['control_run', robotController.controlRun.bind(robotController)],
    ['get_runs', robotController.getRuns.bind(robotController)],
    ['get_run_status', robotController.getRunStatus.bind(robotController)],
    ['robot_health', robotController.robotHealth.bind(robotController)],
    ['control_lights', robotController.controlLights.bind(robotController)],
    ['home_robot', robotController.homeRobot.bind(robotController)],
    ['set_default_robot_ip', robotController.setDefaultRobotIP.bind(robotController)],
    ['get_default_robot_ip', robotController.getDefaultRobotIP.bind(robotController)],
    
    // 错误修复工具
    ['poll_error_endpoint_and_fix', errorFixer.pollErrorEndpointAndFix.bind(errorFixer)]
  ]);
}

/**
 * 处理工具调用请求
 * @param {string} toolName - 工具名称
 * @param {Object} args - 工具参数
 * @param {Map} dispatcher - 工具分发器映射表
 * @returns {Promise<Object>} 工具执行结果
 */
export async function handleToolCall(toolName, args, dispatcher) {
  const handler = dispatcher.get(toolName);
  
  if (!handler) {
    return {
      content: [{
        type: "text", 
        text: `❌ Unknown tool: ${toolName}`
      }]
    };
  }
  
  try {
    return await handler(args);
  } catch (error) {
    return {
      content: [{
        type: "text",
        text: `❌ Tool execution error: ${error.message}`
      }]
    };
  }
} 