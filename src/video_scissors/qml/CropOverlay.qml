import QtQuick

/**
 * CropOverlay - Direct manipulation crop selection over video.
 *
 * Click and drag anywhere to create a crop rectangle.
 * Drag corners to resize, drag inside to move.
 * Shows apply/cancel when a crop selection exists.
 */
Item {
    id: root

    // Video dimensions for coordinate mapping
    property int videoWidth: 0
    property int videoHeight: 0

    // Whether a crop selection exists
    readonly property bool hasCrop: cropRect.width > 0 && cropRect.height > 0
        && (cropRect.x > 0 || cropRect.y > 0
            || cropRect.width < videoWidth || cropRect.height < videoHeight)

    // The crop rectangle in video coordinates (empty = no selection)
    property rect cropRect: Qt.rect(0, 0, 0, 0)

    // Minimum crop size in video pixels
    readonly property int minCropSize: 32

    signal cropApplied(int x, int y, int width, int height)
    signal cropCancelled()

    // Click anywhere to start drawing a crop rectangle
    MouseArea {
        id: drawArea
        anchors.fill: parent
        enabled: !root.hasCrop  // Only when no crop exists
        cursorShape: Qt.CrossCursor

        property point dragStart

        onPressed: function(mouse) {
            dragStart = Qt.point(mouse.x, mouse.y)
            root.cropRect = Qt.rect(
                mapToVideoX(mouse.x),
                mapToVideoY(mouse.y),
                0, 0
            )
        }

        onPositionChanged: function(mouse) {
            var startX = mapToVideoX(dragStart.x)
            var startY = mapToVideoY(dragStart.y)
            var endX = mapToVideoX(mouse.x)
            var endY = mapToVideoY(mouse.y)

            // Handle dragging in any direction
            var x = Math.min(startX, endX)
            var y = Math.min(startY, endY)
            var w = Math.abs(endX - startX)
            var h = Math.abs(endY - startY)

            // Clamp to video bounds
            x = Math.max(0, x)
            y = Math.max(0, y)
            w = Math.min(w, root.videoWidth - x)
            h = Math.min(h, root.videoHeight - y)

            root.cropRect = Qt.rect(x, y, w, h)
        }
    }

    // Dimmed regions outside crop area (only visible when crop exists)
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: cropArea.y
        color: "#80000000"
        visible: root.hasCrop
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: parent.height - cropArea.y - cropArea.height
        color: "#80000000"
        visible: root.hasCrop
    }

    Rectangle {
        anchors.left: parent.left
        y: cropArea.y
        width: cropArea.x
        height: cropArea.height
        color: "#80000000"
        visible: root.hasCrop
    }

    Rectangle {
        anchors.right: parent.right
        y: cropArea.y
        width: parent.width - cropArea.x - cropArea.width
        height: cropArea.height
        color: "#80000000"
        visible: root.hasCrop
    }

    // The crop rectangle
    Rectangle {
        id: cropArea
        visible: root.hasCrop
        x: mapFromVideoX(root.cropRect.x)
        y: mapFromVideoY(root.cropRect.y)
        width: mapFromVideoX(root.cropRect.width)
        height: mapFromVideoY(root.cropRect.height)

        color: "transparent"
        border.color: "white"
        border.width: 2

        // Corner handles
        Repeater {
            model: [
                { corner: "topLeft", anchorX: 0, anchorY: 0 },
                { corner: "topRight", anchorX: 1, anchorY: 0 },
                { corner: "bottomLeft", anchorX: 0, anchorY: 1 },
                { corner: "bottomRight", anchorX: 1, anchorY: 1 }
            ]

            Rectangle {
                required property var modelData
                x: modelData.anchorX * (cropArea.width - width)
                y: modelData.anchorY * (cropArea.height - height)
                width: 16
                height: 16
                color: "white"
                radius: 2

                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -8  // Larger hit area
                    cursorShape: {
                        if (modelData.corner === "topLeft" || modelData.corner === "bottomRight")
                            return Qt.SizeFDiagCursor
                        return Qt.SizeBDiagCursor
                    }

                    property point startPos
                    property rect startRect

                    onPressed: function(mouse) {
                        startPos = Qt.point(mouse.x, mouse.y)
                        startRect = root.cropRect
                    }

                    onPositionChanged: function(mouse) {
                        var dx = mapToVideoX(mouse.x - startPos.x)
                        var dy = mapToVideoY(mouse.y - startPos.y)

                        var newRect = startRect

                        if (modelData.corner === "topLeft") {
                            newRect = Qt.rect(
                                Math.min(startRect.x + dx, startRect.x + startRect.width - minCropSize),
                                Math.min(startRect.y + dy, startRect.y + startRect.height - minCropSize),
                                Math.max(startRect.width - dx, minCropSize),
                                Math.max(startRect.height - dy, minCropSize)
                            )
                        } else if (modelData.corner === "topRight") {
                            newRect = Qt.rect(
                                startRect.x,
                                Math.min(startRect.y + dy, startRect.y + startRect.height - minCropSize),
                                Math.max(startRect.width + dx, minCropSize),
                                Math.max(startRect.height - dy, minCropSize)
                            )
                        } else if (modelData.corner === "bottomLeft") {
                            newRect = Qt.rect(
                                Math.min(startRect.x + dx, startRect.x + startRect.width - minCropSize),
                                startRect.y,
                                Math.max(startRect.width - dx, minCropSize),
                                Math.max(startRect.height + dy, minCropSize)
                            )
                        } else {  // bottomRight
                            newRect = Qt.rect(
                                startRect.x,
                                startRect.y,
                                Math.max(startRect.width + dx, minCropSize),
                                Math.max(startRect.height + dy, minCropSize)
                            )
                        }

                        // Clamp to video bounds
                        newRect.x = Math.max(0, newRect.x)
                        newRect.y = Math.max(0, newRect.y)
                        newRect.width = Math.min(newRect.width, root.videoWidth - newRect.x)
                        newRect.height = Math.min(newRect.height, root.videoHeight - newRect.y)

                        root.cropRect = newRect
                    }
                }
            }
        }

        // Drag the whole crop area
        MouseArea {
            anchors.fill: parent
            anchors.margins: 16  // Don't overlap corner handles
            cursorShape: Qt.SizeAllCursor

            property point startPos
            property rect startRect

            onPressed: function(mouse) {
                startPos = Qt.point(mouse.x, mouse.y)
                startRect = root.cropRect
            }

            onPositionChanged: function(mouse) {
                var dx = mapToVideoX(mouse.x - startPos.x)
                var dy = mapToVideoY(mouse.y - startPos.y)

                var newX = Math.max(0, Math.min(startRect.x + dx, root.videoWidth - startRect.width))
                var newY = Math.max(0, Math.min(startRect.y + dy, root.videoHeight - startRect.height))

                root.cropRect = Qt.rect(newX, newY, startRect.width, startRect.height)
            }
        }
    }

    // Helper functions to map between screen and video coordinates
    function mapFromVideoX(videoX) {
        if (root.videoWidth <= 0) return 0
        return videoX * root.width / root.videoWidth
    }

    function mapFromVideoY(videoY) {
        if (root.videoHeight <= 0) return 0
        return videoY * root.height / root.videoHeight
    }

    function mapToVideoX(screenX) {
        if (root.width <= 0) return 0
        return screenX * root.videoWidth / root.width
    }

    function mapToVideoY(screenY) {
        if (root.height <= 0) return 0
        return screenY * root.videoHeight / root.height
    }

    // Clear the crop selection
    function clear() {
        cropRect = Qt.rect(0, 0, 0, 0)
    }

    // Apply the current crop
    function apply() {
        if (hasCrop) {
            cropApplied(
                Math.round(cropRect.x),
                Math.round(cropRect.y),
                Math.round(cropRect.width),
                Math.round(cropRect.height)
            )
        }
    }

    // Cancel cropping
    function cancel() {
        clear()
        cropCancelled()
    }
}
