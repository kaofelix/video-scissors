"""Video Scissors application entry point."""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from video_scissors.bridge import SessionBridge
from video_scissors.session import EditorSession


def main() -> int:
    """Run the Video Scissors application."""
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

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
