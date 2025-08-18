from __future__ import annotations

from typing import List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    input: str
    messages: List[str]
    plan: List[str]
    next_action: str
    observations: List[str]
    step_index: int
    max_steps: int
    final_answer: Optional[str]
    error: Optional[str]


