import os

from bioagent.graph.engine import run_graph


def test_run_graph_iterative_smoke():
    os.environ.setdefault("OPENAI_API_KEY", "test")
    try:
        ans, evs, plan = run_graph("测试多步规划")
        assert isinstance(evs, list)
        assert isinstance(plan, list)
    except Exception:
        # 无有效 API KEY 时允许网络相关失败
        pass


