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

            // Placeholder when no video (light color for black background)
            Text {
                anchors.centerIn: parent
                text: "Drop a video or use File → Open"
                color: "#888888"
                font.pixelSize: 18
                visible: !session.hasVideo
            }
        }

        // Timeline scrubber
        Timeline {
            id: timeline
            Layout.fillWidth: true
            position: videoPlayer.position
            duration: videoPlayer.duration
            enabled: session.hasVideo

            onSeekRequested: function(positionMs) {
                videoPlayer.position = positionMs
            }
        }

        // Controls row
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: "Open"
                onClicked: fileDialog.open()
            }

            Button {
                text: videoPlayer.playbackState === MediaPlayer.PlayingState ? "Pause" : "Play"
                enabled: session.hasVideo
                onClicked: {
                    if (videoPlayer.playbackState === MediaPlayer.PlayingState) {
                        videoPlayer.pause()
                    } else {
                        videoPlayer.play()
                    }
                }
            }

            // Time display
            Text {
                color: palette.text
                text: formatTime(videoPlayer.position) + " / " + formatTime(videoPlayer.duration)

                function formatTime(ms) {
                    var seconds = Math.floor(ms / 1000)
                    var minutes = Math.floor(seconds / 60)
                    seconds = seconds % 60
                    return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
                }
            }

            Item { Layout.fillWidth: true }

            Button {
                text: "Close"
                enabled: session.hasVideo
                onClicked: session.close()
            }
        }
    }
}
