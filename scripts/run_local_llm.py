#!/usr/bin/env python3
"""
ローカル LLM（Ollama）自動化 CLI。

使い方（Mac・Ollama 起動後）:
  python3 scripts/run_local_llm.py doctor
  python3 scripts/run_local_llm.py x-post --draft docs/drafts/note-issue-04-free.txt
  python3 scripts/run_local_llm.py tone-check --draft docs/drafts/note-issue-04-free.txt
  python3 scripts/run_local_llm.py summarize --draft docs/drafts/note-issue-04-free.txt

Ollama 未導入環境でのテスト:
  OLLAMA_DRY_RUN=1 python3 scripts/run_local_llm.py x-post --draft docs/drafts/note-issue-04-free.txt
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from local_llm.client import OllamaClient, OllamaError  # noqa: E402
from local_llm.config import LocalLlmSettings  # noqa: E402
from local_llm.logging_util import log_event, setup_logging  # noqa: E402
from local_llm.tasks import check_tone, generate_x_post, summarize_draft  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--verbose", action="store_true", help="デバッグログを出す")
    shared.add_argument("--model", default=None, help="モデルタグ上書き（例: qwen2.5:14b）")
    shared.add_argument("--base-url", default=None, help="Ollama URL 上書き")
    shared.add_argument(
        "--dry-run",
        action="store_true",
        help="API を呼ばずプレースホルダを返す",
    )
    shared.add_argument(
        "--json",
        action="store_true",
        help="結果を JSON のみ stdout に出す（ログは stderr）",
    )

    p = argparse.ArgumentParser(
        description="Ollama ローカル LLM による週次コンテンツ自動化",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", parents=[shared], help="Ollama 接続とモデル有無を確認")

    xp = sub.add_parser("x-post", parents=[shared], help="無料下書きから X 投稿案を生成")
    xp.add_argument("--draft", required=True, type=Path, help="無料ダイジェスト txt")
    xp.add_argument("--free-url", default=None, help="投稿末尾に入れる無料 note URL")
    xp.add_argument("--issue", type=int, default=None, help="号数（任意）")
    xp.add_argument("-o", "--output", type=Path, default=None, help="結果 JSON の保存先")

    tc = sub.add_parser("tone-check", parents=[shared], help="投資助言口調のチェック")
    tc.add_argument("--draft", required=True, type=Path)
    tc.add_argument("-o", "--output", type=Path, default=None)

    sm = sub.add_parser("summarize", parents=[shared], help="下書きの短要約")
    sm.add_argument("--draft", required=True, type=Path)
    sm.add_argument("-o", "--output", type=Path, default=None)

    return p


def _client_from_args(args: argparse.Namespace) -> OllamaClient:
    settings = LocalLlmSettings.from_env(
        model=args.model,
        base_url=args.base_url,
        dry_run=True if args.dry_run else None,
    )
    if args.dry_run:
        settings = settings.model_copy(update={"dry_run": True})
    return OllamaClient(settings=settings)


def _emit(data: object, *, as_json: bool, output: Path | None) -> None:
    if hasattr(data, "model_dump"):
        payload = data.model_dump()  # type: ignore[attr-defined]
    elif isinstance(data, dict):
        payload = data
    else:
        payload = {"result": data}

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    if as_json or output is None:
        print(text)
    elif output is not None and not as_json:
        print(f"wrote {output}")


def cmd_doctor(client: OllamaClient, as_json: bool) -> int:
    health = client.health()
    _emit(health, as_json=as_json, output=None)
    if not health.get("ok"):
        return 2
    if not health.get("dry_run") and not health.get("model_present"):
        print(
            f"警告: 既定モデル `{client.settings.model}` が見つかりません。"
            f" `ollama pull {client.settings.model}` を実行してください。",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logger = setup_logging(verbose=args.verbose)
    client = _client_from_args(args)

    try:
        if args.command == "doctor":
            return cmd_doctor(client, as_json=args.json)

        if args.command == "x-post":
            result = generate_x_post(
                client,
                args.draft,
                free_url=args.free_url,
                issue=args.issue,
            )
            _emit(result, as_json=args.json, output=args.output)
            return 0

        if args.command == "tone-check":
            result = check_tone(client, args.draft)
            _emit(result, as_json=args.json, output=args.output)
            return 0 if result.ok else 1

        if args.command == "summarize":
            result = summarize_draft(client, args.draft)
            _emit(result, as_json=args.json, output=args.output)
            return 0

        parser.error(f"unknown command: {args.command}")
        return 2
    except FileNotFoundError as exc:
        log_event(logger, logging.ERROR, "file_missing", error=str(exc))
        print(f"エラー: {exc}", file=sys.stderr)
        return 2
    except OllamaError as exc:
        log_event(logger, logging.ERROR, "ollama_error", error=str(exc))
        print(f"エラー: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI 境界でユーザー向けに集約
        log_event(logger, logging.ERROR, "unexpected_error", error=str(exc))
        print(f"予期しないエラー: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
