#!/usr/bin/env python3
import json
import subprocess
import sys

CARD_WIDTH = 160
CARD_HEIGHT = 100
CARD_SPACING = 16
NUM_WORKSPACES = 5
TOP_MARGIN = 36
TOTAL_WIDTH = NUM_WORKSPACES * CARD_WIDTH + (NUM_WORKSPACES - 1) * CARD_SPACING

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
        return res.stdout.strip()
    except Exception:
        return ""

def main():
    # 1. Hide overlay immediately
    subprocess.run("omarchy-shell dropspace hide 2>/dev/null || omarchy-shell shell hide dropspace 2>/dev/null", shell=True)

    # 2. Get cursor pos
    cursor_str = run_cmd("hyprctl cursorpos")
    if not cursor_str or "," not in cursor_str:
        return

    try:
        parts = cursor_str.split(",")
        cx = float(parts[0].strip())
        cy = float(parts[1].strip())
    except Exception:
        return

    # 3. Get monitors info
    monitors_json = run_cmd("hyprctl monitors -j")
    if not monitors_json:
        return

    try:
        monitors = json.loads(monitors_json)
    except Exception:
        return

    # 4. Find which monitor contains the cursor
    target_mon = None
    for mon in monitors:
        mx = mon.get("x", 0)
        my = mon.get("y", 0)
        scale = float(mon.get("scale", 1.0))
        mw = float(mon.get("width", 1920)) / scale
        mh = float(mon.get("height", 1080)) / scale

        if mx <= cx < mx + mw and my <= cy < my + mh:
            target_mon = (mon, mx, my, mw, mh)
            break

    if not target_mon and monitors:
        # Fallback to focused monitor
        for mon in monitors:
            if mon.get("focused"):
                scale = float(mon.get("scale", 1.0))
                target_mon = (mon, mon.get("x", 0), mon.get("y", 0), float(mon.get("width", 1920)) / scale, float(mon.get("height", 1080)) / scale)
                break

    if not target_mon:
        return

    mon, mx, my, mw, mh = target_mon
    rel_x = cx - mx
    rel_y = cy - my

    # 5. Check if cursor is within top drop region
    # Active vertical zone: from screen top (0) to bottom of cards (+ generous tolerance)
    if rel_y < 0 or rel_y > (TOP_MARGIN + CARD_HEIGHT + 35):
        return

    start_x = (mw - TOTAL_WIDTH) / 2.0
    end_x = start_x + TOTAL_WIDTH

    if rel_x < (start_x - 12) or rel_x > (end_x + 12):
        return

    offset_x = rel_x - start_x
    slot_width = CARD_WIDTH + CARD_SPACING
    card_index = int(offset_x // slot_width)

    # Check if within card or slot tolerance
    if 0 <= card_index < NUM_WORKSPACES:
        target_workspace = card_index + 1
        # Move active window to workspace and switch to it
        subprocess.run(f"hyprctl dispatch movetoworkspace {target_workspace}", shell=True)

if __name__ == "__main__":
    main()
