import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Quickshell.Services.Pipewire

ColumnLayout {
    id: mixer_menu
    required property PwNode node

    // bind the node so we can read its properties
    PwObjectTracker {
        objects: [mixer_menu.node]
    }

    RowLayout {
        Image {
            visible: source != ""
            source: {
                const icon = mixer_menu.node.properties["application.icon-name"] ?? "audio-volume-high-symbolic";
                return `image://icon/${icon}`;
            }

            sourceSize.width: 20
            sourceSize.height: 20
        }

        Label {
            text: {
                // application.name -> description -> name
                const app = mixer_menu.node.properties["application.name"] ?? (mixer_menu.node.description != "" ? mixer_menu.node.description : mixer_menu.node.name);
                const media = mixer_menu.node.properties["media.name"];
                return media != undefined ? `${app} - ${media}` : app;
            }
        }

        Button {
            text: mixer_menu.node.audio.muted ? "unmute" : "mute"
            onClicked: mixer_menu.node.audio.muted = !mixer_menu.node.audio.muted
        }
    }

    RowLayout {
        Label {
            Layout.preferredWidth: 50
            text: `${Math.floor(mixer_menu.node.audio.volume * 100)}%`
        }

        Slider {
            Layout.fillWidth: true
            value: mixer_menu.node.audio.volume
            onValueChanged: mixer_menu.node.audio.volume = value
        }
    }
}
