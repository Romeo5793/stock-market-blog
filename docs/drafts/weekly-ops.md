# 週次ルーチン（月30万への運用）

所要目安: **週2〜3時間**（平日に少しずつでも可）
目的: 無料で集客 → 有料980円記事で売上 → 継続更新で信頼を積む

---

## 毎週やること（固定）

### ① データ更新（自動・金曜）
| 時刻 (JST) | 処理 | リポジトリ |
|---|---|---|
| 15:00 | ランキング強制更新 → ブログ反映 | `stock-marketing-bot` / `friday-ranking-refresh` |
| 15:40 | note 無料+有料下書き生成（鮮度チェック付き） | `stock-market-blog` / `friday-note-drafts` |

手動でランキングだけ更新する場合:
```bash
cd ~/Projects/stock-marketing-bot
python3 main.py --blog-sync --refresh-rankings
```

### ② note下書き生成（自動）
金曜 **15:40** JST に GitHub Actions（`friday-note-drafts`）が実行する。

手動でも可:
```bash
cd ~/Projects/stock-market-blog
python3 scripts/render_note_draft.py
```
出力:
- `docs/drafts/note-issue-XX-free.txt`
- `docs/drafts/note-issue-XX-paid.txt`
- `docs/drafts/pending/manifest.json`（status=pending → ローカル公開検知用）

### ③ note無料＋有料の公開（Mac起動後）
クラウドが `docs/drafts/pending/manifest.json` を `pending` にする。
Mac ではログイン時／30分ごとに検知する（スリープ中は動かない）。

**初回だけ**（Ollama + launchd）:
```bash
cd ~/Projects/stock-market-blog
chmod +x scripts/macos/*.sh scripts/sync_note_pending.py scripts/weekly_llm_prep.sh
./scripts/macos/setup_ollama.sh          # Ollama + qwen2.5:14b（未導入時のみ）
./scripts/macos/install_note_pending_agent.sh
```

launchd を入れ直したとき（`--llm-check` 追加後など）も `install_note_pending_agent.sh` を再実行する。

検知されたら（**自動で tone-check 済み**）:
1. 通知が出る／`docs/drafts/pending/READY_FOR_AGENT.md` が開く
   - 本文に **ローカル LLM トーンチェック結果**（無料・有料）が載る
   - 詳細 JSON: `docs/drafts/pending/tone-check-issue-XX.json`
   - 要確認（⚠️）なら公開前に原稿を直す
2. Cursor Agent に「READY_FOR_AGENT の手順で note 公開して」と依頼（ブラウザ自動可）
3. **マガジン「株価調査メモ（週次）」の「追加」ボタンまで含めて公開**（チェックだけでは不足）
4. マガジン一覧で無料・有料の両方を確認
5. 完了後（**無料 URL を渡すと X 投稿案も自動生成**）:
```bash
cd ~/Projects/stock-market-blog
python3 scripts/sync_note_pending.py --mark-published \
  --free-url 'https://note.com/merry_orca9232/n/........'
git add docs/drafts/pending/manifest.json && git commit -m "docs: mark note issue N as published." && git push
```
- X 投稿案: `docs/drafts/pending/x-post-issue-XX.json`（`primary` をコピペ）

詳細: `docs/drafts/note-publish-runbook.md`  
Ollama 詳細: `docs/drafts/local-llm-automation.md`

手動で pending を確認（tone-check 付き）:
```bash
python3 scripts/sync_note_pending.py --notify --open-ready --llm-check
```

tone-check だけ手動で一括:
```bash
./scripts/weekly_llm_prep.sh
```

### ④ Xに1投稿（2分）
`--mark-published` で生成された `docs/drafts/pending/x-post-issue-XX.json` の **`primary`** をコピーして投稿。買い推奨にしない。

投稿文を再生成したいとき:
```bash
python3 scripts/run_local_llm.py x-post \
  --draft docs/drafts/note-issue-XX-free.txt \
  --free-url '（無料URL）' \
  --issue XX \
  -o docs/drafts/pending/x-post-issue-XX.json
```

tone-check を個別にやり直す場合:
```bash
python3 scripts/run_local_llm.py tone-check --draft docs/drafts/note-issue-XX-free.txt
python3 scripts/run_local_llm.py tone-check --draft docs/drafts/note-issue-XX-paid.txt
```

テンプレ（LLM 未使用・Ollama 停止時）:
```text
今週の調査メモを公開しました（非助言）。

無料: Top5と動いた銘柄
有料: Top20全文と差分（980円）

↓
（無料URL）
```

### ⑤ 数字チェック（10分）
記録するだけ（完璧でなくてよい）:

| 項目 | 今週 |
|---|---|
| noteスキ数（合計） | |
| 有料販売数 | |
| Xインプレッション | |
| ブログのSearch Consoleクリック | |

---

## 公開タイミング（固定）

**本公開: 毎週金曜 16:30（JST）**

理由:
- 東証クローズ（15:00）直後で、その週の値がほぼ確定している
- 「今週どうだったか」を週末前に読めるので、情報が一番おいしい
- 米国は金曜夜〜土曜朝に動くので、必要なら **土曜 9:00 に追記 or Xで一言** で足りる

| 曜日 | 内容 | 時刻目安 |
|---|---|---|
| 金曜 15:30〜16:20 | データ更新＋下書き生成＋（Mac）tone-check | 公開前 |
| **金曜 16:30** | **note無料／有料を公開** | 本番 |
| 金曜 16:35 | `--mark-published --free-url` → X文案確認 | 公開直後 |
| 金曜 16:40 | X投稿（`x-post-issue-XX.json` の primary） | 公開直後 |
| 土曜 9:00（任意） | 米国の動きが大きければXで1行追記 | 補足 |
| 日曜 21:00（任意） | 反応が良い回だけ再投稿／引用 | 拾い直し |

残り時間はカルテ増やす／SEOページ改善に回す。

---

## やってはいけないこと

- 毎日長文を無理に書く（疲れる）
- 買い推奨っぽい言い回し
- 無料を全部有料に閉じる（集客が死ぬ）
- 数字を見ずに機能追加だけする

---

## マイルストーン（目安）

| 時期 | 目標 |
|---|---|
| 2週後 | 有料が1本でも売れる／反応の型が分かる |
| 1ヶ月 | 週次更新が習慣化、記事10本前後 |
| 2〜3ヶ月 | 月額（定期購読）へ移行検討 |
| 半年 | 有料読者・購読で月30万に近づく設計を再計算 |

月30万 ≈ 有料980円なら約 **360本/月** は非現実的なので、
やがて **月額1,980円 × 約150人** か **法人・高単価** に寄せる。
今は「売れる文章と更新習慣」を作る期間。

---

## 今週の次アクション（今すぐ）

1. 来週の更新日をカレンダーに入れる（例: 毎週木曜 20:00）
2. 有料が売れた／売れないを1行でメモする
3. 売れたら「何が刺さったか」を次号タイトルに反映
