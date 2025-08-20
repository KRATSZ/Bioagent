from __future__ import annotations

import json
import os
from typing import Any, Dict

import requests
from langchain.tools import BaseTool


class OtcoderHTTPTool(BaseTool):
    """
    通过 HTTP 调用 Otcoder FastAPI 服务（生成 SOP / 生成代码 / 模拟）。

    输入(JSON或dict):
      {
        "action": "generate_sop" | "generate_code" | "simulate",
        "base_url": "http://127.0.0.1:8000"  # 可选，默认取 env OTCODER_BASE_URL 或 http://127.0.0.1:8000
        "payload": { ... }  # 与各端点匹配
      }

    端点与 payload：
      - generate_sop: POST /api/generate-sop
          {"hardware_config": str, "user_goal": str}
      - generate_code: POST /api/generate-protocol-code
          {"sop_markdown": str, "hardware_config": str, "robot_model": str|None}
      - simulate: POST /api/simulate-protocol
          {"protocol_code": str}
    """

    name = "OtcoderHTTP"
    description = "通过 HTTP 调用 Otcoder API：生成SOP、生成协议代码、模拟协议。"

    def _run(self, input_str: str | Dict[str, Any]) -> str:
        try:
            spec = json.loads(input_str) if isinstance(input_str, str) else input_str
            action = (spec.get("action") or "").lower()
            payload: Dict[str, Any] = spec.get("payload") or {}
            base_url = spec.get("base_url") or os.getenv("OTCODER_BASE_URL") or "http://127.0.0.1:8000"

            if action not in ("generate_sop", "generate_code", "simulate"):
                return "Error: action must be one of generate_sop, generate_code, simulate"

            if action == "generate_sop":
                url = f"{base_url.rstrip('/')}/api/generate-sop"
            elif action == "generate_code":
                url = f"{base_url.rstrip('/')}/api/generate-protocol-code"
            else:
                url = f"{base_url.rstrip('/')}/api/simulate-protocol"

            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code >= 400:
                return f"Error: HTTP {resp.status_code} - {resp.text}"
            try:
                return json.dumps(resp.json(), ensure_ascii=False)
            except Exception:
                return resp.text
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, input_str: str) -> str:
        raise NotImplementedError("Async not implemented")



