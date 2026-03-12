import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects

/**
 * Timeline scrubber component for video playback.
 *
 * Displays frame thumbnails filling the timeline width, with a playhead
 * that follows playback position. Supports click-to-seek and drag-to-scrub.
 *
 * Cut selection:
 *   - Shift+drag to select a time range for cutting
 *   - Delete key removes the selected range
 *
 * Properties:
 *   - position: Current playback position in milliseconds
 *   - duration: Total video duration in milliseconds
 *   - videoWidth: Video width for aspect ratio calculation
 *   - videoHeight: Video height for aspect ratio calculation
 *   - enabled: Whether interaction is allowed
 *   - selectionStart: Start of cut selection in ms (-1 if none)
 *   - selectionEnd: End of cut selection in ms (-1 if none)
 *
 * Signals:
 *   - seekRequested(real positionMs): Emitted when user seeks
 *   - thumbnailsRequested(int count, int height): Request thumbnail extraction
 *   - cutRequested(real startMs, real endMs): Emitted when user confirms cut
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

    // Cut selection (in milliseconds, -1 means no selection)
    property real selectionStart: -1
    property real selectionEnd: -1
    readonly property bool hasSelection: selectionStart >= 0 && selectionEnd >= 0

    // Signals
    signal seekRequested(real positionMs)
    signal thumbnailsRequested(int count, int height, int revision)
    signal cutRequested(real startMs, real endMs)

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
        clearSelection()
        requestThumbnails()
    }

    // Request thumbnail extraction
    function requestThumbnails() {
        if (frameCount > 0 && thumbHeight > 0) {
            thumbnailsRequested(frameCount, thumbHeight, videoRevision)
        }
    }

    // Clear cut selection
    function clearSelection() {
        selectionStart = -1
        selectionEnd = -1
    }

    // Apply the current selection as a cut
    function applyCut() {
        if (hasSelection) {
            var start = Math.min(selectionStart, selectionEnd)
            var end = Math.max(selectionStart, selectionEnd)
            cutRequested(start, end)
            clearSelection()
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

        // Cut selection overlay
        Rectangle {
            id: selectionOverlay
            visible: root.hasSelection
            anchors.top: parent.top
            anchors.bottom: parent.bottom

            property real startPos: root.duration > 0 ? Math.min(root.selectionStart, root.selectionEnd) / root.duration * parent.width : 0
            property real endPos: root.duration > 0 ? Math.max(root.selectionStart, root.selectionEnd) / root.duration * parent.width : 0

            x: startPos
            width: Math.max(0, endPos - startPos)
            color: "#CC4444"  // Red tint for "to be removed"
            opacity: 0.5
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

        property bool isSelecting: false

        onPressed: function(mouse) {
            if (mouse.modifiers & Qt.ShiftModifier) {
                // Shift+click starts cut selection
                isSelecting = true
                root.selectionStart = xToTime(mouse.x)
                root.selectionEnd = root.selectionStart
            } else {
                // Normal click seeks
                root.dragging = true
                seekToPosition(mouse.x)
            }
        }

        onReleased: function(mouse) {
            if (isSelecting) {
                isSelecting = false
                // If selection is too small (< 50ms), clear it
                var selLength = Math.abs(root.selectionEnd - root.selectionStart)
                if (selLength < 50) {
                    root.clearSelection()
                }
            } else {
                root.dragging = false
            }
        }

        onPositionChanged: function(mouse) {
            if (isSelecting) {
                root.selectionEnd = xToTime(mouse.x)
            } else if (root.dragging) {
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

    // Keyboard handling for cut
    Keys.onPressed: function(event) {
        if ((event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace) && root.hasSelection) {
            root.applyCut()
            event.accepted = true
        } else if (event.key === Qt.Key_Escape && root.hasSelection) {
            root.clearSelection()
            event.accepted = true
        }
    }
}
