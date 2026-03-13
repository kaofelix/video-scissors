import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtMultimedia

ApplicationWindow {
    id: window
    visible: true
    width: 800
    height: 600
    title: "Video Scissors"

    menuBar: MenuBar {
        Menu {
            title: qsTr("&File")
            Action {
                text: qsTr("&Open…")
                shortcut: StandardKey.Open
                onTriggered: fileDialog.open()
            }
        }
        Menu {
            title: qsTr("&Edit")
            Action {
                text: qsTr("&Undo")
                shortcut: StandardKey.Undo
                enabled: session.canUndo && !cropOverlay.hasCrop
                onTriggered: session.undo()
            }
            Action {
                text: qsTr("&Redo")
                shortcut: StandardKey.Redo
                enabled: session.canRedo && !cropOverlay.hasCrop
                onTriggered: session.redo()
            }
        }
    }

    FileDialog {
        id: fileDialog
        title: "Open Video"
        nameFilters: ["Video files (*.mp4 *.mov *.avi *.mkv)", "All files (*)"]
        onAccepted: {
            session.openFile(selectedFile.toString().replace("file://", ""))
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        // Video display area
        Rectangle {
            id: videoContainer
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#000000"

            Video {
                id: videoPlayer
                objectName: "videoPlayer"
                anchors.fill: parent
                fillMode: VideoOutput.PreserveAspectFit
                source: session.workingVideoUrl

                // Reload when working video changes
                Connections {
                    target: session
                    function onVideoChanged() {
                        if (session.hasVideo) {
                            videoPlayer.source = session.workingVideoUrl
                            // Play-pause trick to render first frame immediately
                            videoPlayer.play()
                            videoPlayer.pause()
                            videoPlayer.position = 0
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
                    session.applyCrop(x, y, width, height)
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

        // Cut bar for marker-based cutting
        CutBar {
            id: cutBar
            objectName: "cutBar"
            Layout.fillWidth: true
            Layout.preferredHeight: 20
            duration: videoPlayer.duration
            markers: session.markers
            enabled: session.hasVideo && !cropOverlay.hasCrop

            onMarkerAdded: function(timeSeconds) {
                session.addMarker(timeSeconds)
            }

            onMarkerRemoved: function(timeSeconds) {
                session.removeMarker(timeSeconds)
            }

            onMarkerMoved: function(oldTime, newTime) {
                session.moveMarker(oldTime, newTime)
            }

            onSegmentCut: function(startSeconds, endSeconds) {
                session.applyCut(startSeconds, endSeconds)
            }
        }

        // Timeline scrubber
        Timeline {
            id: timeline
            objectName: "timeline"
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            Layout.topMargin: -4  // Bring closer to cut bar
            leftPadding: cutBar.trackLeftOffset  // Align with cut bar track
            position: videoPlayer.position
            duration: videoPlayer.duration
            videoWidth: session.videoWidth
            videoHeight: session.videoHeight
            videoRevision: session.workingVideoRevision
            enabled: session.hasVideo
            focus: session.hasVideo && !cropOverlay.hasCrop

            onSeekRequested: function(positionMs) {
                videoPlayer.position = positionMs
            }

            onThumbnailsRequested: function(count, height, revision) {
                session.requestThumbnails(count, height, revision)
            }

            Connections {
                target: session
                function onThumbnailsReady(urls) {
                    timeline.thumbnailUrls = urls
                }
            }
        }

        // Controls row
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Spacer matching time display width for centering
            Item {
                Layout.preferredWidth: timeDisplay.width
            }

            Item { Layout.fillWidth: true }

            RoundButton {
                id: playButton
                implicitWidth: 48
                implicitHeight: 48
                enabled: session.hasVideo
                text: videoPlayer.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
                font.pixelSize: 18
                onClicked: {
                    if (videoPlayer.playbackState === MediaPlayer.PlayingState) {
                        videoPlayer.pause()
                    } else {
                        videoPlayer.play()
                    }
                }

                background: Rectangle {
                    radius: playButton.radius
                    color: playButton.hovered ? palette.mid : "transparent"
                }
            }

            Item { Layout.fillWidth: true }

            // Time display
            Text {
                id: timeDisplay
                color: palette.text
                text: formatTime(videoPlayer.position) + " / " + formatTime(videoPlayer.duration)

                function formatTime(ms) {
                    var seconds = Math.floor(ms / 1000)
                    var minutes = Math.floor(seconds / 60)
                    seconds = seconds % 60
                    return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
                }
            }
        }
    }
}
