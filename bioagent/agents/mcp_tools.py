
"""MCP tool discovery and LangChain Tool wrappers.

This module discovers tools from MCP servers (e.g., BioMCP, ChemMCP)
based on a YAML configuration file and exposes them as LangChain Tools.

Windows-friendly; relies on STDIO transport and creates a fresh
connection per tool call for robustness.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import nest_asyncio
import yaml
from langchain.tools import BaseTool
from pydantic import Field

try:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
except Exception:  # pragma: no cover
    ClientSession = None  # type: ignore
    StdioServerParameters = None  # type: ignore
    stdio_client = None  # type: ignore


@dataclass
class _ServerSpec:
    name: str
    command: List[str]
    env: Dict[str, str]


class MCPToolWrapper(BaseTool):
    name: str
    description: str

    server_command: List[str] = Field(default_factory=list)
    server_env: Dict[str, str] = Field(default_factory=dict)
    tool_name: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)

    def _parse_input(self, tool_input: str | Dict[str, Any]) -> Dict[str, Any]:
        """Best-effort input mapping from string to tool kwargs.

        Heuristics:
        - dict → return as-is
        - string → try JSON; if fails, map to a preferred key
          Preference order: query > prompt > input > text > smiles > id
        - if schema has exactly one property, map to that property
        - if schema has any of preferred keys, use the first available
        - otherwise default to {"query": s}
        """
        if isinstance(tool_input, dict):
            return tool_input

        s = (tool_input or "").strip()
        # Try parse JSON first
        if s:
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        props = (self.input_schema or {}).get("properties", {}) or {}
        preferred_keys = ["query", "prompt", "input", "text", "smiles", "id"]

        # Single-property schema → map directly
        if len(props) == 1:
            only_key = next(iter(props.keys()))
            return {only_key: s}

        # If schema defines any preferred key → pick the first available
        for key in preferred_keys:
            if key in props:
                return {key: s}

        # If no schema or no matching keys → default to 'query'
        if s:
            return {"query": s}
        return {}

    def _run(self, tool_input: str) -> str:
        if ClientSession is None or stdio_client is None or StdioServerParameters is None:
            return "MCP client library not installed. Please install 'mcp'."

        nest_asyncio.apply()

        async def _call() -> str:
            params = StdioServerParameters(
                command=self.server_command[0], args=self.server_command[1:], env=self.server_env
            )
            try:
                async with stdio_client(params) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        kwargs = self._parse_input(tool_input)
                        result = await session.call_tool(self.tool_name, kwargs)
                        contents = result.content or []
                        if not contents:
                            return ""
                        content = contents[0]
                        if hasattr(content, "json") and content.json is not None:
                            try:
                                return json.dumps(content.json, ensure_ascii=False)
                            except Exception:
                                pass
                        return getattr(content, "text", "") or ""
            except Exception as e:  # pragma: no cover
                return f"MCP tool '{self.tool_name}' execution failed: {e}"

        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(_call())  # type: ignore
        except RuntimeError:
            return asyncio.run(_call())


def _load_yaml(path: str | Path) -> Dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def _resolve_env(env: Dict[str, Any]) -> Dict[str, str]:
    resolved: Dict[str, str] = {}
    for k, v in (env or {}).items():
        if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
            key = v[2:-1]
            resolved[k] = os.getenv(key, "")
        else:
            resolved[k] = str(v)
    return resolved


def _discover_tools(server: _ServerSpec) -> List[Dict[str, Any]]:
    if ClientSession is None:
        return []

    nest_asyncio.apply()

    async def _list() -> List[Dict[str, Any]]:
        params = StdioServerParameters(command=server.command[0], args=server.command[1:], env=server.env)
        try:
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    res = await session.list_tools()
                    tools = getattr(res, "tools", res)
                    out: List[Dict[str, Any]] = []
                    for t in tools:
                        out.append(
                            {
                                "name": getattr(t, "name", None),
                                "description": getattr(t, "description", ""),
                                "inputSchema": getattr(t, "inputSchema", {}),
                            }
                        )
                    return [x for x in out if x.get("name")]
        except Exception:
            return []

    try:
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(_list())  # type: ignore
    except RuntimeError:
        return asyncio.run(_list())


def load_mcp_tools(config_path: str | Path = "./mcp_config.yaml") -> List[BaseTool]:
    cfg: Dict[str, Any] = {}
    try:
        if Path(config_path).exists():
            cfg = _load_yaml(config_path)
        else:
            return []
    except Exception:
        return []

    servers = cfg.get("mcp_servers", {}) or {}
    wrappers: List[BaseTool] = []

    for name, meta in servers.items():
        if not meta or meta.get("enabled", True) is False:
            continue
        cmd = meta.get("command", [])
        if not isinstance(cmd, list) or not cmd:
            continue
        launcher = str(cmd[0]).lower()
        if launcher == "python":
            cmd = [sys.executable] + cmd[1:]
        elif launcher == "biomcp":
            cmd = [sys.executable, "-m", "biomcp"] + cmd[1:]
        elif launcher == "uv":
            pass
        env = _resolve_env(meta.get("env", {}))
        spec = _ServerSpec(name=name, command=cmd, env=env)

        tools = meta.get("tools") or _discover_tools(spec)
        if not tools:
            continue

        for t in tools:
            tool_name = t.get("name")
            if not tool_name:
                continue
            desc = t.get("description", f"MCP tool: {tool_name}")
            schema = t.get("inputSchema", {})
            wrappers.append(
                MCPToolWrapper(
                    name=f"{name}:{tool_name}",
                    description=desc,
                    server_command=spec.command,
                    server_env=spec.env,
                    tool_name=tool_name,
                    input_schema=schema,
                )
            )

    return wrappers

