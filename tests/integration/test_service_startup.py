"""
Test module for test_service_startup.py.
"""

import threading

# import pytest # pytest is implicitly used by test functions
from mower.main_controller import ResourceManager, main


def test_main_controller_startup(monkeypatch):
    """
    Test that the main controller starts up and exits gracefully.

    This patches ResourceManager.start_web_interface to avoid starting the
    web server, and patches threading.Event.wait to raise KeyboardInterrupt
    after the first wait.
    """
    # Avoid starting the web interface
    monkeypatch.setattr(ResourceManager, "start_web_interface", lambda self: None)

    # Patch threading.Event.wait to trigger exit
    original_wait = threading.Event.wait
    call_count = {"count": 0}

    def fake_wait(self, timeout=None):
        call_count["count"] += 1
        if call_count["count"] > 1:
            raise KeyboardInterrupt
        # Wait briefly to simulate loop
        return original_wait(self, 0.01)

    monkeypatch.setattr(threading.Event, "wait", fake_wait)

    # Run main, should exit without exceptions
    main()
