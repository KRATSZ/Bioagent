"""
LightRAG client wrapper used by backend agents to index and retrieve code/protocol snippets.

It uses the embedded LightRAG library directly (no separate HTTP server). Provide minimal
helpers for indexing a list of documents and performing top-k queries.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List

# Import LightRAG local package
from lightrag.lightrag import LightRAG
from lightrag.base import QueryParam


class LightRAGClient:
    def __init__(self, working_dir: str | None = None) -> None:
        self.working_dir = working_dir or str(Path(".rag_storage").absolute())
        self.rag = LightRAG(working_dir=self.working_dir)

    def index_files(self, paths: Iterable[str]) -> str:
        """Index the given files/folders into LightRAG storage."""
        contents: List[str] = []
        for p in paths:
            pth = Path(p)
            if pth.is_file():
                contents.append(pth.read_text(encoding="utf-8", errors="ignore"))
            elif pth.is_dir():
                for fp in pth.rglob("*"):
                    if fp.is_file() and fp.suffix.lower() in {".py", ".md", ".txt", ".json", ".tsx", ".ts"}:
                        try:
                            contents.append(fp.read_text(encoding="utf-8", errors="ignore"))
                        except Exception:
                            pass
        if not contents:
            return "no-input"
        track_id = self.rag.insert(contents)
        return track_id

    def topk(self, query: str, k: int = 5) -> str:
        param = QueryParam(top_k=k)
        return self.rag.query(query, param)





