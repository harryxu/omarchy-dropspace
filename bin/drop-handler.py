#!/usr/bin/env python3
import json
import subprocess
import sys
import time

LOG_FILE = "/tmp/dropspace.log"

CARD_WIDTH = 160
CARD_HEIGHT = 100
CARD_SPACING = 16
NUM_WORKSPACES = 5
TOP_MARGIN = 36
TOTAL_WIDTH = NUM_WORKSPACES * CARD_WIDTH + (NUM_WORKSPACES - 1) * CARD_SPACING

def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%X')}] {msg}\n")
    except Exception:
        pass

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
        return res.stdout.strip()
    except Exception as e:
        log(f"Error running '{cmd}': {e}")
        return ""

def main():
    log("drop-handler invoked")

    # 1. Check if DropSpace is open
    state = run_cmd("omarchy-shell dropspace state")
    log(f"DropSpace state: '{state}'")
    if state != "open":
        log("DropSpace is not open, ignoring")
        return

    # 2. Get cursor pos
    cursor_str = run_cmd("hyprctl cursorpos")
    log(f"Cursor pos: '{cursor_str}'")
    if not cursor_str or "," not in cursor_str:
        run_cmd("omarchy-shell dropspace hide")
        return

    try:
        parts = cursor_str.split(",")
        cx = float(parts[0].strip())
        cy = float(parts[1].strip())
    except Exception as e:
        log(f"Failed to parse cursorpos: {e}")
        run_cmd("omarchy-shell dropspace hide")
        return

    # 3. Get monitors info
    monitors_json = run_cmd("hyprctl monitors -j")
    try:
        monitors = json.loads(monitors_json)
    except Exception as e:
        log(f"Failed to parse monitors: {e}")
        run_cmd("omarchy-shell dropspace hide")
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
        for mon in monitors:
            if mon.get("focused"):
                scale = float(mon.get("scale", 1.0))
                target_mon = (mon, mon.get("x", 0), mon.get("y", 0), float(mon.get("width", 1920)) / scale, float(mon.get("height", 1080)) / scale)
                break

    if not target_mon:
        log("No monitor found for cursor")
        run_cmd("omarchy-shell dropspace hide")
        return

    mon, mx, my, mw, mh = target_mon
    rel_x = cx - mx
    rel_y = cy - my
    log(f"Monitor {mon.get('name')}: rel_x={rel_x}, rel_y={rel_y}, mw={mw}, mh={mh}")

    # Hide overlay now
    run_cmd("omarchy-shell dropspace hide")

    # 5. Check if cursor is within top drop region
    # Active vertical zone: from screen top (0) to bottom of cards (+ generous tolerance)
    if rel_y < 0 or rel_y > (TOP_MARGIN + CARD_HEIGHT + 45):
        log(f"rel_y {rel_y} is outside drop zone [0, {TOP_MARGIN + CARD_HEIGHT + 45}]")
        return

    start_x = (mw - TOTAL_WIDTH) / 2.0
    end_x = start_x + TOTAL_WIDTH
    log(f"Cards horizontal range: [{start_x}, {end_x}]")

    if rel_x < (start_x - 16) or rel_x > (end_x + 16):
        log(f"rel_x {rel_x} is outside horizontal range [{start_x - 16}, {end_x + 16}]")
        return

    offset_x = rel_x - start_x
    slot_width = CARD_WIDTH + CARD_SPACING
    card_index = int(offset_x // slot_width)
    log(f"Calculated card_index: {card_index}")

    if 0 <= card_index < NUM_WORKSPACES:
        target_workspace = card_index + 1
        cmd = f"hyprctl dispatch 'hl.dsp.window.move({{ workspace = \"{target_workspace}\" }})'"
        log(f"Moving to workspace {target_workspace}: {cmd}")
        run_cmd(cmd)

if __name__ == "__main__":
    main()
