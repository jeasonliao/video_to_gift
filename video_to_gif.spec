# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['video_to_gif_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('ffmpeg_binaries/macos', 'ffmpeg_binaries')],
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
    [],
    exclude_binaries=True,
    name='video_to_gif',
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
    name='video_to_gif',
)
app = BUNDLE(
    coll,
    name='video_to_gif.app',
    icon=None,
    bundle_identifier=None,
)
