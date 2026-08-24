# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 — 运费试算工具
用法: pyinstaller build.spec --clean -y
"""

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/templates', 'app/templates'),
        ('app/static', 'app/static'),
    ],
    hiddenimports=[
        'app.routes.delivery',
        'app.routes.contract',
        'app.routes.ltl_approval',
        'app.routes.trial',
        'app.routes.config',
        'app.routes.update',
        'app.services.contract_status',
        'app.services.excel_io',
        'app.engine.calculator',
        'app.engine.matcher',
        'app.engine.exceptions',
        'app.updater',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='运费试算工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX 会导致启动崩溃
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 美化后的控制台窗口，关闭即退出
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
