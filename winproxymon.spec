# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['winproxymon.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Копируем папку 'img' целиком в папку 'img' внутри exe
        ('img', 'img'),
        # Копируем папку 'plugins' целиком в папку 'plugins' внутри exe
        ('plugins', 'plugins')
    ],
    hiddenimports=['socks'],
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
    name='winproxymon',
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
)