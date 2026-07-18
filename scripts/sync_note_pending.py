#!/usr/bin/env python3
"""
Mac ローカル: リポジトリを同期し、note 下書きの pending を検知する。

使い方:
  python3 scripts/sync_note_pending.py           # pull + 検知（通知用メッセージを stdout）
  python3 scripts/sync_note_pending.py --json    # JSON で結果
  python3 scripts/sync_note_pending.py --mark-published  # 公開後に status=published
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
PENDING = ROOT / "docs" / "drafts" / "pending"
MANIFEST = PENDING / "manifest.json"
READY = PENDING / "READY_FOR_AGENT.md"


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


def write_ready_prompt(manifest: dict[str, Any]) -> Path:
    PENDING.mkdir(parents=True, exist_ok=True)
    issue = manifest.get("issue")
    free_path = manifest.get("free_path") or ""
    paid_path = manifest.get("paid_path") or ""
    text = f"""# note 公開タスク（自動生成・編集しないでOK）

pending の第{issue}号があります。Cursor Agent にこのファイルを渡して実行してください。

## やること
1. `{paid_path}` を開き、note 有料記事として新規作成（または下書き）して公開（980円）
2. 有料URLを控える
3. `{free_path}` の「有料記事URLを貼ってください」を実URLに置換して無料公開
4. 両方をマガジン https://note.com/merry_orca9232/m/m471c1317cc4e に追加
5. 完了後、ターミナルで:

```bash
cd {ROOT}
python3 scripts/sync_note_pending.py --mark-published
```

## 注意
- 投資助言にしない（原稿の免責を維持）
- Cmd+A で全文置換しない（追記・新規作成）
- note ログインが切れていたら先に Cursor ブラウザでログイン
"""
    READY.write_text(text, encoding="utf-8")
    return READY


def mark_published() -> dict[str, Any]:
    manifest = load_manifest()
    if not manifest:
        raise SystemExit("manifest.json がありません")
    manifest["status"] = "published"
    manifest["published_at"] = datetime.now().isoformat(timespec="seconds")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if READY.exists():
        READY.unlink()
    return manifest


def build_result(*, pulled: str | None, manifest: dict[str, Any] | None) -> dict[str, Any]:
    pending = bool(manifest and str(manifest.get("status") or "") == "pending")
    out: dict[str, Any] = {
        "repo": str(ROOT),
        "pulled": pulled,
        "pending": pending,
        "manifest_path": str(MANIFEST) if MANIFEST.exists() else None,
        "manifest": manifest,
    }
    if pending and manifest:
        out["ready_path"] = str(write_ready_prompt(manifest))
        out["message"] = (
            f"note 第{manifest.get('issue')}号の下書きが pending です。"
            f" {out['ready_path']} を開いて Agent に公開を依頼してください。"
        )
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
    parser.add_argument("--notify", action="store_true", help="pending 時に macOS 通知")
    parser.add_argument("--open-ready", action="store_true", help="pending 時に READY を開く")
    args = parser.parse_args(argv)

    try:
        if args.mark_published:
            m = mark_published()
            result = {
                "pending": False,
                "message": f"第{m.get('issue')}号を published に更新しました。",
                "manifest": m,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["message"])
            return 1

        pulled = None
        if not args.no_pull:
            pulled = git_pull()

        manifest = load_manifest()
        result = build_result(pulled=pulled, manifest=manifest)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if pulled:
                print(f"git: {pulled}")
            print(result["message"])

        if result["pending"]:
            if args.notify:
                notify_macos("note 下書きあり", result["message"])
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
