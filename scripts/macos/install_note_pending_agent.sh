#!/bin/zsh
# launchd エージェントをインストールする
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LABEL="com.romeo5793.stock-market-blog.note-pending"
DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"
TEMPLATE="$ROOT/scripts/macos/${LABEL}.plist.template"

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$HOME/Library/Logs/stock-market-blog"
chmod +x "$ROOT/scripts/macos/run_note_pending_check.sh"
chmod +x "$ROOT/scripts/sync_note_pending.py"

sed -e "s|__REPO_ROOT__|${ROOT}|g" -e "s|__HOME__|${HOME}|g" "$TEMPLATE" > "$DEST"

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}" || true

echo "Installed: $DEST"
echo "Logs: $HOME/Library/Logs/stock-market-blog/"
echo "Test now: python3 $ROOT/scripts/sync_note_pending.py --notify --open-ready"
echo "Unload: launchctl bootout gui/\$(id -u)/${LABEL}"
