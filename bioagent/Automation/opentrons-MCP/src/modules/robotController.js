/**
 * 机器人控制器模块
 * 负责直接控制 Opentrons 机器人的硬件和运行状态
 */
import axios from 'axios';
import { config, getApiUrl, getDefaultHeaders } from '../../config/index.js';

export class RobotController {
  constructor(defaultRobotIP) {
    this.defaultRobotIP = defaultRobotIP;
  }

  async makeApiRequest(method, url, headers = {}, data = null) {
    try {
      const requestConfig = {
        method,
        url,
        headers: getDefaultHeaders(headers),
        timeout: config.api.requestTimeout
      };
      
      if (data) {
        requestConfig.data = data;
      }
      
      const response = await axios(requestConfig);
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
        throw new Error(`Cannot connect to robot. Please check the IP address and ensure the robot is powered on.`);
      }
      if (error.response) {
        const errorData = error.response.data;
        throw new Error(`API Error ${error.response.status}: ${errorData.message || JSON.stringify(errorData)}`);
      }
      throw error;
    }
  }

  getRobotIP(providedIP) {
    return providedIP || this.defaultRobotIP;
  }

  setDefaultRobotIP(args) {
    const { robot_ip } = args;
    this.defaultRobotIP = robot_ip;
    
    return {
      content: [{
        type: "text",
        text: `✅ Default robot IP set to: ${robot_ip}`
      }]
    };
  }

  getDefaultRobotIP(args) {
    return {
      content: [{
        type: "text",
        text: `**Current default robot IP**: ${this.defaultRobotIP}`
      }]
    };
  }

  async createRun(args) {
    const { robot_ip, protocol_id, run_time_parameters } = args;
    
    try {
      const body = { data: { protocolId: protocol_id } };
      if (run_time_parameters) {
        body.data.runTimeParameterValues = run_time_parameters;
      }
      
      const data = await this.makeApiRequest('POST', getApiUrl(robot_ip, 'runs'), { 'Content-Type': 'application/json' }, JSON.stringify(body));
      const run = data.data;
      return { content: [{ type: "text", text: `✅ Run created: ${run.id}` }] };
    } catch (error) {
      return { content: [{ type: "text", text: `❌ Failed to create run: ${error.message}` }] };
    }
  }

  async controlRun(args) {
    const { robot_ip, run_id, action } = args;
    
    try {
      const body = { data: { actionType: action } };
      await this.makeApiRequest('POST', getApiUrl(robot_ip, `runs/${run_id}/actions`), { 'Content-Type': 'application/json' }, JSON.stringify(body));
      return { content: [{ type: "text", text: `✅ Action '${action}' sent to run ${run_id}.` }] };
    } catch (error) {
      return { content: [{ type: "text", text: `❌ Failed to control run: ${error.message}` }] };
    }
  }

  async getRuns(args) {
    const { robot_ip } = args;
    
    try {
      const data = await this.makeApiRequest('GET', getApiUrl(robot_ip, 'runs'));
      const runs = data.data || [];
      const runList = runs.map(r => `ID: ${r.id}, Status: ${r.status}, Protocol: ${r.protocolId}`).join('\n');
      return { content: [{ type: "text", text: `Found ${runs.length} runs:\n${runList}` }] };
    } catch (error) {
      return { content: [{ type: "text", text: `❌ Failed to get runs: ${error.message}` }] };
    }
  }

  async getRunStatus(args) {
    const { robot_ip, run_id } = args;
    
    try {
      const data = await this.makeApiRequest('GET', getApiUrl(robot_ip, `runs/${run_id}`));
      const run = data.data;
      return { content: [{ type: "text", text: `Run ${run.id} status: ${run.status}` }] };
    } catch (error) {
      return { content: [{ type: "text", text: `❌ Failed to get run status: ${error.message}` }] };
    }
  }

  async robotHealth(args) {
    const robot_ip = this.getRobotIP(args.robot_ip);
    
    try {
      const data = await this.makeApiRequest('GET', getApiUrl(robot_ip, 'health'));
      return { content: [{ type: "text", text: `✅ Robot is healthy. Name: ${data.name}, API: ${data.api_version}` }] };
    } catch (error) {
      return { content: [{ type: "text", text: `❌ Health check failed: ${error.message}` }] };
    }
  }

  async controlLights(args) {
    const { robot_ip, on } = args;
    
    try {
      await this.makeApiRequest('POST', getApiUrl(robot_ip, 'robot/lights'), { 'Content-Type': 'application/json' }, JSON.stringify({ on }));
      return { content: [{ type: "text", text: `✅ Lights turned ${on ? 'ON' : 'OFF'}.` }] };
    } catch (error) {
      return { content: [{ type: "text", text: `❌ Failed to control lights: ${error.message}` }] };
    }
  }

  async homeRobot(args) {
    const { robot_ip, target = "robot", mount } = args;
    
    try {
      const body = { target };
      if (target === "pipette" && mount) body.mount = mount;
      await this.makeApiRequest('POST', getApiUrl(robot_ip, 'robot/home'), { 'Content-Type': 'application/json' }, JSON.stringify(body));
      return { content: [{ type: "text", text: `✅ Home command sent.` }] };
    } catch (error) {
      return { content: [{ type: "text", text: `❌ Failed to home robot: ${error.message}` }] };
    }
  }
} 