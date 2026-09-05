#!/usr/bin/env python3
"""CLI utility to manage DropSpace coordination state securely."""

import os
import sys

# Ensure dropspace_runtime can be imported from script directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dropspace_runtime


def main():
    if len(sys.argv) < 2:
        print("Usage: dropspace-state.py {open|close|check|path}", file=sys.stderr)
        sys.exit(2)

    action = sys.argv[1].lower()
    if action == "open":
        dropspace_runtime.set_state_open()
    elif action == "close":
        dropspace_runtime.set_state_closed()
    elif action == "check":
        if dropspace_runtime.is_state_open():
            sys.exit(0)
        else:
            sys.exit(1)
    elif action == "path":
        print(dropspace_runtime.get_state_file_path())
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
