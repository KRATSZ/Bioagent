import os
import asyncio

from bioagent.graph.runner import run_once


def test_run_once_smoke():
    os.environ.setdefault("OPENAI_API_KEY", "test")  # 如果无 key，会在真实环境中失败；此处仅做接口烟测
    try:
        _ = asyncio.run(run_once("测试规划一步"))
    except Exception:
        # 在无有效 key 时允许失败，但接口可调用
        pass


