#!/bin/zsh
# launchd から呼ばれる: pull → pending 検知 → 通知 → READY を開く
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/bin:/usr/bin:/bin"
LOG_DIR="$HOME/Library/Logs/stock-market-blog"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/note-pending.log"
{
  echo "---- $(date '+%Y-%m-%d %H:%M:%S') ----"
  cd "$ROOT"
  /usr/bin/python3 scripts/sync_note_pending.py --notify --open-ready
  code=$?
  echo "exit=$code"
  exit 0
} >>"$LOG" 2>&1
