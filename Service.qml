import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

Item {
  id: root

  property var shell: null
  property var manifest: null

  readonly property string home: Quickshell.env("HOME") || ""
  readonly property string manifestId: (manifest && manifest.id) ? manifest.id : "harryxu.dropspace"

  // Dynamically resolve handler path
  readonly property string handlerPath: {
    var url = Qt.resolvedUrl("bin/drop-handler.sh").toString()
    if (url.indexOf("file://") === 0) {
      return url.substring(7)
    }
    return home + "/.config/omarchy/plugins/" + manifestId + "/bin/drop-handler.sh"
  }

  readonly property string configPath: home + "/.config/omarchy/dropspace.json"

  // Configuration and registration state
  property string activeShortcut: "SUPER + d"
  property string boundShortcut: ""
  property bool autoBindEnabled: true
  property bool isRegistered: false
  property int attempts: 0
  readonly property int maxAttempts: 5

  FileView {
    id: configFile
    path: root.configPath
    watchChanges: true
    printErrors: false
    onLoaded: root.handleConfigLoaded()
    onFileChanged: reload()
  }

  function handleConfigLoaded() {
    var shortcut = "SUPER + d"
    var autoBind = true
    try {
      var raw = configFile.text()
      if (raw && raw.trim().length > 0) {
        var parsed = JSON.parse(raw)
        if (parsed.auto_bind === false || parsed.shortcut === false) {
          autoBind = false
        } else if (typeof parsed.shortcut === "string" && parsed.shortcut.trim().length > 0) {
          shortcut = parsed.shortcut.trim()
        }
      }
    } catch (e) {
      // Ignore transient JSON parse errors during file writes
    }

    if (root.activeShortcut !== shortcut || root.autoBindEnabled !== autoBind) {
      root.activeShortcut = shortcut
      root.autoBindEnabled = autoBind
      applyDebounceTimer.restart()
    }
  }

  function buildRegisterLua() {
    var id = manifestId
    var handler = handlerPath
    var newKey = activeShortcut
    var oldKey = boundShortcut

    var statements = [
      "pcall(function() hl.unbind(\"SUPER + mouse:272\") end);",
      "pcall(function() o.bind(\"SUPER + mouse:272\", \"Move window\", hl.dsp.window.drag(), { mouse = true }) end);",
      "o.bind(\"SUPER + mouse:272\", \"DropSpace: Drop window to workspace\", [[" + handler + "]], { mouse = true, release = true });"
    ]

    if (oldKey && oldKey.length > 0 && oldKey !== newKey) {
      statements.push("pcall(function() hl.unbind(\"" + oldKey + "\") end);")
    }

    if (autoBindEnabled && newKey && newKey.length > 0) {
      statements.push("pcall(function() hl.unbind(\"" + newKey + "\") end);")
      statements.push("o.bind(\"" + newKey + "\", \"DropSpace: Toggle workspace targets\", \"omarchy-shell shell toggle " + id + " '{}'\");")
    }

    statements.push("_G.__dropspace_shortcut = true;")
    statements.push("return 'registered'")

    return statements.join(" ")
  }

  function buildUnregisterLua(unregKey) {
    var statements = [
      "pcall(function() hl.unbind(\"SUPER + mouse:272\") end);",
      "pcall(function() o.bind(\"SUPER + mouse:272\", \"Move window\", hl.dsp.window.drag(), { mouse = true }) end);"
    ]
    var key = unregKey || boundShortcut || activeShortcut
    if (key && key.length > 0) {
      statements.push("pcall(function() hl.unbind(\"" + key + "\") end);")
    }
    statements.push("_G.__dropspace_shortcut = nil;")
    statements.push("return 'unregistered'")
    return statements.join(" ")
  }

  function registerShortcuts() {
    if (!autoBindEnabled) {
      if (root.isRegistered) {
        unregisterAll()
      }
      return
    }

    var lua = buildRegisterLua()
    registerProc.command = ["bash", "-c", "echo '" + lua + "' | hyprctl repl"]
    registerProc.running = true
  }

  function unregisterAll() {
    var lua = buildUnregisterLua(boundShortcut || activeShortcut)
    Quickshell.execDetached(["bash", "-c", "echo '" + lua + "' | hyprctl repl"])
    root.boundShortcut = ""
    root.isRegistered = false
  }

  Process {
    id: registerProc
    running: false
    stdout: StdioCollector {
      onStreamFinished: {
        var res = (text || "").trim()
        if (res.indexOf("registered") !== -1 || res.indexOf("present") !== -1) {
          root.isRegistered = true
          root.boundShortcut = root.activeShortcut
          root.attempts = 0
        } else {
          if (root.attempts < root.maxAttempts) {
            root.attempts++
            retryTimer.restart()
          }
        }
      }
    }
  }

  Timer {
    id: applyDebounceTimer
    interval: 200
    repeat: false
    onTriggered: {
      root.attempts = 0
      root.registerShortcuts()
    }
  }

  Timer {
    id: retryTimer
    interval: 2000
    repeat: false
    onTriggered: root.registerShortcuts()
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (event && event.name === "configreloaded") {
        root.isRegistered = false
        applyDebounceTimer.restart()
      }
    }
  }

  Component.onCompleted: {
    applyDebounceTimer.restart()
  }

  Component.onDestruction: {
    root.unregisterAll()
  }

  IpcHandler {
    target: "harryxu.dropspace.service"
    function status(): string {
      var state = {
        "registered": root.isRegistered,
        "auto_bind": root.autoBindEnabled,
        "shortcut": root.activeShortcut,
        "bound": root.boundShortcut,
        "handler": root.handlerPath
      }
      return JSON.stringify(state)
    }
    function reregister(): string {
      root.isRegistered = false
      root.registerShortcuts()
      return "triggered"
    }
    function unregister(): string {
      root.unregisterAll()
      return "triggered"
    }
  }
}
