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
 *   - Click on marker to select it
 *   - Click elsewhere to deselect
 *   - Drag markers to reposition them
 *   - Hover over segment (between markers) → highlights the section
 *   - Hold ⌘/Ctrl + click on segment → removes that segment
 *   - Arrow keys: move selected marker (small increment)
 *   - Shift+Arrow: move selected marker (large increment)
 *   - Delete/Backspace: remove selected marker
 *
 * Properties:
 *   - duration: Total video duration in milliseconds
 *   - markers: List of marker times in seconds (from backend)
 *   - enabled: Whether interaction is allowed
 *   - topRadius: Radius for top corners
 *   - bottomRadius: Radius for bottom corners (0 when joined with Scrubber)
 *   - selectedMarkerTime: Time of selected marker (-1 if none)
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
    property real selectedMarkerTime: -1  // Selected marker time (-1 = none)
    property real videoFrameRate: 30.0  // Video frame rate for precise movement

    // Movement increments for keyboard navigation (in seconds)
    // Small increment = 1 frame, large increment = 1 second
    readonly property real smallIncrement: videoFrameRate > 0 ? 1.0 / videoFrameRate : 1.0 / 30.0
    readonly property real largeIncrement: 1.0

    // Signals
    signal markerAdded(real timeSeconds)
    signal markerRemoved(real timeSeconds)
    signal markerMoved(real oldTime, real newTime)
    signal segmentCut(real startSeconds, real endSeconds)

    // Enable focus for keyboard handling
    focus: selectedMarkerTime >= 0
    Keys.onPressed: function(event) {
        if (selectedMarkerTime < 0) return

        var increment = (event.modifiers & Qt.ShiftModifier) ? largeIncrement : smallIncrement
        var durationSeconds = duration / 1000

        if (event.key === Qt.Key_Left) {
            var newTime = Math.max(0, selectedMarkerTime - increment)
            if (newTime !== selectedMarkerTime) {
                var oldTime = selectedMarkerTime
                // Update selection first so onMarkersChanged finds it
                selectedMarkerTime = newTime
                root.markerMoved(oldTime, newTime)
            }
            event.accepted = true
        } else if (event.key === Qt.Key_Right) {
            var newTime = Math.min(durationSeconds, selectedMarkerTime + increment)
            if (newTime !== selectedMarkerTime) {
                var oldTime = selectedMarkerTime
                // Update selection first so onMarkersChanged finds it
                selectedMarkerTime = newTime
                root.markerMoved(oldTime, newTime)
            }
            event.accepted = true
        } else if (event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace) {
            var timeToRemove = selectedMarkerTime
            selectedMarkerTime = -1
            root.markerRemoved(timeToRemove)
            event.accepted = true
        }
    }

    // Internal: segment boundaries (0, markers..., duration/1000)
    property var segmentBoundaries: {
        var bounds = [0]
        for (var i = 0; i < markers.length; i++) {
            bounds.push(markers[i])
        }
        bounds.push(duration / 1000)
        return bounds
    }

    // Clear selection when selected marker is removed externally
    // Use small epsilon for floating point comparison
    onMarkersChanged: {
        if (selectedMarkerTime >= 0) {
            var found = false
            var epsilon = 0.001  // 1ms tolerance
            for (var i = 0; i < markers.length; i++) {
                if (Math.abs(markers[i] - selectedMarkerTime) < epsilon) {
                    // Update to exact value from markers array
                    selectedMarkerTime = markers[i]
                    found = true
                    break
                }
            }
            if (!found) {
                selectedMarkerTime = -1
            }
        }
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
                property bool isHovered: false
                property bool isSelected: root.selectedMarkerTime === markerTime

                x: markerPos
                width: 1
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                z: 1  // Above track MouseArea for proper event handling

                // Marker color (adapts to dark/light mode)
                property color markerColor: palette.text
                // Highlight color is inverse of marker (white in light theme, black in dark theme)
                property color highlightColor: palette.base

                // Solid line extending down from handle
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 7
                    anchors.bottom: parent.bottom
                    width: 1
                    color: markerItem.markerColor
                }

                // Marker handle (flag shape: rectangle with triangle pointing down)
                Item {
                    id: handleArea
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: -2
                    width: 10
                    height: 10

                    // Flag-shaped highlight (drawn behind the marker)
                    Canvas {
                        id: highlightCanvas
                        anchors.centerIn: parent
                        width: 16
                        height: 16
                        visible: markerItem.isSelected || markerItem.isHovered

                        property color highlightColor: markerItem.highlightColor
                        property bool isSelected: markerItem.isSelected
                        property bool isHovered: markerItem.isHovered

                        onHighlightColorChanged: requestPaint()
                        onIsSelectedChanged: requestPaint()
                        onIsHoveredChanged: requestPaint()

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)

                            // Draw flag shape outline (scaled up version of the marker)
                            var centerX = width / 2
                            var rectWidth = 12
                            var rectHeight = 8
                            var triWidth = 10
                            var triHeight = 6
                            var rectLeft = centerX - rectWidth / 2
                            var rectTop = 1

                            ctx.beginPath()
                            // Top-left corner
                            ctx.moveTo(rectLeft + 1, rectTop)
                            // Top edge
                            ctx.lineTo(rectLeft + rectWidth - 1, rectTop)
                            // Top-right corner
                            ctx.quadraticCurveTo(rectLeft + rectWidth, rectTop, rectLeft + rectWidth, rectTop + 1)
                            // Right edge
                            ctx.lineTo(rectLeft + rectWidth, rectTop + rectHeight - 1)
                            // Right to triangle
                            ctx.lineTo(centerX + triWidth / 2, rectTop + rectHeight)
                            // Triangle right edge to point
                            ctx.lineTo(centerX, rectTop + rectHeight + triHeight)
                            // Triangle point to left edge
                            ctx.lineTo(centerX - triWidth / 2, rectTop + rectHeight)
                            // Left edge of rect
                            ctx.lineTo(rectLeft, rectTop + rectHeight - 1)
                            ctx.lineTo(rectLeft, rectTop + 1)
                            // Top-left corner
                            ctx.quadraticCurveTo(rectLeft, rectTop, rectLeft + 1, rectTop)
                            ctx.closePath()

                            // Fill with highlight color at appropriate opacity
                            var alpha = isSelected ? 0.9 : 0.4
                            ctx.fillStyle = Qt.rgba(highlightColor.r, highlightColor.g, highlightColor.b, alpha)
                            ctx.fill()
                        }
                    }

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

                    // Interaction area for the handle
                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -4
                        cursorShape: Qt.ArrowCursor
                        drag.target: null
                        preventStealing: true
                        hoverEnabled: true

                        property real dragStartTime: 0
                        property bool wasDragged: false

                        onEntered: {
                            markerItem.isHovered = true
                        }

                        onExited: {
                            markerItem.isHovered = false
                        }

                        onPressed: function(mouse) {
                            markerItem.isDragging = true
                            wasDragged = false
                            dragStartTime = markerItem.markerTime
                            mouse.accepted = true
                        }

                        onReleased: function(mouse) {
                            if (markerItem.isDragging) {
                                markerItem.isDragging = false
                                var newTime = xToTime(markerItem.x)
                                if (Math.abs(newTime - dragStartTime) > 0.01) {
                                    // Set selection before move so onMarkersChanged can find it
                                    root.selectedMarkerTime = newTime
                                    root.markerMoved(dragStartTime, newTime)
                                    wasDragged = true
                                } else {
                                    // Didn't move enough, keep selection on original
                                    root.selectedMarkerTime = dragStartTime
                                }
                                root.forceActiveFocus()
                            }
                        }

                        onClicked: function(mouse) {
                            // Select this marker (already handled in onReleased for drag case)
                            if (!wasDragged) {
                                root.selectedMarkerTime = markerItem.markerTime
                                root.forceActiveFocus()
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

                // Check if click is near any marker (within hit area)
                var clickedOnMarker = false
                for (var i = 0; i < root.markers.length; i++) {
                    var markerTime = root.markers[i]
                    var markerX = root.duration > 0 ? (markerTime * 1000 / root.duration) * track.width : 0
                    if (Math.abs(mouse.x - markerX) < 12) {  // Hit area matches handle MouseArea margins
                        clickedOnMarker = true
                        break
                    }
                }

                if (clickedOnMarker) {
                    // Click handled by marker's MouseArea
                    return
                }

                // Deselect any selected marker when clicking elsewhere
                root.selectedMarkerTime = -1

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
