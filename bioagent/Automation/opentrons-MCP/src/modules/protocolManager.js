/**
 * 协议管理器模块
 * 负责处理 Opentrons 协议的上传、管理和模拟
 */
import fs from 'fs';
import path from 'path';
import FormData from 'form-data';
import axios from 'axios';
import { config, getApiUrl, getDefaultHeaders } from '../../config/index.js';

export class ProtocolManager {
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

  async uploadProtocol(args) {
    const { robot_ip, file_path, support_files = [], protocol_kind = config.upload.defaultProtocolKind, run_time_parameters = {} } = args;
    
    try {
      if (!fs.existsSync(file_path)) {
        return {
          content: [{
            type: "text",
            text: `❌ **File not found**: ${file_path}`
          }]
        };
      }

      const form = new FormData();
      
      // Add main protocol file
      const protocolStream = fs.createReadStream(file_path);
      form.append('files', protocolStream, {
        filename: path.basename(file_path),
        contentType: config.upload.fileContentType
      });
      
      // Add support files if any
      for (const supportPath of support_files) {
        if (fs.existsSync(supportPath)) {
          const supportStream = fs.createReadStream(supportPath);
          form.append('supportFiles', supportStream, {
            filename: path.basename(supportPath),
            contentType: config.upload.fileContentType
          });
        }
      }
      
      // Add protocol kind if not standard
      if (protocol_kind !== config.upload.defaultProtocolKind) {
        form.append('protocolKind', protocol_kind);
      }
      
      // Add runtime parameters if provided
      if (Object.keys(run_time_parameters).length > 0) {
        form.append('runTimeParameterValues', JSON.stringify(run_time_parameters));
      }

      const url = getApiUrl(robot_ip, 'protocols');
      if (config.debug.showCommands) {
        console.error(`Uploading protocol to: ${url}`);
      }
      
      const responseData = await this.makeApiRequest('POST', url, {
        ...form.getHeaders(),
        'accept': 'application/json'
      }, form);
      
      if (responseData.errors || (responseData.data && responseData.data.errors)) {
        const errors = responseData.errors || responseData.data.errors || [];
        throw new Error(errors.map(err => err.detail || err.message).join(', '));
      }

      const protocolId = responseData?.data?.id;
      return {
        content: [{
          type: "text",
          text: `✅ Protocol uploaded successfully! ID: ${protocolId}`
        }]
      };

    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `❌ Upload error: ${error.message}`
        }]
      };
    }
  }

  async getProtocols(args) {
    const { robot_ip, protocol_kind } = args;
    
    try {
      const data = await this.makeApiRequest(
        'GET',
        getApiUrl(robot_ip, 'protocols')
      );
      
      let protocols = data.data || [];
      if (protocol_kind) {
        protocols = protocols.filter(p => p.protocolKind === protocol_kind);
      }
      
      const protocolList = protocols.map(p => `ID: ${p.id}, Name: ${p.metadata?.protocolName || 'Unnamed'}`).join('\n');
      return {
        content: [{
          type: "text",
          text: `Found ${protocols.length} protocols:\n${protocolList}`
        }]
      };
    } catch (error) {
      return { content: [{ type: "text", text: `❌ Failed to get protocols: ${error.message}` }] };
    }
  }

  async simulateProtocol(args) {
    const { protocol_path, protocol_code, output_format = config.simulation.defaultOutputFormat } = args;
    
    try {
      const { exec } = await import('child_process');
      const { promisify } = await import('util');
      const execAsync = promisify(exec);
      
      // Use the relative path from config directly, assuming CWD is project root.
      const scriptPath = config.simulation.simulationScriptPath;

      let command;
      let tempFileToDelete = null;
      
      if (protocol_path) {
        if (!fs.existsSync(protocol_path)) {
          return { content: [{ type: "text", text: `❌ **Protocol file not found**: ${protocol_path}` }] };
        }
        command = `python "${scriptPath}" --file "${protocol_path}" --format ${output_format}`;
      } else if (protocol_code) {
        const os = await import('os');
        const tempFile = path.join(os.tmpdir(), `${config.simulation.tempFilePrefix}${Date.now()}.py`);
        tempFileToDelete = tempFile;
        fs.writeFileSync(tempFile, protocol_code, 'utf8');
        command = `python "${scriptPath}" --file "${tempFile}" --format ${output_format}`;
      } else {
        return { content: [{ type: "text", text: "❌ **Missing input**: Provide 'protocol_path' or 'protocol_code'." }] };
      }
      
      if (config.debug.showCommands) {
        console.error(`Executing simulation: ${command}`);
      }
      
      const { stdout, stderr } = await execAsync(command);
      
      if (tempFileToDelete) {
        fs.unlinkSync(tempFileToDelete);
      }
      
      if (stderr) {
        // Log stderr but don't fail immediately, as some warnings go to stderr
        console.error(`Simulation stderr: ${stderr}`);
      }
      
      const result = JSON.parse(stdout);
      return this.formatSimulationResult(result, output_format);
      
    } catch (error) {
       let errorMessage = `❌ **Simulation error**: ${error.message}`;
      if (error.stdout) {
        errorMessage += `\n\n**STDOUT**:\n${error.stdout}`;
      }
      if (error.stderr) {
        errorMessage += `\n\n**STDERR**:\n${error.stderr}`;
      }
       return { content: [{ type: "text", text: errorMessage }] };
    }
  }

  formatSimulationResult(result, output_format) {
    if (!result.success) {
      let errorText = `❌ **Protocol simulation failed**\n\n`;
      errorText += `**Type**: ${result.error_type}\n`;
      errorText += `**Error**: ${result.error}\n\n`;
      if (result.traceback) {
        errorText += `**Traceback**:\n\`\`\`\n${result.traceback.split('\n').slice(-7).join('\n')}\n\`\`\``;
      }
      return { content: [{ type: "text", text: errorText }] };
    }
    
    let successText = `✅ **Simulation successful!**\n\n`;
    
    if (output_format === 'summary' && result.summary) {
      const summary = result.summary;
      successText += `## 📊 Summary\n`;
      successText += `- **Steps**: ${summary.total_steps}\n`;
      successText += `- **Instruments**: ${summary.instruments_used.join(', ') || 'None'}\n`;
      successText += `- **Key Actions**: ${summary.key_actions.slice(0,5).join(', ')}...`;
    } else if (output_format === 'detailed' && result.steps) {
      successText += `## 📋 Detailed Steps\n`;
      successText += result.steps.join('\n');
    } else if (output_format === 'json' && result.runlog) {
      successText += `## 🔧 JSON Output\n`;
      successText += '```json\n' + JSON.stringify(result.runlog, null, 2) + '\n```';
    }
    
    return { content: [{ type: "text", text: successText }] };
  }
} 