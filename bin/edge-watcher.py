#!/usr/bin/env python3
import os
import socket
import subprocess
import time
import json

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
        s.settimeout(0.15)
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
        return

    # Cache monitors info for 3 seconds
    monitors_cache = []
    last_mon_time = 0

    is_open = False
    last_toggle_time = 0

    while True:
        time.sleep(0.035) # ~28Hz, ultra-low CPU (<0.1%)
        now = time.time()

        # Update monitors cache
        if now - last_mon_time > 3.0 or not monitors_cache:
            raw_mon = query_socket(sock_path, "j/monitors")
            if raw_mon:
                try:
                    monitors_cache = json.loads(raw_mon)
                    last_mon_time = now
                except Exception:
                    pass

        pos_str = query_socket(sock_path, "cursorpos")
        if not pos_str or "," not in pos_str:
            continue

        try:
            parts = pos_str.split(",")
            cx = float(parts[0].strip())
            cy = float(parts[1].strip())
        except Exception:
            continue

        # Find which monitor contains the cursor
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
            continue

        mx, my, mw, mh = curr_mon
        rel_x = cx - mx
        rel_y = cy - my

        # Trigger zone: top edge (rel_y <= 12) and central 60% of monitor
        in_top_center = (rel_y <= 12) and (mw * 0.20 <= rel_x <= mw * 0.80)

        # Trigger open
        if in_top_center and not is_open and (now - last_toggle_time) > 0.35:
            subprocess.run(["omarchy-shell", "shell", "summon", "dropspace", "{}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            is_open = True
            last_toggle_time = now

        # Auto-cancel: if pulled back down (rel_y > 180)
        elif rel_y > 180 and is_open and (now - last_toggle_time) > 0.35:
            subprocess.run(["omarchy-shell", "shell", "hide", "dropspace"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            is_open = False
            last_toggle_time = now

if __name__ == "__main__":
    main()
