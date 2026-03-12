import QtQuick

/**
 * CropOverlay - Direct manipulation crop selection over video.
 *
 * Crop geometry lives in video-space coordinates. A single transformed layer
 * maps that geometry into the displayed video rect.
 */
Item {
    id: root

    // Video dimensions for coordinate mapping
    property int videoWidth: 0
    property int videoHeight: 0
    property int videoRevision: 0
    readonly property rect videoContentRect: calculateVideoContentRect()
    readonly property real videoScale: videoWidth > 0 ? videoContentRect.width / videoWidth : 1.0
    readonly property rect cropSceneRect: Qt.rect(
        videoLayer.x + cropRect.x * videoScale,
        videoLayer.y + cropRect.y * videoScale,
        cropRect.width * videoScale,
        cropRect.height * videoScale
    )

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

    onVideoRevisionChanged: clear()

    // Click anywhere on the displayed video to start drawing a crop rectangle.
    Item {
        id: videoLayer
        objectName: "cropVideoLayer"
        x: root.videoContentRect.x
        y: root.videoContentRect.y
        width: root.videoWidth
        height: root.videoHeight
        scale: root.videoScale
        transformOrigin: Item.TopLeft

        MouseArea {
            id: drawArea
            anchors.fill: parent
            enabled: !root.hasCrop
            cursorShape: Qt.CrossCursor

            property point dragStart

            onPressed: function(mouse) {
                dragStart = root.videoPointFromItemPoint(videoLayer, mouse.x, mouse.y)
                root.cropRect = Qt.rect(dragStart.x, dragStart.y, 0, 0)
            }

            onPositionChanged: function(mouse) {
                var current = root.videoPointFromItemPoint(videoLayer, mouse.x, mouse.y)
                var x = Math.min(dragStart.x, current.x)
                var y = Math.min(dragStart.y, current.y)
                var w = Math.abs(current.x - dragStart.x)
                var h = Math.abs(current.y - dragStart.y)

                x = Math.max(0, x)
                y = Math.max(0, y)
                w = Math.min(w, root.videoWidth - x)
                h = Math.min(h, root.videoHeight - y)

                root.cropRect = Qt.rect(x, y, w, h)
            }
        }

        // The crop rectangle in source video coordinates.
        Rectangle {
            id: cropArea
            objectName: "cropArea"
            visible: root.hasCrop
            x: root.cropRect.x
            y: root.cropRect.y
            width: root.cropRect.width
            height: root.cropRect.height

            color: "transparent"
            border.color: "white"
            border.width: Math.max(1, 2 / root.videoScale)

            Repeater {
                model: [
                    { corner: "topLeft", anchorX: 0, anchorY: 0 },
                    { corner: "topRight", anchorX: 1, anchorY: 0 },
                    { corner: "bottomLeft", anchorX: 0, anchorY: 1 },
                    { corner: "bottomRight", anchorX: 1, anchorY: 1 }
                ]

                Rectangle {
                    required property var modelData
                    width: Math.max(12, 16 / root.videoScale)
                    height: width
                    x: modelData.anchorX * (cropArea.width - width)
                    y: modelData.anchorY * (cropArea.height - height)
                    color: "white"
                    radius: 2 / root.videoScale

                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -8 / root.videoScale
                        cursorShape: {
                            if (modelData.corner === "topLeft" || modelData.corner === "bottomRight")
                                return Qt.SizeFDiagCursor
                            return Qt.SizeBDiagCursor
                        }

                        property point startPos
                        property rect startRect

                        onPressed: function(mouse) {
                            startPos = root.videoPointFromItemPoint(parent, mouse.x, mouse.y)
                            startRect = root.cropRect
                        }

                        onPositionChanged: function(mouse) {
                            var currentPos = root.videoPointFromItemPoint(parent, mouse.x, mouse.y)
                            var dx = currentPos.x - startPos.x
                            var dy = currentPos.y - startPos.y
                            var newRect = startRect

                            if (modelData.corner === "topLeft") {
                                newRect = Qt.rect(
                                    Math.min(startRect.x + dx, startRect.x + startRect.width - root.minCropSize),
                                    Math.min(startRect.y + dy, startRect.y + startRect.height - root.minCropSize),
                                    Math.max(startRect.width - dx, root.minCropSize),
                                    Math.max(startRect.height - dy, root.minCropSize)
                                )
                            } else if (modelData.corner === "topRight") {
                                newRect = Qt.rect(
                                    startRect.x,
                                    Math.min(startRect.y + dy, startRect.y + startRect.height - root.minCropSize),
                                    Math.max(startRect.width + dx, root.minCropSize),
                                    Math.max(startRect.height - dy, root.minCropSize)
                                )
                            } else if (modelData.corner === "bottomLeft") {
                                newRect = Qt.rect(
                                    Math.min(startRect.x + dx, startRect.x + startRect.width - root.minCropSize),
                                    startRect.y,
                                    Math.max(startRect.width - dx, root.minCropSize),
                                    Math.max(startRect.height + dy, root.minCropSize)
                                )
                            } else {
                                newRect = Qt.rect(
                                    startRect.x,
                                    startRect.y,
                                    Math.max(startRect.width + dx, root.minCropSize),
                                    Math.max(startRect.height + dy, root.minCropSize)
                                )
                            }

                            newRect.x = Math.max(0, newRect.x)
                            newRect.y = Math.max(0, newRect.y)
                            newRect.width = Math.min(newRect.width, root.videoWidth - newRect.x)
                            newRect.height = Math.min(newRect.height, root.videoHeight - newRect.y)

                            root.cropRect = newRect
                        }
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                anchors.margins: 16 / root.videoScale
                cursorShape: Qt.SizeAllCursor

                property point startPos
                property rect startRect

                onPressed: function(mouse) {
                    startPos = root.videoPointFromItemPoint(cropArea, mouse.x, mouse.y)
                    startRect = root.cropRect
                }

                onPositionChanged: function(mouse) {
                    var currentPos = root.videoPointFromItemPoint(cropArea, mouse.x, mouse.y)
                    var dx = currentPos.x - startPos.x
                    var dy = currentPos.y - startPos.y

                    var newX = Math.max(0, Math.min(startRect.x + dx, root.videoWidth - startRect.width))
                    var newY = Math.max(0, Math.min(startRect.y + dy, root.videoHeight - startRect.height))

                    root.cropRect = Qt.rect(newX, newY, startRect.width, startRect.height)
                }
            }
        }
    }

    // Dimmed regions outside crop area (only visible when crop exists)
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: root.cropSceneRect.y
        color: "#80000000"
        visible: root.hasCrop
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: parent.height - root.cropSceneRect.y - root.cropSceneRect.height
        color: "#80000000"
        visible: root.hasCrop
    }

    Rectangle {
        anchors.left: parent.left
        y: root.cropSceneRect.y
        width: root.cropSceneRect.x
        height: root.cropSceneRect.height
        color: "#80000000"
        visible: root.hasCrop
    }

    Rectangle {
        anchors.right: parent.right
        y: root.cropSceneRect.y
        width: parent.width - root.cropSceneRect.x - root.cropSceneRect.width
        height: root.cropSceneRect.height
        color: "#80000000"
        visible: root.hasCrop
    }

    function calculateVideoContentRect() {
        if (root.videoWidth <= 0 || root.videoHeight <= 0 || root.width <= 0 || root.height <= 0) {
            return Qt.rect(0, 0, 0, 0)
        }

        var videoAspect = root.videoWidth / root.videoHeight
        var containerAspect = root.width / root.height

        if (videoAspect > containerAspect) {
            var fittedHeight = root.width / videoAspect
            return Qt.rect(0, (root.height - fittedHeight) / 2, root.width, fittedHeight)
        }

        var fittedWidth = root.height * videoAspect
        return Qt.rect((root.width - fittedWidth) / 2, 0, fittedWidth, root.height)
    }

    function videoPointFromItemPoint(item, x, y) {
        var scenePoint = item.mapToItem(root, x, y)
        return Qt.point(mapToVideoX(scenePoint.x), mapToVideoY(scenePoint.y))
    }

    function mapFromVideoX(videoX) {
        return root.videoContentRect.x + videoX * root.videoScale
    }

    function mapFromVideoY(videoY) {
        return root.videoContentRect.y + videoY * root.videoScale
    }

    function mapToVideoX(screenX) {
        if (root.videoScale <= 0 || root.videoContentRect.width <= 0) return 0
        var clampedX = Math.max(root.videoContentRect.x, Math.min(screenX, root.videoContentRect.x + root.videoContentRect.width))
        return (clampedX - root.videoContentRect.x) / root.videoScale
    }

    function mapToVideoY(screenY) {
        if (root.videoScale <= 0 || root.videoContentRect.height <= 0) return 0
        var clampedY = Math.max(root.videoContentRect.y, Math.min(screenY, root.videoContentRect.y + root.videoContentRect.height))
        return (clampedY - root.videoContentRect.y) / root.videoScale
    }

    function clear() {
        cropRect = Qt.rect(0, 0, 0, 0)
    }

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

    function cancel() {
        clear()
        cropCancelled()
    }
}
