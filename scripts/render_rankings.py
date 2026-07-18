#!/usr/bin/env python3
"""JSONランキングから HTML を再生成する（無料Top5 + 有料CTA を維持）。"""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1] / "docs"
JST = ZoneInfo("Asia/Tokyo")
FIN_STALE_DAYS = 7

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

ANALYTICS_SCRIPTS = """  <script src="assets/site-config.js"></script>
  <script src="assets/analytics.js"></script>
  <script src="assets/cta.js"></script>"""


def parse_ts(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(text)
        # 保存値がタイムゾーン無しのときは JST 壁時計として扱う
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        return dt.astimezone(JST)
    except ValueError:
        return None


def format_ts(value: object, *, empty: str = "-") -> str:
    dt = parse_ts(value)
    if not dt:
        return empty if not str(value or "").strip() else str(value)
    days = max(0, (datetime.now(JST).date() - dt.date()).days)
    if days == 0:
        age = "今日"
    elif days == 1:
        age = "1日前"
    else:
        age = f"{days}日前"
    return f"{dt.strftime('%Y-%m-%d %H:%M')} JST（{age}）"


def age_days(value: object) -> int | None:
    dt = parse_ts(value)
    if not dt:
        return None
    return max(0, (datetime.now(JST).date() - dt.date()).days)


def max_financial_age(items: list[dict]) -> int | None:
    ages = [age_days(i.get("financialUpdatedAt")) for i in items]
    ages = [a for a in ages if a is not None]
    return max(ages) if ages else None


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
    upd_label = format_ts(upd)
    stale = ""
    days = age_days(upd)
    if days is not None and days >= FIN_STALE_DAYS:
        stale = ' <span class="freshness-hint">財務キャッシュ再利用中</span>'
    title = f'{escape(str(rank))}. <a href="{href}">{escape(ticker)} {escape(name)}</a>'
    if full:
        return f"""    <article class="card">
      <h2>{title}</h2>
      <p class="meta">業種: {escape(sector)} ／ スコア: {escape(str(score))}</p>
      {chips(fs)}
      <p class="fin-meta-row"><span>財務更新: <strong>{escape(upd_label)}</strong>{stale}</span><span>データ源: <strong>{escape(str(src))}</strong></span></p>
      <p>{escape(reason)}</p>
      <p><a href="{href}">企業カルテを見る</a></p>
    </article>"""
    fin_teaser = ""
    if upd:
        fin_teaser = f'<p class="meta">財務更新: {escape(upd_label)}{stale}</p>'
    return f"""    <article class="card rank-teaser">
      <h2>{title}</h2>
      <p class="meta">業種: {escape(sector)} ／ スコア: {escape(str(score))}</p>
      {fin_teaser}
      <p class="teaser-note">選定理由・詳細コメントは有料マガジンで公開予定。企業カルテは無料です。</p>
      <p><a href="{href}">企業カルテを見る</a></p>
    </article>"""


def ranking_meta_line(updated: object, items: list[dict], signal: dict) -> str:
    status = signal.get("status") or ""
    reason = signal.get("reason") or ""
    rank_label = format_ts(updated)
    fin_age = max_financial_age(items)
    if fin_age is None:
        fin_part = "財務データ: 未取得あり"
    elif fin_age == 0:
        fin_part = "財務データ: 今日取得分あり"
    else:
        fin_part = f"財務データ: 古いもの最大{fin_age}日前"
        if fin_age >= FIN_STALE_DAYS:
            fin_part += "（キャッシュ再利用中）"
    return (
        f"順位更新: {escape(rank_label)} ／ {escape(fin_part)} ／ "
        f"市場シグナル: {escape(str(status))} — {escape(str(reason))}"
    )


def render(
    market_json: str,
    out_name: str,
    page_title: str,
    h1: str,
    seo_desc: str,
    canonical: str,
) -> dict:
    data = json.loads((ROOT / market_json).read_text(encoding="utf-8"))
    items = data.get("ranking20") or []
    signal = data.get("marketSignal") or {}
    updated = data.get("updated_at") or ""
    free = "\n".join(card(i, True) for i in items[:5])
    locked = "\n".join(card(i, False) for i in items[5:])
    meta = ranking_meta_line(updated, items, signal)
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
    <p class="meta-strong">{meta}</p>
    <p class="site-sub">無料公開はTop5の選定理由まで。6位以下は銘柄名とスコア、企業カルテへのリンクを掲載しています。カルテ本文は無料です。ランキング本文の再計算は週次（金曜）が基本です。</p>

    <p class="rank-free-label">無料公開：Top 5</p>
{free}

    <div data-cta
         data-cta-kicker="6位〜20位の全文"
         data-cta-title="有料マガジンで Top20 全文と差分を配信"
         data-cta-body="無料ではTop5の理由まで。有料では週次のTop20全文・順位差分・深掘り更新を届けます（買い切り980円の号もあります）。"
         data-cta-pricing="pricing.html"></div>

    <p class="rank-locked-label">6位〜20位：銘柄名のみ（理由は有料）</p>
{locked}
    <p class="footer">本ページは情報提供目的であり、投資助言ではありません。投資判断は自己責任でお願いします。</p>
  </main>
{ANALYTICS_SCRIPTS}
</body>
</html>
"""
    (ROOT / out_name).write_text(html, encoding="utf-8")
    print(f"wrote {out_name} ({len(items)} items)")
    return {"updated_at": updated, "label": h1}


def render_index(jp: dict, us: dict) -> None:
    jp_ts = format_ts(jp.get("updated_at"), empty="未取得")
    us_ts = format_ts(us.get("updated_at"), empty="未取得")
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>株価マーケティングBlog</title>
  <meta name="description" content="日本株・米国株の注目ランキングと企業カルテ。情報提供であり投資助言ではありません。">
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
    <h1 class="site-title">株価マーケティングBlog</h1>
    <p class="site-sub">日本株・米国株のおすすめランキングと、銘柄ごとの企業カルテを公開しています。</p>
    <p class="meta-strong">最終更新 — 日本株: {escape(jp_ts)} ／ 米国株: {escape(us_ts)}</p>
    <p class="meta">ランキング本文は週次更新が基本。財務データはキャッシュを再利用することがあります。</p>

    <section class="card">
      <h2><a href="japan-top20.html">日本株おすすめ20選</a></h2>
      <p>東証銘柄の注目ランキング。各銘柄名から企業カルテへ移動できます。</p>
    </section>

    <section class="card">
      <h2><a href="us-top20.html">米国株おすすめ20選</a></h2>
      <p>米国株の注目ランキング。各銘柄名から企業カルテへ移動できます。</p>
    </section>

    <section class="card">
      <h2><a href="pricing.html">無料と有料の違い</a></h2>
      <p>無料の範囲と、note有料記事で読める内容を比較できます。</p>
    </section>

    <p class="footer">本サイトは情報提供目的であり、投資助言ではありません。投資判断は自己責任でお願いします。</p>
  </main>
{ANALYTICS_SCRIPTS}
</body>
</html>
"""
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print("wrote index.html")


def main() -> None:
    jp = render(
        "rankings/jp-top20.json",
        "japan-top20.html",
        "日本株おすすめランキング最新20選｜無料Top5と企業カルテ",
        "日本株（東証）おすすめ20選",
        "東証銘柄の注目ランキング。無料でTop5の選定理由と企業カルテを公開。財務健全性・ファンダも整理。",
        "https://romeo5793.github.io/stock-market-blog/japan-top20.html",
    )
    us = render(
        "rankings/us-top20.json",
        "us-top20.html",
        "米国株おすすめランキング最新20選｜無料Top5と企業カルテ",
        "米国株おすすめ20選",
        "米国株の注目ランキング。無料でTop5の選定理由と企業カルテを公開。財務健全性・ファンダも整理。",
        "https://romeo5793.github.io/stock-market-blog/us-top20.html",
    )
    render_index(jp, us)


if __name__ == "__main__":
    main()
