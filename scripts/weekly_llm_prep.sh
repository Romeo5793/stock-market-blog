#!/usr/bin/env bash
# 週次: ローカル LLM で公開前チェック（tone-check）を一括実行
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> doctor"
python3 scripts/run_local_llm.py doctor

MANIFEST="$REPO_ROOT/docs/drafts/pending/manifest.json"
if [[ ! -f "$MANIFEST" ]]; then
  echo "manifest.json がありません。先に render_note_draft.py を実行してください。" >&2
  exit 1
fi

read -r FREE PAID ISSUE < <(
  python3 -c "
import json
m = json.load(open('$MANIFEST'))
print(m.get('free_path',''), m.get('paid_path',''), m.get('issue',''))
"
)

if [[ -z "$FREE" || -z "$PAID" ]]; then
  echo "manifest に free_path / paid_path がありません。" >&2
  exit 1
fi

echo "==> tone-check 第${ISSUE}号（無料）"
python3 scripts/run_local_llm.py tone-check --draft "$FREE" -o \
  "docs/drafts/pending/tone-check-issue-${ISSUE}-free.json"

echo "==> tone-check 第${ISSUE}号（有料）"
python3 scripts/run_local_llm.py tone-check --draft "$PAID" -o \
  "docs/drafts/pending/tone-check-issue-${ISSUE}-paid.json"

echo
echo "完了。問題なければ note 公開へ。詳細は pending/ 内の JSON を参照。"
