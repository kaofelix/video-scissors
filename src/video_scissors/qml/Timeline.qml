import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects

/**
 * Timeline scrubber component for video playback.
 *
 * Displays frame thumbnails filling the timeline width, with a playhead
 * that follows playback position. Supports click-to-seek and drag-to-scrub.
 *
 * Properties:
 *   - position: Current playback position in milliseconds
 *   - duration: Total video duration in milliseconds
 *   - videoWidth: Video width for aspect ratio calculation
 *   - videoHeight: Video height for aspect ratio calculation
 *   - enabled: Whether interaction is allowed
 *
 * Signals:
 *   - seekRequested(real positionMs): Emitted when user seeks
 *   - thumbnailsRequested(int count, int height): Request thumbnail extraction
 */
Item {
    id: root

    // Public properties
    property real position: 0          // Current position in ms
    property real duration: 0          // Total duration in ms
    property int videoWidth: 0         // Video width for aspect ratio
    property int videoHeight: 0        // Video height for aspect ratio
    property int videoRevision: 0      // Strategic identity for the working video
    property bool enabled: true
    property var thumbnailUrls: []     // List of thumbnail file:// URLs

    // Signals
    signal seekRequested(real positionMs)
    signal thumbnailsRequested(int count, int height, int revision)

    // Internal state
    property bool dragging: false
    property int thumbHeight: height - 16  // Track height (with margins)
    property int thumbWidth: videoHeight > 0 ? Math.floor(thumbHeight * videoWidth / videoHeight) : 0
    property int frameCount: thumbWidth > 0 ? Math.ceil(width / thumbWidth) : 0

    implicitHeight: 60

    // Request thumbnails when layout parameters change
    onFrameCountChanged: {
        requestThumbnails()
    }

    onVideoRevisionChanged: {
        thumbnailUrls = []
        requestThumbnails()
    }

    // Request thumbnail extraction
    function requestThumbnails() {
        if (frameCount > 0 && thumbHeight > 0) {
            thumbnailsRequested(frameCount, thumbHeight, videoRevision)
        }
    }

    // Timeline track with thumbnails
    Rectangle {
        id: track
        anchors.fill: parent
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        color: palette.mid
        radius: 6

        // Use layer for rounded corner clipping
        layer.enabled: true
        layer.effect: OpacityMask {
            maskSource: Rectangle {
                width: track.width
                height: track.height
                radius: track.radius
            }
        }

        // Thumbnail row
        Row {
            id: thumbnailRow
            anchors.fill: parent

            Repeater {
                model: root.thumbnailUrls.length > 0 ? root.thumbnailUrls : root.frameCount

                Image {
                    width: root.thumbWidth
                    height: root.thumbHeight
                    fillMode: Image.PreserveAspectCrop
                    source: root.thumbnailUrls.length > 0
                        ? (root.thumbnailUrls[index] || "")
                        : ""
                    asynchronous: true
                    cache: false  // Disable caching to ensure fresh loads

                    // Placeholder while loading
                    Rectangle {
                        anchors.fill: parent
                        color: palette.mid
                        visible: parent.status !== Image.Ready
                    }
                }
            }
        }

        // Semi-transparent overlay for unplayed portion (right of playhead)
        Rectangle {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            width: root.duration > 0 ? parent.width - (root.position / root.duration) * parent.width : parent.width
            color: palette.base
            opacity: 0.4
            radius: track.radius

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
        width: 3
        height: parent.height
        radius: 1
        color: "white"
        x: root.duration > 0 ? (root.position / root.duration) * (root.width - width) : 0

        // Smooth animation during playback, instant during drag
        Behavior on x {
            enabled: !root.dragging
            NumberAnimation {
                duration: 80
                easing.type: Easing.Linear
            }
        }

        // Drop shadow for visibility on any background
        Rectangle {
            anchors.fill: parent
            anchors.margins: -1
            radius: 2
            color: "black"
            opacity: 0.5
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

        function xToTime(x) {
            var clampedX = Math.max(0, Math.min(x, root.width))
            return (clampedX / root.width) * root.duration
        }

        function seekToPosition(x) {
            root.seekRequested(xToTime(x))
        }
    }
}
