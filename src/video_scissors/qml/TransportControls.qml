import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

RowLayout {
    id: root

    property int position: 0
    property int duration: 0
    property int playbackState: MediaPlayer.StoppedState

    signal playRequested()
    signal pauseRequested()
    signal stepForwardRequested()
    signal stepBackwardRequested()

    spacing: 8

    // Spacer matching time display width for centering
    Item {
        Layout.preferredWidth: timeDisplay.width
    }

    Item { Layout.fillWidth: true }

    RoundButton {
        id: stepBackwardButton
        objectName: "stepBackwardButton"
        implicitWidth: 36
        implicitHeight: 36
        text: "◀|"
        font.pixelSize: 12
        onClicked: root.stepBackwardRequested()

        background: Rectangle {
            radius: stepBackwardButton.radius
            color: stepBackwardButton.hovered ? palette.mid : "transparent"
        }
    }

    RoundButton {
        id: playButton
        implicitWidth: 48
        implicitHeight: 48
        text: root.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
        font.pixelSize: 18
        onClicked: {
            if (root.playbackState === MediaPlayer.PlayingState) {
                root.pauseRequested()
            } else {
                root.playRequested()
            }
        }

        background: Rectangle {
            radius: playButton.radius
            color: playButton.hovered ? palette.mid : "transparent"
        }
    }

    RoundButton {
        id: stepForwardButton
        objectName: "stepForwardButton"
        implicitWidth: 36
        implicitHeight: 36
        text: "|▶"
        font.pixelSize: 12
        onClicked: root.stepForwardRequested()

        background: Rectangle {
            radius: stepForwardButton.radius
            color: stepForwardButton.hovered ? palette.mid : "transparent"
        }
    }

    Item { Layout.fillWidth: true }

    // Time display
    Text {
        id: timeDisplay
        color: palette.text
        font.pixelSize: 11
        font.family: "Menlo, monospace"
        opacity: 0.7
        text: formatTime(root.position) + " / " + formatTime(root.duration)

        function formatTime(ms) {
            var totalSeconds = Math.floor(ms / 1000)
            var minutes = Math.floor(totalSeconds / 60)
            var seconds = totalSeconds % 60
            var millis = Math.floor(ms % 1000)
            var centis = Math.floor(millis / 10)
            return minutes + ":"
                + (seconds < 10 ? "0" : "") + seconds + "."
                + (centis < 10 ? "0" : "") + centis
        }
    }
}
