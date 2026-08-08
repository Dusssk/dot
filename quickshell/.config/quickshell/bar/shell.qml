import Quickshell
import Quickshell.Hyprland
import QtQuick
import QtQuick.Layouts

PanelWindow {
    anchors {
        top: true
        left: false
        right: false
    }
    implicitHeight: 28
    implicitWidth: 400

    Rectangle {
        anchors.fill: parent
        radius: 10
        color: "#1a1b26"
        RowLayout {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 12
            }
            Text {
                text: ""
                color: "#cdd6f4"
            }
        }

        RowLayout {
            anchors.centerIn: parent

            spacing: 10
            SystemClock {
                id: clock
                precision: SystemClock.Minutes
            }
            Text {
                text: Qt.formatDateTime(clock.date, "    hh:mm   dddd   ||   dd   MMMM")
                color: "#cdd6f4"
            }
        }
        RowLayout {
            anchors {
                right: parent.right
                verticalCenter: parent.verticalCenter
                rightMargin: 12
            }
            spacing: 10
        }
    }
}
// 
// 
// 
// 
// 
// 
