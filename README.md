# DropSpace

Visual workspace drag-and-drop overlay for Omarchy.

Drag a window onto a workspace card at the top of the screen to move the window and focus the target workspace.

![Drop Space](preview.png)

## Installation

```sh
omarchy plugin add https://github.com/harryxu/omarchy-dropspace.git --enable
```

Keybindings are registered automatically by the background service and restored on Hyprland reload:
- `SUPER + ALT + D`: Toggle workspace overlay
- `SUPER + Left Mouse Release`: Drop dragged window into target workspace

### Customizing Keybindings

The trigger shortcut defaults to `SUPER + ALT + D`. If this combination is already assigned in your `bindings.lua`, DropSpace leaves it alone.

You can modify or disable the shortcut:

- **Via CLI**:
  ```sh
  dropspace shortcut "SUPER + D"    # Set custom shortcut
  dropspace shortcut default        # Reset to SUPER + ALT + D
  dropspace shortcut disable        # Disable automatic shortcut
  ```

- **Via Configuration File (`~/.config/omarchy/dropspace.json`)**:
  ```json
  {
    "shortcut": "SUPER + D"
  }
  ```
  Set `"shortcut": false` to disable automatic binding and manage it manually in `~/.config/hypr/bindings.lua`.

## Usage

1. Press `SUPER + ALT + D` to open workspace targets.
2. Drag any window (`SUPER + Left Click`) onto a workspace card.
3. Release the mouse button to move the window to that workspace.
4. Press `Escape` or `SUPER + ALT + D` to dismiss without moving.

### Optional: Top-Edge Trigger

To automatically reveal the workspace bar when dragging a window toward the top edge, add this to `~/.config/hypr/autostart.lua`:

```lua
local dropspace_autostart = (os.getenv("HOME") or "") .. "/.config/omarchy/plugins/harryxu.dropspace/bin/dropspace-autostart.sh"
hl.exec_cmd(dropspace_autostart)
```

Then reload Hyprland:

```sh
hyprctl reload
```

### CLI Utility Setup

To use the `dropspace` CLI utility directly from anywhere in your terminal, run:

```sh
~/.config/omarchy/plugins/harryxu.dropspace/bin/dropspace setup
```

## Configuration

Configuration file: `~/.config/omarchy/dropspace.json`

```json
{
  "shortcut": "SUPER + ALT + D",
  "top_edge_threshold": 12,
  "cancel_threshold": 180
}
```

- `shortcut`: Toggle keybinding (string, default: `"SUPER + ALT + D"`, or `false` to disable).
- `top_edge_threshold`: Distance from screen top to trigger overlay (pixels, default: `12`).
- `cancel_threshold`: Downward distance to auto-dismiss when pulling away (pixels, default: `180`).

## Removal

```sh
omarchy plugin remove harryxu.dropspace
omarchy restart shell
```

Keybindings are released automatically.

Optional cleanup (stops background watchers, removes CLI symlink and data):
```sh
dropspace uninstall --purge
```

If you added the optional line to `~/.config/hypr/autostart.lua`, remove it and run `hyprctl reload`.

## Dependencies

- `python3`
- `hyprland`
- `omarchy-shell` (Quickshell)

## License

[MIT](LICENSE)