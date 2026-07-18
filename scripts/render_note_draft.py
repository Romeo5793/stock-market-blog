#!/usr/bin/env python3
"""現在のランキングと直前スナップショットから note 下書きを生成する。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RANK = DOCS / "rankings"
HIST = RANK / "history"
DRAFTS = DOCS / "drafts"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rank_map(data: dict) -> dict:
    return {str(i["ticker"]): i for i in data.get("ranking20", [])}


def diff(old: dict, new: dict):
    old_m, new_m = rank_map(old), rank_map(new)
    rows = []
    for ticker, item in sorted(new_m.items(), key=lambda x: x[1]["rank"]):
        prev = old_m.get(ticker)
        if not prev:
            change, delta = "NEW", None
        else:
            delta = prev["rank"] - item["rank"]
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
    dropped = [(t, old_m[t]) for t in old_m if t not in new_m]
    return rows, dropped


def movers(rows, n=8):
    m = [r for r in rows if r["change"] not in ("→",)]
    m.sort(key=lambda r: (-abs(r["delta"] or 99), r["rank"]))
    return m[:n]


def snapshot_path(market: str) -> Path:
    return HIST / f"{market}-previous.json"


def ensure_history(market: str, current: dict) -> dict | None:
    HIST.mkdir(parents=True, exist_ok=True)
    path = snapshot_path(market)
    previous = load_json(path) if path.exists() else None
    # always refresh previous with current after draft generation (caller decides)
    return previous


def render_issue(issue_no: int, jp_old, jp_new, us_old, us_new) -> str:
    jp_rows, _ = diff(jp_old, jp_new)
    us_rows, _ = diff(us_old, us_new)
    jp_m = movers(jp_rows)
    us_m = movers(us_rows)
    jp_top5 = [r for r in jp_rows if r["rank"] <= 5]
    us_top5 = [r for r in us_rows if r["rank"] <= 5]
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"【無料】順位が動いた銘柄まとめ｜日本株の上げ下げ（投資助言ではありません）",
        "",
        f"第{issue_no}号です。今回は「順位の変化」に焦点を当てます。",
        "",
        "このマガジンは買い推奨ではありません。",
        "銘柄を比較する時間を短くするための、調査メモです。",
        "",
        "無料: Top5 ＋ 大きく動いた銘柄の差分",
        "有料予定: Top20全文・毎日差分・深掘り（月額1,980円）",
        "",
        "※情報提供であり、投資助言ではありません。投資判断は自己責任でお願いします。",
        "",
        "---",
        "",
        "## 比較期間",
        "",
        f"- 前回: {jp_old.get('updated_at')}",
        f"- 今回: {jp_new.get('updated_at')}",
        f"- 作成日: {today}",
        "",
        "## 市場メモ",
        "",
        f"- 日本: {(jp_new.get('marketSignal') or {}).get('status')} — {(jp_new.get('marketSignal') or {}).get('reason')}",
        f"- 米国: {(us_new.get('marketSignal') or {}).get('status')} — {(us_new.get('marketSignal') or {}).get('reason')}",
        "",
        "## 今回いちばん動いた日本株",
        "",
    ]
    for r in jp_m:
        direction = "上昇" if (r["delta"] or 0) > 0 else "下落"
        lines.append(
            f"- {r['ticker']} {r['companyName']}: {r['prev_rank']}位 → {r['rank']}位（{direction} {abs(r['delta'])}） / スコア{r['score']}"
        )
        lines.append(f"  一言: {r.get('reason', '')}")
    lines += ["", "## 日本株 Top5（今回）", ""]
    for r in jp_top5:
        lines.append(
            f"{r['rank']}. **{r['ticker']} {r['companyName']}**（スコア{r['score']} / {r['change']}）"
        )
        if r.get("prev_rank"):
            lines.append(f"   前回{r['prev_rank']}位")
        lines.append(f"   {r.get('reason', '')}")
        lines.append("")
    lines += ["## 米国株で動いた銘柄（参考）", ""]
    for r in us_m[:5]:
        lines.append(
            f"- {r['ticker']} {r['companyName']}: {r['prev_rank']}位 → {r['rank']}位（{r['change']}）"
        )
    lines += ["", "## 米国株 Top5（参考）", ""]
    for r in us_top5:
        lines.append(
            f"{r['rank']}. {r['ticker']} {r['companyName']}（{r['score']} / {r['change']}）"
        )
    lines += [
        "",
        "## 読み方（重要）",
        "",
        "- 順位が上がった = 買え、ではありません",
        "- 見るべきは「なぜ動いたか」と、企業カルテの財務シグナル変化です",
        "- 6〜20位の全文理由は有料配信の予定です",
        "",
        "## リンク",
        "",
        "- マガジン: https://note.com/merry_orca9232/m/m471c1317cc4e",
        "- ブログ: https://romeo5793.github.io/stock-market-blog/",
        "- 日本株ランキング: https://romeo5793.github.io/stock-market-blog/japan-top20.html",
        "- 無料と有料: https://romeo5793.github.io/stock-market-blog/pricing.html",
        "",
        "## 有料で届けるもの（予告）",
        "",
        "- 毎日の Top20 全文",
        "- 全銘柄の前日差分一覧",
        "- 注目銘柄の追加コメント",
        "",
        "---",
        "",
        "【X投稿用・短文】",
        "",
        "今週は「順位の変化」に注目した調査メモです。",
        "買い推奨ではなく、比較用。",
        "",
        "詳細はマガジンへ",
        "https://note.com/merry_orca9232/m/m471c1317cc4e",
        "",
        "#日本株 #株式投資 #投資メモ",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    jp_new = load_json(RANK / "jp-top20.json")
    us_new = load_json(RANK / "us-top20.json")
    HIST.mkdir(parents=True, exist_ok=True)
    jp_prev_path = snapshot_path("jp")
    us_prev_path = snapshot_path("us")

    if not jp_prev_path.exists() or not us_prev_path.exists():
        raise SystemExit(
            "history snapshot missing. Seed docs/rankings/history/*-previous.json first."
        )

    jp_old = load_json(jp_prev_path)
    us_old = load_json(us_prev_path)
    issue_no = 2
    existing = sorted(DRAFTS.glob("note-issue-*.txt"))
    if existing:
        try:
            issue_no = int(existing[-1].stem.split("-")[-1]) + 1
        except ValueError:
            issue_no = len(existing) + 1

    text = render_issue(issue_no, jp_old, jp_new, us_old, us_new)
    out = DRAFTS / f"note-issue-{issue_no:02d}.txt"
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")

    # roll history forward after draft
    jp_prev_path.write_text(
        json.dumps(jp_new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    us_prev_path.write_text(
        json.dumps(us_new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("updated history snapshots")


if __name__ == "__main__":
    main()
