"""Tests for Qt test-environment configuration."""

from video_scissors.testing_qt import configure_qt_test_environment


class TestConfigureQtTestEnvironment:
    """Qt test environment defaults should be headless but overridable."""

    def test_defaults_to_offscreen_platform(self):
        """Headless Qt platform is enabled by default for pytest runs."""
        env = {}

        configure_qt_test_environment(env)

        assert env["QT_QPA_PLATFORM"] == "offscreen"

    def test_preserves_external_platform_override(self):
        """An externally provided Qt platform is respected."""
        env = {"QT_QPA_PLATFORM": "cocoa"}

        configure_qt_test_environment(env)

        assert env["QT_QPA_PLATFORM"] == "cocoa"
