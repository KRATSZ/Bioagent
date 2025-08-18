import json

from bioagent.tools.biomni_wrappers import make_biomni_wrapped_tools


def find_tool(tools, name):
    for t in tools:
        if getattr(t, "name", None) == name:
            return t
    return None


def test_biomni_help():
    tools = make_biomni_wrapped_tools(
        whitelist_modules=["database", "literature", "biochemistry", "genetics"]
    )
    help_tool = find_tool(tools, "biomni:help")
    assert help_tool is not None
    out = help_tool.run(json.dumps({"filter": "bio"}))
    assert isinstance(out, str)


def test_biomni_example_call():
    tools = make_biomni_wrapped_tools(
        whitelist_modules=["database", "literature"]
    )
    # 简单地挑一个工具名包含 'literature' 的函数进行 smoke test（如果存在）
    lit_tool = None
    for t in tools:
        if getattr(t, "name", "").startswith("biomni:") and "literature" in getattr(t, "description", "").lower():
            lit_tool = t
            break
    if lit_tool is None:
        return
    # 传入字符串参数，验证字符串→JSON/类型转换不报错
    _ = lit_tool.run("search terms")


