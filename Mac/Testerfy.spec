# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_macos.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtSvg', 'pynput', 'keyring'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Testerfy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity='',
    entitlements_file=None,
    icon=['green_t.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Testerfy',
)
app = BUNDLE(
    coll,
    name='Testerfy.app',
    icon='green_t.icns',
    bundle_identifier=None,
)
