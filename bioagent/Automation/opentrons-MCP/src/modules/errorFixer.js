/**
 * 错误修复器模块
 * 负责处理协议错误的自动检测和 AI 修复
 */
import fs from 'fs';
import axios from 'axios';
import { config } from '../../config/index.js';

export class ErrorFixer {
  async pollErrorEndpointAndFix(args) {
    const { 
      json_filename = config.errorFixer.defaultErrorReportFile, 
      original_protocol_path = config.errorFixer.defaultProtocolPath 
    } = args;
    
    try {
      const response = await axios.get(`${config.errorFixer.errorReportServer}/${json_filename}`, {
        timeout: config.api.shortTimeout
      });
      const errorText = response.data;
      const originalProtocol = fs.readFileSync(original_protocol_path, 'utf8');
      const fixedProtocol = await this.generateFixedProtocol(errorText, originalProtocol);
      
      return {
        content: [{
          type: "text",
          text: `🔧 **FIXED PROTOCOL**:\n\`\`\`python\n${fixedProtocol}\n\`\`\``
        }]
      };
    } catch (error) {
      return { content: [{ type: "text", text: `❌ Failed to process: ${error.message}` }] };
    }
  }

  async generateFixedProtocol(errorText, originalProtocol, lastCompletedStep = null, currentRunId = null) {
    if (!config.errorFixer.anthropicApiKey) {
      throw new Error("ANTHROPIC_API_KEY not configured");
    }
    
    const workingExample = `from opentrons import protocol_api
# ... (rest of the example protocol)
`;
    let contextInfo = "";
    if (lastCompletedStep !== null && currentRunId !== null) {
      contextInfo = `\n\nRUN CONTEXT:\n- Run ID: ${currentRunId}\n- The protocol should resume from step ${lastCompletedStep + 1}.`;
    }

    const prompt = `Fix this Opentrons Flex protocol that failed with this error:
ERROR: ${errorText}
ORIGINAL FAILED PROTOCOL:
${originalProtocol}
WORKING REFERENCE PROTOCOL:
${workingExample}${contextInfo}
Return ONLY the fixed Python code.`;

    try {
      const response = await axios.post(config.errorFixer.anthropicApiUrl, {
        model: config.errorFixer.anthropicModel,
        max_tokens: config.errorFixer.anthropicMaxTokens,
        messages: [{ role: "user", content: prompt }]
      }, {
        headers: {
          "x-api-key": config.errorFixer.anthropicApiKey,
          "Content-Type": "application/json",
          "anthropic-version": config.errorFixer.anthropicApiVersion
        },
        timeout: config.api.requestTimeout
      });
      
      return response.data.content[0].text;
      
    } catch (error) {
      return `❌ Failed to generate fix: ${error.message}`;
    }
  }
} 