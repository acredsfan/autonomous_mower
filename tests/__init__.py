"""Test utilities for the test suite.

This file ensures the project's ``src`` directory is added to ``sys.path`` so
that tests can import the :mod:`mower` package without requiring an editable
install.  This mirrors the layout on the Raspberry Pi where the package is
installed system-wide.
"""

from __future__ import annotations

import os
import sys

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
