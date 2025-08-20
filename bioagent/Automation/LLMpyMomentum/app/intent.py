from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import json
import re

from .config import get_settings
from .llm import chat as llm_chat


class Intent(BaseModel):
    action: str = Field(..., description="one of: start, simulate, stop, status, version, devices, nests, processes, workqueue, run_process")
    # common flags
    dry_run: bool = False

    # run_process params
    process_name: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    iterations: int = 1
    append: bool = True
    minimum_delay: int = 0
    workunit_name: Optional[str] = None


SYSTEM_PROMPT = (
    "你是一个严谨的解析器。把用户的自然语言意图解析为 JSON。只输出 JSON，不要多余文字。\n"
    "可用 action: start, simulate, stop, status, version, devices, nests, processes, workqueue, run_process。\n"
    "- 当用户请求运行进程（如：运行/执行/开始 进程X），使用 run_process，并解析变量与参数。\n"
    "- 变量可从自然语言中提取，如 a=1;b=2 或 列表用 ; 分隔。\n"
    "- 未明确参数时使用合理默认值。\n"
    "- 字段含义：{action, dry_run, process_name, variables, iterations, append, minimum_delay, workunit_name}.\n"
)


USER_TEMPLATE = (
    "用户输入:\n{query}\n"
    "严格输出 JSON，形如:\n"
    "{\n"
    "  \"action\": \"status\",\n"
    "  \"dry_run\": false\n"
    "}\n"
)


def _extract_json(text: str) -> str:
    # strip code fences
    s = text.strip()
    if s.startswith("```"):
        # ```json\n{...}\n```
        s = s.strip("`")
        parts = s.split("\n", 1)
        s = parts[1] if len(parts) > 1 else s
    # Try to find first {...} greedily, tolerate trailing tokens
    m = re.search(r"\{[\s\S]*\}", s)
    if m:
        return m.group(0)
    return s


def parse_intent(query: str) -> Intent:
    # If no API key, skip LLM
    if not get_settings().ai190_api_key:
        return parse_intent_rules(query)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(query=query)},
    ]
    try:
        out = llm_chat(messages, json_mode=True)
        js = _extract_json(out)
        data = json.loads(js)
        return Intent(**data)
    except Exception:
        return parse_intent_rules(query)


def parse_intent_rules(query: str) -> Intent:
    original = query.strip()
    t = original.lower()
    # quick detect for run_process intent
    if (
        "run process" in t
        or "运行进程" in t
        or "执行进程" in t
        or "运行流程" in t
        or "执行流程" in t
        or ("process" in t and ("run" in t or "start" in t or "执行" in t))
    ):
        process_name: Optional[str] = None
        variables: Dict[str, Any] = {}
        iterations: Optional[int] = None
        append: Optional[bool] = None
        minimum_delay: Optional[int] = None
        workunit_name: Optional[str] = None
        dry_run: bool = False

        def coerce_value(v: str) -> Any:
            vs = v.strip()
            # bools (en/zh)
            if vs.lower() in {"true", "yes", "y", "是", "真", "开启", "打开"}:
                return True
            if vs.lower() in {"false", "no", "n", "否", "假", "关闭"}:
                return False
            # ints
            if re.fullmatch(r"[-+]?\d+", vs):
                try:
                    return int(vs)
                except Exception:
                    pass
            # floats
            if re.fullmatch(r"[-+]?\d*\.\d+", vs):
                try:
                    return float(vs)
                except Exception:
                    pass
            return vs

        # 1) process name after keywords
        proc_pat = re.compile(
            r"(?:run\s+process|运行进程|执行进程|运行流程|执行流程)[:：]?\s*([^\s;，。:：,]+)",
            re.IGNORECASE,
        )
        m = proc_pat.search(original)
        if m:
            process_name = m.group(1).strip().strip(",.;，。:：")

        # 2) variables parsing from segment like "variables a=1;b=2" or "变量 a=1;b=2"
        var_pat = re.compile(
            r"(?:variables|变量)[:：]?\s*(.+?)(?=(?:\s+(?:iterations?|次数|迭代|append|追加|minimum[_-]?delay|min[_-]?delay|delay|最小间隔|延迟|workunit(?:_?name)?|工单|dry\s*-?\s*run))|$)",
            re.IGNORECASE,
        )
        vm = var_pat.search(original)
        if vm:
            var_str = vm.group(1)
            # split by ; , Chinese commas
            for token in re.split(r"[;，、,]", var_str):
                token = token.strip()
                if not token or "=" not in token:
                    continue
                k, v = token.split("=", 1)
                variables[k.strip()] = coerce_value(v)

        # 3) iterations / 次数
        it_m = re.search(r"(?:iterations?|次数|迭代)[:：]?\s*=?\s*(\d+)", t)
        if it_m:
            try:
                iterations = int(it_m.group(1))
            except Exception:
                iterations = None

        # 4) append / 追加
        # Chinese compact form like "追加否"
        if "追加否" in original:
            append = False
        elif "追加是" in original:
            append = True
        else:
            ap_m = re.search(r"(?:append)[:：]?\s*=?\s*([a-zA-Z]+)", original, re.IGNORECASE)
            if ap_m:
                append = bool(coerce_value(ap_m.group(1)))

        # 5) minimum_delay / delay / 最小间隔 / 延迟
        dl_m = re.search(r"(?:minimum[_-]?delay|min[_-]?delay|delay|最小间隔|延迟)[:：]?\s*=?\s*(\d+)", t)
        if dl_m:
            try:
                minimum_delay = int(dl_m.group(1))
            except Exception:
                minimum_delay = None

        # 6) workunit name / 工单
        wu_m = re.search(r"(?:workunit(?:_?name)?|工单)[:：]?\s*=?\s*([^\s;，。]+)", original, re.IGNORECASE)
        if wu_m:
            workunit_name = wu_m.group(1).strip().strip(",.;，。:：")

        # 7) dry-run hints
        if re.search(r"\b(dry\s*-?\s*run)\b", t) or any(k in t for k in ["试运行", "只计划", "计划但不执行", "不执行"]):
            dry_run = True

        return Intent(
            action="run_process",
            dry_run=dry_run,
            process_name=process_name,
            variables=variables,
            iterations=iterations or 1,
            append=True if append is None else append,
            minimum_delay=minimum_delay or 0,
            workunit_name=workunit_name,
        )
    if "simulate" in t or "仿真" in t:
        return Intent(action="simulate")
    if "start" in t or "启动" in t:
        return Intent(action="start")
    if "stop" in t or "停止" in t:
        return Intent(action="stop")
    if "version" in t or "版本" in t:
        return Intent(action="version")
    if "device" in t or "设备" in t:
        return Intent(action="devices")
    if "nest" in t or "库位" in t:
        return Intent(action="nests")
    if "workqueue" in t or "队列" in t:
        return Intent(action="workqueue")
    if "process" in t or "流程" in t or "进程" in t:
        return Intent(action="processes")
    if "status" in t or "状态" in t:
        return Intent(action="status")
    return Intent(action="status")




