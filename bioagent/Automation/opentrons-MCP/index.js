#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema
} from "@modelcontextprotocol/sdk/types.js";
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { API_ENDPOINTS } from './apiEndpoints.js';
import { TOOL_SCHEMAS } from './toolSchemas.js';
import { ApiExplorer } from './src/modules/apiExplorer.js';
import { RobotController } from './src/modules/robotController.js';
import { ProtocolManager } from './src/modules/protocolManager.js';
import { ErrorFixer } from './src/modules/errorFixer.js';
import { createToolDispatcher, handleToolCall } from './src/toolDispatcher.js';
import { config } from './config/index.js';

class OpentronsMCP {
  constructor() {
    this.server = new Server(
      {
        name: config.server.name,
        version: config.server.version,
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.endpoints = API_ENDPOINTS;
    
    // 初始化模块
    this.apiExplorer = new ApiExplorer(this.endpoints);
    this.robotController = new RobotController(config.api.defaultRobotIP);
    this.protocolManager = new ProtocolManager();
    this.errorFixer = new ErrorFixer();
    
    // 创建工具分发器
    this.toolDispatcher = createToolDispatcher({
      apiExplorer: this.apiExplorer,
      robotController: this.robotController,
      protocolManager: this.protocolManager,
      errorFixer: this.errorFixer
    });
    
    this.setupTools();
  }

  setupTools() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: TOOL_SCHEMAS
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      return handleToolCall(name, args, this.toolDispatcher);
    });
  }




  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Opentrons MCP server running on stdio");
  }
}

const server = new OpentronsMCP();
server.run().catch(console.error);