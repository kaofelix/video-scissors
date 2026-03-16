import QtQuick
import QtQuick.Controls
import QtMultimedia

Rectangle {
    id: root

    property alias position: videoPlayer.position
    readonly property alias duration: videoPlayer.duration
    readonly property alias playbackState: videoPlayer.playbackState
    readonly property alias hasCrop: cropOverlay.hasCrop

    function play() { videoPlayer.play() }
    function pause() { videoPlayer.pause() }

    color: "#000000"

    Video {
        id: videoPlayer
        objectName: "videoPlayer"
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectFit
        source: session.workingVideoUrl

        // Auto-skip cut regions during playback
        onPositionChanged: {
            var cutRegions = session.cutRegions
            for (var i = 0; i < cutRegions.length; i++) {
                var cut = cutRegions[i]
                // If inside a cut region, skip to end of cut
                if (position >= cut.start && position < cut.end) {
                    videoPlayer.position = cut.end
                    break
                }
            }
        }

        // Reload when working video changes
        Connections {
            target: session
            function onVideoChanged() {
                if (session.hasVideo) {
                    videoPlayer.source = session.workingVideoUrl
                    // Play-pause trick to render first frame immediately
                    videoPlayer.play()
                    videoPlayer.pause()
                    // Use suggested position from backend, clamped to valid range
                    var suggestedPos = session.suggestedPositionMs
                    var maxPos = videoPlayer.duration > 0 ? videoPlayer.duration : 0
                    videoPlayer.position = Math.min(suggestedPos, maxPos)
                } else {
                    videoPlayer.stop()
                    videoPlayer.source = ""
                }
            }
        }
    }

    // Crop overlay - always active when video loaded
    CropOverlay {
        id: cropOverlay
        objectName: "cropOverlay"
        anchors.fill: parent
        visible: session.hasVideo
        videoWidth: session.videoWidth
        videoHeight: session.videoHeight
        videoRevision: session.workingVideoRevision

        onCropApplied: function(x, y, width, height) {
            session.setCrop(x, y, width, height)
            clear()
        }

        onCropCancelled: {
            // Already cleared by cancel()
        }
    }

    // Placeholder when no video
    Text {
        anchors.centerIn: parent
        text: "File → Open or ⌘O"
        color: "#888888"
        font.pixelSize: 18
        visible: !session.hasVideo
    }

    // Crop controls - appear when crop selection exists
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
