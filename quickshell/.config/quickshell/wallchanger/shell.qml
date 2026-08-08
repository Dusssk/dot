import Quickshell
import QtQuick
import QtQuick.Layouts

Scope {
    id: root
    PanelWindow {
        anchors.bottom: true
        margins.bottom: screen.height / 1.5
        exclusiveZone: 0

        implicitWidth: screen.width / 2 + 100
        implicitHeight: screen.height / 4 + 1
        color: "transparent"

        mask: Region {}
        Rectangle {
            anchors.fill: parent
            radius: 14
            color: "#800000"

            RowLayout {
                anchors {
                    fill: parent
                    leftMargin: 10
                    rightMargin: 10
                }
                // Rectangle {
                //     Layout.leftMargin: 1
                //     radius: 14
                //     color: "#90000000"
                //     implicitWidth: 330
                //     implicitHeight: 240
                // }
                Rectangle {
                    id: wall
                    radius: 14
                    color: "#90000000"
                    implicitWidth: 330
                    implicitHeight: 240

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                    }
                    states: State {
                        name: "down"
                        when: mouseArea.pressed == true
                        PropertyChanges {
                            wall {
                                y: 160
                            }
                        }
                    }
                    ParallelAnimation {
                        NumberAnimation {
                            properties: "y,rotation"
                            duration: 500
                            easing.type: Easing.InOutQuad
                        }
                        ColorAnimation {
                            duration: 500
                        }
                    }

                    transitions: Transition {
                        from: ""
                        to: "down"
                        reversible: true
                        ParallelAnimation {
                            NumberAnimation {
                                properties: "y,rotation"
                                duration: 500
                                easing.type: Easing.InOutQuad
                            }
                            ColorAnimation {
                                duration: 500
                            }
                        }
                    }
                }
                // Rectangle {
                //     Layout.rightMargin: 1
                //     radius: 14
                //     color: "#90000000"
                //     implicitWidth: 330
                //     implicitHeight: 240
                // }
            }
        }
    }
}
