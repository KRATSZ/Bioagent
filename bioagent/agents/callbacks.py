from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from langchain.callbacks.base import BaseCallbackHandler


class ToolLoggingCallbackHandler(BaseCallbackHandler):
    """Collects step-by-step events for tools/chains to power a timeline view.

    Each event schema:
      {
        "timestamp": float,
        "node": "tool"|"chain"|"llm",
        "name": str,               # tool or chain name
        "action": str,             # start|end|error
        "input": Any,
        "output": Any,
        "run_id": str,
        "parent_run_id": Optional[str],
        "duration_ms": Optional[int],
        "error": Optional[str],
      }
    """

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []
        self._starts: Dict[str, float] = {}

    # Tool events
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        self._starts[run_id] = time.time()
        self.events.append(
            {
                "timestamp": time.time(),
                "node": "tool",
                "name": serialized.get("name") or serialized.get("id") or "tool",
                "action": "start",
                "input": input_str,
                "output": None,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "duration_ms": None,
                "error": None,
            }
        )

    def on_tool_end(self, output: str, run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        start = self._starts.pop(run_id, None)
        dur = int((time.time() - start) * 1000) if start else None
        self.events.append(
            {
                "timestamp": time.time(),
                "node": "tool",
                "name": "tool",
                "action": "end",
                "input": None,
                "output": output,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "duration_ms": dur,
                "error": None,
            }
        )

    def on_tool_error(self, error: Exception, run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:  # pragma: no cover
        start = self._starts.pop(run_id, None)
        dur = int((time.time() - start) * 1000) if start else None
        self.events.append(
            {
                "timestamp": time.time(),
                "node": "tool",
                "name": "tool",
                "action": "error",
                "input": None,
                "output": None,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "duration_ms": dur,
                "error": str(error),
            }
        )

    # Chain events (coarse)
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        self._starts[run_id] = time.time()
        self.events.append(
            {
                "timestamp": time.time(),
                "node": "chain",
                "name": serialized.get("name") or serialized.get("id") or "chain",
                "action": "start",
                "input": inputs,
                "output": None,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "duration_ms": None,
                "error": None,
            }
        )

    def on_chain_end(self, outputs: Dict[str, Any], run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        start = self._starts.pop(run_id, None)
        dur = int((time.time() - start) * 1000) if start else None
        self.events.append(
            {
                "timestamp": time.time(),
                "node": "chain",
                "name": "chain",
                "action": "end",
                "input": None,
                "output": outputs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "duration_ms": dur,
                "error": None,
            }
        )

    def pop_events(self) -> List[Dict[str, Any]]:
        out = list(self.events)
        self.events.clear()
        return out


