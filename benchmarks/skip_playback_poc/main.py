#!/usr/bin/env python3
"""PoC: Video playback with auto-skip cut regions.

Tests whether seeking past cut regions during playback feels smooth
or has noticeable stutters/glitches.

Usage:
    python benchmarks/skip_playback_poc/main.py [video_path]
"""

import sys
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


class SkipController(QObject):
    """Controller that defines cut regions and exposes them to QML."""

    cutRegionsChanged = Signal()

    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self._video_path = video_path
        # Define a cut region in the middle (adjust based on video duration)
        # Format: list of {start, end} in milliseconds
        self._cut_regions = [
            {"start": 5000, "end": 10000},  # Skip 5-10 seconds
        ]

    @Property(str, constant=True)
    def videoUrl(self) -> str:
        return QUrl.fromLocalFile(self._video_path).toString()

    @Property(list, notify=cutRegionsChanged)
    def cutRegions(self) -> list:
        return self._cut_regions

    @Slot(float, float)
    def setCutRegion(self, start_sec: float, end_sec: float):
        """Set a single cut region (for testing different ranges)."""
        self._cut_regions = [{"start": int(start_sec * 1000), "end": int(end_sec * 1000)}]
        self.cutRegionsChanged.emit()
        print(f"Cut region set: {start_sec}s - {end_sec}s")

    @Slot()
    def clearCuts(self):
        """Clear all cut regions."""
        self._cut_regions = []
        self.cutRegionsChanged.emit()
        print("Cut regions cleared")


QML_CONTENT = """
import QtQuick
import QtQuick.Controls
import QtMultimedia

ApplicationWindow {
    id: window
    visible: true
    width: 1280
    height: 800
    title: "Skip Playback PoC"
    color: "#1a1a1a"

    property var cutRegions: controller.cutRegions
    property bool skipEnabled: true
    property int skipCount: 0

    Video {
        id: video
        anchors.fill: parent
        anchors.bottomMargin: 150
        source: controller.videoUrl
        fillMode: VideoOutput.PreserveAspectFit

        // Auto-skip logic
        onPositionChanged: {
            if (!skipEnabled) return

            for (var i = 0; i < cutRegions.length; i++) {
                var cut = cutRegions[i]
                // If we're inside a cut region, skip to end
                if (position >= cut.start && position < cut.end) {
                    console.log("Skipping cut region:", cut.start, "-", cut.end)
                    video.position = cut.end
                    skipCount++
                    break
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (video.playbackState === MediaPlayer.PlayingState) {
                    video.pause()
                } else {
                    video.play()
                }
            }
        }
    }

    // Timeline with cut visualization
    Rectangle {
        id: timeline
        anchors.bottom: controls.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        height: 40
        color: "#333"
        radius: 4

        // Progress bar
        Rectangle {
            width: video.duration > 0 ? (video.position / video.duration) * parent.width : 0
            height: parent.height
            color: "#4a9eff"
            radius: 4
        }

        // Cut regions overlay
        Repeater {
            model: cutRegions
            Rectangle {
                x: video.duration > 0 ? (modelData.start / video.duration) * timeline.width : 0
                width: {
                    var dur = modelData.end - modelData.start
                    return video.duration > 0 ? (dur / video.duration) * timeline.width : 0
                }
                height: parent.height
                color: "#cc3333"
                opacity: 0.7

                // Hatching pattern
                Canvas {
                    anchors.fill: parent
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.strokeStyle = "#661111"
                        ctx.lineWidth = 2
                        for (var i = -height; i < width + height; i += 8) {
                            ctx.beginPath()
                            ctx.moveTo(i, 0)
                            ctx.lineTo(i + height, height)
                            ctx.stroke()
                        }
                    }
                }
            }
        }

        // Click to seek
        MouseArea {
            anchors.fill: parent
            onClicked: function(mouse) {
                var seekPos = (mouse.x / width) * video.duration
                video.position = seekPos
            }
        }
    }

    // Controls
    Column {
        id: controls
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 10

        Row {
            spacing: 20
            anchors.horizontalCenter: parent.horizontalCenter

            Button {
                text: video.playbackState === MediaPlayer.PlayingState ? "⏸ Pause" : "▶ Play"
                onClicked: {
                    if (video.playbackState === MediaPlayer.PlayingState) {
                        video.pause()
                    } else {
                        video.play()
                    }
                }
            }

            Button {
                text: "⏮ Restart"
                onClicked: {
                    video.position = 0
                    skipCount = 0
                }
            }

            Button {
                text: skipEnabled ? "🔴 Skip ON" : "⚪ Skip OFF"
                onClicked: skipEnabled = !skipEnabled
            }

            Button {
                text: "Clear Cuts"
                onClicked: controller.clearCuts()
            }
        }

        Row {
            spacing: 10
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                text: "Cut region:"
                color: "white"
                anchors.verticalCenter: parent.verticalCenter
            }

            TextField {
                id: startField
                width: 80
                placeholderText: "Start (s)"
                text: "5"
            }

            Text { text: "-"; color: "white"; anchors.verticalCenter: parent.verticalCenter }

            TextField {
                id: endField
                width: 80
                placeholderText: "End (s)"
                text: "10"
            }

            Button {
                text: "Set Cut"
                onClicked: {
                    controller.setCutRegion(parseFloat(startField.text), parseFloat(endField.text))
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            color: "#888"
            text: {
                var pos = (video.position / 1000).toFixed(2)
                var dur = (video.duration / 1000).toFixed(2)
                return "Position: " + pos + "s / " + dur + "s | Skips: " + skipCount + " | " +
                       (skipEnabled ? "Auto-skip ENABLED" : "Auto-skip DISABLED")
            }
        }
    }

    Component.onCompleted: {
        video.play()
        video.pause()  // Show first frame
    }
}
"""


def main():
    # Default video path
    video_path = "/Users/kaofelix/Documents/combo.mov"

    if len(sys.argv) > 1:
        video_path = sys.argv[1]

    if not Path(video_path).exists():
        print(f"Error: Video not found: {video_path}")
        sys.exit(1)

    print(f"Testing skip playback with: {video_path}")
    print("=" * 50)
    print("Controls:")
    print("  - Click video to play/pause")
    print("  - Click timeline to seek")
    print("  - Red regions are 'cut' - will be auto-skipped")
    print("  - Toggle 'Skip ON/OFF' to compare behavior")
    print("  - Adjust cut region with text fields")
    print("=" * 50)

    app = QGuiApplication(sys.argv)

    controller = SkipController(video_path)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("controller", controller)
    engine.loadData(QML_CONTENT.encode())

    if not engine.rootObjects():
        print("Failed to load QML")
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
