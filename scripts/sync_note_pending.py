#!/usr/bin/env python3
"""
Mac ローカル: リポジトリを同期し、note 下書きの pending を検知する。

使い方:
  python3 scripts/sync_note_pending.py           # pull + 検知（通知用メッセージを stdout）
  python3 scripts/sync_note_pending.py --json    # JSON で結果
  python3 scripts/sync_note_pending.py --mark-published  # 公開後に status=published
  python3 scripts/sync_note_pending.py --mark-published --free-url 'https://note.com/...'
  python3 scripts/sync_note_pending.py --llm-check --notify --open-ready
  python3 scripts/sync_note_pending.py --no-pull # 同期せず検知のみ

終了コード:
  0 = pending あり（公開待ち）
  1 = pending なし / エラー以外の「やる事なし」
  2 = エラー
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
PENDING = ROOT / "docs" / "drafts" / "pending"
MANIFEST = PENDING / "manifest.json"
READY = PENDING / "READY_FOR_AGENT.md"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def git_pull() -> str:
    # Fast-forward only to avoid surprise merges on the agent machine
    fetch = run_git(["fetch", "origin", "main"])
    if fetch.returncode != 0:
        return f"fetch failed: {fetch.stderr.strip() or fetch.stdout.strip()}"
    pull = run_git(["pull", "--ff-only", "origin", "main"])
    if pull.returncode != 0:
        return f"pull failed: {pull.stderr.strip() or pull.stdout.strip()}"
    return (pull.stdout or "").strip() or "up to date"


def load_manifest() -> dict[str, Any] | None:
    if not MANIFEST.exists():
        return None
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def save_manifest(manifest: dict[str, Any]) -> None:
    PENDING.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _draft_path(rel: str) -> Path:
    return ROOT / rel if rel and not rel.startswith("/") else Path(rel)


def _tone_check_path(issue: Any) -> Path:
    return PENDING / f"tone-check-issue-{issue}.json"


def _x_post_path(issue: Any) -> Path:
    return PENDING / f"x-post-issue-{issue}.json"


def run_llm_tone_checks(manifest: dict[str, Any]) -> dict[str, Any]:
    """無料・有料原稿の tone-check を実行し、結果 JSON を保存する。"""
    from local_llm.client import OllamaClient, OllamaError
    from local_llm.tasks import check_tone

    issue = manifest.get("issue")
    free_rel = str(manifest.get("free_path") or "")
    paid_rel = str(manifest.get("paid_path") or "")
    out: dict[str, Any] = {
        "issue": issue,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "ok": True,
        "free": None,
        "paid": None,
        "error": None,
    }

    client = OllamaClient()
    health = client.health()
    if not health.get("ok"):
        out["ok"] = False
        out["error"] = health.get("error") or "Ollama に接続できません"
        return out
    if not health.get("dry_run") and not health.get("model_present"):
        out["ok"] = False
        out["error"] = f"モデル `{client.settings.model}` がありません。ollama pull を実行してください。"
        return out

    for key, rel in (("free", free_rel), ("paid", paid_rel)):
        if not rel:
            continue
        path = _draft_path(rel)
        try:
            result = check_tone(client, path)
            payload = result.model_dump()
            out[key] = payload
            if not result.ok:
                out["ok"] = False
        except (FileNotFoundError, ValueError, OllamaError) as exc:
            out["ok"] = False
            out[key] = {"ok": False, "summary": str(exc), "issues": []}
            out["error"] = str(exc)

    tone_path = _tone_check_path(issue)
    tone_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out["tone_check_path"] = str(tone_path)
    return out


def format_tone_check_section(llm: dict[str, Any] | None) -> str:
    if not llm:
        return ""
    if llm.get("error") and not llm.get("free") and not llm.get("paid"):
        return f"""## ローカル LLM トーンチェック（自動）

⚠️ {llm["error"]}

手動実行:
```bash
cd {ROOT}
python3 scripts/run_local_llm.py tone-check --draft docs/drafts/note-issue-XX-free.txt
```
"""

    lines = [
        "## ローカル LLM トーンチェック（自動）",
        "",
        "| 原稿 | 結果 |",
        "|------|------|",
    ]
    for key, label in (("free", "無料"), ("paid", "有料")):
        block = llm.get(key)
        if not block:
            continue
        icon = "✅ OK" if block.get("ok") else "⚠️ 要確認"
        lines.append(f"| {label} | {icon} |")
    lines.append("")

    for key, label in (("free", "無料"), ("paid", "有料")):
        block = llm.get(key)
        if not block or block.get("ok"):
            continue
        issues = block.get("issues") or []
        if not issues:
            lines.append(f"### {label}原稿")
            lines.append(f"- {block.get('summary', '要確認')}")
            lines.append("")
            continue
        lines.append(f"### {label}原稿の指摘")
        for item in issues:
            sev = item.get("severity", "warn")
            quote = item.get("quote", "")
            reason = item.get("reason", "")
            suggestion = item.get("suggestion", "")
            lines.append(f"- **{sev}**: 「{quote}」— {reason}")
            if suggestion:
                lines.append(f"  - 言い換え案: {suggestion}")
        lines.append("")

    if path := llm.get("tone_check_path"):
        lines.append(f"詳細: `{path}`")
        lines.append("")

    if not llm.get("ok"):
        lines.extend(
            [
                "> **公開前に原稿を確認してください**（block / warn がある場合は修正を推奨）",
                "",
            ]
        )
    return "\n".join(lines)


def write_ready_prompt(manifest: dict[str, Any], *, llm_check: dict[str, Any] | None = None) -> Path:
    PENDING.mkdir(parents=True, exist_ok=True)
    issue = manifest.get("issue")
    free_path = manifest.get("free_path") or ""
    paid_path = manifest.get("paid_path") or ""
    magazine = (
        manifest.get("note_magazine")
        or "https://note.com/merry_orca9232/m/m471c1317cc4e"
    )
    tone_section = format_tone_check_section(llm_check)
    text = f"""# note 公開タスク（自動生成・編集しないでOK）

pending の第{issue}号があります。Cursor Agent にこのファイルを渡して実行してください。
詳細手順: `docs/drafts/note-publish-runbook.md`

{tone_section}## やること
1. `{paid_path}` を note **有料**（980円・買い切り）として新規作成して公開
2. 有料URLを控える
3. `{free_path}` の「有料記事URLを貼ってください」を実URLに置換して **無料**公開
4. **マガジン追加（必須・チェックだけでは不足）**
   - 公開設定で「株価調査メモ（週次）」の横の **「追加」ボタン** を押す（無料・有料とも）
   - 投稿後、{magazine} を開き、両方の記事が一覧に出ていることを確認
   - 出ていなければ記事編集からマガジン追加をやり直す
5. マガジン確認が終わってから、ターミナルで:

```bash
cd {ROOT}
python3 scripts/sync_note_pending.py --mark-published --free-url '（無料記事のURL）'
```

## 注意
- 投資助言にしない（原稿の免責を維持）
- Cmd+A で全文置換しない（追記・新規作成）
- note ログインが切れていたら先に Cursor ブラウザでログイン
- 「マガジン」チェックのみで投稿すると、マガジンに入らないことがある（第4号で確認済み）
"""
    READY.write_text(text, encoding="utf-8")
    return READY


def maybe_generate_x_post(manifest: dict[str, Any]) -> dict[str, Any] | None:
    """公開後に X 投稿案を生成する（free_url が manifest にある場合）。"""
    from local_llm.client import OllamaClient, OllamaError
    from local_llm.tasks import generate_x_post

    free_rel = str(manifest.get("free_path") or "")
    free_url = manifest.get("free_url")
    if not free_rel:
        return None

    client = OllamaClient()
    health = client.health()
    if not health.get("ok") or (not health.get("dry_run") and not health.get("model_present")):
        return {
            "ok": False,
            "error": health.get("error") or "Ollama / モデルが利用できません",
        }

    try:
        result = generate_x_post(
            client,
            _draft_path(free_rel),
            free_url=str(free_url) if free_url else None,
            issue=manifest.get("issue"),
        )
        payload = result.model_dump()
        payload["ok"] = True
        payload["generated_at"] = datetime.now().isoformat(timespec="seconds")
        out_path = _x_post_path(manifest.get("issue"))
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        payload["x_post_path"] = str(out_path)
        return payload
    except (FileNotFoundError, ValueError, OllamaError) as exc:
        return {"ok": False, "error": str(exc)}


def mark_published(
    *,
    free_url: str | None = None,
    paid_url: str | None = None,
    skip_llm: bool = False,
) -> dict[str, Any]:
    manifest = load_manifest()
    if not manifest:
        raise SystemExit("manifest.json がありません")
    if free_url:
        manifest["free_url"] = free_url.strip()
    if paid_url:
        manifest["paid_url"] = paid_url.strip()
    manifest["status"] = "published"
    manifest["published_at"] = datetime.now().isoformat(timespec="seconds")
    save_manifest(manifest)
    if READY.exists():
        READY.unlink()

    x_post: dict[str, Any] | None = None
    if not skip_llm:
        x_post = maybe_generate_x_post(manifest)
        if x_post and x_post.get("x_post_path"):
            manifest["x_post_path"] = x_post["x_post_path"]
            save_manifest(manifest)

    manifest["_x_post"] = x_post
    return manifest


def build_result(
    *,
    pulled: str | None,
    manifest: dict[str, Any] | None,
    llm_check: bool = False,
) -> dict[str, Any]:
    pending = bool(manifest and str(manifest.get("status") or "") == "pending")
    out: dict[str, Any] = {
        "repo": str(ROOT),
        "pulled": pulled,
        "pending": pending,
        "manifest_path": str(MANIFEST) if MANIFEST.exists() else None,
        "manifest": manifest,
    }
    llm: dict[str, Any] | None = None
    if pending and manifest and llm_check:
        llm = run_llm_tone_checks(manifest)
        out["llm_check"] = llm
    if pending and manifest:
        out["ready_path"] = str(write_ready_prompt(manifest, llm_check=llm))
        msg = (
            f"note 第{manifest.get('issue')}号の下書きが pending です。"
            f" {out['ready_path']} を開いて Agent に公開を依頼してください。"
        )
        if llm and not llm.get("ok"):
            msg += " （トーンチェックで要確認あり）"
        out["message"] = msg
    else:
        out["message"] = "pending の note 下書きはありません。"
    return out


def notify_macos(title: str, message: str) -> None:
    # Best-effort; ignore failures in headless/CI
    script = (
        f'display notification {json.dumps(message)} '
        f'with title {json.dumps(title)}'
    )
    subprocess.run(["osascript", "-e", script], check=False, capture_output=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-pull", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mark-published", action="store_true")
    parser.add_argument("--free-url", default=None, help="公開した無料 note の URL（x-post 生成に使用）")
    parser.add_argument("--paid-url", default=None, help="公開した有料 note の URL（manifest 記録用）")
    parser.add_argument("--skip-llm", action="store_true", help="mark-published 時の x-post 生成をスキップ")
    parser.add_argument(
        "--llm-check",
        action="store_true",
        help="pending 検知時に tone-check を実行し READY に結果を追記",
    )
    parser.add_argument("--notify", action="store_true", help="pending 時に macOS 通知")
    parser.add_argument("--open-ready", action="store_true", help="pending 時に READY を開く")
    args = parser.parse_args(argv)

    try:
        if args.mark_published:
            m = mark_published(
                free_url=args.free_url,
                paid_url=args.paid_url,
                skip_llm=args.skip_llm,
            )
            x_post = m.pop("_x_post", None)
            result: dict[str, Any] = {
                "pending": False,
                "message": f"第{m.get('issue')}号を published に更新しました。",
                "manifest": m,
            }
            if x_post:
                result["x_post"] = x_post
                if x_post.get("ok") and x_post.get("primary"):
                    result["message"] += f" X投稿案: {x_post['primary'][:80]}…"
                elif x_post.get("error"):
                    result["message"] += f" （x-post 未生成: {x_post['error']}）"
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["message"])
            return 1

        pulled = None
        if not args.no_pull:
            pulled = git_pull()

        manifest = load_manifest()
        result = build_result(pulled=pulled, manifest=manifest, llm_check=args.llm_check)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if pulled:
                print(f"git: {pulled}")
            print(result["message"])

        if result["pending"]:
            llm = result.get("llm_check")
            if args.notify:
                title = "note 下書きあり"
                if llm and not llm.get("ok"):
                    title = "note 下書き・要確認"
                notify_macos(title, result["message"])
            if args.open_ready and result.get("ready_path"):
                subprocess.run(["open", result["ready_path"]], check=False)
            return 0
        return 1
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
