"""Video Scissors application entry point."""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from video_scissors.bridge import SessionBridge
from video_scissors.session import EditorSession


def main() -> int:
    """Run the Video Scissors application."""
    parser = argparse.ArgumentParser(description="Video Scissors - Quick video editor")
    parser.add_argument("file", nargs="?", help="Video file to open")
    args = parser.parse_args()

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Video Scissors")
    app.setOrganizationName("VideoScissors")

    # Create session and bridge
    session = EditorSession()
    bridge = SessionBridge(session)

    # Load QML
    engine = QQmlApplicationEngine()

    # Expose bridge to QML as 'session'
    engine.rootContext().setContextProperty("session", bridge)

    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        return 1

    # Open file if provided on command line
    if args.file:
        file_path = Path(args.file).resolve()
        if file_path.exists():
            # Use QTimer to open after event loop starts
            QTimer.singleShot(0, lambda: bridge.openFile(str(file_path)))

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
