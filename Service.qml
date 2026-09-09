import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

Item {
  id: root

  // ---- host contract ----
  property var shell: null
  property var manifest: null

  readonly property string home: Quickshell.env("HOME") || ""
  readonly property string manifestId: (manifest && manifest.id) ? manifest.id : "harryxu.dropspace"

  readonly property string pluginRoot: {
    var u = Qt.resolvedUrl(".").toString()
    if (u.indexOf("file://") === 0) u = u.substring(7)
    while (u.length > 1 && u.charAt(u.length - 1) === "/")
      u = u.substring(0, u.length - 1)
    return u
  }

  readonly property string configPath: home + "/.config/omarchy/dropspace.json"

  // ---- Keybinding configuration ----
  readonly property string defaultShortcut: "SUPER + ALT + D"
  property string keybind: defaultShortcut
  property string boundKeys: ""
  property bool alive: true

  FileView {
    id: configFile
    path: root.configPath
    watchChanges: true
    printErrors: false
    onLoaded: root.handleConfigLoaded()
    onFileChanged: reload()
  }

  function handleConfigLoaded() {
    var shortcut = root.defaultShortcut
    try {
      var raw = configFile.text()
      if (raw && raw.trim().length > 0) {
        var parsed = JSON.parse(raw)
        if (parsed.auto_bind === false || parsed.shortcut === false) {
          shortcut = ""
        } else if (typeof parsed.shortcut === "string" && parsed.shortcut.trim().length > 0) {
          shortcut = parsed.shortcut.trim()
        }
      }
    } catch (e) {
      // Ignore transient JSON parse errors during writes
    }
    root.keybind = shortcut
  }

  onKeybindChanged: root.applyKeybind()

  function applyKeybind() {
    if (root.boundKeys !== "" && root.boundKeys !== root.keybind) {
      root.enqueueKeybind("unbind", root.boundKeys)
    }
    root.boundKeys = root.keybind
    root.enqueueKeybind("bind", root.boundKeys)
  }

  // Serialized queue for keybind actions
  property var keybindQueue: []
  function enqueueKeybind(action, keys) {
    root.keybindQueue.push(["bash", root.pluginRoot + "/bin/dropspace-keybind.sh", action, keys || ""])
    if (!keybindProc.running) root.runNextKeybind()
  }

  function runNextKeybind() {
    if (root.keybindQueue.length === 0) return
    keybindProc.command = root.keybindQueue.shift()
    keybindProc.running = true
  }

  Process {
    id: keybindProc
    running: false
    stderr: SplitParser {
      onRead: function(data) {
        console.warn("dropspace keybind: " + data)
      }
    }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        console.warn("dropspace: keybind.sh exited " + exitCode)
      }
      root.runNextKeybind()
    }
  }

  // Hyprland config reloads wipe runtime bindings; restore ours
  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (event && String(event.name) === "configreloaded") {
        root.enqueueKeybind("bind", root.boundKeys)
      }
    }
  }

  Component.onCompleted: Qt.callLater(function() {
    if (root.alive !== true) return
    root.handleConfigLoaded()
    root.applyKeybind()
  })

  Component.onDestruction: {
    root.alive = false
    var disabled = false
    try {
      var reg = root.shell ? root.shell.pluginRegistry : null
      disabled = !reg || reg.isEnabled(root.manifestId) === false
    } catch (e) {}

    if (disabled && root.boundKeys !== "") {
      Quickshell.execDetached(["bash", root.pluginRoot + "/bin/dropspace-keybind.sh", "unbind-all", root.boundKeys])
    }
  }

  IpcHandler {
    target: "harryxu.dropspace.service"
    function status(): string {
      var state = {
        "auto_bind": root.keybind !== "",
        "shortcut": root.keybind !== "" ? root.keybind : "disabled",
        "bound": root.boundKeys,
        "default": root.defaultShortcut
      }
      return JSON.stringify(state)
    }
    function reregister(): string {
      root.applyKeybind()
      return "triggered"
    }
    function unregister(): string {
      root.enqueueKeybind("unbind-all", root.boundKeys)
      root.boundKeys = ""
      return "triggered"
    }
  }
}
