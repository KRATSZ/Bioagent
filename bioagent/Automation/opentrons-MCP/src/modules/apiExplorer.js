/**
 * API 探索器模块
 * 负责搜索、浏览和展示 Opentrons HTTP API 端点信息
 */

export class ApiExplorer {
  constructor(endpoints) {
    this.endpoints = endpoints;
  }

  searchEndpoints(args) {
    const { query, method, tag, include_deprecated = false } = args;

    let filtered = this.endpoints.filter(endpoint => {
      if (!include_deprecated && endpoint.deprecated) return false;
      if (method && endpoint.method !== method.toUpperCase()) return false;
      if (tag && !endpoint.tags.some(t =>
        t.toLowerCase().includes(tag.toLowerCase())
      )) return false;

      const searchText = query.toLowerCase();
      return (
        endpoint.summary.toLowerCase().includes(searchText) ||
        endpoint.description.toLowerCase().includes(searchText) ||
        endpoint.path.toLowerCase().includes(searchText) ||
        endpoint.tags.some(t => t.toLowerCase().includes(searchText)) ||
        (endpoint.operationId && endpoint.operationId.toLowerCase().includes(searchText))
      );
    });

    filtered.sort((a, b) => {
      const queryLower = query.toLowerCase();
      const aExact = a.summary.toLowerCase().includes(queryLower) || a.path.toLowerCase().includes(queryLower);
      const bExact = b.summary.toLowerCase().includes(queryLower) || b.path.toLowerCase().includes(queryLower);

      if (aExact && !bExact) return -1;
      if (bExact && !aExact) return 1;
      return 0;
    });

    const results = filtered.slice(0, 20).map(endpoint => ({
      method: endpoint.method,
      path: endpoint.path,
      summary: endpoint.summary,
      tags: endpoint.tags,
      deprecated: endpoint.deprecated || false
    }));

    return {
      content: [
        {
          type: "text",
          text: `Found ${filtered.length} matching endpoints${filtered.length > 20 ? ' (showing first 20)' : ''}:\n\n` +
            results.map(r =>
              `**${r.method} ${r.path}** ${r.deprecated ? '⚠️ DEPRECATED' : ''}\n` +
              `${r.summary}\n` +
              `Tags: ${r.tags.join(', ')}\n`
            ).join('\n')
        }
      ]
    };
  }

  getEndpointDetails(args) {
    const { method, path: endpointPath } = args;

    const endpoint = this.endpoints.find(
      e => e.method === method.toUpperCase() && e.path === endpointPath
    );

    if (!endpoint) {
      return {
        content: [
          {
            type: "text",
            text: `Endpoint ${method.toUpperCase()} ${endpointPath} not found.`
          }
        ]
      };
    }

    let details = `# ${endpoint.method} ${endpoint.path}\n\n`;
    details += `**Summary:** ${endpoint.summary}\n\n`;
    details += `**Description:** ${endpoint.description}\n\n`;
    details += `**Tags:** ${endpoint.tags.join(', ')}\n\n`;

    if (endpoint.deprecated) {
      details += `⚠️ **DEPRECATED** - This endpoint is deprecated and may be removed in future versions\n\n`;
    }

    if (endpoint.parameters && endpoint.parameters.length > 0) {
      details += `## Parameters\n\n`;
      endpoint.parameters.forEach(param => {
        details += `- **${param.name}** (${param.in})${param.required ? ' *required*' : ''}: ${param.description}\n`;
        if (param.schema && param.schema.enum) {
          details += `  - Allowed values: ${param.schema.enum.join(', ')}\n`;
        }
        if (param.schema && param.schema.default !== undefined) {
          details += `  - Default: ${param.schema.default}\n`;
        }
      });
      details += '\n';
    }

    if (endpoint.requestBody) {
      details += `## Request Body\n\n`;
      if (endpoint.requestBody.required) {
        details += `*Required*\n\n`;
      }
      details += `${endpoint.requestBody.description || 'Request body data'}\n\n`;

      if (endpoint.requestBody.properties) {
        details += `### Properties:\n`;
        Object.entries(endpoint.requestBody.properties).forEach(([key, prop]) => {
          details += `- **${key}** (${prop.type || 'object'}): ${prop.description || 'No description'}\n`;
          if (prop.enum) {
            details += `  - Allowed values: ${prop.enum.join(', ')}\n`;
          }
          if (prop.default !== undefined) {
            details += `  - Default: ${prop.default}\n`;
          }
        });
      }
      details += '\n';
    }

    if (endpoint.responses) {
      details += `## Responses\n\n`;
      Object.entries(endpoint.responses).forEach(([code, description]) => {
        details += `- **${code}**: ${description}\n`;
      });
      details += '\n';
    }

    details += `## Usage Context\n\n`;
    if (endpoint.tags.includes('Health')) {
      details += `This endpoint is used for monitoring robot health and status. The /health endpoint is commonly used to verify robot connectivity.\n\n`;
    } else if (endpoint.tags.includes('Networking')) {
      details += `This endpoint manages robot network connectivity. Useful for configuring Wi-Fi, checking network status, and managing network credentials.\n\n`;
    } else if (endpoint.tags.includes('Run Management')) {
      details += `This endpoint is part of the protocol execution workflow. Use to create, monitor, and control protocol runs.\n\n`;
    } else if (endpoint.tags.includes('Protocol Management')) {
      details += `This endpoint manages protocol files on the robot. Use to upload, analyze, and manage protocol definitions.\n\n`;
    } else if (endpoint.tags.includes('Control')) {
      details += `This endpoint provides direct robot hardware control. Use for movement, homing, lighting, and other physical operations.\n\n`;
    }

    return {
      content: [
        {
          type: "text",
          text: details
        }
      ]
    };
  }

  listByCategory(args) {
    const { category } = args;

    const filtered = this.endpoints.filter(endpoint =>
      endpoint.tags.some(tag => tag.toLowerCase().includes(category.toLowerCase()))
    );

    if (filtered.length === 0) {
      const availableCategories = [...new Set(this.endpoints.flatMap(e => e.tags))];
      return {
        content: [
          {
            type: "text",
            text: `No endpoints found for category "${category}".\n\nAvailable categories:\n${availableCategories.map(cat => `- ${cat}`).join('\n')}`
          }
        ]
      };
    }

    const groupedByTag = {};
    filtered.forEach(endpoint => {
      endpoint.tags.forEach(tag => {
        if (tag.toLowerCase().includes(category.toLowerCase())) {
          if (!groupedByTag[tag]) groupedByTag[tag] = [];
          groupedByTag[tag].push(endpoint);
        }
      });
    });

    let content = `**${category} API Endpoints** (${filtered.length} found):\n\n`;

    Object.entries(groupedByTag).forEach(([tag, endpoints]) => {
      content += `## ${tag}\n\n`;
      endpoints.forEach(endpoint => {
        content += `• **${endpoint.method} ${endpoint.path}** ${endpoint.deprecated ? '⚠️ DEPRECATED' : ''}\n`;
        content += `  ${endpoint.summary}\n\n`;
      });
    });

    return {
      content: [
        {
          type: "text",
          text: content
        }
      ]
    };
  }

  getApiOverview() {
    const categories = [...new Set(this.endpoints.flatMap(e => e.tags))];
    const totalEndpoints = this.endpoints.length;
    const deprecatedCount = this.endpoints.filter(e => e.deprecated).length;
    const methodCounts = this.endpoints.reduce((acc, e) => {
      acc[e.method] = (acc[e.method] || 0) + 1;
      return acc;
    }, {});

    let overview = `# Opentrons HTTP API Overview\n\n`;
    overview += `The Opentrons HTTP API provides comprehensive control over Opentrons Flex and OT-2 robots. This RESTful API runs on port 31950 and enables protocol execution, hardware control, calibration, and system management.\n\n`;

    overview += `## API Statistics\n\n`;
    overview += `- **Total Endpoints**: ${totalEndpoints}\n`;
    overview += `- **Deprecated Endpoints**: ${deprecatedCount}\n`;
    overview += `- **HTTP Methods**: ${Object.entries(methodCounts).map(([method, count]) => `${method} (${count})`).join(', ')}\n\n`;

    overview += `## API Categories\n\n`;

    const categoryDescriptions = {
      'Health': 'Monitor robot status, get logs, check server health',
      'Networking': 'Configure Wi-Fi, manage network settings, connectivity status',
      'Control': 'Direct hardware control - movement, homing, lights, motors',
      'Settings': 'Robot configuration, feature flags, calibration settings',
      'Run Management': 'Execute protocols, control run state (play/pause/stop)',
      'Protocol Management': 'Upload, analyze, and manage protocol files',
      'Maintenance Run Management': 'Calibration workflows and diagnostics',
      'Attached Modules': 'Control temperature modules, magnetic modules, etc.',
      'Attached Instruments': 'Pipette information and configuration',
      'Data files Management': 'CSV data files for runtime parameters',
      'Simple Commands': 'Execute individual robot commands',
      'Labware Offset Management': 'Calibration data for labware positioning',
      'System Control': 'System time, restart, low-level system operations',
      'Client Data': 'Store arbitrary key-value data on robot',
      'Flex Deck Configuration': 'Flex-specific deck setup and configuration',
      'Error Recovery Settings': 'Configure error handling policies'
    };

    categories.forEach(category => {
      const count = this.endpoints.filter(e => e.tags.includes(category)).length;
      const description = categoryDescriptions[category] || 'Robot functionality';
      overview += `- **${category}** (${count} endpoints): ${description}\n`;
    });

    overview += `\n## Getting Started\n\n`;
    overview += `1. **Check Robot Health**: Start with \`GET /health\` to verify connectivity\n`;
    overview += `2. **Network Setup**: Use \`/networking/status\` and \`/wifi/*\` endpoints for network configuration\n`;
    overview += `3. **Upload Protocol**: Use \`POST /protocols\` to upload protocol files\n`;
    overview += `4. **Create Run**: Use \`POST /runs\` to create a protocol run\n`;
    overview += `5. **Execute**: Use \`POST /runs/{id}/actions\` to play/pause/stop runs\n`;
    overview += `6. **Monitor**: Use \`GET /runs/{id}\` and \`GET /runs/{id}/commands\` to monitor progress\n\n`;

    overview += `## Important Notes\n\n`;
    overview += `- **API Versioning**: All requests must include \`Opentrons-Version\` header (use "*" for latest)\n`;
    overview += `- **Port**: API runs on port 31950\n`;
    overview += `- **OpenAPI Spec**: Available at \`/openapi\` endpoint\n`;
    overview += `- **Documentation**: Interactive docs at \`/redoc\`\n`;
    overview += `- **Robot Differences**: Some endpoints are OT-2 or Flex specific\n`;
    overview += `- **Deprecated Endpoints**: ${deprecatedCount} endpoints are deprecated - use modern alternatives\n\n`;

    overview += `## Common Workflows\n\n`;
    overview += `### Protocol Execution\n`;
    overview += `1. Upload protocol: \`POST /protocols\`\n`;
    overview += `2. Create run: \`POST /runs\`\n`;
    overview += `3. Start execution: \`POST /runs/{id}/actions\` with "play"\n`;
    overview += `4. Monitor progress: \`GET /runs/{id}/commands\`\n\n`;

    overview += `### Robot Calibration\n`;
    overview += `1. Create maintenance run: \`POST /maintenance_runs\`\n`;
    overview += `2. Execute calibration commands: \`POST /maintenance_runs/{id}/commands\`\n`;
    overview += `3. Check calibration status: \`GET /calibration/status\`\n\n`;

    overview += `### Hardware Control\n`;
    overview += `1. Home robot: \`POST /robot/home\`\n`;
    overview += `2. Check attached instruments: \`GET /instruments\`\n`;
    overview += `3. Control lights: \`POST /robot/lights\`\n`;
    overview += `4. Execute simple commands: \`POST /commands\`\n\n`;

    return {
      content: [
        {
          type: "text",
          text: overview
        }
      ]
    };
  }
} 