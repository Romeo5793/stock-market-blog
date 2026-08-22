# 株価マーケティングBlog — 運用メモ

公開URL: https://romeo5793.github.io/stock-market-blog/

## 収益モデル（現行）

- 無料: 企業カルテ全文 + ランキング Top5 の選定理由 + note無料ダイジェスト
- 有料: note 買い切り（例: 980円）で Top20全文・順位差分

`docs/assets/site-config.js` の `noteUrl` に最新の無料ダイジェストURLを入れると、全ページのCTAが有効化されます。

## 鮮度の見方

- ランキング本文の再計算は **週次（金曜）** が基本
- 財務データは最大14日キャッシュ（画面上は7日超で「再利用中」表示）
- トップ／ランキングに「順位更新」と「財務データの古さ」を分けて表示

## ブログ計測（Umami）

1. https://cloud.umami.is で無料アカウント作成
2. Website に `https://romeo5793.github.io/stock-market-blog/` を追加
3. 発行された Website ID を `docs/assets/site-config.js` の `umamiWebsiteId` に貼る
4. push 後、ダッシュボードでPVを確認（空文字のあいだは計測オフ）

Cookieレス想定のため、同意バナーは通常不要です。

## ランキングHTMLの再生成

JSONを更新したら、必ずこのスクリプトでHTMLを作り直す（手編集の導線を消さないため）:

```bash
python3 scripts/render_rankings.py
```

## ローカル LLM 自動化（Ollama）

週次の X 投稿案・助言口調チェック・要約を Mac 上の Ollama で処理できます。

```bash
./scripts/macos/setup_ollama.sh
python3 scripts/run_local_llm.py doctor
```

詳細: `docs/drafts/local-llm-automation.md`

## note 開設（初回チェックリスト）

1. https://note.com/signup でアカウント作成（済ならスキップ）
2. 「マガジンを作成」→ 名前例: `株価調査メモ（週次）`
3. まず **無料ダイジェスト + 有料買い切り** で開始
4. 公開URLを `docs/assets/site-config.js` に設定して push

## SEO

- `docs/sitemap.xml` / `docs/robots.txt` あり
- Google Search Console にサイトを追加し、sitemap を送信:
  `https://romeo5793.github.io/stock-market-blog/sitemap.xml`
