from __future__ import annotations

import json
import time
from typing import Any, Dict

from langchain.tools import BaseTool
from neo4j import GraphDatabase


class KGWriteTool(BaseTool):
    """
    写入/更新 Neo4j 知识图谱（按用户要求，先保留硬编码连接）。

    输入(JSON或dict):
      {"op":"add_edge","data": {"head":"A","tail":"B","type":"REL","props":{...}}}
      {"op":"add_node","data": {"id":"A","props":{...}}}
    """

    name = "KGWrite"
    description = "写入/更新知识图谱：add_node/add_edge，包含溯源元数据。"

    # 按指示：Neo4j 先硬编码（可后续环境化）
    _URI = "neo4j+s://bb60f546.databases.neo4j.io:7687"
    _USER = "neo4j"
    _PWD = "sWFLqNrAjD50BrArVUhQHh3CKiPSH0qJnUPU0nW1BpQ"

    def _run(self, payload: str | Dict[str, Any]) -> str:
        try:
            p = json.loads(payload) if isinstance(payload, str) else payload
            op = (p.get("op") or "").lower()
            data = p.get("data") or {}
            if op not in ("add_node", "add_edge"):
                return "Error: op must be add_node or add_edge"

            driver = GraphDatabase.driver(self._URI, auth=(self._USER, self._PWD))
            with driver.session() as s:
                if op == "add_node":
                    node_id = data.get("id")
                    if not node_id:
                        return "Error: add_node requires data.id"
                    props = data.get("props") or {}
                    props.setdefault("created_at", int(time.time()))
                    cy = "MERGE (n{id:$id}) SET n += $props"
                    s.run(cy, id=node_id, props=props)
                    return "ok"

                # add_edge
                head = data.get("head")
                tail = data.get("tail")
                rel_type = data.get("type")
                if not (head and tail and rel_type):
                    return "Error: add_edge requires data.head, data.tail, data.type"
                props = data.get("props") or {}
                props.setdefault("created_at", int(time.time()))
                # 安全考虑：限制关系名只包含字母数字下划线
                if not rel_type.replace("_", "").isalnum():
                    return "Error: invalid relation type"
                cy = f"MERGE (a{{id:$h}}) MERGE (b{{id:$t}}) MERGE (a)-[r:{rel_type}]->(b) SET r += $props"
                s.run(cy, h=head, t=tail, props=props)
                return "ok"
        except Exception as e:
            return f"Error: {e}"

    async def _arun(self, payload: str) -> str:
        raise NotImplementedError("Async not implemented")



