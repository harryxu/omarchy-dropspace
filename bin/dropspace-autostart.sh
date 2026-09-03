#!/usr/bin/env bash
# DropSpace autostart helper
CONFIG="$HOME/.config/omarchy/dropspace.json"

if [ -f "$CONFIG" ] && grep -Eq '"edge_watcher"[[:space:]]*:[[:space:]]*true' "$CONFIG"; then
    # Start edge-watcher in background if not already running
    if ! pgrep -fa "edge-watcher.py" >/dev/null 2>&1; then
        nohup /usr/bin/env python3 /home/harry/Work/dropspace/bin/edge-watcher.py >/dev/null 2>&1 &
    fi
fi
