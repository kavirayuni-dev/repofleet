"""Zero-install launcher for repofleet.

Lets a teammate run the CLI straight from an unzipped folder without pip:

    python bootstrap.py sync
    python bootstrap.py --help
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from repofleet.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
