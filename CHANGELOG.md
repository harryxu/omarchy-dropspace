# Changelog

## [v1.1.0]

### Added
- Auto-register keybindings via background service (`Service.qml`) without manual `bindings.lua` setup.
- Click-to-switch workspace support by clicking workspace cards directly without moving windows.
- Proportional window wireframe previews with dynamic aspect ratio calculation based on monitor geometries.
- Live Hyprland window geometries synchronization via IPC to keep wireframe previews up to date.
- Window application name display inside wireframes with adaptive font size and overflow protection.
- Drop shadow effect for workspace container dock and adjusted background opacity.

### Changed
- Default trigger keybinding updated to `SUPER + ALT + D` across Service, CLI, and configuration.
- Standardized card layout and dynamic aspect ratio calculations across QML and Python runtime helpers.
- Refactored shared card layout constants and functions into `dropspace_runtime.py`.
- Reorganized and streamlined usage and optional setup instructions in `README.md`.
- Updated preview image for improved visual representation.

## [v1.0.0] - 2026-09-08

- Initial release