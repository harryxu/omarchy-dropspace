#!/usr/bin/env python3
import os
import socket
import subprocess
import time
import json
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dropspace_runtime

CONFIG_PATH = os.path.expanduser("~/.config/omarchy/dropspace.json")

def load_config():
    defaults = {
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

def get_socket_path(timeout=15.0):
    start = time.time()
    while True:
        sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        if not sig:
            try:
                hypr_dir = f"/run/user/{os.getuid()}/hypr"
                if os.path.exists(hypr_dir):
                    entries = [e for e in os.listdir(hypr_dir) if not e.startswith(".")]
                    if entries:
                        sig = entries[0]
            except Exception:
                pass
        if sig:
            sock = f"/run/user/{os.getuid()}/hypr/{sig}/.socket.sock"
            if os.path.exists(sock):
                return sock

        if (time.time() - start) >= timeout:
            break
        time.sleep(0.2)
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
    # Wait up to 15s for Hyprland IPC socket to become available on boot
    sock_path = get_socket_path(timeout=15.0)
    if not sock_path or not os.path.exists(sock_path):
        return

    cfg = load_config()
    top_threshold = cfg.get("top_edge_threshold", 16)
    cancel_threshold = cfg.get("cancel_threshold", 180)

    monitors_cache = []
    last_mon_time = 0

    is_open = False
    summoned_by_edge = False
    last_toggle_time = 0
    last_cfg_check_time = time.time()

    # Active window drag tracking state
    is_actively_dragged = False
    last_w_addr = None
    last_w_pos = None
    accumulated_drag = 0.0

    sleep_duration = 0.5 # Start in deep sleep

    # Robust Lua query: cursor pos, SUPER key state, and active window position
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
        "if not w then "
        "  return tostring(p.x) .. ',' .. tostring(p.y) .. ',' .. tostring(is_super()) .. ',none,0,0' "
        "else "
        "  return tostring(p.x) .. ',' .. tostring(p.y) .. ',' .. tostring(is_super()) .. ',' .. tostring(w.address) .. ',' .. tostring(w.at.x) .. ',' .. tostring(w.at.y) "
        "end"
    )

    try:
        while True:
            time.sleep(sleep_duration)
            now = time.time()

            # Check config changes every 5 seconds
            if now - last_cfg_check_time > 5.0:
                cfg = load_config()
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
                is_super_down = (parts[2].strip().lower() == "true")
                w_addr = parts[3].strip() if len(parts) > 3 else "none"
                wx = float(parts[4].strip()) if len(parts) > 4 else 0.0
                wy = float(parts[5].strip()) if len(parts) > 5 else 0.0

                file_open = dropspace_runtime.is_state_open()
                if not file_open and (now - last_toggle_time > 0.4):
                    is_open = False
                    summoned_by_edge = False
                elif file_open:
                    is_open = True
            except Exception:
                sleep_duration = 0.5
                continue

            # Strict drag state evaluation:
            # Active window is dragged if SUPER is held AND the window position physically moved!
            if not is_super_down or w_addr == "none":
                is_actively_dragged = False
                last_w_addr = None
                last_w_pos = None
                accumulated_drag = 0.0
            else:
                if last_w_addr != w_addr:
                    last_w_addr = w_addr
                    last_w_pos = (wx, wy)
                    accumulated_drag = 0.0
                    is_actively_dragged = False
                else:
                    if last_w_pos is not None:
                        dw = abs(wx - last_w_pos[0]) + abs(wy - last_w_pos[1])
                        accumulated_drag += dw
                        last_w_pos = (wx, wy)

                        if accumulated_drag >= 8.0:
                            is_actively_dragged = True

            is_dragging = is_actively_dragged

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
            if is_open and not summoned_by_edge:
                # Panel was opened manually (e.g. SUPER+D): stay in deep sleep and do not interfere
                sleep_duration = 0.5
            elif is_dragging or (is_open and summoned_by_edge) or is_super_down:
                # Dragging window, edge-triggered panel active, or SUPER is pressed: sample at ~30Hz
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
                summoned_by_edge = True
                last_toggle_time = now

            # Auto-hide when cursor is pulled back down below the cancel threshold
            # IMPORTANT: Only auto-hide if DropSpace was summoned by edge watcher!
            elif summoned_by_edge and is_open and rel_y > cancel_threshold and (now - last_toggle_time) > 0.35:
                subprocess.run(["omarchy-shell", "shell", "hide", "dropspace"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                is_open = False
                summoned_by_edge = False
                last_toggle_time = now
    finally:
        if is_open and summoned_by_edge:
            subprocess.run(["omarchy-shell", "shell", "hide", "dropspace"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass
