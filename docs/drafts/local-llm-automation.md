# ローカル LLM 自動化（Ollama）

週次の **定型テキスト処理**（X投稿案・助言口調チェック・要約）を、
Mac 上の Ollama に任せるための手順です。

Cloud Agent / Cursor Chat の代替ではなく、**繰り返し・機密・オフライン**向けです。

---

## [Local LLM Recommendation]

- **Recommended Model:** `Qwen2.5-14B-Instruct`（`Q4_K_M` 相当 / Ollama タグ `qwen2.5:14b`）
- **Estimated VRAM/RAM Usage:** 約 9–10 GB（Unified Memory）
- **Ollama Pull Command:** `ollama pull qwen2.5:14b`
- **Why this model:** 24GB M5 で OS/Cursor 用に ~8GB を残しつつ、日本語の要約・JSON 構造化・トーン検査に十分な能力。コーディング専用ではないので 14B 汎用が最適。

軽量代替: `ollama pull qwen2.5:7b`（約 5GB・速度優先）

---

## 初回セットアップ（Mac）

```bash
cd ~/Projects/stock-market-blog   # 実際のパスに合わせる
chmod +x scripts/macos/setup_ollama.sh
./scripts/macos/setup_ollama.sh
```

手動でも可:

```bash
brew install ollama
# または https://ollama.com/download

ollama pull qwen2.5:14b
python3 -m pip install -r requirements-local-llm.txt
python3 scripts/run_local_llm.py doctor
```

環境変数（任意）:

| 変数 | 既定 | 意味 |
|------|------|------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | API 先 |
| `OLLAMA_MODEL` | `qwen2.5:14b` | モデル |
| `OLLAMA_NUM_CTX` | `16384` | コンテキスト長 |
| `OLLAMA_DRY_RUN` | （空） | `1` で API なしテスト |

---

## コマンド

### 接続確認
```bash
python3 scripts/run_local_llm.py doctor
```

### X 投稿案（週次ルーチン④向け）
```bash
python3 scripts/run_local_llm.py x-post \
  --draft docs/drafts/note-issue-04-free.txt \
  --free-url 'https://note.com/...' \
  --issue 4 \
  -o docs/drafts/pending/x-post-issue-04.json
```

### 投資助言口調チェック（公開前）
```bash
python3 scripts/run_local_llm.py tone-check \
  --draft docs/drafts/note-issue-04-free.txt
# exit 0 = OK / 1 = 要修正 / 2 = エラー
```

### 短要約
```bash
python3 scripts/run_local_llm.py summarize \
  --draft docs/drafts/note-issue-04-free.txt
```

### Ollama なしで CLI 動作確認
```bash
python3 scripts/run_local_llm.py x-post --dry-run --json \
  --draft docs/drafts/note-issue-04-free.txt
```

---

## 週次フローへの差し込み方

`docs/drafts/weekly-ops.md` ③〜④に組み込み済み:

1. `render_note_draft.py` で下書き生成（既存・自動）
2. Mac の `sync_note_pending.py --llm-check` で **tone-check**（launchd が pending 検知時に実行）
3. note 公開（READY_FOR_AGENT → Cursor Agent）
4. `--mark-published --free-url …` で **x-post** JSON 生成 → X に貼る

手動一括: `./scripts/weekly_llm_prep.sh`  
公開後の `sync_note_pending.py --mark-published` と manifest の git push は従来どおり。

---

## Cursor との役割分担

| 作業 | 担当 |
|------|------|
| note 公開のブラウザ操作・マガジン追加 | Cursor Agent（既存） |
| X 文面の量産・トーン検査・要約 | **ローカル LLM（本スクリプト）** |
| Tab 補完・複雑な設計判断 | Cursor クラウド |

---

## トラブルシュート

| 症状 | 対処 |
|------|------|
| `Ollama に接続できません` | メニューバーで Ollama 起動、または `ollama serve` |
| `model が見つかりません` | `ollama pull qwen2.5:14b` |
| 応答が遅い / メモリ逼迫 | `OLLAMA_MODEL=qwen2.5:7b` に落とす |
| JSON パース失敗 | `--verbose` でログ確認。同じコマンド再実行で多くの場合回復 |
