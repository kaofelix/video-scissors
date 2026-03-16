import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

/**
 * Timeline - unified editing timeline component.
 *
 * Combines the CutBar (marker-based cutting) and Scrubber (thumbnail playback)
 * into a single cohesive component with a 2x2 grid layout:
 *
 *   | Icon  |  CutBar track    |
 *   |-------|------------------|
 *   | empty |  Scrubber track  |
 *
 * The tracks share rounded corners on outer edges only, appearing as one unit.
 */
Item {
    id: root

    // Playback properties
    property real position: 0          // Current position in ms
    property real duration: 0          // Total duration in ms

    // Video properties (for thumbnails)
    property int videoWidth: 0
    property int videoHeight: 0
    property int contentRevision: 0
    property real videoFrameRate: 30.0  // Default to 30fps

    // Marker properties
    property var markers: []

    // State
    property bool enabled: true

    // Expose thumbnail URLs for external connection
    property alias thumbnailUrls: scrubber.thumbnailUrls

    // Signals - forwarded from child components
    signal seekRequested(real positionMs)
    signal thumbnailsRequested(int count, int height, int revision)
    signal markerAdded(real timeSeconds)
    signal markerRemoved(string markerId)
    signal markerMoved(string markerId, real newTime)
    signal segmentCut(real startSeconds, real endSeconds)

    // Layout constants
    readonly property int iconColumnWidth: 28
    readonly property int cutBarHeight: 20
    readonly property int scrubberHeight: 44
    readonly property int cornerRadius: 6

    implicitHeight: cutBarHeight + scrubberHeight

    // Grid layout using anchors for precise control
    Item {
        id: layout
        anchors.fill: parent

        // Top-left: Scissor icon
        Item {
            id: iconCell
            anchors.left: parent.left
            anchors.top: parent.top
            width: root.iconColumnWidth
            height: root.cutBarHeight

            Text {
                anchors.centerIn: parent
                text: "✂"
                font.pixelSize: 14
                color: palette.text
                opacity: root.enabled ? 0.7 : 0.3
            }
        }

        // Top-right: CutBar track
        CutBar {
            id: cutBar
            objectName: "cutBar"
            anchors.left: iconCell.right
            anchors.right: parent.right
            anchors.top: parent.top
            height: root.cutBarHeight

            duration: root.duration
            markers: root.markers
            enabled: root.enabled
            topRadius: root.cornerRadius
            bottomRadius: 0  // Square where it meets scrubber
            videoFrameRate: root.videoFrameRate

            onMarkerAdded: function(timeSeconds) {
                root.markerAdded(timeSeconds)
            }
            onMarkerRemoved: function(markerId) {
                root.markerRemoved(markerId)
            }
            onMarkerMoved: function(markerId, newTime) {
                root.markerMoved(markerId, newTime)
            }
            onSegmentCut: function(startSeconds, endSeconds) {
                root.segmentCut(startSeconds, endSeconds)
            }
        }

        // Bottom-left: Empty spacer (same width as icon)
        Item {
            id: spacerCell
            anchors.left: parent.left
            anchors.top: iconCell.bottom
            width: root.iconColumnWidth
            height: root.scrubberHeight
        }

        // Bottom-right: Scrubber track
        Scrubber {
            id: scrubber
            anchors.left: spacerCell.right
            anchors.right: parent.right
            anchors.top: cutBar.bottom
            height: root.scrubberHeight

            position: root.position
            duration: root.duration
            videoWidth: root.videoWidth
            videoHeight: root.videoHeight
            contentRevision: root.contentRevision
            enabled: root.enabled
            topRadius: 0  // Square where it meets CutBar
            bottomRadius: root.cornerRadius

            onSeekRequested: function(positionMs) {
                root.seekRequested(positionMs)
            }
            onThumbnailsRequested: function(count, height, revision) {
                root.thumbnailsRequested(count, height, revision)
            }
        }
    }
}
