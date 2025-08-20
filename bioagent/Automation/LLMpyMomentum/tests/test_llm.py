import os
import pytest

from app.intent import parse_intent


requires_key = pytest.mark.skipif(
    not os.getenv("AI190_API_KEY"), reason="AI190_API_KEY not set; skipping live LLM test"
)


@requires_key
def test_llm_parse_basic_status():
    it = parse_intent("show devices and status")
    # allow model variability; at least must produce an action
    assert it.action in {"devices", "status", "processes", "workqueue", "version", "start", "simulate", "stop", "run_process"}




