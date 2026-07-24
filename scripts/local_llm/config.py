"""環境変数 / CLI から読むローカル LLM 設定。"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator


class LocalLlmSettings(BaseModel):
    """Ollama 接続と既定モデルの設定。"""

    base_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama API のベース URL",
    )
    model: str = Field(
        default="qwen2.5:14b",
        description="既定モデルタグ（ollama list の名前と一致させる）",
    )
    timeout_sec: float = Field(default=180.0, ge=5.0, le=1800.0)
    num_ctx: int = Field(default=16384, ge=2048, le=131072)
    temperature: float = Field(default=0.3, ge=0.0, le=1.5)
    dry_run: bool = Field(
        default=False,
        description="True なら API を呼ばず固定レスポンスを返す（テスト用）",
    )

    @field_validator("base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @classmethod
    def from_env(cls, **overrides: object) -> LocalLlmSettings:
        data: dict[str, object] = {
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            "model": os.getenv("OLLAMA_MODEL", "qwen2.5:14b"),
            "timeout_sec": float(os.getenv("OLLAMA_TIMEOUT_SEC", "180")),
            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "16384")),
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.3")),
            "dry_run": os.getenv("OLLAMA_DRY_RUN", "").lower() in {"1", "true", "yes"},
        }
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls.model_validate(data)


@lru_cache(maxsize=1)
def get_settings() -> LocalLlmSettings:
    return LocalLlmSettings.from_env()
