#!/usr/bin/env python3
"""JSONランキングから HTML を再生成する（無料Top5 + 有料CTA を維持）。"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs"

CHIP = {
    ("A", "health"): "health-a",
    ("B", "health"): "health-b",
    ("C", "health"): "health-c",
    ("S", "quality"): "quality-s",
    ("A", "quality"): "quality-a",
    ("C", "quality"): "quality-c",
    ("低", "fraud"): "fraud-low",
    ("注意", "fraud"): "fraud-warn",
    ("高", "fraud"): "fraud-high",
}


def chips(fs: dict) -> str:
    if not fs:
        return ""
    h = fs.get("health_rank") or "-"
    q = fs.get("quality_rank") or "-"
    f = fs.get("fraud_risk") or "-"
    return (
        '<div class="signal-banner">'
        f'<span class="signal-chip {CHIP.get((h, "health"), "")}">健全性 {escape(str(h))}</span>'
        f'<span class="signal-chip {CHIP.get((q, "quality"), "")}">ファンダ {escape(str(q))}</span>'
        f'<span class="signal-chip {CHIP.get((f, "fraud"), "")}">粉飾 {escape(str(f))}</span>'
        "</div>"
    )


def card(item: dict, full: bool = True) -> str:
    ticker = str(item.get("ticker", ""))
    name = str(item.get("companyName", ""))
    sector = str(item.get("sector", ""))
    score = item.get("score", "")
    reason = str(item.get("reason", ""))
    rank = item.get("rank", "")
    href = f"posts/{escape(ticker)}.html"
    fs = item.get("financialSignals") or {}
    src = item.get("financialSource") or ""
    upd = item.get("financialUpdatedAt") or ""
    title = f'{escape(str(rank))}. <a href="{href}">{escape(ticker)} {escape(name)}</a>'
    if full:
        return f"""    <article class="card">
      <h2>{title}</h2>
      <p class="meta">業種: {escape(sector)} ／ スコア: {escape(str(score))}</p>
      {chips(fs)}
      <p class="fin-meta-row"><span>財務更新: <strong>{escape(str(upd))}</strong></span><span>データ源: <strong>{escape(str(src))}</strong></span></p>
      <p>{escape(reason)}</p>
      <p><a href="{href}">企業カルテを見る</a></p>
    </article>"""
    return f"""    <article class="card rank-teaser">
      <h2>{title}</h2>
      <p class="meta">業種: {escape(sector)} ／ スコア: {escape(str(score))}</p>
      <p class="teaser-note">選定理由・詳細コメントは有料マガジンで公開予定。企業カルテは無料です。</p>
      <p><a href="{href}">企業カルテを見る</a></p>
    </article>"""


def render(
    market_json: str,
    out_name: str,
    page_title: str,
    h1: str,
    seo_desc: str,
    canonical: str,
) -> None:
    data = json.loads((ROOT / market_json).read_text(encoding="utf-8"))
    items = data.get("ranking20") or []
    signal = data.get("marketSignal") or {}
    updated = data.get("updated_at") or ""
    status = signal.get("status") or ""
    reason = signal.get("reason") or ""
    free = "\n".join(card(i, True) for i in items[:5])
    locked = "\n".join(card(i, False) for i in items[5:])
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(page_title)}</title>
  <meta name="description" content="{escape(seo_desc)}">
  <link rel="canonical" href="{escape(canonical)}">
  <meta property="og:title" content="{escape(page_title)}">
  <meta property="og:description" content="{escape(seo_desc)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{escape(canonical)}">
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <main class="wrap">
    <nav class="site-nav" aria-label="サイト内リンク">
      <a href="index.html">トップ</a>
      <a href="japan-top20.html">日本株</a>
      <a href="us-top20.html">米国株</a>
      <a href="pricing.html">無料と有料</a>
    </nav>
    <a class="back" href="index.html">トップへ戻る</a>
    <h1 class="site-title">{escape(h1)}</h1>
    <p class="meta-strong">更新: {escape(str(updated))} ／ 市場シグナル: {escape(str(status))} — {escape(str(reason))}</p>
    <p class="site-sub">無料公開はTop5の選定理由まで。6位以下は銘柄名とスコア、企業カルテへのリンクを掲載しています。カルテ本文は無料です。</p>

    <p class="rank-free-label">無料公開：Top 5</p>
{free}

    <div data-cta
         data-cta-kicker="6位〜20位の全文"
         data-cta-title="有料マガジンで Top20 全文と差分を配信"
         data-cta-body="無料ではTop5の理由まで。有料では毎日のTop20全文・順位の前日差分・深掘り更新を届けます。月額 1,980円予定。"
         data-cta-pricing="pricing.html"></div>

    <p class="rank-locked-label">6位〜20位：銘柄名のみ（理由は有料）</p>
{locked}
    <p class="footer">本ページは情報提供目的であり、投資助言ではありません。投資判断は自己責任でお願いします。</p>
  </main>
  <script src="assets/site-config.js"></script>
  <script src="assets/cta.js"></script>
</body>
</html>
"""
    (ROOT / out_name).write_text(html, encoding="utf-8")
    print(f"wrote {out_name} ({len(items)} items)")


def main() -> None:
    render(
        "rankings/jp-top20.json",
        "japan-top20.html",
        "日本株おすすめランキング最新20選｜無料Top5と企業カルテ",
        "日本株（東証）おすすめ20選",
        "東証銘柄の注目ランキング。無料でTop5の選定理由と企業カルテを公開。財務健全性・ファンダも整理。",
        "https://romeo5793.github.io/stock-market-blog/japan-top20.html",
    )
    render(
        "rankings/us-top20.json",
        "us-top20.html",
        "米国株おすすめランキング最新20選｜無料Top5と企業カルテ",
        "米国株おすすめ20選",
        "米国株の注目ランキング。無料でTop5の選定理由と企業カルテを公開。財務健全性・ファンダも整理。",
        "https://romeo5793.github.io/stock-market-blog/us-top20.html",
    )


if __name__ == "__main__":
    main()
