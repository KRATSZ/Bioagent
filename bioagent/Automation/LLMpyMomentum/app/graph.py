from __future__ import annotations

import json
from typing import Any, Dict
from dataclasses import dataclass

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .momentum_client import create_momentum_client, MomentumLike
from .intent import parse_intent


@dataclass
class GraphState:
    user_input: str
    result: str | None = None
    dry_run: bool = False


def node_router(state: GraphState) -> str:
    text = state.user_input.strip().lower()
    if any(k in text for k in ["start", "simulate", "stop", "status", "version", "devices", "nests", "process", "workqueue"]):
        return "agent"
    return "agent"


def create_agent_node(momentum: MomentumLike):
    def agent(state: GraphState) -> GraphState:
        q = state.user_input.strip()
        # LLM-first intent parsing, fallback到规则
        intent = parse_intent(q)
        # merge external dry_run
        if state.dry_run:
            intent.dry_run = True
        try:
            if intent.action == "simulate":
                if not intent.dry_run:
                    momentum.simulate()
                result = "simulate: ok"
            elif intent.action == "start":
                if not intent.dry_run:
                    momentum.start()
                result = "start: ok"
            elif intent.action == "stop":
                if not intent.dry_run:
                    momentum.stop()
                result = "stop: ok"
            elif intent.action == "version":
                result = json.dumps(momentum.get_version(), ensure_ascii=False)
            elif intent.action == "devices":
                result = json.dumps(momentum.get_devices(), ensure_ascii=False)
            elif intent.action == "nests":
                result = json.dumps(momentum.get_nests(), ensure_ascii=False)
            elif intent.action == "workqueue":
                result = json.dumps(momentum.get_workqueue(), ensure_ascii=False)
            elif intent.action == "processes":
                result = json.dumps(momentum.get_processes(), ensure_ascii=False)
            elif intent.action == "run_process":
                if intent.dry_run or not intent.process_name:
                    result = (
                        f"planned run_process: process={intent.process_name}, "
                        f"vars={intent.variables}, iterations={intent.iterations}, "
                        f"append={intent.append}, minDelay={intent.minimum_delay}, "
                        f"workunit={intent.workunit_name}"
                    )
                else:
                    r = momentum.run_process(
                        process=intent.process_name,
                        variables=intent.variables,
                        iterations=intent.iterations,
                        append=intent.append,
                        minimum_delay=intent.minimum_delay,
                        workunit_name=intent.workunit_name,
                    )
                    result = str(r) if r is not None else "run_process: submitted"
            else:
                result = json.dumps(momentum.get_status(), ensure_ascii=False)
        except Exception as e:
            result = f"执行错误: {e}"
        return GraphState(user_input=state.user_input, result=result)

    return agent


def build_graph() -> tuple[Any, MomentumLike]:
    momentum = create_momentum_client()
    memory = MemorySaver()
    sg = StateGraph(GraphState)
    agent = create_agent_node(momentum)
    sg.add_node("agent", agent)
    sg.set_entry_point("agent")
    sg.add_edge("agent", END)
    app = sg.compile(checkpointer=memory)
    return app, momentum


