"""Qt test-environment configuration helpers."""

from collections.abc import MutableMapping


def configure_qt_test_environment(env: MutableMapping[str, str]) -> None:
    """Apply default Qt settings for automated tests.

    Defaults to the offscreen platform for headless test runs while respecting
    any environment values already provided from the outside.
    """
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
