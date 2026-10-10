# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['../outputs/sifeng_planet.pyw'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/guqig/Documents/Codex/2026-10-09/new-chat/outputs/sifeng_planet.ico', '.'), ('C:/Users/guqig/Documents/Codex/2026-10-09/new-chat/outputs/minimize.svg', '.'), ('C:/Users/guqig/Documents/Codex/2026-10-09/new-chat/outputs/maximize.svg', '.'), ('C:/Users/guqig/Documents/Codex/2026-10-09/new-chat/outputs/restore.svg', '.'), ('C:/Users/guqig/Documents/Codex/2026-10-09/new-chat/outputs/close.svg', '.')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='SiFengPlanet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/guqig/Documents/Codex/2026-10-09/new-chat/outputs/sifeng_planet.ico'],
)
