"""Dynamic wrappers to expose Biomni tools as LangChain Tools.

This module imports functions from selected `Biomni/biomni/tool/*.py` modules
and wraps them as LangChain Tools. Inputs are accepted as JSON strings mapping
to the underlying Python function parameters.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
from typing import Any, Dict, List, get_args, get_origin

from langchain.tools import BaseTool


def _coerce_value(value: Any, annotation: Any) -> Any:
    """Convert a string value to the annotated type when possible.

    Supports: bool, int, float, list[str], list[int], list[float].
    Falls back to the original value if conversion is not applicable.
    """
    if annotation is inspect._empty or value is None:
        return value

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Basic scalars
    if annotation in (str,) or origin is str:
        return str(value)
    if annotation in (int,) or origin is int:
        try:
            return int(value)
        except Exception:
            return value
    if annotation in (float,) or origin is float:
        try:
            return float(value)
        except Exception:
            return value
    if annotation in (bool,) or origin is bool:
        s = str(value).strip().lower()
        if s in ("true", "1", "yes", "y", "t"):
            return True
        if s in ("false", "0", "no", "n", "f"):
            return False
        return value

    # Lists
    if origin in (list, List):
        # Try JSON array first
        if isinstance(value, str):
            v = value.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    return parsed
                except Exception:
                    pass
            # Comma-separated
            items = [x.strip() for x in v.split(",") if x.strip()]
        elif isinstance(value, list):
            items = value
        else:
            items = [value]

        # Coerce inner type if provided
        if args:
            inner = args[0]
            coerced: List[Any] = []
            for it in items:
                coerced.append(_coerce_value(it, inner))
            return coerced
        return items

    return value


def _build_tool(func) -> BaseTool:
    sig = inspect.signature(func)
    func_name = func.__name__
    doc = (func.__doc__ or "").strip() or f"Wrapped Biomni tool: {func_name}"

    class _Wrapped(BaseTool):
        name: str = f"biomni:{func_name}"
        description: str = doc

        def _run(self, tool_input: str) -> str:
            try:
                kwargs: Dict[str, Any]
                try:
                    kwargs = json.loads(tool_input) if tool_input else {}
                except Exception:
                    # Heuristic: if single str parameter, pass through
                    params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]
                    if len(params) == 1 and params[0].annotation in (str, inspect._empty):
                        kwargs = {params[0].name: tool_input}
                    else:
                        kwargs = {}

                # Type coercion for simple scalar/list types
                coerced: Dict[str, Any] = {}
                for name, param in sig.parameters.items():
                    if name in kwargs:
                        coerced[name] = _coerce_value(kwargs[name], param.annotation)

                bound = sig.bind_partial(**coerced)
                bound.apply_defaults()
                result = func(*bound.args, **bound.kwargs)
                if isinstance(result, (dict, list)):
                    return json.dumps(result, ensure_ascii=False)
                return str(result)
            except Exception as e:
                return f"Biomni tool '{func_name}' failed: {e}"

        async def _arun(self, tool_input: str) -> str:  # pragma: no cover
            raise NotImplementedError("Async not supported")

    return _Wrapped()


def make_biomni_wrapped_tools(whitelist_modules: List[str] | None = None) -> List[BaseTool]:
    """Create LangChain Tools wrapping Biomni tool functions.

    Args:
        whitelist_modules: module names under `biomni.tool` (e.g.,
            ["database", "literature", "biochemistry", "genetics"]).

    Returns:
        List[BaseTool]
    """
    if whitelist_modules is None:
        env_whitelist = os.getenv("BIOMNI_WHITELIST")
        if env_whitelist:
            whitelist_modules = [m.strip() for m in env_whitelist.split(",") if m.strip()]
        else:
            whitelist_modules = [
                "database",
                "literature",
                "biochemistry",
                "genetics",
                "bioengineering",
            ]

    tools: List[BaseTool] = []
    for mod in whitelist_modules:
        module_name = f"Biomni.biomni.tool.{mod}"
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue

        for attr in dir(module):
            if attr.startswith("_"):
                continue
            obj = getattr(module, attr)
            if callable(obj):
                try:
                    tools.append(_build_tool(obj))
                except Exception:
                    # Skip non-callables or complex signatures
                    continue

    # Add a help/registry tool for discoverability
    class _Help(BaseTool):
        name: str = "biomni:help"
        description: str = (
            "List available Biomni-wrapped tools and usage hints. "
            "Optionally filter by substring in tool name via JSON {\"filter\": \"text\"}."
        )

        def _run(self, tool_input: str) -> str:
            try:
                filt = ""
                if tool_input:
                    try:
                        obj = json.loads(tool_input)
                        if isinstance(obj, dict):
                            filt = str(obj.get("filter", "")).strip().lower()
                    except Exception:
                        filt = str(tool_input).strip().lower()

                lines: List[str] = []
                for t in tools:
                    if not getattr(t, "name", None):
                        continue
                    name = t.name
                    if filt and filt not in name.lower():
                        continue
                    desc = getattr(t, "description", "")
                    lines.append(f"- {name}: {desc}")
                if not lines:
                    return "No Biomni tools available."
                return "\n".join(lines)
            except Exception as e:
                return f"biomni:help failed: {e}"

        async def _arun(self, tool_input: str) -> str:  # pragma: no cover
            raise NotImplementedError

    tools.append(_Help())
    return tools


