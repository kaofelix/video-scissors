import QtQuick
import QtQuick.Controls

/**
 * Timeline scrubber component for video playback.
 *
 * Displays a visual track with a playhead that follows playback position.
 * Supports click-to-seek and drag-to-scrub interactions.
 *
 * Properties:
 *   - position: Current playback position in milliseconds
 *   - duration: Total video duration in milliseconds
 *   - enabled: Whether interaction is allowed
 *
 * Signals:
 *   - seekRequested(real positionMs): Emitted when user seeks to a position
 */
Item {
    id: root

    // Public properties
    property real position: 0      // Current position in ms
    property real duration: 0      // Total duration in ms
    property bool enabled: true

    // Signal emitted when user seeks
    signal seekRequested(real positionMs)

    // Internal state
    property bool dragging: false

    implicitHeight: 32

    // Timeline track background
    Rectangle {
        id: track
        anchors.fill: parent
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        color: palette.mid
        radius: 3

        // Progress fill (played portion)
        Rectangle {
            id: progressFill
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: root.duration > 0 ? (root.position / root.duration) * parent.width : 0
            color: palette.highlight
            radius: 3

            // Smooth animation during playback, instant during drag
            Behavior on width {
                enabled: !root.dragging
                NumberAnimation {
                    duration: 80
                    easing.type: Easing.Linear
                }
            }
        }
    }

    // Playhead indicator
    Rectangle {
        id: playhead
        width: 4
        height: parent.height
        radius: 2
        color: palette.highlightedText
        x: root.duration > 0 ? (root.position / root.duration) * (root.width - width) : 0

        // Smooth animation during playback, instant during drag
        Behavior on x {
            enabled: !root.dragging
            NumberAnimation {
                duration: 80
                easing.type: Easing.Linear
            }
        }

        // Subtle shadow for visibility
        Rectangle {
            anchors.fill: parent
            anchors.margins: -1
            radius: 3
            color: "black"
            opacity: 0.3
            z: -1
        }
    }

    // Mouse interaction area
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.enabled && root.duration > 0
        hoverEnabled: true
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

        onPressed: function(mouse) {
            root.dragging = true
            seekToPosition(mouse.x)
        }

        onReleased: {
            root.dragging = false
        }

        onPositionChanged: function(mouse) {
            if (root.dragging) {
                seekToPosition(mouse.x)
            }
        }

        function seekToPosition(x) {
            // Clamp x to valid range
            var clampedX = Math.max(0, Math.min(x, root.width))
            // Convert pixel position to time
            var positionMs = (clampedX / root.width) * root.duration
            root.seekRequested(positionMs)
        }
    }
}
