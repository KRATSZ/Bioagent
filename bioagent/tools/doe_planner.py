from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain.tools import BaseTool


class DoEPlannerTool(BaseTool):
    """
    简易 DoE 规划工具：支持全因子与基础拉丁超立方(降级为均匀采样)两种模式。

    输入(JSON或dict):
      {
        "factors": {"temp": [20,30,40], "pH": [6,7,8]},
        "mode": "full" | "lhs",
        "samples": 10   # 仅 lhs 模式使用
      }

    输出: JSON 数组，每个元素是一条实验条件。
    注意: 如安装 pyDOE2，可后续升级为正统 LHS/Taguchi 等设计。
    """

    name = "DoEPlanner"
    description = "基于给定因素范围生成实验设计矩阵，支持全因子/简化LHS。"

    def _run(self, input_spec: str | Dict[str, Any]) -> str:
        try:
            spec = json.loads(input_spec) if isinstance(input_spec, str) else input_spec
            factors: Dict[str, List[Any]] = spec.get("factors", {})
            mode = (spec.get("mode") or "full").lower()
            if not factors:
                return "Error: factors is required"

            if mode == "full":
                import itertools
                keys = list(factors.keys())
                values = [factors[k] for k in keys]
                grid = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
                return json.dumps(grid, ensure_ascii=False)

            # 简化的 LHS：对每个 factor 在其域上等距划分 + 乱序采样
            samples = int(spec.get("samples", 8))
            import random
            keys = list(factors.keys())
            # 将离散水平扩展到 samples 长度（重复/截断），再按列独立乱序，最后按行组合
            columns: List[List[Any]] = []
            for k in keys:
                levels = list(factors[k])
                if not levels:
                    return f"Error: factor {k} has no levels"
                # 扩展/截断
                arr = (levels * ((samples + len(levels) - 1) // len(levels)))[:samples]
                random.shuffle(arr)
                columns.append(arr)
            rows = [dict(zip(keys, [columns[j][i] for j in range(len(keys))])) for i in range(samples)]
            return json.dumps(rows, ensure_ascii=False)
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, input_spec: str) -> str:
        raise NotImplementedError("Async not implemented")



