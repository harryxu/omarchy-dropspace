# DropSpace

Visual workspace drag-and-drop overlay for Omarchy.

Drag a window onto a target workspace card at the top of the screen and release it to move the window and switch workspace focus seamlessly.

![Drop Space](preview.png)


---

## Install

```sh
omarchy plugin add https://github.com/harryxu/omarchy-dropspace.git --enable
omarchy restart shell
```

**That's it!** DropSpace is now ready to [use](#usage) immediately with `SUPER + D`. Keybindings (`SUPER + D` to toggle and `SUPER + Left Mouse Release` to drop) are managed automatically by DropSpace's background service.

---

### Customizing the Shortcut

DropSpace works out of the box with `SUPER + D`, but you can customize it at any time:

- **Via CLI** (Instant hot reload, no restart required):
  ```sh
  dropspace shortcut "SUPER + ALT + D"    # Set custom shortcut
  dropspace shortcut default              # Restore default SUPER + D
  dropspace shortcut disable              # Disable auto-managed shortcut
  ```

- **Via Configuration File**:
  Edit `~/.config/omarchy/dropspace.json`:
  ```json
  {
    "shortcut": "SUPER + ALT + D"
  }
  ```

- **Via `~/.config/hypr/bindings.lua` (Manual Management)**:
  If you prefer managing all bindings in your Hyprland configuration:
  1. Set `"shortcut": false` in `~/.config/omarchy/dropspace.json`.
  2. Add your custom binding to `~/.config/hypr/bindings.lua`:
     ```lua
     o.bind("SUPER + z", "DropSpace: Toggle workspace targets", "omarchy-shell shell toggle harryxu.dropspace '{}'")
     ```

---

### Optional Setup

#### Enable Top Edge Push Trigger
If you want the workspace bar to automatically slide down when dragging a window toward the top edge of the screen, add this to `~/.config/hypr/autostart.lua`:

```lua
local dropspace_autostart = (os.getenv("HOME") or "") .. "/.config/omarchy/plugins/harryxu.dropspace/bin/dropspace-autostart.sh"
hl.exec_cmd(dropspace_autostart)
```

Then run `hyprctl reload` to launch it immediately.

#### CLI Command Symlink
If you want to use the `dropspace` CLI utility directly from anywhere in your terminal (to check status, view configuration, customize shortcuts, or uninstall), run:

```sh
~/.config/omarchy/plugins/harryxu.dropspace/bin/dropspace setup
```

---

## Usage

### Default Mode (No Background Daemons)

1. Press `SUPER + D` to toggle the workspace bar at the top of the screen.
2. Drag any window using `SUPER + Left Click` onto a target workspace card (e.g., Workspace 2).
3. **Release mouse button**: the window moves to that workspace, focus switches, and the workspace bar automatically closes.
4. Press `Escape` or press `SUPER + D` again to dismiss without dropping.

### Optional: Top Edge Push Trigger

If you added the optional autostart line to `~/.config/hypr/autostart.lua` during installation, top-edge triggering is automatically enabled:

1. Drag any window with `SUPER + Left Click` toward the top center of the screen; the workspace bar automatically slides down.
2. Hover over the desired workspace card and release the mouse button.
3. If you change your mind, simply pull the window back down below the cancel threshold to auto-dismiss.

*(To disable top-edge triggering, simply remove or comment out the autostart line in `~/.config/hypr/autostart.lua` and reload Hyprland).*

---

## Configure

Configuration file location: `~/.config/omarchy/dropspace.json`

```json
{
  "shortcut": "SUPER + d",
  "top_edge_threshold": 12,
  "cancel_threshold": 180
}
```

- `shortcut`: Trigger keybinding to toggle the overlay (string, default: `"SUPER + d"`, or `false` to disable auto-binding).
- `top_edge_threshold`: Distance from the top screen edge to summon the panel (pixels, default: `12`).
- `cancel_threshold`: Downward distance from the top edge to auto-dismiss when pulling away (pixels, default: `180`).

---

## Remove

To safely and completely remove DropSpace:

### 1. Run the Uninstall Helper (Optional)

Stops background daemons, cleans up temporary files, and removes the CLI symlink:

```sh
dropspace uninstall
# (Or: ~/.config/omarchy/plugins/harryxu.dropspace/bin/dropspace uninstall)
```

*(Optional: pass `--purge` to delete `~/.config/omarchy/dropspace.json` as well).*

### 2. Remove the Plugin from Omarchy

```sh
omarchy plugin remove harryxu.dropspace
omarchy restart shell
```

Keybindings are automatically released when the plugin is removed. If you added optional top-edge triggering in `~/.config/hypr/autostart.lua` (or legacy manual lines in `bindings.lua`), remove those lines and run `hyprctl reload`.

---

## Dependencies & Permissions

- **Runtime Dependencies**: `python3`, `hyprland`, `omarchy-shell` (Quickshell).
- **Permissions**: Runs entirely within standard user.
- **Background Processes**: By default, **no persistent background daemons** are used. The cursor tracker runs only while the overlay is actively open and terminates automatically when closed.

## License

[MIT](LICENSE)