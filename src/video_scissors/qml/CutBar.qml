import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects

/**
 * CutBar - marker-based cutting interface.
 *
 * A track for placing cut markers and removing segments.
 * Represents video time with marker placement and segment highlighting.
 *
 * Interactions:
 *   - Click to place a cut marker at that position
 *   - Drag markers to reposition them
 *   - Hover over segment (between markers) → highlights the section
 *   - Hold ⌘/Ctrl + click on segment → removes that segment
 *
 * Properties:
 *   - duration: Total video duration in milliseconds
 *   - markers: List of marker times in seconds (from backend)
 *   - enabled: Whether interaction is allowed
 *   - topRadius: Radius for top corners
 *   - bottomRadius: Radius for bottom corners (0 when joined with Scrubber)
 *
 * Signals:
 *   - markerAdded(real timeSeconds): User clicked to add a marker
 *   - markerRemoved(real timeSeconds): User removed a marker
 *   - markerMoved(real oldTime, real newTime): User dragged a marker
 *   - segmentCut(real startSeconds, real endSeconds): User cut a segment
 */
Item {
    id: root

    // Public properties
    property real duration: 0           // Total duration in ms
    property var markers: []            // Marker times in seconds
    property bool enabled: true
    property int topRadius: 6           // Top corner radius
    property int bottomRadius: 0        // Bottom corner radius (0 when joined)

    // Signals
    signal markerAdded(real timeSeconds)
    signal markerRemoved(real timeSeconds)
    signal markerMoved(real oldTime, real newTime)
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
    // Only allow segment interaction when there are markers
    property int hoveredSegment: -1
    property bool hasSegments: markers.length > 0

    implicitHeight: 20

    // Track with custom corner radii
    Rectangle {
        id: track
        anchors.fill: parent
        color: palette.mid
        radius: root.topRadius

        // Cover bottom corners to make them square (when joined with Scrubber)
        Rectangle {
            visible: root.bottomRadius < root.topRadius
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: parent.radius
            color: parent.color
        }

        // Segment highlights container - clipped to rounded shape
        Item {
            id: highlightContainer
            anchors.fill: parent

            // Layer mask for rounded clipping
            layer.enabled: true
            layer.effect: OpacityMask {
                maskSource: Rectangle {
                    width: highlightContainer.width
                    height: highlightContainer.height
                    radius: root.topRadius
                    // Square off bottom corners
                    Rectangle {
                        visible: root.bottomRadius < root.topRadius
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: root.topRadius
                        color: "white"
                    }
                }
            }

            // Segment highlight overlays (only when there are markers)
            Repeater {
                model: root.hasSegments ? root.segmentBoundaries.length - 1 : 0

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
                    color: "white"
                    opacity: isHovered ? 0.25 : 0

                    Behavior on opacity {
                        NumberAnimation { duration: 100 }
                    }
                }
            }
        }

        // Marker lines and handles
        Repeater {
            model: root.markers

            Item {
                id: markerItem
                property real markerTime: modelData
                property real markerPos: root.duration > 0 ? (markerTime * 1000 / root.duration) * track.width : 0
                property bool isDragging: false

                x: markerPos
                width: 1
                anchors.top: parent.top
                anchors.bottom: parent.bottom

                // Marker color (adapts to dark/light mode)
                property color markerColor: palette.text

                // Solid line extending down from handle
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 7
                    anchors.bottom: parent.bottom
                    width: 1
                    color: markerItem.markerColor
                }

                // Marker handle (rectangle with triangle pointing down)
                Item {
                    id: handleArea
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: -2
                    width: 10
                    height: 10

                    // Rectangle part
                    Rectangle {
                        id: handleRect
                        anchors.top: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 8
                        height: 6
                        color: markerItem.markerColor
                        border.color: palette.mid
                        border.width: 1
                        radius: 1
                    }

                    // Triangle part (pointing down)
                    Canvas {
                        id: triangleCanvas
                        anchors.top: handleRect.bottom
                        anchors.topMargin: -1
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 6
                        height: 4

                        property color fillColor: markerItem.markerColor

                        onFillColorChanged: requestPaint()

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.fillStyle = fillColor
                            ctx.beginPath()
                            ctx.moveTo(0, 0)
                            ctx.lineTo(width, 0)
                            ctx.lineTo(width / 2, height)
                            ctx.closePath()
                            ctx.fill()
                        }
                    }

                    // Drag area for the handle
                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -4
                        cursorShape: Qt.SizeHorCursor
                        drag.target: null
                        preventStealing: true

                        property real dragStartTime: 0

                        onPressed: function(mouse) {
                            markerItem.isDragging = true
                            dragStartTime = markerItem.markerTime
                            mouse.accepted = true
                        }

                        onReleased: function(mouse) {
                            if (markerItem.isDragging) {
                                markerItem.isDragging = false
                                var newTime = xToTime(markerItem.x)
                                if (Math.abs(newTime - dragStartTime) > 0.01) {
                                    root.markerMoved(dragStartTime, newTime)
                                }
                            }
                        }

                        onPositionChanged: function(mouse) {
                            if (markerItem.isDragging) {
                                var globalX = mapToItem(track, mouse.x, 0).x
                                var clampedX = Math.max(0, Math.min(globalX, track.width))
                                markerItem.x = clampedX
                            }
                        }

                        function xToTime(x) {
                            return (x / track.width) * (root.duration / 1000)
                        }
                    }
                }
            }
        }

        // Mouse interaction area for track
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            enabled: root.enabled && root.duration > 0
            hoverEnabled: true
            cursorShape: Qt.ArrowCursor

            onPositionChanged: function(mouse) {
                // Only track segment hover when markers exist
                if (root.hasSegments) {
                    root.hoveredSegment = findSegmentAt(mouse.x)
                } else {
                    root.hoveredSegment = -1
                }
            }

            onExited: {
                root.hoveredSegment = -1
            }

            onClicked: function(mouse) {
                var timeSeconds = xToTime(mouse.x)

                if (root.hasSegments && (mouse.modifiers & Qt.ControlModifier || mouse.modifiers & Qt.MetaModifier)) {
                    // ⌘/Ctrl + click: cut the hovered segment (only when markers exist)
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
        text: root.hoveredSegment >= 0 ? "⌘+click to cut" : ""
        font.pixelSize: 10
        color: palette.text
        opacity: 0.5
        visible: root.hoveredSegment >= 0

        Behavior on opacity {
            NumberAnimation { duration: 150 }
        }
    }
}
