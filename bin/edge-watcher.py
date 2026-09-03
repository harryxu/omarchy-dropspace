#!/usr/bin/env python3
import os
import socket
import subprocess
import time
import json
import sys
import signal

CONFIG_PATH = os.path.expanduser("~/.config/omarchy/dropspace.json")

def load_config():
    defaults = {
        "edge_watcher": False,
        "top_edge_threshold": 16,
        "cancel_threshold": 180
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                user_cfg = json.load(f)
                defaults.update(user_cfg)
        except Exception:
            pass
    return defaults

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
    cfg = load_config()
    # Check if edge_watcher is enabled in config
    if not cfg.get("edge_watcher", False) and "--force" not in sys.argv:
        print("edge_watcher is disabled in ~/.config/omarchy/dropspace.json. Exiting.")
        return

    sock_path = get_socket_path()
    if not sock_path or not os.path.exists(sock_path):
        return

    top_threshold = cfg.get("top_edge_threshold", 16)
    cancel_threshold = cfg.get("cancel_threshold", 180)

    monitors_cache = []
    last_mon_time = 0

    is_open = False
    last_toggle_time = 0
    last_cfg_check_time = time.time()

    sleep_duration = 0.5 # Start in deep sleep

    # Robust Lua query: gets cursor position and whether SUPER key is currently held
    QUERY_CMD = (
        "repl "
        "local p = hl.get_cursor_pos() "
        "local function is_super() "
        "  local ok1, r1 = pcall(hl.is_key_down, 'Super_L') if ok1 and r1 then return true end "
        "  local ok2, r2 = pcall(hl.is_key_down, 'Super_R') if ok2 and r2 then return true end "
        "  local ok3, r3 = pcall(hl.is_key_down, 125) if ok3 and r3 then return true end "
        "  local ok4, r4 = pcall(hl.is_key_down, 133) if ok4 and r4 then return true end "
        "  return false "
        "end "
        "local w = hl.get_active_window() "
        "local is_dragging = is_super() and (w ~= nil) "
        "return tostring(p.x) .. ',' .. tostring(p.y) .. ',' .. tostring(is_dragging)"
    )

    try:
        while True:
            time.sleep(sleep_duration)
            now = time.time()

            # Check config changes every 5 seconds
            if now - last_cfg_check_time > 5.0:
                cfg = load_config()
                if not cfg.get("edge_watcher", False) and "--force" not in sys.argv:
                    print("edge_watcher disabled via config change. Exiting.")
                    break
                top_threshold = cfg.get("top_edge_threshold", 16)
                cancel_threshold = cfg.get("cancel_threshold", 180)
                last_cfg_check_time = now

            # Update monitors cache
            if now - last_mon_time > 3.0 or not monitors_cache:
                raw_mon = query_socket(sock_path, "j/monitors")
                if raw_mon:
                    try:
                        monitors_cache = json.loads(raw_mon)
                        last_mon_time = now
                    except Exception:
                        pass

            raw_resp = query_socket(sock_path, QUERY_CMD)
            if not raw_resp or "," not in raw_resp:
                sleep_duration = 0.5
                continue

            try:
                parts = raw_resp.split(",")
                cx = float(parts[0].strip())
                cy = float(parts[1].strip())
                is_dragging = (parts[2].strip().lower() == "true")
                is_open = os.path.exists("/tmp/dropspace_is_open")
            except Exception:
                sleep_duration = 0.5
                continue

            # Find monitor
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
                sleep_duration = 0.5
                continue

            mx, my, mw, mh = curr_mon
            rel_x = cx - mx
            rel_y = cy - my

            # ==========================================
            # Adaptive Sleep Scheduling
            # ==========================================
            if is_dragging or is_open:
                # Dragging window (SUPER pressed) or panel is open: sample at ~30Hz
                sleep_duration = 0.035
            elif rel_y <= 100:
                # Near top edge without dragging: moderate polling
                sleep_duration = 0.1
            elif rel_y <= 250:
                sleep_duration = 0.25
            else:
                # Main screen area: deep sleep with minimal CPU usage
                sleep_duration = 0.5

            # Trigger area: top-center 60% of the screen
            in_top_center = (rel_y <= top_threshold) and (mw * 0.20 <= rel_x <= mw * 0.80)

            # Summon panel only when cursor is in the top center while dragging with SUPER
            if in_top_center and is_dragging and not is_open and (now - last_toggle_time) > 0.35:
                subprocess.run(["omarchy-shell", "shell", "summon", "dropspace", "{}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                is_open = True
                last_toggle_time = now

            # Auto-hide when cursor is pulled back down below the cancel threshold
            elif rel_y > cancel_threshold and is_open and (now - last_toggle_time) > 0.35:
                subprocess.run(["omarchy-shell", "shell", "hide", "dropspace"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                is_open = False
                last_toggle_time = now
    finally:
        if is_open:
            subprocess.run(["omarchy-shell", "shell", "hide", "dropspace"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass
