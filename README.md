# 株価マーケティングBlog — 運用メモ

公開URL: https://romeo5793.github.io/stock-market-blog/

## 収益モデル（現行）

- 無料: 企業カルテ全文 + ランキング Top5 の選定理由
- 有料予定: note 月額 1,980円（Top20全文・順位差分・深掘り）

`docs/assets/site-config.js` の `noteUrl` に note マガジンURLを入れると、全ページのCTAが有効化されます。

## ランキングHTMLの再生成

JSONを更新したら、必ずこのスクリプトでHTMLを作り直す（手編集の導線を消さないため）:

```bash
python3 scripts/render_rankings.py
```

## note 開設（初回チェックリスト）

1. https://note.com/signup でアカウント作成（済ならスキップ）
2. 「マガジンを作成」→ 名前例: `株価調査メモ（週次）`
3. まず **無料マガジン** で開始
4. `docs/drafts/note-issue-01.txt` をコピーして第1号を公開
5. 公開URLをこのリポジトリの `docs/assets/site-config.js` に設定して push
6. 反応を見てから有料（月額1,980円）に切替

## SEO

- `docs/sitemap.xml` / `docs/robots.txt` あり
- Google Search Console にサイトを追加し、sitemap を送信:
  `https://romeo5793.github.io/stock-market-blog/sitemap.xml`
