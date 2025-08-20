from __future__ import annotations

import json
from typing import Any, Dict

from langchain.tools import BaseTool


class SOPGeneratorTool(BaseTool):
    """
    基于 Otcoder 的协议生成链：输入硬件与实验目标，产出 SOP 与/或协议代码。

    两种动作：
      - action: "sop"  -> 仅生成 SOP
      - action: "code" -> 生成代码(内部先生成 SOP，再生成代码)

    输入(JSON或dict):
      {
        "hardware_config": "Robot Model: ...\nAPI Version: 2.19\n...",
        "user_goal": "描述你的实验目标...",
        "max_iterations": 5,
        "action": "sop" | "code"
      }
    """

    name = "SOPGenerator"
    description = "调用 Otcoder 生成 SOP 或 Opentrons 协议代码（本地链）。"

    def _run(self, input_str: str | Dict[str, Any]) -> str:
        try:
            spec = json.loads(input_str) if isinstance(input_str, str) else input_str
            hardware_config = spec.get("hardware_config", "").strip()
            user_goal = spec.get("user_goal", "").strip()
            action = (spec.get("action") or "code").lower()
            max_iter = int(spec.get("max_iterations", 5))
            if not user_goal:
                return "Error: user_goal is required"

            # 直接调用 Otcoder 本地链（避免HTTP依赖）
            # 处理 Otcoder 内部使用的别名导入 "backend.*"
            import importlib, sys
            try:
                import bioagent.OTcoder as _ot
                sys.modules.setdefault("backend", _ot)  # alias
                # 还需确保子模块可通过 backend.* 访问
                for sub in ("config", "diff_utils", "opentrons_utils", "prompts", "pylabrobot_utils", "pylabrobot_agent", "file_exporter"):
                    try:
                        mod = importlib.import_module(f"bioagent.OTcoder.{sub}")
                        sys.modules.setdefault(f"backend.{sub}", mod)
                    except Exception:
                        pass
            except Exception:
                pass

            from bioagent.OTcoder.langchain_agent import generate_sop_with_langchain, generate_protocol_code

            if action == "sop":
                combined = f"{hardware_config}---{user_goal}"
                sop = generate_sop_with_langchain(combined)
                return json.dumps({"sop": sop}, ensure_ascii=False)

            # action == code
            # 先生成 SOP，再生成代码
            combined = f"{hardware_config}---{user_goal}"
            sop = generate_sop_with_langchain(combined)
            code = generate_protocol_code(sop, hardware_config, max_iterations=max_iter)
            return json.dumps({"sop": sop, "code": code}, ensure_ascii=False)
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, input_str: str) -> str:
        raise NotImplementedError("Async not implemented")


