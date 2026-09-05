#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dropspace_runtime

dropspace_runtime.init_journal("dropspace-drop-handler")

BASE_CARD_WIDTH = 160
CARD_HEIGHT = 100
CARD_SPACING = 16
TOP_MARGIN = 36

MAX_WORKSPACE_COUNT = 5

def get_workspace_ids():
    ws_json = run_cmd("hyprctl workspaces -j")
    ids = []
    max_id = 1
    try:
        workspaces = json.loads(ws_json)
        for ws in workspaces:
            wid = ws.get("id", 0)
            if wid > 0:
                if wid not in ids:
                    ids.append(wid)
                if wid > max_id:
                    max_id = wid
    except Exception:
        pass

    if (max_id + 1) not in ids:
        ids.append(max_id + 1)

    min_count = 4
    for m in range(1, min_count + 1):
        if m not in ids:
            ids.append(m)

    ids.sort()
    return ids[:MAX_WORKSPACE_COUNT]

def log(msg):
    dropspace_runtime.log(msg)

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

    # 5. Dynamically calculate workspace cards
    workspace_ids = get_workspace_ids()
    count = len(workspace_ids)
    log(f"Dynamic workspace IDs: {workspace_ids}")

    available = mw - 64
    card_width = max(100, min(BASE_CARD_WIDTH, int((available - (count - 1) * CARD_SPACING) // count)))
    total_width = count * card_width + (count - 1) * CARD_SPACING

    # Active vertical zone: from screen top (0) to bottom of cards (+ generous tolerance)
    if rel_y < 0 or rel_y > (TOP_MARGIN + CARD_HEIGHT + 45):
        log(f"rel_y {rel_y} is outside drop zone [0, {TOP_MARGIN + CARD_HEIGHT + 45}]")
        return

    start_x = (mw - total_width) / 2.0
    end_x = start_x + total_width
    log(f"Cards horizontal range: [{start_x}, {end_x}], card_width={card_width}")

    if rel_x < (start_x - 16) or rel_x > (end_x + 16):
        log(f"rel_x {rel_x} is outside horizontal range [{start_x - 16}, {end_x + 16}]")
        return

    offset_x = rel_x - start_x
    slot_width = card_width + CARD_SPACING
    card_index = int(offset_x // slot_width)
    log(f"Calculated card_index: {card_index}")

    if 0 <= card_index < count:
        target_workspace = workspace_ids[card_index]
        cmd = f"hyprctl dispatch 'hl.dsp.window.move({{ workspace = \"{target_workspace}\" }})'"
        log(f"Moving to workspace {target_workspace}: {cmd}")
        run_cmd(cmd)

if __name__ == "__main__":
    main()
