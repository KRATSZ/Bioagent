from __future__ import annotations

import json
from typing import Any, Dict

from langchain.tools import BaseTool


class HumanInTheLoopTool(BaseTool):
    """
    人在回路(HITL)占位工具：
    - 不修改前端时，此工具返回一段结构化请求，提示用户在聊天中提供确认/编辑后的JSON。
    - Agent 可在拿到用户粘贴的JSON后继续流程。

    输入(JSON或dict):
      {
        "title": "需要专家确认的步骤",
        "instruction": "请在下方返回确认后的本体/关系JSON...",
        "payload": {... 任意待确认内容 ...}
      }
    输出: 带有 "HITL_REQUEST" 标记的JSON字符串。
    """

    name = "HumanInTheLoop"
    description = "暂停并请求人类确认/输入：返回带 HITL_REQUEST 标记的结构化提示。"

    def _run(self, input_str: str | Dict[str, Any]) -> str:
        try:
            data = json.loads(input_str) if isinstance(input_str, str) else input_str
            title = data.get("title") or "Human Confirmation Required"
            instruction = data.get("instruction") or "Please provide a confirmed JSON payload."
            payload = data.get("payload") or {}
            return json.dumps({
                "type": "HITL_REQUEST",
                "title": title,
                "instruction": instruction,
                "payload": payload,
                "how_to_respond": "在对话中粘贴一个 JSON 对象作为回复。"
            }, ensure_ascii=False)
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, input_str: str) -> str:
        raise NotImplementedError("Async not implemented")



