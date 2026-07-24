"""Ollama HTTP クライアント（OpenAI 互換 + native generate）。"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .config import LocalLlmSettings
from .logging_util import log_event

T = TypeVar("T", bound=BaseModel)


class OllamaError(RuntimeError):
    """Ollama 呼び出し失敗。"""


class OllamaClient:
    def __init__(
        self,
        settings: LocalLlmSettings | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings or LocalLlmSettings.from_env()
        self.logger = logger or logging.getLogger("local_llm")

    def health(self) -> dict[str, Any]:
        if self.settings.dry_run:
            return {"ok": True, "dry_run": True, "models": [self.settings.model]}
        try:
            tags = self._request("GET", "/api/tags")
        except OllamaError as exc:
            return {"ok": False, "error": str(exc)}
        models = [m.get("name") for m in (tags.get("models") or []) if isinstance(m, dict)]
        return {
            "ok": True,
            "base_url": self.settings.base_url,
            "models": models,
            "default_model": self.settings.model,
            "model_present": self.settings.model in models
            or any(str(m).startswith(self.settings.model.split(":")[0]) for m in models),
        }

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        format_json: bool = False,
        dry_run_schema: str | None = None,
    ) -> str:
        if self.settings.dry_run:
            log_event(self.logger, logging.INFO, "dry_run_generate", model=model or self.settings.model)
            return self._dry_run_text(dry_run_schema or prompt, format_json=format_json)

        payload: dict[str, Any] = {
            "model": model or self.settings.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.settings.temperature if temperature is None else temperature,
                "num_ctx": self.settings.num_ctx,
            },
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"

        log_event(
            self.logger,
            logging.INFO,
            "ollama_generate_start",
            model=payload["model"],
            prompt_chars=len(prompt),
            format_json=format_json,
        )
        data = self._request("POST", "/api/generate", payload)
        text = str(data.get("response") or "").strip()
        if not text:
            raise OllamaError("Ollama から空のレスポンスが返りました")
        log_event(
            self.logger,
            logging.INFO,
            "ollama_generate_ok",
            model=payload["model"],
            response_chars=len(text),
        )
        return text

    def generate_json(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        retries: int = 1,
    ) -> T:
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        full_system = (
            (system or "")
            + "\n\n必ず有効な JSON オブジェクトのみを出力せよ。"
            + " 説明文・コードフェンスは禁止。"
            + f"\nJSON Schema:\n{schema_hint}"
        ).strip()

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            raw = self.generate(
                prompt,
                system=full_system,
                model=model,
                temperature=temperature,
                format_json=True,
                dry_run_schema=schema.__name__,
            )
            try:
                return self._parse_model(raw, schema)
            except (OllamaError, ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                log_event(
                    self.logger,
                    logging.WARNING,
                    "json_parse_retry",
                    attempt=attempt,
                    error=str(exc),
                )
        raise OllamaError(f"JSON スキーマ検証に失敗: {last_error}") from last_error

    def _parse_model(self, raw: str, schema: type[T]) -> T:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if not match:
                raise
            data = json.loads(match.group(0))
        return schema.model_validate(data)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.settings.base_url}{path}"
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.settings.timeout_sec) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"HTTP {exc.code} from Ollama ({path}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise OllamaError(
                "Ollama に接続できません。"
                f" `{self.settings.base_url}` で ollama serve が起動しているか確認してください"
                f"（原因: {exc.reason}）"
            ) from exc
        except TimeoutError as exc:
            raise OllamaError(
                f"Ollama が {self.settings.timeout_sec}s 以内に応答しませんでした"
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaError(f"Ollama の応答が JSON ではありません: {raw[:200]}") from exc
        if not isinstance(data, dict):
            raise OllamaError("Ollama の応答形式が不正です")
        return data

    def _dry_run_text(self, key: str, *, format_json: bool) -> str:
        if not format_json:
            return "[dry-run] local LLM 応答のプレースホルダです。"
        if key == "XPostResult":
            return json.dumps(
                {
                    "primary": "今週の調査メモを公開しました（非助言）。\n無料: Top5と動いた銘柄\n有料: Top20全文と差分（980円）",
                    "alternatives": ["今週号のダイジェストを公開（非助言）。詳細はnoteへ。"],
                    "hashtags": ["株式", "調査メモ"],
                    "notes": "dry-run のため固定文です",
                },
                ensure_ascii=False,
            )
        if key == "ToneCheckResult":
            return json.dumps(
                {
                    "ok": True,
                    "summary": "dry-run: 重大な助言口調は検出されませんでした",
                    "issues": [],
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "title": "dry-run 要約",
                "bullets": ["プレースホルダ1", "プレースホルダ2", "プレースホルダ3"],
                "one_liner": "ローカルLLM dry-run の要約です。",
            },
            ensure_ascii=False,
        )
