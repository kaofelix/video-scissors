import QtQuick
import QtQuick.Controls
import QtMultimedia

Rectangle {
    id: root
    objectName: "videoArea"

    property alias position: videoPlayer.position
    readonly property alias duration: videoPlayer.duration
    readonly property alias playbackState: videoPlayer.playbackState
    readonly property alias hasCrop: cropOverlay.hasCrop

    // Whether a crop from the EditSpec is actively clipping the video
    readonly property bool cropActive: session.document.editSpec.hasCrop

    // Whether the proxy is ready and video can be displayed
    readonly property bool proxyReady: session.hasVideo && session.proxyVideoUrl !== ""

    function play() { videoPlayer.play() }
    function pause() { videoPlayer.pause() }

    color: "#000000"

    // --- Crop preview clipping ---
    // When a crop is applied in the EditSpec, we clip the video to show
    // only the cropped region, scaled to fill the available space.

    // Compute the displayed video rect (where the video renders within root)
    // This matches VideoOutput.PreserveAspectFit layout.
    readonly property int sourceWidth: session.videoWidth
    readonly property int sourceHeight: session.videoHeight
    readonly property var activeCrop: session.document.editSpec.cropRect

    // The region we want to display: crop rect when active, full frame otherwise
    readonly property int displayRegionX: root.cropActive && activeCrop ? activeCrop.x : 0
    readonly property int displayRegionY: root.cropActive && activeCrop ? activeCrop.y : 0
    readonly property int displayRegionW: root.cropActive && activeCrop ? activeCrop.width : sourceWidth
    readonly property int displayRegionH: root.cropActive && activeCrop ? activeCrop.height : sourceHeight

    Item {
        id: clipContainer
        anchors.centerIn: parent
        clip: root.cropActive
        visible: root.proxyReady

        // When crop active: sized to fit crop aspect ratio within parent.
        // When no crop: fill parent entirely (video handles its own aspect).
        width: root.cropActive ? fittedSize.width : root.width
        height: root.cropActive ? fittedSize.height : root.height

        // Compute fitted size for the crop region within the parent
        readonly property size fittedSize: {
            if (!root.cropActive || root.displayRegionW <= 0 || root.displayRegionH <= 0)
                return Qt.size(root.width, root.height)

            var cropAspect = root.displayRegionW / root.displayRegionH
            var parentAspect = root.width / root.height

            if (cropAspect > parentAspect) {
                // Crop is wider: fit to width
                return Qt.size(root.width, root.width / cropAspect)
            } else {
                // Crop is taller: fit to height
                return Qt.size(root.height * cropAspect, root.height)
            }
        }

        // Scale factor: how much to scale the full video so the crop region
        // fills the clip container
        readonly property real cropScale: {
            if (!root.cropActive || root.displayRegionW <= 0)
                return 1.0
            return clipContainer.width / root.displayRegionW
        }

        Video {
            id: videoPlayer
            objectName: "videoPlayer"

            // When crop active: position and scale so crop region fills container
            // When no crop: fill container normally with aspect-fit
            x: root.cropActive ? -root.displayRegionX * clipContainer.cropScale : 0
            y: root.cropActive ? -root.displayRegionY * clipContainer.cropScale : 0
            width: root.cropActive ? root.sourceWidth * clipContainer.cropScale : parent.width
            height: root.cropActive ? root.sourceHeight * clipContainer.cropScale : parent.height
            fillMode: root.cropActive ? VideoOutput.Stretch : VideoOutput.PreserveAspectFit

            source: session.proxyVideoUrl

            // Keep the last frame visible when playback ends instead of
            // showing a black screen. Available since Qt 6.9.
            endOfStreamPolicy: VideoOutput.KeepLastFrame

            // Auto-skip cut regions during playback.
            // Only active while playing — not during seeks or restarts.
            onPositionChanged: {
                if (videoPlayer.playbackState !== MediaPlayer.PlayingState) return
                var cutRegions = session.document.editSpec.cutRegions
                for (var i = 0; i < cutRegions.length; i++) {
                    var cut = cutRegions[i]
                    if (position >= cut.start && position < cut.end) {
                        videoPlayer.position = cut.end
                        return
                    }
                }
            }

            // Load proxy when ready
            Connections {
                target: session
                function onProxyVideoUrlChanged() {
                    if (session.proxyVideoUrl !== "") {
                        videoPlayer.source = session.proxyVideoUrl
                        // Play-pause trick to render first frame immediately
                        videoPlayer.play()
                        videoPlayer.pause()
                        // Use suggested position from backend, clamped to valid range
                        var suggestedPos = session.suggestedPositionMs
                        var maxPos = videoPlayer.duration > 0 ? videoPlayer.duration : 0
                        videoPlayer.position = Math.min(suggestedPos, maxPos)
                    } else {
                        videoPlayer.stop()
                        videoPlayer.clearOutput()
                        videoPlayer.source = ""
                    }
                }
            }
        }
    }

    // Loading indicator during proxy generation
    Column {
        anchors.centerIn: parent
        spacing: 16
        visible: session.isGeneratingProxy

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Preparing video..."
            color: "#888888"
            font.pixelSize: 18
        }

        ProgressBar {
            width: 200
            from: 0.0
            to: 1.0
            value: session.proxyProgressValue
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Math.round(session.proxyProgressValue * 100) + "%"
            color: "#666666"
            font.pixelSize: 14
        }
    }

    // Crop overlay - works in source coords when no crop, or in crop-relative
    // coords when a crop is active (overlay dimensions match visible region).
    // Only visible when proxy is ready (no cropping during loading).
    CropOverlay {
        id: cropOverlay
        objectName: "cropOverlay"
        anchors.fill: parent
        visible: root.proxyReady
        videoWidth: root.displayRegionW
        videoHeight: root.displayRegionH
        videoRevision: session.workingVideoRevision

        onCropApplied: function(x, y, width, height) {
            // Translate crop-relative coordinates to source coordinates
            var sourceX = root.displayRegionX + x
            var sourceY = root.displayRegionY + y
            session.setCrop(sourceX, sourceY, width, height)
            clear()
        }

        onCropCancelled: {
            // Already cleared by cancel()
        }
    }

    // Placeholder when no video (and not loading)
    Text {
        anchors.centerIn: parent
        text: "File → Open or ⌘O"
        color: "#888888"
        font.pixelSize: 18
        visible: !session.hasVideo && !session.isGeneratingProxy
    }

    // Crop controls - appear when crop selection exists (during drawing)
    Row {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 16
        spacing: 16
        visible: cropOverlay.hasCrop

        Button {
            text: "Cancel"
            onClicked: cropOverlay.cancel()
        }

        Button {
            text: "Apply Crop"
            highlighted: true
            onClicked: cropOverlay.apply()
        }
    }
}
