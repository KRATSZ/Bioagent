/**
 * Opentrons MCP 工具定义
 * 包含所有可用工具的 schema 定义
 */

export const TOOL_SCHEMAS = [
  {
    name: "search_endpoints",
    description: "Search Opentrons HTTP API endpoints by functionality, method, path, or any keyword",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search query - searches across endpoint names, descriptions, paths, and tags"
        },
        method: {
          type: "string",
          description: "HTTP method filter (GET, POST, PUT, DELETE, PATCH)",
          enum: ["GET", "POST", "PUT", "DELETE", "PATCH"]
        },
        tag: {
          type: "string",
          description: "Filter by API category/tag"
        },
        include_deprecated: {
          type: "boolean",
          description: "Include deprecated endpoints in results",
          default: false
        }
      },
      required: ["query"]
    }
  },
  {
    name: "get_endpoint_details",
    description: "Get comprehensive details about a specific API endpoint",
    inputSchema: {
      type: "object",
      properties: {
        method: {
          type: "string",
          description: "HTTP method (GET, POST, etc.)"
        },
        path: {
          type: "string",
          description: "API endpoint path"
        }
      },
      required: ["method", "path"]
    }
  },
  {
    name: "list_by_category",
    description: "List all endpoints in a specific functional category",
    inputSchema: {
      type: "object",
      properties: {
        category: {
          type: "string",
          description: "API category/tag to filter by",
          enum: [
            "Health", "Networking", "Control", "Settings", "Modules",
            "Pipettes", "Calibration", "Run Management", "Protocol Management",
            "Data files Management", "Simple Commands", "Flex Deck Configuration",
            "Error Recovery Settings", "Attached Modules", "Attached Instruments",
            "Labware Offset Management", "System Control", "Client Data",
            "Maintenance Run Management", "Robot", "Subsystem Management"
          ]
        }
      },
      required: ["category"]
    }
  },
  {
    name: "get_api_overview",
    description: "Get high-level overview of the Opentrons HTTP API structure and capabilities",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false
    }
  },
  {
    name: "upload_protocol",
    description: "Upload a protocol file to an Opentrons robot",
    inputSchema: {
      type: "object",
      properties: {
        robot_ip: { type: "string", description: "Robot IP address (e.g., '192.168.1.100')" },
        file_path: { type: "string", description: "Path to protocol file (.py or .json)" },
        protocol_kind: { type: "string", enum: ["standard", "quick-transfer"], default: "standard" },
        key: { type: "string", description: "Optional client tracking key (~100 chars)" },
        run_time_parameters: { type: "object", description: "Optional runtime parameter values" }
      },
      required: ["robot_ip", "file_path"]
    }
  },
  {
    name: "get_protocols", 
    description: "List all protocols stored on the robot",
    inputSchema: {
      type: "object",
      properties: {
        robot_ip: { type: "string", description: "Robot IP address" },
        protocol_kind: { type: "string", enum: ["standard", "quick-transfer"], description: "Filter by protocol type (optional)" }
      },
      required: ["robot_ip"]
    }
  },
  {
    name: "create_run",
    description: "Create a new protocol run on the robot",
    inputSchema: {
      type: "object", 
      properties: {
        robot_ip: { type: "string", description: "Robot IP address" },
        protocol_id: { type: "string", description: "ID of protocol to run" },
        run_time_parameters: { type: "object", description: "Optional runtime parameter values" }
      },
      required: ["robot_ip", "protocol_id"]
    }
  },
  {
    name: "control_run",
    description: "Control run execution (play, pause, stop, resume)",
    inputSchema: {
      type: "object",
      properties: {
        robot_ip: { type: "string", description: "Robot IP address" },
        run_id: { type: "string", description: "Run ID to control" },
        action: { type: "string", enum: ["play", "pause", "stop", "resume-from-recovery"], description: "Action to perform" }
      },
      required: ["robot_ip", "run_id", "action"]
    }
  },
  {
    name: "get_runs",
    description: "List all runs on the robot",
    inputSchema: {
      type: "object",
      properties: {
        robot_ip: { type: "string", description: "Robot IP address" }
      },
      required: ["robot_ip"]
    }
  },
  {
    name: "get_run_status",
    description: "Get detailed status of a specific run",
    inputSchema: {
      type: "object",
      properties: {
        robot_ip: { type: "string", description: "Robot IP address" },
        run_id: { type: "string", description: "Run ID to check" }
      },
      required: ["robot_ip", "run_id"]
    }
  },
  {
    name: "robot_health",
    description: "Check robot health and connectivity",
    inputSchema: {
      type: "object",
      properties: {
        robot_ip: { type: "string", description: "Robot IP address" }
      },
      required: ["robot_ip"]
    }
  },
  {
    name: "control_lights",
    description: "Turn robot lights on or off",
    inputSchema: {
      type: "object",
      properties: {
        robot_ip: { type: "string", description: "Robot IP address" },
        on: { type: "boolean", description: "True to turn lights on, false to turn off" }
      },
      required: ["robot_ip", "on"]
    }
  },
  {
    name: "home_robot",
    description: "Home robot axes or specific pipette",
    inputSchema: {
      type: "object",
      properties: {
        robot_ip: { type: "string", description: "Robot IP address" },
        target: { type: "string", enum: ["robot", "pipette"], default: "robot", description: "What to home" },
        mount: { type: "string", enum: ["left", "right"], description: "Which mount (required if target is 'pipette')" }
      },
      required: ["robot_ip"]
    }
  },
  {
    name: "poll_error_endpoint_and_fix",
    description: "Fetch specific JSON error report and automatically fix protocols",
    inputSchema: {
      type: "object",
      properties: {
        json_filename: { type: "string", default: "error_report_20250622_124746.json", description: "Name of JSON file to fetch" },
        original_protocol_path: { type: "string", default: "/Users/gene/Developer/failed-protocol-5.py", description: "Path to original protocol file" }
      }
    }
  },
  {
    name: "set_default_robot_ip",
    description: "Set the default robot IP address for subsequent operations",
    inputSchema: {
      type: "object",
      properties: {
        robot_ip: { type: "string", description: "Robot IP address to set as default" }
      },
      required: ["robot_ip"]
    }
  },
  {
    name: "get_default_robot_ip",
    description: "Get the current default robot IP address",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false
    }
  },
  {
    name: "simulate_protocol",
    description: "Simulate an Opentrons protocol using Python opentrons.simulate module",
    inputSchema: {
      type: "object",
      properties: {
        protocol_path: { 
          type: "string", 
          description: "Path to protocol file (.py) to simulate" 
        },
        protocol_code: { 
          type: "string", 
          description: "Protocol code as string to simulate (alternative to protocol_path)" 
        },
        output_format: {
          type: "string",
          enum: ["summary", "detailed", "json"],
          default: "summary",
          description: "Format of simulation output"
        }
      }
    }
  }
]; 