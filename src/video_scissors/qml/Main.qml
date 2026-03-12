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

    property bool cropMode: false

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
                enabled: session.canUndo && !cropMode
                onTriggered: session.undo()
            }
            Action {
                text: qsTr("&Redo")
                shortcut: StandardKey.Redo
                enabled: session.canRedo && !cropMode
                onTriggered: session.redo()
            }
            MenuSeparator {}
            Action {
                text: qsTr("&Crop")
                shortcut: "C"
                enabled: session.hasVideo && !cropMode
                onTriggered: {
                    cropOverlay.reset()
                    cropMode = true
                }
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
                anchors.fill: parent
                source: session.workingVideoUrl

                // Reload when working video changes
                Connections {
                    target: session
                    function onVideoChanged() {
                        // Clear old thumbnails
                        timeline.thumbnailUrls = []

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

            // Crop overlay
            CropOverlay {
                id: cropOverlay
                anchors.fill: parent
                visible: cropMode
                videoWidth: session.videoWidth
                videoHeight: session.videoHeight

                onCropApplied: function(x, y, width, height) {
                    session.applyCrop(x, y, width, height)
                    cropMode = false
                }

                onCropCancelled: {
                    cropMode = false
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

            // Crop controls overlay
            Row {
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottomMargin: 16
                spacing: 16
                visible: cropMode

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

        // Timeline scrubber
        Timeline {
            id: timeline
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            position: videoPlayer.position
            duration: videoPlayer.duration
            videoWidth: session.videoWidth
            videoHeight: session.videoHeight
            enabled: session.hasVideo

            onSeekRequested: function(positionMs) {
                videoPlayer.position = positionMs
            }

            onThumbnailsRequested: function(count, height) {
                session.requestThumbnails(count, height)
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
