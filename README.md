# DropSpace

Visual workspace drag-and-drop overlay for Omarchy Quattro and Hyprland.

Drag a window onto a target workspace card at the top of the screen and release it to move the window and switch workspace focus seamlessly.

---

## Install

### 1. Add the Plugin to Omarchy

```sh
omarchy plugin add https://github.com/harryxu/dropspace.git --enable
```

### 2. Initialize Setup

Run the setup helper to create the CLI symlink (`~/.local/bin/dropspace`) and initialize default configuration:

```sh
~/.config/omarchy/plugins/dropspace/bin/dropspace setup
```

### 3. Add Hyprland Keybindings

Add the following bindings to `~/.config/hypr/bindings.lua`:

```lua
local dropspace_handler = (os.getenv("HOME") or "") .. "/.config/omarchy/plugins/dropspace/bin/drop-handler.sh"
o.bind("SUPER + d", "DropSpace: Toggle workspace targets", "omarchy-shell shell toggle dropspace '{}'")
o.bind("SUPER + mouse:272", "DropSpace: Drop window to workspace", dropspace_handler, { mouse = true, release = true })
```

*(Optional)* If you plan to use the adaptive top-edge push trigger daemon, add this to `~/.config/hypr/autostart.lua`:

```lua
local dropspace_autostart = (os.getenv("HOME") or "") .. "/.config/omarchy/plugins/dropspace/bin/dropspace-autostart.sh"
o.exec_on_start(dropspace_autostart)
```

Reload Hyprland to apply the bindings:

```sh
hyprctl reload
```

---

## Usage

### Default Mode (Zero Background Daemons)

1. Press `SUPER + D` to toggle the workspace bar at the top of the screen.
2. Drag any window using `SUPER + Left Click` onto a target workspace card (e.g., Workspace 2).
3. **Release mouse button**: the window moves to that workspace, focus switches, and the workspace bar automatically closes.
4. Press `Escape` or press `SUPER + D` again to dismiss without dropping.

### Optional: Top Edge Push Trigger

To enable auto-summoning when pushing a window to the top edge:

```sh
dropspace edge-watcher enable
```

With edge watcher enabled:
1. Drag a window toward the top center of the screen; the bar automatically slides down.
2. Hover over the desired workspace card and release.

To disable and return to default mode:

```sh
dropspace edge-watcher disable
```

---

## Configure

Configuration file location: `~/.config/omarchy/dropspace.json`

```json
{
  "edge_watcher": false,
  "top_edge_threshold": 12,
  "cancel_threshold": 180
}
```

- `edge_watcher`: `false` (default, disabled, zero background daemons) / `true` (adaptive top-edge trigger enabled).
- `top_edge_threshold`: Distance from the top edge to summon the panel (pixels, default: `12`).
- `cancel_threshold`: Downward distance from top edge to auto-dismiss (pixels, default: `180`).

---

## Remove

To safely and completely remove DropSpace without leaving dangling processes or broken bindings:

### 1. Run the Uninstall Helper

Stops running daemons, removes temporary files, and unlinks `~/.local/bin/dropspace`:

```sh
dropspace uninstall
```

*(Optional: pass `--purge` to delete `~/.config/omarchy/dropspace.json` as well).*

### 2. Remove the Plugin from Omarchy

```sh
omarchy plugin remove dropspace
```

### 3. Clean up Hyprland Configuration

Remove or comment out the DropSpace lines from `~/.config/hypr/bindings.lua` (and `~/.config/hypr/autostart.lua` if added), then reload:

```sh
hyprctl reload
```

---

## Dependencies & Permissions

- **Runtime Dependencies**: `python3`, `hyprland`, `omarchy-shell` (Quickshell).
- **Permissions**: Runs entirely within standard user permissions. Never requires `sudo`.
- **Background Processes**: By default, **zero persistent background daemons** are used. The cursor tracker runs only while the overlay is actively open and terminates automatically when closed.
