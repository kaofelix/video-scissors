"""Test configuration and fixtures for video-scissors."""

import json
import subprocess
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


# --- pytest-qt configuration ---


@pytest.fixture(scope="session")
def qapp_cls():
    """Use QGuiApplication for QML tests."""
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication


# --- GUI test fixtures ---


@pytest.fixture
def app_window(qtbot):
    """Create and show the main application window.

    Returns the ApplicationWindow with Main.qml loaded and session bridge configured.
    """
    import os

    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    from video_scissors.bridge import SessionBridge
    from video_scissors.session import EditorSession

    # Set Qt Quick Controls style for consistent rendering
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")

    # Create session and bridge
    session = EditorSession()
    bridge = SessionBridge(session)

    # Create engine and load QML
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("session", bridge)

    qml_file = Path(__file__).parent.parent / "src" / "video_scissors" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        pytest.fail("Failed to load QML: no root objects created")

    window = engine.rootObjects()[0]
    qtbot.waitExposed(window)

    # Wait for scene to fully render
    qtbot.wait(100)

    # Keep references alive
    window._engine = engine
    window._session = session
    window._bridge = bridge

    yield window

    window.close()


@pytest.fixture
def capture_screenshot(qapp, qtbot):
    """Fixture providing screenshot capture function.

    Usage:
        def test_something(app_window, capture_screenshot):
            capture_screenshot(app_window, "my_test_name")
    """
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    def _capture(window, name: str) -> Path:
        """Capture a screenshot of the window.

        Args:
            window: QWindow or similar window
            name: Name for the screenshot file (without extension)

        Returns:
            Path to the saved screenshot
        """
        from PySide6.QtCore import QCoreApplication, QEventLoop
        from PySide6.QtGui import QGuiApplication

        # Process pending events to ensure rendering is complete
        QCoreApplication.processEvents(QEventLoop.AllEvents, 100)

        # Get the screen and grab the window
        screen = QGuiApplication.primaryScreen()
        pixmap = screen.grabWindow(window.winId())

        path = SCREENSHOTS_DIR / f"{name}.png"
        pixmap.save(str(path))
        return path

    return _capture


def generate_test_video(
    output_path: Path,
    duration: float = 2.0,
    width: int = 320,
    height: int = 240,
    fps: int = 30,
) -> Path:
    """Generate a minimal test video using FFmpeg testsrc.

    Creates a small video with color bars pattern - suitable for testing
    crop, trim, and other operations without needing external fixtures.
    """
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


@pytest.fixture(scope="session")
def test_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Provide a generated test video for the session."""
    video_dir = tmp_path_factory.mktemp("videos")
    video_path = video_dir / "test_320x240_2s.mp4"
    return generate_test_video(video_path, duration=2.0, width=320, height=240)


# --- Media probe helpers ---


def probe_video(path: Path) -> dict:
    """Probe video file and return metadata as dict."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, check=True, text=True)
    return json.loads(result.stdout)


def get_video_stream(path: Path) -> dict:
    """Get the first video stream metadata."""
    info = probe_video(path)
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    raise ValueError(f"No video stream found in {path}")


def get_dimensions(path: Path) -> tuple[int, int]:
    """Get video dimensions as (width, height)."""
    stream = get_video_stream(path)
    return stream["width"], stream["height"]


def get_duration(path: Path) -> float:
    """Get video duration in seconds."""
    info = probe_video(path)
    return float(info["format"]["duration"])
