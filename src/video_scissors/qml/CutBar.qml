import QtQuick
import QtQuick.Controls

/**
 * CutBar - marker-based cutting interface.
 *
 * A dedicated bar for placing cut markers and removing segments.
 * Same width as timeline scrubber, represents video time.
 *
 * Interactions:
 *   - Click to place a cut marker at that frame
 *   - Hover over segment (between markers) → highlights the section
 *   - Hold ⌘/Ctrl + click on segment → removes that segment
 *
 * Properties:
 *   - duration: Total video duration in milliseconds
 *   - markers: List of marker times in seconds (from backend)
 *   - enabled: Whether interaction is allowed
 *
 * Signals:
 *   - markerAdded(real timeSeconds): User clicked to add a marker
 *   - markerRemoved(real timeSeconds): User removed a marker
 *   - segmentCut(real startSeconds, real endSeconds): User cut a segment
 */
Item {
    id: root

    // Public properties
    property real duration: 0           // Total duration in ms
    property var markers: []            // Marker times in seconds
    property bool enabled: true

    // Signals
    signal markerAdded(real timeSeconds)
    signal markerRemoved(real timeSeconds)
    signal segmentCut(real startSeconds, real endSeconds)

    // Internal: segment boundaries (0, markers..., duration/1000)
    property var segmentBoundaries: {
        var bounds = [0]
        for (var i = 0; i < markers.length; i++) {
            bounds.push(markers[i])
        }
        bounds.push(duration / 1000)
        return bounds
    }

    // Internal: hovered segment index (-1 for none)
    property int hoveredSegment: -1

    implicitHeight: 32

    // Scissor icon on the left
    Text {
        id: scissorIcon
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 4
        text: "✂"
        font.pixelSize: 16
        color: palette.text
        opacity: 0.7
    }

    // Track area (to the right of scissor icon)
    Rectangle {
        id: track
        anchors.left: scissorIcon.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: 8
        anchors.topMargin: 4
        anchors.bottomMargin: 4
        color: palette.mid
        radius: 4

        // Segment highlight overlays
        Repeater {
            model: root.segmentBoundaries.length > 1 ? root.segmentBoundaries.length - 1 : 0

            Rectangle {
                id: segmentRect
                property real startTime: root.segmentBoundaries[index]
                property real endTime: root.segmentBoundaries[index + 1]
                property real startPos: root.duration > 0 ? (startTime * 1000 / root.duration) * track.width : 0
                property real endPos: root.duration > 0 ? (endTime * 1000 / root.duration) * track.width : 0
                property bool isHovered: root.hoveredSegment === index

                x: startPos
                width: Math.max(0, endPos - startPos)
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                color: isHovered ? "#4488CC" : "transparent"
                opacity: isHovered ? 0.4 : 0

                Behavior on opacity {
                    NumberAnimation { duration: 100 }
                }
            }
        }

        // Marker lines
        Repeater {
            model: root.markers

            Rectangle {
                id: markerLine
                property real markerTime: modelData
                property real markerPos: root.duration > 0 ? (markerTime * 1000 / root.duration) * track.width : 0

                x: markerPos - width / 2
                width: 2
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                color: "#FF6644"
                radius: 1

                // Marker handle for visibility
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: -2
                    width: 8
                    height: 8
                    radius: 4
                    color: parent.color
                }
            }
        }

        // Mouse interaction area
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            enabled: root.enabled && root.duration > 0
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

            onPositionChanged: function(mouse) {
                root.hoveredSegment = findSegmentAt(mouse.x)
            }

            onExited: {
                root.hoveredSegment = -1
            }

            onClicked: function(mouse) {
                var timeSeconds = xToTime(mouse.x)

                if (mouse.modifiers & Qt.ControlModifier || mouse.modifiers & Qt.MetaModifier) {
                    // ⌘/Ctrl + click: cut the hovered segment
                    var segIndex = findSegmentAt(mouse.x)
                    if (segIndex >= 0 && segIndex < root.segmentBoundaries.length - 1) {
                        var start = root.segmentBoundaries[segIndex]
                        var end = root.segmentBoundaries[segIndex + 1]
                        root.segmentCut(start, end)
                    }
                } else {
                    // Normal click: add marker
                    root.markerAdded(timeSeconds)
                }
            }

            function xToTime(x) {
                var clampedX = Math.max(0, Math.min(x, track.width))
                return (clampedX / track.width) * (root.duration / 1000)
            }

            function findSegmentAt(x) {
                var timeSeconds = xToTime(x)
                for (var i = 0; i < root.segmentBoundaries.length - 1; i++) {
                    if (timeSeconds >= root.segmentBoundaries[i] && timeSeconds < root.segmentBoundaries[i + 1]) {
                        return i
                    }
                }
                return -1
            }
        }
    }

    // Status hint
    Text {
        id: statusHint
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.rightMargin: 8
        text: root.hoveredSegment >= 0 ? "Hold ⌘ and click to cut" : ""
        font.pixelSize: 11
        color: palette.text
        opacity: 0.6
        visible: root.hoveredSegment >= 0

        Behavior on opacity {
            NumberAnimation { duration: 150 }
        }
    }
}
