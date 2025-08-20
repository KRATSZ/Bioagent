from __future__ import annotations

import json
import os
from typing import Any, Dict

from langchain.tools import BaseTool


class LiteratureProcessorTool(BaseTool):
    """
    封装 Biomni biorxiv 抽取脚本为工具：按 subject/limit 处理并输出结果目录与汇总文件。

    输入(JSON或dict):
      {
        "subject": "bioinformatics",
        "limit": 10,
        "metadata_path": "(可选，默认使用脚本内部默认路径)",
        "output_dir": "(可选，默认在工作目录自动创建)"
      }

    输出: JSON，包含 output_dir、results_glob、summary_csv（如有）。
    """

    name = "LiteratureProcessor"
    description = "使用 Biomni 的 biorxiv 抽取流程批处理论文，输出结构化结果路径。"

    def _run(self, input_str: str | Dict[str, Any]) -> str:
        try:
            spec = json.loads(input_str) if isinstance(input_str, str) else input_str
            subject = (spec.get("subject") or "all").strip()
            limit = int(spec.get("limit", 10))
            metadata_path = spec.get("metadata_path")
            output_dir = spec.get("output_dir")

            # 直接调用脚本的 main 级函数不方便，这里动态导入并调用其内部函数
            import importlib.util
            import pathlib
            script_path = pathlib.Path(__file__).resolve().parents[1] / "Biomni" / "biomni" / "biorxiv_scripts" / "extract_biorxiv_tasks.py"
            if not script_path.exists():
                return "Error: extract_biorxiv_tasks.py not found"

            # 利用 runpy 执行不可控；这里改为导入并调用其函数
            # 该脚本定义了 process_papers 与 generate_summary，可复用
            import types
            import sys
            module_name = "_ba_biorxiv_extract"
            if module_name in sys.modules:
                del sys.modules[module_name]
            spec_mod = importlib.util.spec_from_file_location(module_name, str(script_path))
            mod = importlib.util.module_from_spec(spec_mod)  # type: ignore
            assert spec_mod and spec_mod.loader
            spec_mod.loader.exec_module(mod)  # type: ignore

            # 准备参数对象的替代：直接构造具有属性的简易对象
            class Args:
                pass
            args = Args()
            args.subject = subject
            args.limit = limit
            args.metadata_path = metadata_path or "/dfs/user/kexinh/BioAgentOS/data/biorxiv_metadata.csv"
            args.output_dir = output_dir
            args.model = "claude-3-haiku-20240307"
            args.chunk_size = 4000
            args.chunk_overlap = 400
            args.max_paper_length = 35000
            args.random_sample = True
            args.save_pdfs = False

            # 对齐脚本 main 中的逻辑
            if args.output_dir is None:
                clean_subject = args.subject.lower().replace(" ", "_").replace("/", "_")
                args.output_dir = f"./biorxiv_results_{clean_subject}_{args.limit}"

            os.makedirs(args.output_dir, exist_ok=True)
            os.makedirs(os.path.join(args.output_dir, "results"), exist_ok=True)

            papers_df = mod.load_papers_from_csv(args.metadata_path, args.subject, args.limit, args.random_sample)
            if len(papers_df) == 0:
                return json.dumps({"output_dir": args.output_dir, "results": [], "summary_path": None})

            res = mod.process_papers(papers_df, args)
            mod.generate_summary(res, args.output_dir)

            # 约定输出
            summary_csv = os.path.join(args.output_dir, "summary.csv")
            if not os.path.exists(summary_csv):
                summary_csv = None

            return json.dumps({
                "output_dir": args.output_dir,
                "results_dir": os.path.join(args.output_dir, "results"),
                "summary_path": summary_csv
            }, ensure_ascii=False)
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, input_str: str) -> str:
        raise NotImplementedError("Async not implemented")



