#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
TARGET="$SCRIPT_DIR/drop-handler.py"

if [ ! -f "$TARGET" ]; then
    exit 0
fi

exec /usr/bin/env python3 "$TARGET" "$@"
