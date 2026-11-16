#!/usr/bin/env python3
"""Launch the de-Identification desktop application."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repair_qt_plugins_visibility() -> None:
    """Clear macOS hidden flags that can hide Qt plugins from QDir."""
    if sys.platform != "darwin":
        return

    pyside_dir = Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "PySide6"
    if not pyside_dir.is_dir():
        return

    try:
        hidden = bool(pyside_dir.stat().st_flags & 0x8000)  # macOS UF_HIDDEN
        platforms = pyside_dir / "Qt" / "plugins" / "platforms"
        hidden = hidden or bool(platforms.stat().st_flags & 0x8000)
    except (AttributeError, OSError):
        return

    if hidden:
        subprocess.run(
            ["chflags", "-R", "nohidden", str(pyside_dir)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


_repair_qt_plugins_visibility()

try:
    from app.gui import run
except ImportError as exc:
    if exc.name == "PySide6":
        raise SystemExit(
            "Для запуска GUI установите зависимости: "
            "python3.13 -m pip install -r requirements.txt"
        ) from exc
    raise


if __name__ == "__main__":
    sys.exit(run())
