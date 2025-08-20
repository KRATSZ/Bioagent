from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd
from langchain.tools import BaseTool
from langchain.llms import BaseLLM
import numpy as np
import warnings


class LCMSParserTool(BaseTool):
    """
    解析 LC-MS/MS (MRM) 导出表格，按给定过渡(precursor/product)聚合峰面积或强度。

    输入(JSON字符串或字典):
      {
        "csv_path": "path/to/file.csv",
        "transitions": [
          {"precursor_mz": 707.0, "product_mz": 425.0, "ppm": 10},
          {"precursor_mz": 673.0, "product_mz": 391.0, "ppm": 10}
        ],
        "rt_window": [min_rt, max_rt]  # 可选，单位分钟
      }

    输出: JSON 字符串，包含匹配到的峰及聚合度量。
    """

    name = "LCMSParser"
    description = "解析LC-MS MRM CSV并按过渡汇总峰面积/强度，支持ppm容差和保留时间窗口过滤。"

    def _run(self, input_str: str | Dict[str, Any]) -> str:
        try:
            spec = json.loads(input_str) if isinstance(input_str, str) else input_str
            csv_path: str = spec.get("csv_path")
            if not csv_path:
                return "Error: csv_path is required"

            transitions: List[Dict[str, Any]] = spec.get("transitions", [])
            if not transitions:
                return "Error: transitions is required"

            rt_window = spec.get("rt_window")  # e.g., [0.5, 12.0]

            # 支持常见导出（CSV/TSV）
            if csv_path.lower().endswith(".tsv"):
                df = pd.read_csv(csv_path, sep="\t")
            else:
                df = pd.read_csv(csv_path)

            # 尝试通用列对齐
            col_map = self._detect_columns(df.columns.tolist())
            if col_map is None:
                return "Error: cannot detect necessary columns (Q1/Q3 or Precursor/Product, RT, Area/Height)."

            # 标准化列名视图
            def _to_float_series(s):
                try:
                    return s.astype(float)
                except Exception:
                    return pd.to_numeric(s, errors="coerce")

            q1 = _to_float_series(df[col_map["precursor"]])
            q3 = _to_float_series(df[col_map["product"]])
            area_series = _to_float_series(df[col_map["area"]])
            rt_series = _to_float_series(df[col_map["rt"]]) if col_map.get("rt") else None
            # 丢弃无效行
            valid_mask = (~q1.isna()) & (~q3.isna()) & (~area_series.isna())
            if rt_series is not None:
                valid_mask = valid_mask & (~rt_series.isna())
            df = df.loc[valid_mask]
            q1 = q1.loc[valid_mask]
            q3 = q3.loc[valid_mask]
            area_series = area_series.loc[valid_mask]
            rt_series = rt_series.loc[valid_mask] if rt_series is not None else None

            results: List[Dict[str, Any]] = []
            for t in transitions:
                pmz = float(t.get("precursor_mz"))
                fz = float(t.get("product_mz"))
                ppm = float(t.get("ppm", 10.0))

                # ppm窗口
                q1_tol = pmz * ppm / 1e6
                q3_tol = fz * ppm / 1e6
                mask = (q1.between(pmz - q1_tol, pmz + q1_tol)) & (q3.between(fz - q3_tol, fz + q3_tol))
                if rt_series is not None and isinstance(rt_window, list) and len(rt_window) == 2:
                    mask = mask & rt_series.between(float(rt_window[0]), float(rt_window[1]))

                sub = df.loc[mask]
                if sub.empty:
                    results.append({
                        "precursor_mz": pmz,
                        "product_mz": fz,
                        "n_peaks": 0,
                        "sum_area": 0.0,
                        "max_area": 0.0,
                        "best_rt": None
                    })
                    continue

                # 选择面积列
                area_vals = sub[col_map["area"]].astype(float)
                best_idx = area_vals.idxmax()
                best_rt = float(sub.loc[best_idx, col_map["rt"]]) if col_map.get("rt") else None

                results.append({
                    "precursor_mz": pmz,
                    "product_mz": fz,
                    "n_peaks": int(sub.shape[0]),
                    "sum_area": float(area_vals.sum()),
                    "max_area": float(area_vals.max()),
                    "best_rt": best_rt
                })

            return json.dumps({"results": results}, ensure_ascii=False)
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, input_str: str) -> str:
        raise NotImplementedError("Async not implemented")

    @staticmethod
    def _detect_columns(cols: List[str]) -> Optional[Dict[str, str]]:
        lower = {c.lower(): c for c in cols}
        # 常见列名映射
        candidates = [
            {
                "precursor": ["q1", "precursor", "precursormz", "parent", "parentmz"],
                "product": ["q3", "product", "productmz", "fragment", "fragmentmz"],
                "area": ["area", "peak area", "intensity", "height"],
                "rt": ["rt", "retention time", "rt(min)", "time"]
            }
        ]
        for cand in candidates:
            mapping: Dict[str, str] = {}
            ok = True
            for key, names in cand.items():
                found = None
                for n in names:
                    if n in lower:
                        found = lower[n]
                        break
                if key in ("rt",):
                    # 可选
                    mapping[key] = found if found else None
                else:
                    if not found:
                        ok = False
                        break
                    mapping[key] = found
            if ok:
                return mapping
        return None


class CFMIDPredictorTool(BaseTool):
    """
    使用 CFM-ID 进行 MS/MS 碎片预测。

    输入(JSON字符串或字典):
      {
        "smiles": "C[C@H](O)C(=O)O...",
        "adduct": "[M+H]+" | "[M-H]-" (可选),
        "energies": [10,20,40] (可选),
        "charge": 1 或 -1 (可选)
      }

    输出: 预测谱图(若库可用)，否则返回安装提示与错误信息。
    """

    name = "CFMIDPredictor"
    description = "调用 CFM-ID 预测质谱碎片。需要 pip 安装 cfm-id。"

    def _run(self, input_str: str | Dict[str, Any]) -> str:
        spec = json.loads(input_str) if isinstance(input_str, str) else input_str
        smiles = spec.get("smiles")
        if not smiles:
            return "Error: smiles is required"
        adduct = spec.get("adduct", "[M+H]+")
        energies = spec.get("energies", [10, 20, 40])
        charge = int(spec.get("charge", 1))

        # 尝试多种导入方式，兼容不同发布形态
        try:
            # 常见封装：cfm_id 包
            import cfm_id  # type: ignore
        except Exception as e:
            return (
                "Error: cfm-id not installed. Please install with 'pip install cfm-id'."
                f" Details: {e}"
            )

        # 逐步尝试可能的API
        try:
            # 假设存在高级便捷函数
            if hasattr(cfm_id, "predict_spectrum"):
                pred = cfm_id.predict_spectrum(smiles=smiles, adduct=adduct, energies=energies, charge=charge)  # type: ignore
                return json.dumps({"predicted": pred}, ensure_ascii=False)

            # 假设存在类接口 CfmId
            if hasattr(cfm_id, "CfmId"):
                C = getattr(cfm_id, "CfmId")
                c = C()  # 某些实现支持无参构造，若需要模型路径会抛错
                out = c.predict(smiles)  # type: ignore
                return json.dumps({"predicted": out}, ensure_ascii=False)

            # 未找到已知接口
            return (
                "Error: cfm-id package found but API is unknown. Please check the package docs."
            )
        except Exception as e:
            return f"Error: CFM-ID prediction failed: {e}"


class MzMLParserTool(BaseTool):
    """
    解析 mzML 文件，抽取指定 m/z±ppm 与保留时间窗口的峰强度/总离子流等指标。

    输入(JSON或dict):
      {
        "mzml_path": "path/to/file.mzML",
        "targets": [ {"mz": 707.0, "ppm": 10, "rt_window": [min,max]} ],
        "tic": true  # 可选，返回 TIC
      }

    输出: JSON {"peaks": [...], "tic": [...]}。
    """

    name = "MzMLParser"
    description = "解析 mzML（pymzML/pyteomics），按 m/z±ppm 与 RT 窗口聚合强度。"

    def _run(self, input_str: str | Dict[str, Any]) -> str:
        try:
            spec = json.loads(input_str) if isinstance(input_str, str) else input_str
            path = spec.get("mzml_path")
            if not path:
                return "Error: mzml_path is required"
            targets = spec.get("targets", [])
            want_tic = bool(spec.get("tic", False))

            # 优先使用 pymzML，失败则回退 pyteomics
            peaks_out: List[Dict[str, Any]] = []
            tic_out: List[Dict[str, float]] = []
            used = None
            try:
                import pymzml
                used = "pymzml"
                run = pymzml.run.Reader(path)
                for t in targets:
                    mz = float(t.get("mz"))
                    ppm = float(t.get("ppm", 10.0))
                    mz_tol = mz * ppm / 1e6
                    rt_min, rt_max = None, None
                    if isinstance(t.get("rt_window"), list) and len(t["rt_window"]) == 2:
                        rt_min = float(t["rt_window"][0])
                        rt_max = float(t["rt_window"][1])
                    total = 0.0
                    max_i = 0.0
                    best_rt = None
                    for spec_ms in run:
                        rt = spec_ms.scan_time_in_minutes() if hasattr(spec_ms, "scan_time_in_minutes") else None
                        if rt is not None and rt_min is not None and (rt < rt_min or rt > rt_max):
                            continue
                        for mzi, inten in spec_ms.peaks("raw"):  # type: ignore
                            if (mzi >= mz - mz_tol) and (mzi <= mz + mz_tol):
                                total += float(inten)
                                if inten > max_i:
                                    max_i = float(inten)
                                    best_rt = rt
                    peaks_out.append({"mz": mz, "ppm": ppm, "sum_intensity": total, "max_intensity": max_i, "best_rt": best_rt, "engine": used})
                if want_tic:
                    for spec_ms in pymzml.run.Reader(path):
                        rt = spec_ms.scan_time_in_minutes() if hasattr(spec_ms, "scan_time_in_minutes") else None
                        if rt is None:
                            continue
                        tic_out.append({"rt": float(rt), "tic": float(sum(i for _, i in spec_ms.peaks("raw")))})
            except Exception:
                import pyteomics.mzml as mzml
                used = "pyteomics"
                with mzml.MzML(path) as reader:
                    for t in targets:
                        mz = float(t.get("mz"))
                        ppm = float(t.get("ppm", 10.0))
                        mz_tol = mz * ppm / 1e6
                        rt_min, rt_max = None, None
                        if isinstance(t.get("rt_window"), list) and len(t["rt_window"]) == 2:
                            rt_min = float(t["rt_window"][0])
                            rt_max = float(t["rt_window"][1])
                        total = 0.0
                        max_i = 0.0
                        best_rt = None
                        for spec_ms in reader:
                            rt = float(spec_ms.get("scanList", {}).get("scan", [{}])[0].get("scan start time", 0.0))
                            if rt_min is not None and (rt < rt_min or rt > rt_max):
                                continue
                            mzs = np.array(spec_ms.get("m/z array", []), dtype=float)
                            ints = np.array(spec_ms.get("intensity array", []), dtype=float)
                            if mzs.size == 0:
                                continue
                            mask = (mzs >= mz - mz_tol) & (mzs <= mz + mz_tol)
                            if not mask.any():
                                continue
                            s = float(ints[mask].sum())
                            m = float(ints[mask].max())
                            total += s
                            if m > max_i:
                                max_i = m
                                best_rt = rt
                        peaks_out.append({"mz": mz, "ppm": ppm, "sum_intensity": total, "max_intensity": max_i, "best_rt": best_rt, "engine": used})
                    if want_tic:
                        with mzml.MzML(path) as reader2:
                            for spec_ms in reader2:
                                rt = float(spec_ms.get("scanList", {}).get("scan", [{}])[0].get("scan start time", 0.0))
                                ints = np.array(spec_ms.get("intensity array", []), dtype=float)
                                if ints.size:
                                    tic_out.append({"rt": float(rt), "tic": float(ints.sum())})

            return json.dumps({"peaks": peaks_out, "tic": tic_out if want_tic else None}, ensure_ascii=False)
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, input_str: str) -> str:
        raise NotImplementedError("Async not implemented")

    async def _arun(self, input_str: str) -> str:
        raise NotImplementedError("Async not implemented")


class HypothesisVerifierTool(BaseTool):
    """
    使用 LLM 对“假设 vs. 实验证据(解析后的LC-MS结果/CFM-ID预测)”进行对照判定。

    输入(JSON字符串或字典):
      {
        "hypothesis": "mPlsC 可以催化 GGGP + acyl-CoA → iaPA",
        "observations": {...},    # 由 LCMSParserTool 输出/人工整理
        "predictions": {...}      # 由 CFMIDPredictorTool 输出（可选）
      }

    输出: JSON，包含 support(yes/no/uncertain)、score(0-1)、rationale。
    """

    name = "HypothesisVerifier"
    description = "对比实验观测与(可选)预测，输出对假设的支持度与理由(结构化)。"
    llm: BaseLLM = None  # 注入

    def __init__(self, llm: BaseLLM):
        super().__init__()
        self.llm = llm

    def _run(self, input_str: str | Dict[str, Any]) -> str:
        try:
            payload = json.loads(input_str) if isinstance(input_str, str) else input_str
            hypothesis = payload.get("hypothesis", "").strip()
            observations = payload.get("observations")
            predictions = payload.get("predictions")
            if not hypothesis:
                return "Error: hypothesis is required"

            prompt = (
                "You are an expert mass-spectrometry analyst.\n"
                "Task: Compare the experimental observations with optional predictions to assess whether the hypothesis is supported.\n"
                "Return a strict JSON with keys: support(one of 'yes','no','uncertain'), score(float 0-1), rationale(short).\n\n"
                f"Hypothesis: {hypothesis}\n\n"
                f"Observations(JSON): {json.dumps(observations, ensure_ascii=False)}\n\n"
                f"Predictions(JSON): {json.dumps(predictions, ensure_ascii=False)}\n\n"
                "Make a conservative judgment and avoid overclaiming."
            )

            resp = self.llm.predict(prompt)
            # 容错：若不是严格JSON，尽量抽取
            data = None
            try:
                data = json.loads(resp)
            except Exception:
                # 简单提取
                resp_str = resp.strip()
                start = resp_str.find("{")
                end = resp_str.rfind("}")
                if start != -1 and end != -1 and end > start:
                    data = json.loads(resp_str[start : end + 1])
            if not isinstance(data, dict):
                data = {"support": "uncertain", "score": 0.5, "rationale": "LLM returned non-JSON; defaulted."}
            # 规范化
            support = str(data.get("support", "uncertain")).lower()
            if support not in ("yes", "no", "uncertain"):
                support = "uncertain"
            score = float(data.get("score", 0.5))
            rationale = str(data.get("rationale", ""))
            return json.dumps({"support": support, "score": score, "rationale": rationale}, ensure_ascii=False)
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, input_str: str) -> str:
        raise NotImplementedError("Async not implemented")


