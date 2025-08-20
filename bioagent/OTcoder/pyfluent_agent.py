"""
PyFluent Agent Service (minimal iterative version)

Mirrors the structure of pylabrobot_agent but simplified for pyFluent. It focuses
on ensuring the presence of the required entry function, structured simulation,
and basic error classification with short iteration.
"""

from __future__ import annotations

import re
from typing import TypedDict, Optional, Dict, Callable
from langgraph.graph import StateGraph, END, START
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from backend.pyfluent_utils import run_pyfluent_simulation, get_pyfluent_error_recommendations
from backend.pyfluent_template import TEMPLATE as PYFLUENT_TEMPLATE
from backend.config import api_key, base_url, model_name


class PyFluentState(TypedDict):
    user_query: str
    python_code: Optional[str]
    simulation_result: Optional[dict]
    attempts: int
    max_attempts: int
    iteration_reporter: Optional[Callable]


def _fill_template(function_body: str) -> str:
    code = PYFLUENT_TEMPLATE
    return code.replace("# [AGENT_FUNCTION_BODY]", function_body.rstrip())


def _creation_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model_name=model_name,
        openai_api_base=base_url,
        openai_api_key=api_key,
        temperature=0.1,
        max_tokens=2048,
    )


def generate_code_node(state: PyFluentState) -> PyFluentState:
    attempt = state["attempts"] + 1
    if state.get("iteration_reporter"):
        state["iteration_reporter"]({"event_type": "node_start", "node_name": "generator", "attempt_num": attempt})

    llm = _creation_llm()
    prompt = f"""
You are a pyFluent protocol expert. Generate ONLY the function body to implement the user request below.
Do NOT include the function signature. Use the chainable pyFluent API: protocol.add_labware(...); protocol.fca().get_tips(...).aspirate(...).dispense(...).drop_tips().
Keep code short and valid. Use reasonable defaults (e.g., channels=[0]).

User Request:
{state['user_query']}
"""
    messages = [SystemMessage(content="You generate only function body for def protocol(protocol):"), HumanMessage(content=prompt)]
    try:
        resp = llm.invoke(messages)
        body = resp.content.strip()
        if body.startswith("```"):
            body = re.sub(r"^```[a-zA-Z]*", "", body).strip()
            if body.endswith("```"):
                body = body[:-3].strip()
        # Ensure indentation (4 spaces)
        body = "\n".join(("    " + line if line.strip() else line) for line in body.splitlines())
        code = _fill_template(body)
    except Exception as e:
        code = _fill_template("    # generation failed\n    pass")

    if state.get("iteration_reporter"):
        state["iteration_reporter"]({"event_type": "node_complete", "node_name": "generator", "attempt_num": attempt, "has_code": True})
    return {"python_code": code, "attempts": attempt}


def simulate_code_node(state: PyFluentState) -> PyFluentState:
    if state.get("iteration_reporter"):
        state["iteration_reporter"]({"event_type": "node_start", "node_name": "simulator", "attempt_num": state["attempts"]})
    code = state["python_code"] or ""
    result = run_pyfluent_simulation(code, return_structured=True)
    if state.get("iteration_reporter"):
        state["iteration_reporter"]({"event_type": "node_complete", "node_name": "simulator", "attempt_num": state["attempts"], "simulation_success": result.get("success")})
    return {"simulation_result": result}


def should_continue(state: PyFluentState) -> str:
    res = state.get("simulation_result") or {}
    if res.get("success"):
        return "end"
    if state["attempts"] >= state["max_attempts"]:
        return "end"
    return "continue"


def prepare_feedback_node(state: PyFluentState) -> PyFluentState:
    # Minimal: on failure, ask LLM to regenerate simpler function body using recommendations
    res = state.get("simulation_result") or {}
    err = res.get("error_details") or ""
    suggestions = get_pyfluent_error_recommendations(err)
    if state.get("iteration_reporter"):
        state["iteration_reporter"]({"event_type": "node_start", "node_name": "feedback_preparer", "attempt_num": state["attempts"]})
    # Reuse generate_code_node next, but encode suggestions into user_query
    augmented = state["user_query"] + "\nConstraints:\n- " + "\n- ".join(suggestions)
    if state.get("iteration_reporter"):
        state["iteration_reporter"]({"event_type": "node_complete", "node_name": "feedback_preparer", "attempt_num": state["attempts"], "has_feedback": True})
    return {"user_query": augmented}


def create_pyfluent_agent():
    g = StateGraph(PyFluentState)
    g.add_node("generator", generate_code_node)
    g.add_node("simulator", simulate_code_node)
    g.add_node("feedback_preparer", prepare_feedback_node)
    g.add_edge(START, "generator")
    g.add_edge("generator", "simulator")
    g.add_conditional_edges("simulator", should_continue, {"continue": "feedback_preparer", "end": END})
    g.add_edge("feedback_preparer", "generator")
    return g.compile()





