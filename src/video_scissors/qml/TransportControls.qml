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

    spacing: 8

    // Spacer matching time display width for centering
    Item {
        Layout.preferredWidth: timeDisplay.width
    }

    Item { Layout.fillWidth: true }

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

    Item { Layout.fillWidth: true }

    // Time display
    Text {
        id: timeDisplay
        color: palette.text
        text: formatTime(root.position) + " / " + formatTime(root.duration)

        function formatTime(ms) {
            var seconds = Math.floor(ms / 1000)
            var minutes = Math.floor(seconds / 60)
            seconds = seconds % 60
            return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
        }
    }
}
