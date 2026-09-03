# AGENTS.md

Context, commands, conventions, and architectural constraints for AI coding agents working on the DropSpace project.

## Critical Rules
- **Git commits**: DO NOT make git commits on your own without being asked by the user.
- **Portability**: NEVER hardcode absolute user paths (such as `/home/...`). Always use dynamic path resolution:
  - In QML: `manifest.__sourceDir` or fallback to `Quickshell.env("HOME") + "/.config/omarchy/plugins/dropspace"`
  - In Shell scripts: `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` (use `readlink -f` for symlinks)
  - In Python scripts: `os.path.expanduser("~/.config/omarchy/...")`
  - In Lua configurations: `(os.getenv("HOME") or "") .. "/.config/omarchy/plugins/dropspace/..."`
- **Theme Binding**: Never hardcode colors, fonts, or corner radii in QML. Always bind to `Color.*` and `Style.*` from `qs.Commons`.
- **Compositor Compatibility**: Omarchy runs Hyprland with Lua configuration. Dispatch commands must follow Lua syntax, e.g., `hyprctl dispatch 'hl.dsp.window.move({ workspace = "<id>" })'`.

## Project Overview
DropSpace is an Omarchy Shell plugin for Hyprland that provides visual workspace drag-and-drop capabilities:
- **UI Component**: Built on Quickshell (`QtQuick` / `QML`), rendered as an overlay layer (`WlrLayer.Overlay`).
- **Input Transparency**: Uses `mask: Region {}` on the `PanelWindow` so compositor window dragging gestures (`bindm`) are never interrupted.
- **Dynamic Workspaces**: Discovers workspaces dynamically from `Hyprland.workspaces.values` and auto-provisions `maxId + 1` for new workspace spawning.
- **Real-time Hover Feedback**: When UI is active (`root.opened`), a temporary streaming process (`bin/cursor-tracker.py`) calculates cursor overlap and feeds hover states into QML for card scaling and glow. It automatically terminates when DropSpace closes.
- **Optional Edge Watcher**: `bin/edge-watcher.py` provides an optional, adaptive-sleeping daemon for auto-summoning on top-edge push. Disabled by default (user prefers pure `SUPER + D` mode).

## Common Verification & Dev Commands

### Testing & Interacting with the Shell Plugin
- **Restart Omarchy Shell** (required after modifying `.qml` because file watching is disabled by default in Omarchy):
  ```bash
  omarchy-restart-shell
  ```
- **Rescan plugins**:
  ```bash
  omarchy-shell shell rescanPlugins
  ```
- **Show / Hide / Toggle DropSpace UI**:
  ```bash
  omarchy-shell dropspace show
  omarchy-shell dropspace hide
  omarchy-shell dropspace toggle
  ```
- **Check DropSpace State**:
  ```bash
  omarchy-shell dropspace state
  ```

### Testing Backend Scripts
- **Check DropSpace CLI status**:
  ```bash
  dropspace status
  ```
- **Enable / Disable Edge Watcher**:
  ```bash
  dropspace edge-watcher enable
  dropspace edge-watcher disable
  ```
- **Test Drop Handler (reads cursor position and logs result)**:
  ```bash
  python3 bin/drop-handler.py
  cat /tmp/dropspace.log
  ```
- **Test Cursor Tracker (streams hovered workspace ID to stdout)**:
  ```bash
  python3 bin/cursor-tracker.py
  ```

### Hyprland Commands
- **Reload Hyprland configuration**:
  ```bash
  hyprctl reload
  ```
- **Check Hyprland config errors**:
  ```bash
  hyprctl configerrors
  ```
- **Inspect active layers**:
  ```bash
  hyprctl layers | grep -A 4 -i dropspace
  ```

## File Map & Responsibilities
- `manifest.json`: Omarchy plugin metadata (id, kind `overlay`, `keepLoaded: true`, entryPoint).
- `WorkspaceDrop.qml`: Main overlay interface. Hosts the top floating dock, dynamic cards, hover animation, and IPC handler.
- `config.example.json`: Default configuration template.
- `bin/dropspace`: User-facing CLI tool for checking status and toggling edge-watcher.
- `bin/dropspace-autostart.sh`: Conditional autostart script invoked by `~/.config/hypr/autostart.lua`.
- `bin/drop-handler.py`: Core drop computation script. Evaluates cursor coordinates on mouse release and moves the active window via Hyprland Lua dispatch.
- `bin/drop-handler.sh`: Executable wrapper for `drop-handler.py`.
- `bin/cursor-tracker.py`: High-speed, microsecond socket polling script running only while UI is open to stream hovered workspace index.
- `bin/edge-watcher.py`: Optional daemon implementing multi-tier adaptive sleep for top-edge push triggering.
- `~/.config/omarchy/dropspace.json`: User runtime configuration (`edge_watcher`, thresholds).
