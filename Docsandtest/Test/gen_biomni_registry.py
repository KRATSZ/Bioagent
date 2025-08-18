import json
from typing import Any, Dict, List

from bioagent.tools.biomni_wrappers import make_biomni_wrapped_tools


def build_registry() -> List[Dict[str, Any]]:
    tools = make_biomni_wrapped_tools()
    reg: List[Dict[str, Any]] = []
    for t in tools:
        name = getattr(t, "name", "")
        if not name or name == "biomni:help":
            continue
        desc = getattr(t, "description", "")
        item = {
            "name": name,
            "description": desc,
        }
        reg.append(item)
    return sorted(reg, key=lambda x: x["name"])


def main():
    reg = build_registry()
    with open("results/biomni_tools.json", "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(reg)} tools to results/biomni_tools.json")


if __name__ == "__main__":
    main()


