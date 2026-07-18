#!/usr/bin/env python3
"""
現在のランキングと直前スナップショットから note 下書き（無料＋有料）を生成する。

出力:
  docs/drafts/note-issue-XX-free.txt
  docs/drafts/note-issue-XX-paid.txt
  docs/drafts/pending/manifest.json   … ローカル公開検知用（status=pending）

クラウド（GitHub Actions）でもローカルでも同じコマンドで動く。
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RANK = DOCS / "rankings"
HIST = RANK / "history"
DRAFTS = DOCS / "drafts"
PENDING = DRAFTS / "pending"
BLOG = "https://romeo5793.github.io/stock-market-blog"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rank_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(i["ticker"]): i for i in data.get("ranking20", [])}


def snapshot_path(market: str) -> Path:
    return HIST / f"{market}-previous.json"


def fin_caption(item: dict[str, Any]) -> str:
    sig = item.get("financialSignals") or {}
    if sig.get("caption"):
        return str(sig["caption"])
    h = sig.get("health_rank") or "-"
    q = sig.get("quality_rank") or "-"
    f = sig.get("fraud_risk") or "-"
    if h == "-" and q == "-" and f == "-":
        return "財務シグナル: 準備中"
    return f"健全性{h} / ファンダ{q} / 粉飾{f}"


def diff(old: dict[str, Any], new: dict[str, Any]):
    old_m, new_m = rank_map(old), rank_map(new)
    rows: list[dict[str, Any]] = []
    for ticker, item in sorted(new_m.items(), key=lambda x: int(x[1].get("rank") or 99)):
        prev = old_m.get(ticker)
        if not prev:
            change, delta = "NEW", None
        else:
            delta = int(prev["rank"]) - int(item["rank"])
            if delta > 0:
                change = f"↑{delta}"
            elif delta < 0:
                change = f"↓{abs(delta)}"
            else:
                change = "→"
        rows.append(
            {
                **item,
                "ticker": ticker,
                "change": change,
                "delta": delta,
                "prev_rank": prev["rank"] if prev else None,
            }
        )
    return rows


def movers(rows: list[dict[str, Any]], n: int = 8) -> list[dict[str, Any]]:
    m = [r for r in rows if r["change"] not in ("→",)]
    m.sort(key=lambda r: (-abs(r["delta"] or 99), int(r["rank"])))
    return m[:n]


def next_issue_no() -> int:
    nums: list[int] = []
    for path in DRAFTS.glob("note-issue-*.txt"):
        m = re.search(r"note-issue-(\d+)", path.stem)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def render_free(
    issue_no: int,
    jp_old: dict[str, Any],
    jp_new: dict[str, Any],
    us_new: dict[str, Any],
    jp_rows: list[dict[str, Any]],
) -> str:
    jp_m = movers(jp_rows)
    jp_top5 = [r for r in jp_rows if int(r["rank"]) <= 5]
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"【無料】第{issue_no}号ダイジェスト｜Top5と動いた銘柄（投資助言ではありません）",
        "",
        f"第{issue_no}号の無料版です。",
        "詳細は有料記事に分けています。",
        "",
        "無料で読めるもの: Top5 ＋ 動きの大きい銘柄の要約",
        "有料記事で読めるもの: 日本株Top20全文 ＋ 全銘柄の順位差分一覧",
        "",
        "※情報提供であり、投資助言ではありません。投資判断は自己責任でお願いします。",
        "",
        "---",
        "",
        "## 市場メモ",
        "",
        f"- 日本: {(jp_new.get('marketSignal') or {}).get('status')} — {(jp_new.get('marketSignal') or {}).get('reason')}",
        f"- 米国: {(us_new.get('marketSignal') or {}).get('status')} — {(us_new.get('marketSignal') or {}).get('reason')}",
        "",
        f"- 前回スナップショット: {jp_old.get('updated_at')}",
        f"- 今回スナップショット: {jp_new.get('updated_at')}",
        f"- 作成日: {today}",
        "",
        "## 日本株 Top5",
        "",
    ]
    for r in jp_top5:
        lines.append(
            f"{r['rank']}. **{r['ticker']} {r.get('companyName', '')}**"
            f"（スコア{r.get('score')} / {r['change']}）"
        )
        lines.append(f"   {r.get('reason', '')}")
        lines.append("")
    lines += ["## 今回動いた銘柄（抜粋）", ""]
    for r in jp_m[:6]:
        direction = "上昇" if (r["delta"] or 0) > 0 else ("下落" if (r["delta"] or 0) < 0 else "新規")
        prev = r["prev_rank"] if r["prev_rank"] is not None else "-"
        if r["change"] == "NEW":
            lines.append(f"- {r['ticker']} {r.get('companyName', '')}: 新規 → {r['rank']}位")
        else:
            lines.append(
                f"- {r['ticker']} {r.get('companyName', '')}: "
                f"{prev}位→{r['rank']}位（{direction}{abs(r['delta'] or 0)}）"
            )
    lines += [
        "",
        "## 続きは有料記事へ",
        "",
        "Top20の全文理由と、全銘柄の差分一覧は有料記事にまとめています。",
        "",
        "→ 公開後、ここに有料記事URLを貼ってください",
        "",
        "価格目安: 980円（買い切り）",
        "",
        "## リンク",
        "",
        "- マガジン: https://note.com/merry_orca9232/m/m471c1317cc4e",
        f"- ブログ: {BLOG}/",
        f"- 日本株ランキング: {BLOG}/japan-top20.html",
        "",
        "---",
        "",
        "【公開設定メモ】",
        "",
        "- 公開範囲: 無料",
        "- マガジン「株価調査メモ（週次）」に追加",
        "",
        "【X投稿用・短文】",
        "",
        f"今週の調査メモ（第{issue_no}号）を公開しました（非助言）。",
        "",
        "無料: Top5と動いた銘柄",
        "有料: Top20全文と差分（980円）",
        "",
        f"{BLOG}/",
        "",
    ]
    return "\n".join(lines)


def render_paid(
    issue_no: int,
    jp_old: dict[str, Any],
    jp_new: dict[str, Any],
    us_new: dict[str, Any],
    jp_rows: list[dict[str, Any]],
) -> str:
    us_rows = [
        {**i, "ticker": str(i.get("ticker") or ""), "change": "→", "delta": 0, "prev_rank": i.get("rank")}
        for i in (us_new.get("ranking20") or [])
    ]
    # US diff if we have history is nicer; optional
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"【有料】第{issue_no}号｜日本株Top20全文と順位差分一覧（投資助言ではありません）",
        "",
        f"第{issue_no}号の有料版です。",
        "",
        "この記事で読めるもの:",
        "- 日本株 Top20 の選定理由全文",
        "- 全銘柄の順位差分（前回比）",
        "- 米国株 Top20（参考）",
        "",
        "買い推奨ではありません。銘柄比較の時短用メモです。",
        "※情報提供であり、投資助言ではありません。投資判断は自己責任でお願いします。",
        "",
        "---",
        "",
        "## 比較の前提",
        "",
        f"- 前回スナップショット: {jp_old.get('updated_at')}",
        f"- 今回スナップショット: {jp_new.get('updated_at')}",
        f"- 作成日: {today}",
        "",
        "## 日本株｜全銘柄の順位差分",
        "",
    ]
    for r in jp_rows:
        prev = r["prev_rank"]
        if prev is None:
            move = f"新規 → 今回{r['rank']}位"
        else:
            move = f"前回{prev}位 → 今回{r['rank']}位（{r['change']}）"
        lines.append(
            f"{int(r['rank']):2d}. {r['ticker']} {r.get('companyName', '')}  "
            f"{move}  スコア{r.get('score')}"
        )
    lines += ["", "## 日本株 Top20 全文", ""]
    for r in jp_rows:
        ticker = r["ticker"]
        lines += [
            f"### {r['rank']}. {ticker} {r.get('companyName', '')}",
            f"業種: {r.get('sector') or '-'} ／ スコア: {r.get('score')} ／ 変化: {r['change']}",
            fin_caption(r),
            str(r.get("reason") or ""),
            f"企業カルテ: {BLOG}/posts/{ticker}.html",
            "",
        ]
    lines += ["## 米国株 Top20（参考）", ""]
    for r in us_rows[:20]:
        ticker = str(r.get("ticker") or "")
        lines.append(
            f"{r.get('rank')}. {ticker} {r.get('companyName', '')} "
            f"（スコア{r.get('score')}） — {r.get('reason', '')}"
        )
    lines += [
        "",
        "## 読み方",
        "",
        "- 変化の大きさと財務シグナルをセットで見る",
        "- 粉飾が「保留」の場合は期間データの取り違え注意（断定しない）",
        "- ライブの最新はブログを正とする",
        f"  {BLOG}/japan-top20.html",
        "",
        "---",
        "",
        "【公開設定メモ】",
        "",
        "- 公開範囲: 有料（980円・買い切り）",
        "- マガジン「株価調査メモ（週次）」に追加",
        "",
    ]
    return "\n".join(lines)


def write_manifest(
    issue_no: int,
    *,
    free_rel: str,
    paid_rel: str,
    jp_updated: str,
    status: str = "pending",
    reason: str = "",
) -> Path:
    PENDING.mkdir(parents=True, exist_ok=True)
    manifest = {
        "issue": issue_no,
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "jp_ranking_updated_at": jp_updated,
        "free_path": free_rel,
        "paid_path": paid_rel,
        "note_magazine": "https://note.com/merry_orca9232/m/m471c1317cc4e",
        "publish_hint": "Mac起動後にローカルが pending を検知して note へ反映する想定",
    }
    if reason:
        manifest["reason"] = reason
    path = PENDING / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def rankings_unchanged(old: dict[str, Any], new: dict[str, Any]) -> bool:
    """前回と同じスナップショットなら True（重複号を防ぐ）。"""
    if str(old.get("updated_at") or "") and str(old.get("updated_at")) == str(
        new.get("updated_at") or ""
    ):
        return True
    old_key = [
        (str(i.get("ticker")), int(i.get("rank") or 0), int(i.get("score") or 0))
        for i in (old.get("ranking20") or [])
    ]
    new_key = [
        (str(i.get("ticker")), int(i.get("rank") or 0), int(i.get("score") or 0))
        for i in (new.get("ranking20") or [])
    ]
    return old_key == new_key and bool(old_key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate note free+paid drafts")
    parser.add_argument(
        "--issue",
        type=int,
        default=0,
        help="Issue number (default: auto-increment)",
    )
    parser.add_argument(
        "--no-roll-history",
        action="store_true",
        help="Do not update rankings/history snapshots after generate",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Generate even when rankings are unchanged vs history",
    )
    args = parser.parse_args(argv)

    jp_new = load_json(RANK / "jp-top20.json")
    us_new = load_json(RANK / "us-top20.json")
    HIST.mkdir(parents=True, exist_ok=True)
    DRAFTS.mkdir(parents=True, exist_ok=True)
    jp_prev_path = snapshot_path("jp")
    us_prev_path = snapshot_path("us")

    if not jp_prev_path.exists() or not us_prev_path.exists():
        # First run: seed previous = current so diff is flat, still produce drafts
        print("history missing — seeding previous snapshots from current rankings")
        jp_prev_path.write_text(
            json.dumps(jp_new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        us_prev_path.write_text(
            json.dumps(us_new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    jp_old = load_json(jp_prev_path)
    us_old = load_json(us_prev_path)

    if not args.force and rankings_unchanged(jp_old, jp_new):
        print(
            "SKIP: rankings unchanged vs history "
            f"(updated_at={jp_new.get('updated_at')}). "
            "Use --force to generate anyway."
        )
        return 3

    issue_no = args.issue if args.issue > 0 else next_issue_no()
    jp_rows = diff(jp_old, jp_new)

    free_text = render_free(issue_no, jp_old, jp_new, us_new, jp_rows)
    paid_text = render_paid(issue_no, jp_old, jp_new, us_new, jp_rows)

    free_path = DRAFTS / f"note-issue-{issue_no:02d}-free.txt"
    paid_path = DRAFTS / f"note-issue-{issue_no:02d}-paid.txt"
    free_path.write_text(free_text, encoding="utf-8")
    paid_path.write_text(paid_text, encoding="utf-8")
    print(f"wrote {free_path}")
    print(f"wrote {paid_path}")

    manifest = write_manifest(
        issue_no,
        free_rel=str(free_path.relative_to(ROOT)),
        paid_rel=str(paid_path.relative_to(ROOT)),
        jp_updated=str(jp_new.get("updated_at") or ""),
    )
    print(f"wrote {manifest} (status=pending)")

    if not args.no_roll_history:
        jp_prev_path.write_text(
            json.dumps(jp_new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        us_prev_path.write_text(
            json.dumps(us_new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("updated history snapshots")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
