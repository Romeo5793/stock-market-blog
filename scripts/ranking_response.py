#!/usr/bin/env python3
"""Gemini ランキング JSON の正規化・リトライ・市場分離ヘルパ。

stock-marketing-bot の Morning blog sync / ranking refresh 向け。
Gemini が root 配列を返すと「オブジェクト形式ではない」で落ちるため、
配列は ranking20 として受理し、非オブジェクトは短いリトライ後に市場単位で失敗させる。

stock-marketing-bot への組み込み例::

    from ranking_response import fetch_ranking_with_retries, sync_markets_independently

    def refresh_one(market: str) -> dict:
        return fetch_ranking_with_retries(
            lambda: call_gemini_ranking(market),  # dict / list / JSON str
            market=market,
            retries=2,
        )

    def blog_sync_rankings(prev_us: dict, prev_jp: dict) -> dict:
        def run(market: str):
            def _run():
                data = refresh_one(market)
                publish_ranking(market, data)  # 成功時のみ上書き
                return data
            return _run

        result = sync_markets_independently(
            {"jp": run("jp"), "us": run("us")},
            on_failure=lambda m, exc: keep_previous_cache(m),  # 失敗市場は触らない
        )
        # JP 成功・US 失敗でも result["partial"] で続行（exit 0）
        if result["all_failed"]:
            raise SystemExit(1)
        return result
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")

NOT_OBJECT_ERROR = "JSON は解析できましたが、オブジェクト形式ではありませんでした。"


class RankingResponseError(ValueError):
    """ランキング JSON が受理できないときのエラー。"""


def coerce_ranking_payload(data: Any, *, market: str | None = None) -> dict[str, Any]:
    """Gemini / ファイル由来の JSON をランキングオブジェクトへ正規化する。

    - dict: そのまま（ranking20 が無ければ空配列を補完）
    - list: {"ranking20": list, ...} として受理
    - それ以外: RankingResponseError
    """
    if isinstance(data, list):
        out: dict[str, Any] = {"ranking20": data}
        if market:
            out.setdefault("market", market)
        return out

    if isinstance(data, dict):
        out = dict(data)
        if "ranking20" not in out:
            # 単一キーが配列だけの包み直しも許容
            if len(out) == 1:
                only = next(iter(out.values()))
                if isinstance(only, list):
                    out = {"ranking20": only}
                    if market:
                        out.setdefault("market", market)
                    return out
            out["ranking20"] = []
        elif not isinstance(out["ranking20"], list):
            raise RankingResponseError(
                f"ranking20 は配列である必要があります（got {type(out['ranking20']).__name__}）"
            )
        if market and "market" not in out:
            out["market"] = market
        return out

    raise RankingResponseError(NOT_OBJECT_ERROR)


def parse_ranking_json_text(text: str, *, market: str | None = None) -> dict[str, Any]:
    """JSON 文字列をパースして coerce_ranking_payload する。"""
    raw = text.strip()
    if raw.startswith("```"):
        # ```json ... ``` を剥がす
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    data = json.loads(raw)
    return coerce_ranking_payload(data, market=market)


def load_ranking_document(path_text: str, *, market: str | None = None) -> dict[str, Any]:
    """ファイル内容（文字列）または既に読んだ JSON テキストをランキング dict にする。"""
    return parse_ranking_json_text(path_text, market=market)


def fetch_ranking_with_retries(
    fetch_once: Callable[[], Any],
    *,
    market: str | None = None,
    retries: int = 2,
    sleep_s: float = 0.0,
) -> dict[str, Any]:
    """fetch_once が JSON 互換値（dict/list/str）を返す前提で、非オブジェクトならリトライする。

    retries=2 なら初回 + 最大2回再試行（合計最大3回）。
    """
    attempts = max(0, int(retries)) + 1
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            payload = fetch_once()
            if isinstance(payload, str):
                return parse_ranking_json_text(payload, market=market)
            return coerce_ranking_payload(payload, market=market)
        except (RankingResponseError, json.JSONDecodeError, TypeError, ValueError) as exc:
            last_exc = exc
            # オブジェクト形式以外・パース失敗のみリトライ
            if i + 1 >= attempts:
                break
            if sleep_s > 0:
                time.sleep(sleep_s)
    assert last_exc is not None
    raise last_exc


def sync_markets_independently(
    markets: dict[str, Callable[[], T]],
    *,
    on_success: Callable[[str, T], None] | None = None,
    on_failure: Callable[[str, Exception], None] | None = None,
) -> dict[str, Any]:
    """市場ごとに独立実行し、一部失敗でも全体を落とさない。

    戻り値:
      {
        "ok": [market, ...],
        "failed": {market: error_message, ...},
        "partial": bool,  # 1つ以上成功かつ1つ以上失敗
        "all_failed": bool,
      }
    """
    ok: list[str] = []
    failed: dict[str, str] = {}
    for name, runner in markets.items():
        try:
            result = runner()
            ok.append(name)
            if on_success:
                on_success(name, result)
        except Exception as exc:  # noqa: BLE001 — 市場分離のため握って記録
            failed[name] = str(exc)
            if on_failure:
                on_failure(name, exc)
    return {
        "ok": ok,
        "failed": failed,
        "partial": bool(ok) and bool(failed),
        "all_failed": not ok and bool(failed),
    }
