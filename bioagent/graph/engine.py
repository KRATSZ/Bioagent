from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Tuple

from bioagent.agents import BioAgent
from bioagent.graph.nodes import planner_node, reflect_node
from bioagent.graph.state import AgentState
from bioagent.agents.prompts import PLANNER_PROMPT


async def run_graph_async(user_prompt: str) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    """Graph loop integrating planner → agent tools → reflector with limited iterations.

    Returns: (final_answer, events, plan)
    """
    # Build agent from environment configuration
    model = os.getenv("OPENAI_MODEL_NAME", "gemini-2.5-pro")
    tools_model = os.getenv("TOOLS_MODEL_NAME", model)
    api_key = os.getenv("OPENAI_API_KEY")
    agent = BioAgent(model=model, tools_model=tools_model, openai_api_key=api_key, api_keys={
        "OPENAI_API_KEY": api_key or "",
        "MCP_CONFIG": os.getenv("MCP_CONFIG", "./mcp_config.yaml"),
    })

    # Initialize state
    state: AgentState = {
        "input": user_prompt,
        "messages": [],
        "observations": [],
        "step_index": 0,
        "max_steps": int(os.getenv("GRAPH_MAX_STEPS", "6")),
    }

    events: List[Dict[str, Any]] = []
    plan: List[str] = []
    prompt_cursor = user_prompt

    for step in range(state.get("max_steps", 6)):
        state["step_index"] = step

        # 1) Planner
        state = await planner_node(agent.llm, state)  # type: ignore
        if state.get("plan"):
            # 累积展示用计划
            plan = state["plan"]

        # 2) Execute with existing agent (LangChain agent 负责具体工具调用)
        answer = agent.run(prompt_cursor)
        evs = agent.pop_tool_events() or []
        if evs:
            events.extend(evs)
        state["observations"] = state.get("observations", []) + [str(answer)]

        # 3) Reflector
        state = await reflect_node(agent.llm, state)  # type: ignore
        if state.get("final_answer"):
            return state["final_answer"], events, plan

        # 4) 若继续，更新 prompt 游标（带上简短上下文）
        prompt_cursor = f"继续完成：{user_prompt}\n已获得：{answer[:500]}\n若需要更多信息，请调用合适工具并给出下一步结果。"

    # 达到步数上限，返回最后答案或汇总
    last = state.get("observations", [])[-1] if state.get("observations") else ""
    final = last or "已完成规划与若干次执行，请检查 Logs。"
    return final, events, plan


def run_graph(prompt: str) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    try:
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(run_graph_async(prompt))  # type: ignore
    except RuntimeError:
        return asyncio.run(run_graph_async(prompt))


