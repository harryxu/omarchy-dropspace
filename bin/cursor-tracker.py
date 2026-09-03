#!/usr/bin/env python3
import os
import socket
import json
import time
import sys

BASE_CARD_WIDTH = 160
CARD_HEIGHT = 100
CARD_SPACING = 16
TOP_MARGIN = 36

def get_socket_path():
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not sig:
        try:
            hypr_dir = f"/run/user/{os.getuid()}/hypr"
            entries = os.listdir(hypr_dir)
            entries = [e for e in entries if not e.startswith(".")]
            if entries:
                sig = entries[0]
        except Exception:
            pass
    if sig:
        return f"/run/user/{os.getuid()}/hypr/{sig}/.socket.sock"
    return None

def query_socket(sock_path, cmd):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.1)
        s.connect(sock_path)
        s.sendall(cmd.encode() if isinstance(cmd, str) else cmd)
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        s.close()
        return data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return None

def main():
    sock_path = get_socket_path()
    if not sock_path or not os.path.exists(sock_path):
        sys.exit(0)

    monitors_cache = []
    workspace_ids = [1, 2, 3, 4]
    last_meta_time = 0
    last_reported_id = -1

    while True:
        now = time.time()

        # Refresh monitors and workspaces metadata every 1.5s
        if now - last_meta_time > 1.5 or not monitors_cache:
            raw_mon = query_socket(sock_path, "j/monitors")
            if raw_mon:
                try:
                    monitors_cache = json.loads(raw_mon)
                except Exception:
                    pass

            raw_ws = query_socket(sock_path, "j/workspaces")
            if raw_ws:
                try:
                    ws_list = json.loads(raw_ws)
                    ids = []
                    max_id = 1
                    for ws in ws_list:
                        wid = ws.get("id", 0)
                        if wid > 0:
                            if wid not in ids:
                                ids.append(wid)
                            if wid > max_id:
                                max_id = wid
                    if (max_id + 1) not in ids:
                        ids.append(max_id + 1)
                    for m in range(1, 5):
                        if m not in ids:
                            ids.append(m)
                    ids.sort()
                    workspace_ids = ids
                except Exception:
                    pass
            last_meta_time = now

        pos_str = query_socket(sock_path, "cursorpos")
        if not pos_str or "," not in pos_str:
            time.sleep(0.035)
            continue

        try:
            parts = pos_str.split(",")
            cx = float(parts[0].strip())
            cy = float(parts[1].strip())
        except Exception:
            time.sleep(0.035)
            continue

        curr_mon = None
        for mon in monitors_cache:
            mx = mon.get("x", 0)
            my = mon.get("y", 0)
            scale = float(mon.get("scale", 1.0))
            mw = float(mon.get("width", 1920)) / scale
            mh = float(mon.get("height", 1080)) / scale
            if mx <= cx < mx + mw and my <= cy < my + mh:
                curr_mon = (mx, my, mw, mh)
                break

        if not curr_mon and monitors_cache:
            scale = float(monitors_cache[0].get("scale", 1.0))
            curr_mon = (monitors_cache[0].get("x", 0), monitors_cache[0].get("y", 0), float(monitors_cache[0].get("width", 1920)) / scale, float(monitors_cache[0].get("height", 1080)) / scale)

        if not curr_mon:
            time.sleep(0.035)
            continue

        mx, my, mw, mh = curr_mon
        rel_x = cx - mx
        rel_y = cy - my

        hover_id = 0
        count = len(workspace_ids)
        available = mw - 64
        card_width = max(100, min(BASE_CARD_WIDTH, int((available - (count - 1) * CARD_SPACING) // count)))
        total_width = count * card_width + (count - 1) * CARD_SPACING
        start_x = (mw - total_width) / 2.0
        end_x = start_x + total_width

        # Check vertical range
        if 0 <= rel_y <= (TOP_MARGIN + CARD_HEIGHT + 45):
            if start_x - 8 <= rel_x <= end_x + 8:
                offset_x = rel_x - start_x
                slot_width = card_width + CARD_SPACING
                card_index = int(offset_x // slot_width)
                if 0 <= card_index < count:
                    hover_id = workspace_ids[card_index]

        if hover_id != last_reported_id:
            print(hover_id, flush=True)
            last_reported_id = hover_id

        time.sleep(0.03)

if __name__ == "__main__":
    main()
