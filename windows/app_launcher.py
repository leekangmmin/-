from __future__ import annotations

import sys

# PyInstaller must see the FastAPI app import statically even though the
# desktop server starts it through the string "app.main:app" at runtime.
import app.main  # noqa: F401

from desktop.launcher import main


if __name__ == "__main__":
    raise SystemExit(main())
