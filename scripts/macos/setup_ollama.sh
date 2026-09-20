#!/usr/bin/env bash
# Mac 向け: Ollama 導入確認 + 推奨モデル pull + doctor
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen2.5:14b}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "==> [1/4] Ollama の有無を確認"
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama が見つかりません。"
  echo "  brew install ollama"
  echo "  または https://ollama.com/download からインストール"
  exit 1
fi
ollama --version

echo "==> [2/4] Ollama サービス起動（すでに動いていればスキップ）"
if ! curl -sf "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
  echo "ollama serve をバックグラウンド起動します…"
  # GUI アプリ版ならメニューバーから起動済みのことが多い
  nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
  sleep 2
fi

echo "==> [3/4] 推奨モデルを pull: ${MODEL}"
ollama pull "${MODEL}"

echo "==> [4/4] Python 依存と doctor"
python3 -m pip install -q -r "${REPO_ROOT}/requirements-local-llm.txt"
cd "${REPO_ROOT}"
python3 scripts/run_local_llm.py doctor

echo
echo "完了。次の例:"
echo "  python3 scripts/run_local_llm.py x-post --draft docs/drafts/note-issue-04-free.txt"
echo "  python3 scripts/run_local_llm.py tone-check --draft docs/drafts/note-issue-04-free.txt"
