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
  readonly property string pluginDir: manifest && manifest.__sourceDir ? String(manifest.__sourceDir) : (home + "/.config/omarchy/plugins/harryxu.dropspace")

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

  property var workspaceWindows: ({})
  property var workspaceAspects: ({})

  function updateWindowData(jsonStr) {
    if (!jsonStr || typeof jsonStr !== "string" || jsonStr.trim().indexOf("{") !== 0) return
    try {
      var data = JSON.parse(jsonStr)
      var monitors = data.monitors || []
      var clients = data.clients || []

      var monMap = {}
      for (var m = 0; m < monitors.length; m++) {
        var mon = monitors[m]
        var s = (mon.scale && mon.scale > 0) ? mon.scale : 1.0
        monMap[mon.id] = {
          x: mon.x / s,
          y: mon.y / s,
          width: mon.width / s,
          height: mon.height / s
        }
      }

      var defaultMon = monitors.length > 0 ? monMap[monitors[0].id] : { x: 0, y: 0, width: 1920, height: 1080 }
      var wsMap = {}
      var aspectMap = {}

      for (var i = 0; i < clients.length; i++) {
        var c = clients[i]
        if (!c.workspace || c.hidden || !c.size || c.size[0] <= 0 || c.size[1] <= 0) continue

        var wid = c.workspace.id
        if (wid <= 0) continue

        var targetMon = monMap[c.monitor] || defaultMon
        aspectMap[wid] = targetMon.width / targetMon.height

        var rx = (c.at[0] - targetMon.x) / targetMon.width
        var ry = (c.at[1] - targetMon.y) / targetMon.height
        var rw = c.size[0] / targetMon.width
        var rh = c.size[1] / targetMon.height

        rx = Math.max(0, Math.min(0.98, rx))
        ry = Math.max(0, Math.min(0.98, ry))
        rw = Math.max(0.04, Math.min(1 - rx, rw))
        rh = Math.max(0.04, Math.min(1 - ry, rh))

        if (!wsMap[wid]) wsMap[wid] = []
        wsMap[wid].push({
          rx: rx,
          ry: ry,
          rw: rw,
          rh: rh,
          activated: (c.focusHistoryID === 0),
          floating: !!c.floating,
          appClass: c["class"] || "",
          title: c.title || "",
          address: c.address || ""
        })
      }

      root.workspaceWindows = wsMap
      root.workspaceAspects = aspectMap
    } catch(e) {
      console.warn("Failed to parse window data: " + e)
    }
  }

  function refreshWindows() {
    if (clientsFetcher.running) {
      clientsFetcher.running = false
    }
    clientsFetcher.running = true
  }

  Process {
    id: clientsFetcher
    command: ["bash", "-c", "echo '{\"monitors\":'$(hyprctl monitors -j)',\"clients\":'$(hyprctl clients -j)'}'"]
    running: false
    stdout: StdioCollector {
      onStreamFinished: {
        root.updateWindowData(text)
      }
    }
  }

  Timer {
    id: livePollTimer
    interval: 500
    running: root.opened
    repeat: true
    onTriggered: root.refreshWindows()
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (root.opened) {
        root.refreshWindows()
      }
    }
    function onFocusedWorkspaceChanged() {
      if (root.opened) {
        root.refreshWindows()
      }
    }
  }

  onOpenedChanged: {
    if (root.opened) {
      root.refreshWindows()
    }
  }

  function open(payloadJson) {
    root.opened = true
    root.refreshWindows()
    Quickshell.execDetached(["/usr/bin/python3", root.pluginDir + "/bin/dropspace-state.py", "open"])
  }

  function close() {
    root.opened = false
    Quickshell.execDetached(["/usr/bin/python3", root.pluginDir + "/bin/dropspace-state.py", "close"])
  }

  function switchToWorkspace(wsId) {
    Quickshell.execDetached(["hyprctl", "dispatch", "hl.dsp.focus({ workspace = \"" + wsId + "\" })"])
    root.dismiss()
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

    // Allow mouse clicks on the container dock while keeping the rest click-through
    mask: Region { item: container }

    // Top workspace bar dock container with semi-transparent background
    Rectangle {
      id: container
      anchors.top: parent.top
      anchors.topMargin: root.opened ? root.topMargin : -height - 50
      anchors.horizontalCenter: parent.horizontalCenter
      width: rowLayout.implicitWidth + 24
      height: rowLayout.implicitHeight + 26
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

          ColumnLayout {
            id: workspaceSlot
            required property int modelData

            function getWorkspace(wsId) {
              var values = Hyprland.workspaces.values
              for (var i = 0; i < values.length; i++) {
                if (values[i].id === wsId) return values[i]
              }
              return null
            }

            readonly property var ws: workspaceSlot.getWorkspace(modelData)
            readonly property bool isCurrent: Hyprland.focusedWorkspace !== null && Hyprland.focusedWorkspace.id === modelData
            readonly property bool isDropTarget: root.hoveredWorkspaceId === modelData
            readonly property bool isMouseHovered: cardMouseArea.containsMouse || textMouseArea.containsMouse
            readonly property var windowList: root.workspaceWindows[modelData] || []
            readonly property int windowCount: windowList.length
            readonly property string workspaceName: (ws && ws.name && ws.name !== "" && ws.name !== String(modelData)) ? ws.name : ("Workspace " + modelData)

            spacing: 8
            Layout.alignment: Qt.AlignHCenter

            Rectangle {
              id: card

              readonly property real aspect: root.workspaceAspects[workspaceSlot.modelData] || (panel.screen ? (panel.screen.width / panel.screen.height) : (16 / 10))

              Layout.preferredWidth: root.cardWidth
              Layout.preferredHeight: Math.round(root.cardWidth / aspect)
              Layout.alignment: Qt.AlignHCenter
              radius: Style.cornerRadius > 0 ? Math.min(Style.cornerRadius, 8) : 6
              clip: true

              scale: workspaceSlot.isDropTarget ? 1.05 : (workspaceSlot.isMouseHovered ? 1.03 : 1.0)
              Behavior on scale {
                NumberAnimation { duration: 130; easing.type: Easing.OutCubic }
              }

              // Colors strictly bound to Omarchy theme
              color: workspaceSlot.isDropTarget
                ? Util.alpha(Color.accent, 0.28)
                : (workspaceSlot.isMouseHovered
                    ? Util.alpha(Color.accent, 0.22)
                    : (workspaceSlot.isCurrent ? Util.alpha(Color.accent, 0.16) : Util.alpha(Color.menu.background, 0.88)))

              border.color: (workspaceSlot.isDropTarget || workspaceSlot.isMouseHovered || workspaceSlot.isCurrent) ? Color.accent : Color.menu.border
              border.width: workspaceSlot.isDropTarget ? 3 : ((workspaceSlot.isMouseHovered || workspaceSlot.isCurrent) ? 2 : 1)

              // Empty workspace placeholder
              Text {
                anchors.centerIn: parent
                visible: workspaceSlot.windowCount === 0 && !workspaceSlot.isDropTarget
                text: "Empty"
                color: Util.alpha(Color.muted, 0.65)
                font.pixelSize: Style.font.caption
                font.family: Style.font.menuFamily
              }

              // Wireframe window rectangles directly inside card
              Repeater {
                model: workspaceSlot.windowList

                Rectangle {
                  id: winWireframe
                  required property var modelData

                  x: Math.round(modelData.rx * card.width)
                  y: Math.round(modelData.ry * card.height)
                  width: Math.max(5, Math.round(modelData.rw * card.width))
                  height: Math.max(5, Math.round(modelData.rh * card.height))

                  radius: Math.min(3, card.radius)

                  color: modelData.activated
                    ? Util.alpha(Color.accent, 0.35)
                    : (workspaceSlot.isCurrent
                        ? Util.alpha(Color.accent, 0.18)
                        : Util.alpha(Color.foreground, 0.12))

                  border.color: modelData.activated
                    ? Color.accent
                    : (workspaceSlot.isCurrent
                        ? Util.alpha(Color.accent, 0.65)
                        : Util.alpha(Color.menu.text, 0.4))
                  border.width: modelData.activated ? 1.5 : 1
                }
              }

              // Drop indicator pill when dragging over this card
              Rectangle {
                anchors.centerIn: parent
                visible: workspaceSlot.isDropTarget
                implicitWidth: dropRow.implicitWidth + 14
                implicitHeight: dropRow.implicitHeight + 6
                radius: 6
                color: Color.accent

                RowLayout {
                  id: dropRow
                  anchors.centerIn: parent
                  spacing: 4

                  Text {
                    text: "󰁝"
                    color: Color.background
                    font.pixelSize: Style.font.caption
                    font.family: Style.font.menuFamily
                  }
                  Text {
                    text: "Drop"
                    color: Color.background
                    font.bold: true
                    font.pixelSize: Style.font.caption
                    font.family: Style.font.menuFamily
                  }
                }
              }

              // Mouse interaction area for clicking card to switch workspace
              MouseArea {
                id: cardMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.switchToWorkspace(workspaceSlot.modelData)
              }
            }

            // Workspace name displayed below the card
            Text {
              id: wsNameText
              Layout.alignment: Qt.AlignHCenter
              text: workspaceSlot.workspaceName
              color: (workspaceSlot.isDropTarget || workspaceSlot.isMouseHovered || workspaceSlot.isCurrent) ? Color.accent : Color.menu.text
              font.bold: true
              font.pixelSize: Style.font.title
              font.family: Style.font.menuFamily
              elide: Text.ElideRight
              Layout.maximumWidth: root.cardWidth + 10

              MouseArea {
                id: textMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.switchToWorkspace(workspaceSlot.modelData)
              }
            }
          }
        }
      }
    }
  }
}
