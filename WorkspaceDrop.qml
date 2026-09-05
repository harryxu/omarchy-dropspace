import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.Commons
import qs.Ui

Item {
  id: root

  property bool opened: false
  property var shell: null
  property var manifest: null

  readonly property string home: Quickshell.env("HOME")
  readonly property string pluginDir: manifest && manifest.__sourceDir ? String(manifest.__sourceDir) : (home + "/.config/omarchy/plugins/dropspace")

  readonly property int baseCardWidth: 160
  readonly property int cardHeight: 100
  readonly property int cardSpacing: 16
  readonly property int topMargin: 36

  readonly property int maxWorkspaceCount: 5

  function workspaceIds() {
    var ids = []
    var values = Hyprland.workspaces.values
    var maxId = 1
    for (var i = 0; i < values.length; i++) {
      var id = values[i].id
      if (id > 0) {
        if (ids.indexOf(id) === -1) ids.push(id)
        if (id > maxId) maxId = id
      }
    }
    // Offer the next new empty workspace
    if (ids.indexOf(maxId + 1) === -1) ids.push(maxId + 1)

    // Ensure a sensible minimum (at least 1..4)
    var minCount = 4
    for (var m = 1; m <= minCount; m++) {
      if (ids.indexOf(m) === -1) ids.push(m)
    }

    ids.sort(function(a, b) { return a - b })
    return ids.slice(0, root.maxWorkspaceCount)
  }

  readonly property var activeWorkspaceList: root.workspaceIds()
  readonly property int cardWidth: {
    var count = activeWorkspaceList.length
    if (count <= 0) return baseCardWidth
    var available = (panel.width > 0 ? panel.width : 1280) - 64
    var computed = Math.floor((available - (count - 1) * cardSpacing) / count)
    return Math.max(100, Math.min(baseCardWidth, computed))
  }

  function open(payloadJson) {
    root.opened = true
    Quickshell.execDetached(["/usr/bin/python3", root.pluginDir + "/bin/dropspace-state.py", "open"])
  }

  function close() {
    root.opened = false
    Quickshell.execDetached(["/usr/bin/python3", root.pluginDir + "/bin/dropspace-state.py", "close"])
  }

  function dismiss() {
    root.close()
    if (root.shell && typeof root.shell.hide === "function") {
      root.shell.hide((root.manifest && root.manifest.id) || "dropspace")
    }
  }

  function toggle() {
    if (root.opened) root.dismiss()
    else root.open("{}")
  }

  IpcHandler {
    target: "harryxu.dropspace"
    function show(): string {
      root.open("{}")
      return "ok"
    }
    function hide(): string {
      root.dismiss()
      return "ok"
    }
    function toggle(): string {
      root.toggle()
      return "ok"
    }
    function state(): string {
      return root.opened ? "open" : "closed"
    }
  }

  Component.onDestruction: {
    root.close()
  }

  property int hoveredWorkspaceId: 0

  Process {
    id: cursorTracker
    command: ["/usr/bin/python3", root.pluginDir + "/bin/cursor-tracker.py"]
    running: root.opened
    stdout: SplitParser {
      onRead: function(line) {
        var str = String(line).trim()
        if (str === "dismiss" || str === "escape") {
          root.dismiss()
          return
        }
        var id = parseInt(str)
        if (!isNaN(id)) {
          root.hoveredWorkspaceId = id
        }
      }
    }
  }

  PanelWindow {
    id: panel
    visible: root.opened
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"

    WlrLayershell.namespace: "dropspace-overlay"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    exclusionMode: ExclusionMode.Ignore

    // Transparent to input so mouse dragging windows is not interrupted
    mask: Region {}

    // Top workspace bar dock container with semi-transparent background
    Rectangle {
      id: container
      anchors.top: parent.top
      anchors.topMargin: root.opened ? root.topMargin : -height - 50
      anchors.horizontalCenter: parent.horizontalCenter
      width: rowLayout.implicitWidth + 24
      height: rowLayout.implicitHeight + 20
      radius: (Style.cornerRadius > 0 ? Style.cornerRadius : 12) + 4

      // Semi-transparent background only behind the workspace bar dock
      color: Util.alpha(Color.menu.background, 0.82)
      border.color: Color.menu.border
      border.width: 1

      opacity: root.opened ? 1 : 0

      Behavior on anchors.topMargin {
        NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
      }
      Behavior on opacity {
        NumberAnimation { duration: 180 }
      }

      RowLayout {
        id: rowLayout
        anchors.centerIn: parent
        spacing: root.cardSpacing

        Repeater {
          model: root.activeWorkspaceList

          Rectangle {
            id: card
            required property int modelData

            function getWorkspace(wsId) {
              var values = Hyprland.workspaces.values
              for (var i = 0; i < values.length; i++) {
                if (values[i].id === wsId) return values[i]
              }
              return null
            }

            readonly property var ws: card.getWorkspace(modelData)
            readonly property bool isCurrent: Hyprland.focusedWorkspace !== null && Hyprland.focusedWorkspace.id === modelData
            readonly property bool isHovered: root.hoveredWorkspaceId === modelData
            readonly property int windowCount: ws !== null ? ws.toplevels.values.length : 0

            Layout.preferredWidth: root.cardWidth
            Layout.preferredHeight: root.cardHeight
            radius: Style.cornerRadius > 0 ? Style.cornerRadius : 12

            scale: card.isHovered ? 1.07 : 1.0
            Behavior on scale {
              NumberAnimation { duration: 130; easing.type: Easing.OutCubic }
            }

            // Colors strictly bound to Omarchy theme
            color: card.isHovered
              ? Util.alpha(Color.accent, 0.28)
              : (card.isCurrent ? Util.alpha(Color.accent, 0.16) : Util.alpha(Color.menu.background, 0.95))

            border.color: (card.isHovered || card.isCurrent) ? Color.accent : Color.menu.border
            border.width: card.isHovered ? 3 : (card.isCurrent ? 2 : 1)

            ColumnLayout {
              anchors.centerIn: parent
              spacing: 6

              RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 6

                Text {
                  text: card.isHovered ? "󰁝" : "󱂬"
                  color: (card.isHovered || card.isCurrent) ? Color.accent : Util.alpha(Color.menu.text, 0.7)
                  font.pixelSize: Style.font.title
                  font.family: Style.font.menuFamily
                }

                Text {
                  text: "Workspace " + card.modelData
                  color: (card.isHovered || card.isCurrent) ? Color.accent : Color.menu.text
                  font.bold: true
                  font.pixelSize: Style.font.title
                  font.family: Style.font.menuFamily
                }
              }

              // Status badge pill
              Rectangle {
                Layout.alignment: Qt.AlignHCenter
                implicitWidth: badgeText.implicitWidth + 14
                implicitHeight: badgeText.implicitHeight + 6
                radius: Style.cornerRadius > 0 ? Math.min(Style.cornerRadius, 8) : 8

                color: card.isHovered
                  ? Color.accent
                  : (card.isCurrent ? Color.accent : (card.windowCount > 0 ? Util.alpha(Color.foreground, 0.12) : "transparent"))

                border.color: (card.isHovered || card.isCurrent)
                  ? "transparent"
                  : (card.windowCount > 0 ? "transparent" : Util.alpha(Color.muted, 0.4))
                border.width: 1

                Text {
                  id: badgeText
                  anchors.centerIn: parent
                  text: card.isHovered
                    ? "Drop to move"
                    : (card.isCurrent ? "Active" : (card.windowCount > 0 ? (card.windowCount + (card.windowCount === 1 ? " window" : " windows")) : "Empty"))
                  color: (card.isHovered || card.isCurrent)
                    ? Color.background
                    : (card.windowCount > 0 ? Color.menu.text : Color.muted)
                  font.bold: card.isHovered || card.isCurrent
                  font.pixelSize: Style.font.caption
                  font.family: Style.font.menuFamily
                }
              }
            }
          }
        }
      }
    }
  }
}
