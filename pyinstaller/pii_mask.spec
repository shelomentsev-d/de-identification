# PyInstaller build definition shared by macOS and Windows.
from pathlib import Path
import sys

project = Path(SPECPATH).parent


a = Analysis(
    [str(project / "run_app.py")],
    pathex=[str(project)],
    binaries=[],
    datas=[
        (str(project / "assets" / "De-identification.icns"), "."),
        (str(project / "assets" / "De-identification.ico"), "."),
    ],
    hiddenimports=[
        "docx",
        "openpyxl",
        "pptx",
        "pypdf",
        "natasha",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="De-identification",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(project / "assets" / "De-identification.ico") if sys.platform == "win32" else None,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="De-identification",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="De-identification.app",
        icon=str(project / "assets" / "De-identification.icns"),
        bundle_identifier="org.deidentification.app",
    )
