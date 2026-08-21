"""一键构建发布包
用法: python build.py
输出: dist/运费试算工具.exe + dist/version.json
"""
import os
import sys
import subprocess
import hashlib
import json

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(__file__))

from app.version import __version__


def main():
    print(f'[Build] Freight Calculator v{__version__}')
    print('=' * 50)

    # 1. Install PyInstaller if missing
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print('[Build] Installing PyInstaller...')
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
                       check=True)

    # 2. PyInstaller package
    print('[Build] Packaging (1-3 minutes)...')
    result = subprocess.run(
        ['pyinstaller', 'build.spec', '--clean', '-y', '--distpath', 'dist'],
        check=False,
    )
    if result.returncode != 0:
        print('[Build] Package FAILED')
        sys.exit(1)

    # 3. Calculate exe hash
    exe_path = os.path.join('dist', '运费试算工具.exe')
    if not os.path.exists(exe_path):
        print(f'[Build] Output not found: {exe_path}')
        sys.exit(1)

    file_hash = hashlib.sha256(open(exe_path, 'rb').read()).hexdigest()
    size_mb = os.path.getsize(exe_path) / 1024 / 1024

    # 4. Output version info
    version_info = {
        'version': __version__,
        'sha256': file_hash,
        'filename': '运费试算工具.exe',
    }
    version_path = os.path.join('dist', 'version.json')
    with open(version_path, 'w', encoding='utf-8') as f:
        json.dump(version_info, f, ensure_ascii=False, indent=2)

    print('=' * 50)
    print(f'[Build] Done: v{__version__}')
    print(f'   exe:    {exe_path} ({size_mb:.1f} MB)')
    print(f'   sha256: {file_hash}')
    print(f'   info:   {version_path}')
    print()
    print('Next steps:')
    print(f'   git add . && git commit -m "v{__version__}"')
    print(f'   git tag v{__version__}')
    print(f'   git push origin main --tags')


if __name__ == '__main__':
    main()
