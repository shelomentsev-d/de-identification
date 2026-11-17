# PyInstaller build definition shared by macOS and Windows.
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all

project = Path(SPECPATH).parent

# natasha and its dependencies ship model/dictionary files (.tar, .txt, DAWG)
# that PyInstaller does not pick up from hiddenimports alone.
NER_PACKAGES = [
    "natasha",
    "navec",
    "slovnet",
    "razdel",
    "yargy",
    "ipymarkup",
    "intervaltree",
    "pymorphy2",
    "pymorphy2_dicts_ru",
    "dawg_python",
]
ner_datas, ner_binaries, ner_hiddenimports = [], [], []
for package in NER_PACKAGES:
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    ner_datas += pkg_datas
    ner_binaries += pkg_binaries
    ner_hiddenimports += pkg_hidden


a = Analysis(
    [str(project / "run_app.py")],
    pathex=[str(project)],
    binaries=ner_binaries,
    datas=[
        (str(project / "assets" / "de-Identification.icns"), "."),
        (str(project / "assets" / "de-Identification.ico"), "."),
    ] + ner_datas,
    hiddenimports=[
        "docx",
        "openpyxl",
        "pptx",
        "pypdf",
    ] + ner_hiddenimports,
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
    name="de-Identification",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(project / "assets" / "de-Identification.ico") if sys.platform == "win32" else None,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="de-Identification",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="de-Identification.app",
        icon=str(project / "assets" / "de-Identification.icns"),
        bundle_identifier="org.deIdentification.app",
    )
