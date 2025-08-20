from __future__ import annotations

from functools import lru_cache
from pydantic import BaseModel
import os
from dotenv import load_dotenv


class Settings(BaseModel):
    # Momentum Web Services
    momentum_url: str = os.getenv("MOMENTUM_URL", "https://localhost/api/")
    momentum_user: str | None = os.getenv("MOMENTUM_USER")
    momentum_passwd: str | None = os.getenv("MOMENTUM_PASSWD")
    momentum_verify: str | bool = os.getenv("MOMENTUM_VERIFY", "false")
    momentum_timeout: int = int(os.getenv("MOMENTUM_TIMEOUT", "5"))
    momentum_mock: bool = os.getenv("MOMENTUM_MOCK", "1").lower() in {"1", "true", "yes"}

    # LLM (ai190 OpenAI-compatible)
    ai190_api_key: str | None = os.getenv("AI190_API_KEY")
    ai190_base_url: str = os.getenv("AI190_BASE_URL", "https://api.ai190.com/v1")
    ai190_model: str = os.getenv("AI190_MODEL", "gemini-2.5-pro")

    # App
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Load .env once
    load_dotenv()
    return Settings()


