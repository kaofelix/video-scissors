import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects

/**
 * Scrubber - video playback scrubber with thumbnails.
 *
 * Displays frame thumbnails filling the width, with a playhead
 * that follows playback position. Supports click-to-seek and drag-to-scrub.
 *
 * Properties:
 *   - position: Current playback position in milliseconds
 *   - duration: Total video duration in milliseconds
 *   - videoWidth: Video width for aspect ratio calculation
 *   - videoHeight: Video height for aspect ratio calculation
 *   - enabled: Whether interaction is allowed
 *   - topRadius: Radius for top corners (0 when joined with CutBar)
 *   - bottomRadius: Radius for bottom corners
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
    property int contentRevision: 0    // Bumps on file load, close, and edit spec changes

    property bool enabled: true
    property var thumbnailUrls: []     // List of thumbnail file:// URLs
    property int topRadius: 0          // Top corner radius (0 when joined)
    property int bottomRadius: 6       // Bottom corner radius

    // Signals
    signal seekRequested(real positionMs)
    signal thumbnailsRequested(int count, int height, int revision)

    // Internal state
    property bool dragging: false
    property int thumbHeight: height
    property int thumbWidth: videoHeight > 0 ? Math.floor(thumbHeight * videoWidth / videoHeight) : 0
    property int frameCount: thumbWidth > 0 ? Math.ceil(width / thumbWidth) : 0

    implicitHeight: 44

    // Request thumbnails when layout or video content changes
    onFrameCountChanged: {
        requestThumbnails()
    }

    onContentRevisionChanged: {
        thumbnailUrls = []
        requestThumbnails()
    }

    // Request thumbnail extraction
    function requestThumbnails() {
        if (frameCount > 0 && thumbHeight > 0) {
            thumbnailsRequested(frameCount, thumbHeight, contentRevision)
        }
    }

    // Track background with custom corner radii
    Rectangle {
        id: track
        anchors.fill: parent
        color: palette.mid

        // Mask for custom corner radii
        layer.enabled: true
        layer.effect: OpacityMask {
            maskSource: Item {
                width: track.width
                height: track.height

                // Use overlapping rectangles for different corner radii
                Rectangle {
                    width: parent.width
                    height: parent.height
                    radius: root.bottomRadius
                }
                // Cover top corners if topRadius is 0
                Rectangle {
                    visible: root.topRadius < root.bottomRadius
                    width: parent.width
                    height: parent.height / 2
                    radius: root.topRadius
                }
            }
        }

        // Thumbnail row
        Row {
            id: thumbnailRow
            anchors.fill: parent
            clip: true

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
