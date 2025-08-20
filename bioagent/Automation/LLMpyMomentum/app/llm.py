from __future__ import annotations

from typing import Any, Dict, List, Optional
from openai import OpenAI

from .config import get_settings


def create_openai() -> OpenAI:
    settings = get_settings()
    api_key = settings.ai190_api_key or ""
    base_url = settings.ai190_base_url
    return OpenAI(api_key=api_key, base_url=base_url)


def chat(messages: List[Dict[str, str]], *, json_mode: bool = False) -> str:
    client = create_openai()
    model = get_settings().ai190_model
    kwargs: Dict[str, Any] = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
    return resp.choices[0].message.content or ""




