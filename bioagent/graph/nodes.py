from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from langchain import PromptTemplate
from langchain.base_language import BaseLanguageModel

from bioagent.agents.prompts import PLANNER_PROMPT, REFLECT_PROMPT
from .state import AgentState


def _json_loads(s: str) -> Dict[str, Any]:
    try:
        return json.loads(s)
    except Exception:
        return {}


async def planner_node(llm: BaseLanguageModel, state: AgentState) -> AgentState:
    tmpl = PromptTemplate(input_variables=["question"], template=PLANNER_PROMPT + "\nQuestion: {question}")
    out = await llm.apredict(tmpl.format(question=state.get("input", "")))
    js = _json_loads(out)
    state["plan"] = js.get("plan", [])
    state["next_action"] = js.get("next_action", "llm")
    return state


async def tool_executor_node(callables: List[Any], state: AgentState, concurrency: int = 3, timeout_s: int = 90) -> AgentState:
    # callables: list of awaitables or sync wrappers prepared outside
    sem = asyncio.Semaphore(concurrency)

    async def _run_one(coro):
        async with sem:
            try:
                return await asyncio.wait_for(coro, timeout=timeout_s)
            except Exception as e:
                return f"tool error: {e}"

    results = await asyncio.gather(*[_run_one(c) for c in callables])
    obs = state.get("observations", [])
    obs.append("\n".join([str(r) for r in results]))
    state["observations"] = obs
    return state


async def reflect_node(llm: BaseLanguageModel, state: AgentState) -> AgentState:
    summary_input = "\n\n".join(state.get("observations", [])[-3:])
    tmpl = PromptTemplate(input_variables=["obs"], template=REFLECT_PROMPT + "\nObservations (latest):\n{obs}")
    out = await llm.apredict(tmpl.format(obs=summary_input))
    js = _json_loads(out)
    if js.get("should_continue") is False:
        state["final_answer"] = js.get("summary") or ""
    else:
        state["next_action"] = js.get("revised_next_action", state.get("next_action", "llm"))
    return state


