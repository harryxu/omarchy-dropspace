#!/usr/bin/env bash
# Register or unbind DropSpace Hyprland keybindings.
#
#   dropspace-keybind.sh bind       "SUPER + ALT + D"
#   dropspace-keybind.sh unbind     "SUPER + ALT + D"
#   dropspace-keybind.sh unbind-all "SUPER + ALT + D"
#
# Follows the Omarchy community best practice:
# - Uses `hyprctl eval` to evaluate Lua helpers directly.
# - Polite & Idempotent: does not hijack keys if bound by user; unbind only removes DropSpace bindings.
# - Preserves Omarchy native "Move window" binding on SUPER + mouse:272.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
HANDLER="$SCRIPT_DIR/drop-handler.sh"
DESCRIPTION="DropSpace: Toggle workspace targets"
MOUSE_DESCRIPTION="DropSpace: Drop window to workspace"
COMMAND="omarchy-shell shell toggle harryxu.dropspace '{}'"

action="${1:-}"
keys="${2:-}"

fail() { echo "dropspace keybind: $*" >&2; exit 1; }

[[ $action == bind || $action == unbind || $action == unbind-all ]] || fail "usage: dropspace-keybind.sh bind|unbind|unbind-all [\"MODS + KEY\"]"
command -v hyprctl >/dev/null 2>&1 || fail "hyprctl not found"
command -v jq >/dev/null 2>&1 || fail "jq not found"

lua_str() { printf '"%s"' "$(sed 's/["\\]/\\&/g' <<<"$1")"; }

parse_combo() {
  local combo="$1"
  modmask=0
  key=""
  IFS='+' read -ra parts <<<"$combo"
  for part in "${parts[@]}"; do
    part=$(tr -d '[:space:]' <<<"$part")
    [[ -n $part ]] || continue
    case "${part^^}" in
      SHIFT) modmask=$((modmask | 1)) ;;
      CAPS | CAPSLOCK) modmask=$((modmask | 2)) ;;
      CTRL | CONTROL) modmask=$((modmask | 4)) ;;
      ALT | MOD1) modmask=$((modmask | 8)) ;;
      MOD2) modmask=$((modmask | 16)) ;;
      MOD3) modmask=$((modmask | 32)) ;;
      SUPER | WIN | LOGO | MOD4) modmask=$((modmask | 64)) ;;
      MOD5) modmask=$((modmask | 128)) ;;
      *) [[ -z $key ]] || fail "more than one key in: $combo"; key="$part" ;;
    esac
  done
  [[ -n $key ]] || fail "no key found in: $combo"
}

bind_keyboard() {
  local target_keys="$1"
  [[ -n $target_keys ]] || return 0
  [[ $target_keys =~ ^[A-Za-z0-9_+[:space:]]+$ ]] || fail "refusing invalid keybinding: $target_keys"

  parse_combo "$target_keys"

  local holder
  holder=$(hyprctl binds -j | jq -r --argjson mods "$modmask" --arg key "$key" '
    map(select(.modmask == $mods and (.key | ascii_downcase) == ($key | ascii_downcase) and .submap == "" and .release == false))
    | if length == 0 then "" else (.[0].description // "(no description)") end')

  if [[ $holder == "$DESCRIPTION" ]]; then
    : # already ours
  elif [[ -n $holder ]]; then
    echo "dropspace keybind: $target_keys is already bound to '$holder'; not overriding" >&2
  else
    hyprctl eval "o.bind($(lua_str "$target_keys"), $(lua_str "$DESCRIPTION"), $(lua_str "$COMMAND"))" >/dev/null
  fi
}

unbind_keyboard() {
  local target_keys="$1"
  [[ -n $target_keys ]] || return 0
  [[ $target_keys =~ ^[A-Za-z0-9_+[:space:]]+$ ]] || return 0

  parse_combo "$target_keys"

  local holder
  holder=$(hyprctl binds -j | jq -r --argjson mods "$modmask" --arg key "$key" '
    map(select(.modmask == $mods and (.key | ascii_downcase) == ($key | ascii_downcase) and .submap == "" and .release == false))
    | if length == 0 then "" else (.[0].description // "(no description)") end')

  if [[ $holder == "$DESCRIPTION" ]]; then
    hyprctl eval "hl.unbind($(lua_str "$target_keys"))" >/dev/null
  fi
}

bind_mouse_release() {
  local has_drop_release
  has_drop_release=$(hyprctl binds -j | jq -r '
    any(.[]; .modmask == 64 and .key == "mouse:272" and .release == true and .description == "DropSpace: Drop window to workspace")')

  if [[ $has_drop_release != "true" ]]; then
    hyprctl eval "o.bind('SUPER + mouse:272', $(lua_str "$MOUSE_DESCRIPTION"), [[$HANDLER]], { mouse = true, release = true })" >/dev/null
  fi

  # Ensure default Move window is also present
  local has_move_window
  has_move_window=$(hyprctl binds -j | jq -r '
    any(.[]; .modmask == 64 and .key == "mouse:272" and .release == false and .description == "Move window")')

  if [[ $has_move_window != "true" ]]; then
    hyprctl eval "o.bind('SUPER + mouse:272', 'Move window', hl.dsp.window.drag(), { mouse = true })" >/dev/null
  fi
}

unbind_mouse_release() {
  local has_drop_release
  has_drop_release=$(hyprctl binds -j | jq -r '
    any(.[]; .modmask == 64 and .key == "mouse:272" and .release == true and .description == "DropSpace: Drop window to workspace")')

  if [[ $has_drop_release == "true" ]]; then
    # Unbinding mouse:272 removes all bindings on SUPER + mouse:272, so restore Move window immediately
    hyprctl eval "hl.unbind('SUPER + mouse:272')" >/dev/null
    hyprctl eval "o.bind('SUPER + mouse:272', 'Move window', hl.dsp.window.drag(), { mouse = true })" >/dev/null
  fi
}

case "$action" in
  bind)
    bind_keyboard "$keys"
    bind_mouse_release
    ;;
  unbind)
    unbind_keyboard "$keys"
    ;;
  unbind-all)
    unbind_keyboard "$keys"
    unbind_mouse_release
    ;;
esac
