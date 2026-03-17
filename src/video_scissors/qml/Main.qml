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

    // -- Effective-time conversion boundary --
    // VideoArea and session operate in source time.
    // Timeline and TransportControls operate in effective time.
    // Main.qml converts at the boundary.

    // Effective position: recomputed when source position or cuts change.
    // Reading contentRevision forces rebind when edit spec changes, since
    // sourceToEffective is a Slot call that QML can't track dependencies for.
    readonly property real effectivePosition: {
        session.contentRevision  // rebind when cuts change
        return session.sourceToEffective(videoArea.position)
    }

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

    // -- Global keyboard shortcuts --

    // Frame step increment in ms (1 frame at video frame rate)
    readonly property real frameStepMs: session.videoFrameRate > 0
        ? 1000.0 / session.videoFrameRate : 1000.0 / 30.0

    function stepPlayhead(deltaMs) {
        // Pause if playing (standard NLE behavior)
        if (videoArea.playbackState === MediaPlayer.PlayingState) {
            videoArea.pause()
        }
        // Step in effective time, then convert to source for seeking
        var newEffective = Math.max(0, Math.min(
            window.effectivePosition + deltaMs,
            session.effectiveDurationMs
        ))
        videoArea.position = session.effectiveToSource(newEffective)
    }

    Shortcut {
        sequence: "Space"
        enabled: session.hasVideo && !videoArea.hasCrop
        onActivated: {
            if (videoArea.playbackState === MediaPlayer.PlayingState) {
                videoArea.pause()
            } else {
                videoArea.play()
            }
        }
    }

    Shortcut {
        sequence: "Right"
        enabled: session.hasVideo && !videoArea.hasCrop && !timeline.hasSelectedMarker
        onActivated: stepPlayhead(window.frameStepMs)
    }

    Shortcut {
        sequence: "Left"
        enabled: session.hasVideo && !videoArea.hasCrop && !timeline.hasSelectedMarker
        onActivated: stepPlayhead(-window.frameStepMs)
    }

    Shortcut {
        sequence: "Shift+Right"
        enabled: session.hasVideo && !videoArea.hasCrop && !timeline.hasSelectedMarker
        onActivated: stepPlayhead(1000)
    }

    Shortcut {
        sequence: "Shift+Left"
        enabled: session.hasVideo && !videoArea.hasCrop && !timeline.hasSelectedMarker
        onActivated: stepPlayhead(-1000)
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
        spacing: 0

        VideoArea {
            id: videoArea
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        // Unified timeline with cut bar and scrubber
        // All times here are in effective (post-cuts) coordinates.
        Timeline {
            id: timeline
            objectName: "timeline"
            Layout.fillWidth: true
            Layout.leftMargin: 8
            Layout.rightMargin: 8
            Layout.topMargin: 8
            Layout.preferredHeight: implicitHeight

            position: window.effectivePosition
            duration: session.effectiveDurationMs
            videoWidth: session.displayWidth
            videoHeight: session.displayHeight
            contentRevision: session.contentRevision
            markers: session.effectiveMarkers
            enabled: session.hasVideo && !videoArea.hasCrop
            focus: session.hasVideo && !videoArea.hasCrop

            onSeekRequested: function(effectiveMs) {
                // Convert effective time back to source for the video player
                videoArea.position = session.effectiveToSource(effectiveMs)
            }

            onThumbnailsRequested: function(count, height, revision) {
                session.requestThumbnails(count, height, revision)
            }

            onMarkerAdded: function(effectiveTimeSeconds) {
                // Convert effective time to source for storage
                var sourceMs = session.effectiveToSource(effectiveTimeSeconds * 1000)
                session.addMarker(sourceMs / 1000)
            }

            onMarkerRemoved: function(markerId) {
                session.removeMarker(markerId)
            }

            onMarkerMoved: function(markerId, effectiveNewTime) {
                // Convert effective time to source for storage
                var sourceMs = session.effectiveToSource(effectiveNewTime * 1000)
                session.moveMarker(markerId, sourceMs / 1000)
            }

            onSegmentCut: function(effectiveStart, effectiveEnd) {
                // Convert effective boundaries to source for the cut operation
                var sourceStart = session.effectiveToSource(effectiveStart * 1000) / 1000
                var sourceEnd = session.effectiveToSource(effectiveEnd * 1000) / 1000
                session.addCut(sourceStart, sourceEnd)
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
            Layout.leftMargin: 8
            Layout.rightMargin: 8
            Layout.bottomMargin: 8
            position: window.effectivePosition
            duration: session.effectiveDurationMs
            playbackState: videoArea.playbackState
            enabled: session.hasVideo
            onPlayRequested: videoArea.play()
            onPauseRequested: videoArea.pause()
            onStepForwardRequested: stepPlayhead(window.frameStepMs)
            onStepBackwardRequested: stepPlayhead(-window.frameStepMs)
        }
    }
}
