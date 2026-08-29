"""週次コンテンツ向けのローカル LLM タスク。"""

from __future__ import annotations

from pathlib import Path

from local_llm.client import OllamaClient
from local_llm.schemas import SummaryResult, ToneCheckResult, XPostResult

DISCLAIMER_SYSTEM = (
    "あなたは株価調査メモの編集アシスタント。"
    "投資助言・買い推奨・売り推奨は絶対に書かない。"
    "断定的な将来予測や『今が買い』『必勝』などの表現を使わない。"
    "出力は指定フォーマットのみ。"
)


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"ファイルがありません: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"空ファイルです: {path}")
    return text


def generate_x_post(
    client: OllamaClient,
    draft_path: Path,
    *,
    free_url: str | None = None,
    issue: int | None = None,
) -> XPostResult:
    draft = _read_text(draft_path)
    url_line = free_url or "（公開後に無料URLを貼る）"
    issue_hint = f"第{issue}号" if issue is not None else "今週号"
    prompt = f"""
次の note 無料ダイジェストから、X（旧Twitter）投稿案を作ってください。

制約:
- 投資助言にしない（買う/売る/おすすめ銘柄、と読める表現禁止）
- 本投稿は日本語、280字以内
- 無料で読める範囲と有料の違いを短く示す
- URL は末尾に1つ: {url_line}
- {issue_hint} であることが分かれば十分

本文:
---
{draft[:6000]}
---
""".strip()
    return client.generate_json(prompt, XPostResult, system=DISCLAIMER_SYSTEM, temperature=0.4)


def check_tone(client: OllamaClient, draft_path: Path) -> ToneCheckResult:
    draft = _read_text(draft_path)
    prompt = f"""
次の記事原稿を、投資助言規制・プラットフォーム規約の観点でチェックしてください。

検出対象の例:
- 買い推奨・売り推奨
- 「今が買い」「必勝」「儲かる」などの煽り
- 断定的な価格予測
- 個人の資産状況に基づく助言に見える表現

問題がなければ issues は空配列、ok=true。
block は公開不可レベル、warn は修正推奨、info は任意改善。

本文:
---
{draft[:12000]}
---
""".strip()
    return client.generate_json(prompt, ToneCheckResult, system=DISCLAIMER_SYSTEM, temperature=0.1)


def summarize_draft(client: OllamaClient, draft_path: Path) -> SummaryResult:
    draft = _read_text(draft_path)
    prompt = f"""
次の調査メモを、非助言のまま短く要約してください。
bullets は3〜5個。銘柄名は最大3つまでに抑える。

本文:
---
{draft[:8000]}
---
""".strip()
    return client.generate_json(prompt, SummaryResult, system=DISCLAIMER_SYSTEM, temperature=0.2)
