#!/usr/bin/env bash
# DropSpace autostart helper
CONFIG="$HOME/.config/omarchy/dropspace.json"
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
WATCHER="$SCRIPT_DIR/edge-watcher.py"

if [ -f "$WATCHER" ]; then
    # Start edge-watcher in background if not already running
    if ! python3 "$SCRIPT_DIR/dropspace-state.py" watcher-running >/dev/null 2>&1; then
        nohup /usr/bin/env python3 "$WATCHER" </dev/null >/dev/null 2>&1 & disown 2>/dev/null || true
    fi
fi
