# DropSpace (Omarchy Shell Plugin)

**DropSpace** is a visual workspace drag-and-drop plugin for Omarchy and Hyprland.

It provides a workspace target bar at the top of the screen: drag a window onto a workspace card and release it to move the window to that workspace and switch focus.

---

## Features

- **Two Operation Modes**:
  - **Default Mode (No background daemons)**: Press `SUPER + D` to toggle the workspace bar, drag a window onto a card, and release. No persistent background processes.
  - **Top Edge Trigger (Adaptive sleep)**: Optional `edge-watcher` daemon that slides down the workspace bar when pushing a window toward the top edge.
- **Adaptive Sleep**:
  - When the cursor is in regular screen areas, the optional daemon stays in deep sleep (polling once per second) with negligible CPU overhead.
  - Polling frequency ramps up only near the top edge and returns to deep sleep immediately after leaving.
- **CLI Utility**:
  - `dropspace status`: View daemon and configuration status.
  - `dropspace edge-watcher enable`: Enable the top-edge trigger daemon.
  - `dropspace edge-watcher disable`: Disable the top-edge trigger daemon.
- **Input Transparency**: Uses `mask: Region {}` on the overlay panel to preserve compositor window drag gestures without input blocking.

---

## Usage

### Default: Keybind Trigger (Zero Background Daemons)

1. Press `SUPER + D` to toggle the workspace bar at the top of the screen.
2. Drag the target window using `SUPER + Left Click` onto a target workspace card (e.g., Workspace 2).
3. **Release the mouse button**: the window moves to that workspace, focus switches, and the workspace bar automatically closes.

### Optional: Top Edge Push Trigger

To enable triggering by pushing a window to the top edge:

```bash
dropspace edge-watcher enable
```

With this enabled:

1. Drag a window with `SUPER + Left Click` toward the top center of the screen.
2. The workspace bar automatically slides down.
3. Hover over the desired workspace card and release the mouse button.

To disable and return to default mode:

```bash
dropspace edge-watcher disable
```

---

## Configuration

Configuration file location: `~/.config/omarchy/dropspace.json`

```json
{
  "edge_watcher": false,
  "top_edge_threshold": 12,
  "cancel_threshold": 180
}
```

- `edge_watcher`: `false` (default, disabled, no background daemon) / `true` (enable adaptive top-edge trigger).
- `top_edge_threshold`: Distance from the top screen edge to trigger the panel (pixels, default: `12`).
- `cancel_threshold`: Distance downward from the top edge to auto-dismiss when pulling away (pixels, default: `180`).

---

## Project Structure

```
dropspace/
├── manifest.json                # Omarchy plugin metadata
├── WorkspaceDrop.qml            # Quickshell top card overlay UI
├── config.example.json          # Default configuration template
├── bin/
│   ├── dropspace                # CLI management utility (symlinked to ~/.local/bin/dropspace)
│   ├── dropspace-autostart.sh   # Autostart check script (starts daemon only if enabled)
│   ├── edge-watcher.py          # Adaptive top-edge trigger daemon
│   ├── drop-handler.py          # Drop coordinate calculation and Hyprland Lua dispatch
│   └── drop-handler.sh          # Drop execution wrapper
└── README.md
```
