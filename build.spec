# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 — 运费试算工具
用法: pyinstaller build.spec --clean -y
"""
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# 收集 pywebview + pythonnet + clr_loader 的全部文件（含 .NET 运行时 DLL）
_webview_datas, _webview_binaries, _webview_hiddenimports = collect_all('webview')
_pythonnet_datas, _pythonnet_binaries, _pythonnet_hiddenimports = collect_all('pythonnet')
_clr_datas, _clr_binaries, _clr_hiddenimports = collect_all('clr_loader')

# 诊断：打印收集结果
print(f'[Spec] webview: {len(_webview_datas)} datas, {len(_webview_binaries)} binaries, {len(_webview_hiddenimports)} hiddenimports')
print(f'[Spec] pythonnet: {len(_pythonnet_datas)} datas, {len(_pythonnet_binaries)} binaries, {len(_pythonnet_hiddenimports)} hiddenimports')
print(f'[Spec] clr_loader: {len(_clr_datas)} datas, {len(_clr_binaries)} binaries, {len(_clr_hiddenimports)} hiddenimports')

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=_webview_binaries + _pythonnet_binaries + _clr_binaries,
    datas=[
        ('app/templates', 'app/templates'),
        ('app/static', 'app/static'),
    ] + _webview_datas + _pythonnet_datas + _clr_datas,
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
    ] + _webview_hiddenimports + _pythonnet_hiddenimports + _clr_hiddenimports + [
        'pythonnet',
        'clr',
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
    name='FreightCalculator',  # ASCII 名，避免 CI 编码乱码
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX 会导致启动崩溃
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 临时开启控制台，方便排查问题
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
