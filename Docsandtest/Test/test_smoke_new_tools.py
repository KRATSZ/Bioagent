import json
import os
from pathlib import Path

from bioagent.tools.doe_planner import DoEPlannerTool
from bioagent.tools.analysis_tools import LCMSParserTool, MzMLParserTool
from bioagent.tools.otcoder_http import OtcoderHTTPTool


def write_dummy_mrm_csv(csv_path: Path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "Q1,Q3,RT,Area\n"  # Precursor, Product, RetentionTime, Area
        "707.0,425.0,5.10,12345\n"
        "673.0,391.0,6.20,6789\n",
        encoding="utf-8",
    )


def test_doe():
    tool = DoEPlannerTool()
    payload = {
        "factors": {"temp": [20, 30], "pH": [6, 7, 8]},
        "mode": "full",
    }
    out = tool.run(json.dumps(payload))
    print("[DoEPlanner]", out[:200])


def test_lcms(csv_path: Path):
    tool = LCMSParserTool()
    payload = {
        "csv_path": str(csv_path),
        "transitions": [
            {"precursor_mz": 707.0, "product_mz": 425.0, "ppm": 10},
            {"precursor_mz": 673.0, "product_mz": 391.0, "ppm": 10},
        ],
    }
    out = tool.run(json.dumps(payload))
    print("[LCMSParser]", out)


def test_mzml_missing():
    tool = MzMLParserTool()
    payload = {"mzml_path": "results/dummy.mzML", "targets": [{"mz": 707.0, "ppm": 10}]}
    out = tool.run(json.dumps(payload))
    print("[MzMLParser]", out)


def test_otcoder_http():
    # 如果未启动 Otcoder FastAPI 服务，期望返回 HTTP 错误消息
    tool = OtcoderHTTPTool()
    payload = {
        "action": "generate_sop",
        "payload": {
            "hardware_config": "Robot Model: OT-2\nAPI Version: 2.19",
            "user_goal": "demo SOP",
        },
    }
    out = tool.run(json.dumps(payload))
    print("[OtcoderHTTP]", out[:300])


if __name__ == "__main__":
    # 1) DoE
    test_doe()

    # 2) LCMS (写入一个最小CSV并解析)
    csv_path = Path("results/smoke_mrm.csv")
    write_dummy_mrm_csv(csv_path)
    test_lcms(csv_path)

    # 3) mzML（无文件，验证错误路径处理）
    test_mzml_missing()

    # 4) Otcoder HTTP（若服务未启动，验证HTTP封装错误输出）
    test_otcoder_http()

    print("[SMOKE] done")



