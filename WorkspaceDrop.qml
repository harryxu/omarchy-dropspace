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

  readonly property int cardWidth: 160
  readonly property int cardHeight: 100
  readonly property int cardSpacing: 16
  readonly property int topMargin: 36

  function open(payloadJson) {
    root.opened = true
    Quickshell.execDetached(["/usr/bin/touch", "/tmp/dropspace_is_open"])
  }

  function close() {
    root.opened = false
    Quickshell.execDetached(["/usr/bin/rm", "-f", "/tmp/dropspace_is_open"])
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
    target: "dropspace"
    function show(): string {
      root.open("{}")
      return "ok"
    }
    function hide(): string {
      root.close()
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

    // Subtle dark scrim background
    Rectangle {
      anchors.fill: parent
      color: Util.alpha(Color.background, 0.45)
      opacity: root.opened ? 1 : 0
      Behavior on opacity {
        NumberAnimation { duration: 150 }
      }
    }

    // Top workspace cards container
    Item {
      id: container
      anchors.top: parent.top
      anchors.topMargin: root.opened ? root.topMargin : -root.cardHeight - 50
      anchors.horizontalCenter: parent.horizontalCenter
      width: rowLayout.implicitWidth
      height: rowLayout.implicitHeight

      opacity: root.opened ? 1 : 0

      Behavior on anchors.topMargin {
        NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
      }
      Behavior on opacity {
        NumberAnimation { duration: 180 }
      }

      RowLayout {
        id: rowLayout
        spacing: root.cardSpacing

        Repeater {
          model: [1, 2, 3, 4, 5]

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
            readonly property int windowCount: ws !== null ? ws.toplevels.values.length : 0

            Layout.preferredWidth: root.cardWidth
            Layout.preferredHeight: root.cardHeight
            radius: Style.cornerRadius > 0 ? Style.cornerRadius : 14

            color: card.isCurrent
              ? Util.alpha(Color.menu.selectedBackground, 0.92)
              : Util.alpha(Color.menu.background, 0.88)

            border.color: card.isCurrent ? Color.accent : Color.menu.border
            border.width: card.isCurrent ? 2 : 1

            ColumnLayout {
              anchors.centerIn: parent
              spacing: 6

              Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Workspace " + card.modelData
                color: card.isCurrent ? Color.menu.selectedText : Color.menu.text
                font.bold: true
                font.pixelSize: Style.font.bodyLarge
                font.family: Style.font.menuFamily
              }

              Text {
                Layout.alignment: Qt.AlignHCenter
                text: card.isCurrent
                  ? "Current"
                  : (card.windowCount > 0 ? (card.windowCount + (card.windowCount === 1 ? " window" : " windows")) : "Empty")
                color: card.isCurrent ? Color.menu.selectedText : Util.alpha(Color.menu.text, 0.6)
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
