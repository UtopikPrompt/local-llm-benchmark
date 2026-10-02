"""Pytest bootstrap for the engine package.

The test suite lives in ``engine/tests/`` but imports the top-level ``app``
package (e.g. ``app.main``, ``app.engines.base``). With pytest's default
``prepend`` import mode, only the individual test files' directories are added
to ``sys.path``, which leaves the ``app`` package unresolvable and raises
``ModuleNotFoundError`` during collection.

This root ``conftest.py`` guarantees that the directory holding the ``app``
package is importable no matter where pytest is launched from.
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
