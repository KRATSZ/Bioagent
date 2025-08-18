from __future__ import annotations

import argparse
import asyncio
import os
from typing import List

import langchain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from bioagent.agents.tools import make_tools
from bioagent.graph.nodes import planner_node, reflect_node
from bioagent.graph.state import AgentState


def _make_llm(model: str, temp: float, api_key: str):
    return langchain.chat_models.ChatOpenAI(
        temperature=temp,
        model_name=model,
        request_timeout=1000,
        streaming=False,
        callbacks=[StreamingStdOutCallbackHandler()],
        openai_api_key=api_key,
    )


async def run_once(prompt: str) -> str:
    model = os.getenv("OPENAI_MODEL_NAME", "gemini-2.5-pro")
    key = os.getenv("OPENAI_API_KEY", "")
    llm = _make_llm(model, 0.1, key)

    # init tools to ensure MCP/Biomni are loaded but we won't wire full parallel executor here
    _ = make_tools(llm, api_keys={"OPENAI_API_KEY": key, "MCP_CONFIG": os.getenv("MCP_CONFIG", "./mcp_config.yaml")})

    state: AgentState = {"input": prompt, "messages": [], "observations": [], "step_index": 0, "max_steps": 8}
    state = await planner_node(llm, state)
    # Minimal loop: plan -> reflect (without real tool exec wiring yet)
    state = await reflect_node(llm, state)
    return state.get("final_answer") or "Plan generated. Enable full graph executor for tool calls."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    args = ap.parse_args()
    out = asyncio.run(run_once(args.prompt))
    print(out)


if __name__ == "__main__":
    main()


