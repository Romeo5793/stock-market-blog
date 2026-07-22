# ローカル（Mac）でこのブランチを続ける手順

Cloud Agent は Mac に移れません。以降は **Cursor Desktop（ローカル）** で同じリポジトリを開いて進めてください。
Ollama もローカルでのみ動きます。

## 1. リポジトリを Mac に用意

すでに clone 済みなら:

```bash
cd ~/Projects/stock-market-blog   # 実際のパスに合わせる
git fetch origin
git checkout cursor/local-llm-automation-0ed6
git pull origin cursor/local-llm-automation-0ed6
```

未 clone なら:

```bash
mkdir -p ~/Projects && cd ~/Projects
git clone https://github.com/Romeo5793/stock-market-blog.git
cd stock-market-blog
git checkout cursor/local-llm-automation-0ed6
```

## 2. Cursor でローカル開く

1. Cursor Desktop を起動
2. **File → Open Folder** → `stock-market-blog`
3. チャットは **Cloud Agent ではなく、通常の Agent / Chat（ローカル）** を使う
4. ターミナルも Cursor 内のローカルターミナル（プロンプトが Mac のホーム配下）であることを確認

Cloud のシェルだと `brew` / `ollama` は見つかりません。

## 3. Ollama 起動確認（Mac）

```bash
# アプリを起動（メニューバーにラマが出ること）
open -a Ollama

which ollama
ollama --version
curl -s http://127.0.0.1:11434/api/tags
ollama pull qwen2.5:14b
```

## 4. このプロジェクトの自動化を動かす

```bash
chmod +x scripts/macos/setup_ollama.sh
./scripts/macos/setup_ollama.sh

python3 scripts/run_local_llm.py doctor
python3 scripts/run_local_llm.py tone-check --draft docs/drafts/note-issue-04-free.txt
python3 scripts/run_local_llm.py x-post --draft docs/drafts/note-issue-04-free.txt --issue 4
```

## 5. PR

ブランチ: `cursor/local-llm-automation-0ed6`  
PR: https://github.com/Romeo5793/stock-market-blog/pull/1

ローカルで追加修正したら、同じブランチに commit / push すれば PR に載ります。

## 詰まったとき

| 症状 | 確認 |
|------|------|
| `ollama: command not found` | Spotlight で Ollama 起動。ターミナルを開き直す |
| `Connection refused` | Ollama アプリ未起動 |
| Cloud のシェルで作業している | プロンプトや `uname` を確認。Linux ならローカルではない |

```bash
uname -s
# Darwin → Mac（正解）
# Linux  → クラウド（ここでは Ollama 不可）
```
