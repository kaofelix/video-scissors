import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

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
                enabled: session.canUndo && !videoArea.hasCrop
                onTriggered: session.undo(videoArea.position)
            }
            Action {
                text: qsTr("&Redo")
                shortcut: StandardKey.Redo
                enabled: session.canRedo && !videoArea.hasCrop
                onTriggered: session.redo(videoArea.position)
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

        VideoArea {
            id: videoArea
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        // Unified timeline with cut bar and scrubber
        Timeline {
            id: timeline
            objectName: "timeline"
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight

            position: videoArea.position
            duration: videoArea.duration
            videoWidth: session.videoWidth
            videoHeight: session.videoHeight
            videoRevision: session.workingVideoRevision
            markers: session.markers
            enabled: session.hasVideo && !videoArea.hasCrop
            focus: session.hasVideo && !videoArea.hasCrop

            onSeekRequested: function(positionMs) {
                videoArea.position = positionMs
            }

            onThumbnailsRequested: function(count, height, revision) {
                session.requestThumbnails(count, height, revision)
            }

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
                session.applyCut(startSeconds, endSeconds, videoArea.position)
            }

            Connections {
                target: session
                function onThumbnailsReady(urls) {
                    timeline.thumbnailUrls = urls
                }
            }
        }

        TransportControls {
            Layout.fillWidth: true
            position: videoArea.position
            duration: videoArea.duration
            playbackState: videoArea.playbackState
            enabled: session.hasVideo
            onPlayRequested: videoArea.play()
            onPauseRequested: videoArea.pause()
        }
    }
}
