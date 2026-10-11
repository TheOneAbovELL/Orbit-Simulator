"""Launcher kept for compatibility with the original single-file script.

Prefer ``python -m orbit_sim``. The original prototype is preserved in
legacy/orbit_simulator_v0.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orbit_sim.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
