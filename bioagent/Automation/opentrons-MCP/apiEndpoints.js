/**
 * Opentrons HTTP API 端点定义
 * 包含所有可用的 API 端点及其详细信息
 */

export const API_ENDPOINTS = [
  {
    method: "GET",
    path: "/health",
    summary: "Get server health",
    description: "Get information about the health of the robot server. Use to check that the robot server is running and ready to operate. A 200 OK response means the server is running. Includes information about software and system.",
    tags: ["Health"],
    responses: {
      200: "Server is healthy - includes robot info, API version, firmware version, system version, logs links",
      422: "Unprocessable entity",
      503: "Service unavailable"
    }
  },
  {
    method: "GET",
    path: "/logs/{log_identifier}",
    summary: "Get troubleshooting logs",
    description: "Get the robot's troubleshooting logs. If you want protocol execution steps, use protocol analysis commands or run commands instead.",
    tags: ["Health"],
    parameters: [
      {
        name: "log_identifier",
        in: "path",
        required: true,
        description: "Type of log to retrieve",
        schema: {
          type: "string",
          enum: ["api.log", "serial.log", "can_bus.log", "server.log", "combined_api_server.log", "update_server.log", "touchscreen.log"]
        }
      },
      {
        name: "format",
        in: "query",
        description: "Format for log records",
        schema: { type: "string", enum: ["text", "json"], default: "text" }
      },
      {
        name: "records",
        in: "query",
        description: "Number of records to retrieve",
        schema: { type: "integer", minimum: 0, maximum: 100000, default: 50000 }
      }
    ]
  },
  {
    method: "GET",
    path: "/networking/status",
    summary: "Query network connectivity state",
    description: "Gets information about the robot's network interfaces including connectivity, addresses, and networking info",
    tags: ["Networking"],
    responses: {
      200: "Network interface information including IP addresses, MAC addresses, connection status for ethernet and wifi"
    }
  },
  {
    method: "GET",
    path: "/wifi/list",
    summary: "Scan for visible Wi-Fi networks",
    description: "Returns list of visible wifi networks with security and signal strength data",
    tags: ["Networking"],
    parameters: [
      {
        name: "rescan",
        in: "query",
        description: "If true, forces rescan for Wi-Fi networks. Expensive operation (~10 seconds)",
        schema: { type: "boolean", default: false }
      }
    ]
  },
  {
    method: "POST",
    path: "/wifi/configure",
    summary: "Configure robot's Wi-Fi",
    description: "Configures the wireless network interface to connect to a network",
    tags: ["Networking"],
    requestBody: {
      required: true,
      description: "WiFi configuration including SSID, security type, and credentials",
      properties: {
        ssid: { type: "string", description: "SSID to connect to" },
        hidden: { type: "boolean", default: false, description: "True if network is hidden" },
        securityType: { type: "string", description: "Security type (none, wpa-psk, wpa-eap)" },
        psk: { type: "string", description: "PSK for secured networks" },
        eapConfig: { type: "object", description: "EAP configuration for enterprise networks" }
      }
    }
  },
  {
    method: "GET",
    path: "/wifi/keys",
    summary: "Get Wi-Fi keys",
    description: "Get list of key files known to the system",
    tags: ["Networking"]
  },
  {
    method: "POST",
    path: "/wifi/keys",
    summary: "Add a Wi-Fi key",
    description: "Send a new key file to the robot",
    tags: ["Networking"],
    requestBody: {
      required: true,
      description: "Multipart form data with key file"
    }
  },
  {
    method: "DELETE",
    path: "/wifi/keys/{key_uuid}",
    summary: "Delete a Wi-Fi key",
    description: "Delete a key file from the robot",
    tags: ["Networking"],
    parameters: [
      {
        name: "key_uuid",
        in: "path",
        required: true,
        description: "ID of key to delete"
      }
    ]
  },
  {
    method: "GET",
    path: "/wifi/eap-options",
    summary: "Get EAP options",
    description: "Get supported EAP variants and their configuration parameters",
    tags: ["Networking"]
  },
  {
    method: "POST",
    path: "/wifi/disconnect",
    summary: "Disconnect from Wi-Fi",
    description: "Deactivates Wi-Fi connection and removes it from known connections",
    tags: ["Networking"]
  },
  {
    method: "POST",
    path: "/identify",
    summary: "Blink the lights",
    description: "Blink the gantry lights so you can pick the robot out of a crowd",
    tags: ["Control"],
    parameters: [
      {
        name: "seconds",
        in: "query",
        required: true,
        description: "Time to blink lights for",
        schema: { type: "integer" }
      }
    ]
  },
  {
    method: "POST",
    path: "/robot/home",
    summary: "Home the robot",
    description: "Home robot axes or specific pipette",
    tags: ["Control"],
    requestBody: {
      required: true,
      properties: {
        target: {
          type: "string",
          enum: ["pipette", "robot"],
          description: "What to home. Robot = all axes; pipette = that pipette's carriage and axes"
        },
        mount: { type: "string", description: "Which mount to home if target is pipette" }
      }
    }
  },
  {
    method: "POST",
    path: "/robot/move",
    summary: "Move the robot",
    description: "Move robot's gantry to a position. DEPRECATED: Use moveToCoordinates command in maintenance run instead",
    tags: ["Control"],
    deprecated: true,
    requestBody: {
      required: true,
      properties: {
        target: { type: "string", enum: ["pipette", "mount"] },
        point: { type: "array", items: { type: "number" }, minItems: 3, maxItems: 3 },
        mount: { type: "string", enum: ["right", "left"] },
        model: { type: "string", description: "Pipette model if target is pipette" }
      }
    }
  },
  {
    method: "GET",
    path: "/robot/positions",
    summary: "Get robot positions",
    description: "Get list of useful positions. DEPRECATED: OT-2 only, no public equivalent for Flex",
    tags: ["Control"],
    deprecated: true
  },
  {
    method: "GET",
    path: "/robot/lights",
    summary: "Get light state",
    description: "Get current status of robot's rail lights",
    tags: ["Control"]
  },
  {
    method: "POST",
    path: "/robot/lights",
    summary: "Control lights",
    description: "Turn rail lights on or off",
    tags: ["Control"],
    requestBody: {
      required: true,
      properties: {
        on: { type: "boolean", description: "True to turn lights on, false to turn off" }
      }
    }
  },
  {
    method: "GET",
    path: "/settings",
    summary: "Get settings",
    description: "Get list of available advanced settings (feature flags) and their values",
    tags: ["Settings"]
  },
  {
    method: "POST",
    path: "/settings",
    summary: "Change a setting",
    description: "Change an advanced setting (feature flag)",
    tags: ["Settings"],
    requestBody: {
      required: true,
      properties: {
        id: { type: "string", description: "ID of setting to change" },
        value: { type: "boolean", description: "New value. If null, reset to default" }
      }
    }
  },
  {
    method: "POST",
    path: "/settings/log_level/local",
    summary: "Set local log level",
    description: "Set minimum level of logs saved locally",
    tags: ["Settings"],
    requestBody: {
      required: true,
      properties: {
        log_level: {
          type: "string",
          enum: ["debug", "info", "warning", "error"],
          description: "Log level conforming to Python log levels"
        }
      }
    }
  },
  {
    method: "GET",
    path: "/settings/reset/options",
    summary: "Get reset options",
    description: "Get robot settings and data that can be reset through POST /settings/reset",
    tags: ["Settings"]
  },
  {
    method: "POST",
    path: "/settings/reset",
    summary: "Reset settings or data",
    description: "Perform reset of requested robot settings or data. Always restart robot after using this endpoint",
    tags: ["Settings"]
  },
  {
    method: "GET",
    path: "/pipettes",
    summary: "Get attached pipettes",
    description: "Lists properties of pipettes currently attached to robot like name, model, and mount. For Flex, prefer GET /instruments",
    tags: ["Attached Instruments"],
    parameters: [
      {
        name: "refresh",
        in: "query",
        description: "If true, actively scan for attached pipettes. WARNING: disables pipette motors, OT-2 only",
        schema: { type: "boolean", default: false }
      }
    ]
  },
  {
    method: "GET",
    path: "/instruments",
    summary: "Get attached instruments",
    description: "Get information about currently attached instruments (pipettes). Preferred endpoint for Flex robots",
    tags: ["Attached Instruments"]
  },
  {
    method: "GET",
    path: "/settings/pipettes",
    summary: "Get pipette settings",
    description: "List all settings for all known pipettes by ID. OT-2 only",
    tags: ["Settings"]
  },
  {
    method: "GET",
    path: "/settings/pipettes/{pipette_id}",
    summary: "Get specific pipette settings",
    description: "Get settings of specific pipette by ID. OT-2 only",
    tags: ["Settings"],
    parameters: [
      {
        name: "pipette_id",
        in: "path",
        required: true,
        description: "Pipette ID"
      }
    ]
  },
  {
    method: "PATCH",
    path: "/settings/pipettes/{pipette_id}",
    summary: "Update pipette settings",
    description: "Change settings of specific pipette. OT-2 only",
    tags: ["Settings"],
    parameters: [
      {
        name: "pipette_id",
        in: "path",
        required: true,
        description: "Pipette ID"
      }
    ]
  },
  {
    method: "GET",
    path: "/modules",
    summary: "Get attached modules",
    description: "Get list of all modules currently attached to the robot",
    tags: ["Attached Modules"]
  },
  {
    method: "POST",
    path: "/modules/{serial}",
    summary: "Execute module command",
    description: "Command a module to take an action. DEPRECATED: Use POST /commands instead",
    tags: ["Attached Modules"],
    deprecated: true,
    parameters: [
      {
        name: "serial",
        in: "path",
        required: true,
        description: "Serial number of module"
      }
    ],
    requestBody: {
      required: true,
      properties: {
        command_type: { type: "string", description: "Name of module function to call" },
        args: { type: "array", description: "Ordered args list for the call" }
      }
    }
  },
  {
    method: "POST",
    path: "/modules/{serial}/update",
    summary: "Update module firmware",
    description: "Command robot to flash bundled firmware file for this module type",
    tags: ["Attached Modules"],
    parameters: [
      {
        name: "serial",
        in: "path",
        required: true,
        description: "Serial number of module"
      }
    ]
  },
  {
    method: "GET",
    path: "/protocols",
    summary: "Get protocols",
    description: "Get list of all protocols stored on the robot",
    tags: ["Protocol Management"]
  },
  {
    method: "POST",
    path: "/protocols",
    summary: "Upload protocol",
    description: "Upload a Python or JSON protocol file to the robot. Can include support files",
    tags: ["Protocol Management"],
    requestBody: {
      required: true,
      description: "Multipart form data with protocol file and optional support files"
    }
  },
  {
    method: "GET",
    path: "/protocols/{protocol_id}",
    summary: "Get protocol details",
    description: "Get detailed information about a specific protocol",
    tags: ["Protocol Management"],
    parameters: [
      {
        name: "protocol_id",
        in: "path",
        required: true,
        description: "Protocol ID"
      }
    ]
  },
  {
    method: "DELETE",
    path: "/protocols/{protocol_id}",
    summary: "Delete protocol",
    description: "Delete a protocol from the robot",
    tags: ["Protocol Management"],
    parameters: [
      {
        name: "protocol_id",
        in: "path",
        required: true,
        description: "Protocol ID to delete"
      }
    ]
  },
  {
    method: "GET",
    path: "/protocols/{protocol_id}/analyses",
    summary: "Get protocol analyses",
    description: "Get list of analyses for a protocol",
    tags: ["Protocol Management"],
    parameters: [
      {
        name: "protocol_id",
        in: "path",
        required: true,
        description: "Protocol ID"
      }
    ]
  },
  {
    method: "GET",
    path: "/protocols/{protocol_id}/analyses/{analysis_id}",
    summary: "Get specific protocol analysis",
    description: "Get detailed analysis results for a protocol including commands, errors, and metadata",
    tags: ["Protocol Management"],
    parameters: [
      {
        name: "protocol_id",
        in: "path",
        required: true,
        description: "Protocol ID"
      },
      {
        name: "analysis_id",
        in: "path",
        required: true,
        description: "Analysis ID"
      }
    ]
  },
  {
    method: "GET",
    path: "/runs",
    summary: "Get runs",
    description: "Get list of all protocol runs",
    tags: ["Run Management"]
  },
  {
    method: "POST",
    path: "/runs",
    summary: "Create run",
    description: "Create a new protocol run",
    tags: ["Run Management"],
    requestBody: {
      required: true,
      properties: {
        data: {
          type: "object",
          properties: {
            protocolId: { type: "string", description: "ID of protocol to run" },
            labwareOffsets: { type: "array", description: "Labware offset data" },
            runTimeParameterValues: { type: "object", description: "Runtime parameter values" }
          }
        }
      }
    }
  },
  {
    method: "GET",
    path: "/runs/{run_id}",
    summary: "Get run details",
    description: "Get detailed information about a specific run",
    tags: ["Run Management"],
    parameters: [
      {
        name: "run_id",
        in: "path",
        required: true,
        description: "Run ID"
      }
    ]
  },
  {
    method: "DELETE",
    path: "/runs/{run_id}",
    summary: "Delete run",
    description: "Delete a protocol run",
    tags: ["Run Management"],
    parameters: [
      {
        name: "run_id",
        in: "path",
        required: true,
        description: "Run ID to delete"
      }
    ]
  },
  {
    method: "GET",
    path: "/runs/{run_id}/commands",
    summary: "Get run commands",
    description: "Get list of commands executed in a run",
    tags: ["Run Management"],
    parameters: [
      {
        name: "run_id",
        in: "path",
        required: true,
        description: "Run ID"
      },
      {
        name: "cursor",
        in: "query",
        description: "Cursor for pagination"
      },
      {
        name: "pageLength",
        in: "query",
        description: "Number of commands to return",
        schema: { type: "integer" }
      }
    ]
  },
  {
    method: "POST",
    path: "/runs/{run_id}/commands",
    summary: "Execute run command",
    description: "Queue a command for execution in a run",
    tags: ["Run Management"],
    parameters: [
      {
        name: "run_id",
        in: "path",
        required: true,
        description: "Run ID"
      }
    ],
    requestBody: {
      required: true,
      description: "Command to execute"
    }
  },
  {
    method: "POST",
    path: "/runs/{run_id}/actions",
    summary: "Control run execution",
    description: "Play, pause, stop, or resume a protocol run",
    tags: ["Run Management"],
    parameters: [
      {
        name: "run_id",
        in: "path",
        required: true,
        description: "Run ID"
      }
    ],
    requestBody: {
      required: true,
      properties: {
        data: {
          type: "object",
          properties: {
            actionType: {
              type: "string",
              enum: ["play", "pause", "stop", "resume-from-recovery"],
              description: "Action to perform on the run"
            }
          }
        }
      }
    }
  },
  {
    method: "GET",
    path: "/maintenance_runs",
    summary: "Get maintenance runs",
    description: "Get list of maintenance runs for robot calibration and setup",
    tags: ["Maintenance Run Management"]
  },
  {
    method: "POST",
    path: "/maintenance_runs",
    summary: "Create maintenance run",
    description: "Create a new maintenance run for calibration or diagnostics",
    tags: ["Maintenance Run Management"],
    requestBody: {
      required: true,
      properties: {
        data: {
          type: "object",
          properties: {
            runType: {
              type: "string",
              enum: ["deck_calibration", "pipette_offset_calibration", "tip_length_calibration"],
              description: "Type of maintenance run"
            }
          }
        }
      }
    }
  },
  {
    method: "GET",
    path: "/maintenance_runs/{run_id}",
    summary: "Get maintenance run details",
    description: "Get detailed information about a maintenance run",
    tags: ["Maintenance Run Management"],
    parameters: [
      {
        name: "run_id",
        in: "path",
        required: true,
        description: "Maintenance run ID"
      }
    ]
  },
  {
    method: "POST",
    path: "/maintenance_runs/{run_id}/commands",
    summary: "Execute maintenance command",
    description: "Execute a command in a maintenance run",
    tags: ["Maintenance Run Management"],
    parameters: [
      {
        name: "run_id",
        in: "path",
        required: true,
        description: "Maintenance run ID"
      }
    ]
  },
  {
    method: "POST",
    path: "/commands",
    summary: "Execute simple command",
    description: "Execute a simple robot command outside of a run context",
    tags: ["Simple Commands"],
    requestBody: {
      required: true,
      description: "Command to execute"
    }
  },
  {
    method: "GET",
    path: "/dataFiles",
    summary: "Get data files",
    description: "Get list of CSV data files stored on robot",
    tags: ["Data files Management"]
  },
  {
    method: "POST",
    path: "/dataFiles",
    summary: "Upload data file",
    description: "Upload a CSV data file to the robot",
    tags: ["Data files Management"],
    requestBody: {
      required: true,
      description: "Multipart form data with CSV file"
    }
  },
  {
    method: "GET",
    path: "/dataFiles/{file_id}",
    summary: "Get data file details",
    description: "Get information about a specific data file",
    tags: ["Data files Management"],
    parameters: [
      {
        name: "file_id",
        in: "path",
        required: true,
        description: "Data file ID"
      }
    ]
  },
  {
    method: "DELETE",
    path: "/dataFiles/{file_id}",
    summary: "Delete data file",
    description: "Delete a data file from the robot",
    tags: ["Data files Management"],
    parameters: [
      {
        name: "file_id",
        in: "path",
        required: true,
        description: "Data file ID to delete"
      }
    ]
  },
  {
    method: "GET",
    path: "/calibration/status",
    summary: "Get calibration status",
    description: "Get current calibration status for deck and instruments",
    tags: ["Deck Calibration"]
  },
  {
    method: "GET",
    path: "/labwareOffsets",
    summary: "Get labware offsets",
    description: "Get list of stored labware offset calibrations",
    tags: ["Labware Offset Management"]
  },
  {
    method: "POST",
    path: "/labwareOffsets",
    summary: "Create labware offset",
    description: "Add new labware offset calibration data",
    tags: ["Labware Offset Management"]
  },
  {
    method: "GET",
    path: "/system/time",
    summary: "Get system time",
    description: "Get current system time",
    tags: ["System Control"]
  },
  {
    method: "PUT",
    path: "/system/time",
    summary: "Set system time",
    description: "Update system time",
    tags: ["System Control"]
  },
  {
    method: "POST",
    path: "/system/restart",
    summary: "Restart robot",
    description: "Restart the robot system",
    tags: ["System Control"]
  },
  {
    method: "GET",
    path: "/motors/engaged",
    summary: "Get engaged motors",
    description: "Query which motors are engaged and holding position",
    tags: ["Control"]
  },
  {
    method: "POST",
    path: "/motors/disengage",
    summary: "Disengage motors",
    description: "Disengage specified motors",
    tags: ["Control"],
    requestBody: {
      required: true,
      properties: {
        axes: {
          type: "array",
          items: {
            type: "string",
            enum: ["x", "y", "z_l", "z_r", "z_g", "p_l", "p_r", "q", "g", "z", "a", "b", "c"]
          },
          description: "List of axes to disengage"
        }
      }
    }
  },
  {
    method: "POST",
    path: "/camera/picture",
    summary: "Capture camera image",
    description: "Capture image from OT-2's on-board camera. OT-2 only",
    tags: ["Control"]
  },
  {
    method: "GET",
    path: "/deck_configuration",
    summary: "Get deck configuration",
    description: "Get current deck configuration including slot status. Flex only",
    tags: ["Flex Deck Configuration"]
  },
  {
    method: "PUT",
    path: "/deck_configuration",
    summary: "Update deck configuration",
    description: "Update deck configuration. Flex only",
    tags: ["Flex Deck Configuration"]
  },
  {
    method: "GET",
    path: "/errorRecovery/settings",
    summary: "Get error recovery settings",
    description: "Get current error recovery policy settings",
    tags: ["Error Recovery Settings"]
  },
  {
    method: "PATCH",
    path: "/errorRecovery/settings",
    summary: "Update error recovery settings",
    description: "Update error recovery policy settings",
    tags: ["Error Recovery Settings"]
  },
  {
    method: "GET",
    path: "/clientData",
    summary: "Get client data",
    description: "Get all client-defined key-value data stored on robot",
    tags: ["Client Data"]
  },
  {
    method: "POST",
    path: "/clientData",
    summary: "Create client data",
    description: "Store new client-defined key-value data",
    tags: ["Client Data"]
  },
  {
    method: "GET",
    path: "/clientData/{key}",
    summary: "Get specific client data",
    description: "Get client data for a specific key",
    tags: ["Client Data"],
    parameters: [
      {
        name: "key",
        in: "path",
        required: true,
        description: "Client data key"
      }
    ]
  },
  {
    method: "PUT",
    path: "/clientData/{key}",
    summary: "Update client data",
    description: "Update client data for a specific key",
    tags: ["Client Data"],
    parameters: [
      {
        name: "key",
        in: "path",
        required: true,
        description: "Client data key"
      }
    ]
  },
  {
    method: "DELETE",
    path: "/clientData/{key}",
    summary: "Delete client data",
    description: "Delete client data for a specific key",
    tags: ["Client Data"],
    parameters: [
      {
        name: "key",
        in: "path",
        required: true,
        description: "Client data key"
      }
    ]
  }
]; 