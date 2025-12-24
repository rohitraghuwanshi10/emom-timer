# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('sounds', 'sounds'), ('icon.png', '.')]
binaries = []
hiddenimports = []

# Collect customtkinter
tmp_ret_ctk = collect_all('customtkinter')
datas += tmp_ret_ctk[0]; binaries += tmp_ret_ctk[1]; hiddenimports += tmp_ret_ctk[2]

# Collect bleak
tmp_ret_bleak = collect_all('bleak')
datas += tmp_ret_bleak[0]; binaries += tmp_ret_bleak[1]; hiddenimports += tmp_ret_bleak[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='EMOM Timer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EMOM Timer',
)
app = BUNDLE(
    coll,
    name='EMOM Timer.app',
    icon=None,
    bundle_identifier=None,
)
