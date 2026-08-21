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
    print(f'📦 构建运费试算工具 v{__version__}')
    print('=' * 50)

    # 1. 安装 PyInstaller（如果没有）
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print('⚙ 安装 PyInstaller...')
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
                       check=True)

    # 2. PyInstaller 打包
    print('🔨 打包中（可能需要 1-3 分钟）...')
    result = subprocess.run(
        ['pyinstaller', 'build.spec', '--clean', '-y', '--distpath', 'dist'],
        check=False,
    )
    if result.returncode != 0:
        print('❌ 打包失败')
        sys.exit(1)

    # 3. 计算 exe 哈希
    exe_path = os.path.join('dist', '运费试算工具.exe')
    if not os.path.exists(exe_path):
        print(f'❌ 找不到输出文件: {exe_path}')
        sys.exit(1)

    file_hash = hashlib.sha256(open(exe_path, 'rb').read()).hexdigest()
    size_mb = os.path.getsize(exe_path) / 1024 / 1024

    # 4. 输出版本信息
    version_info = {
        'version': __version__,
        'sha256': file_hash,
        'filename': '运费试算工具.exe',
    }
    version_path = os.path.join('dist', 'version.json')
    with open(version_path, 'w', encoding='utf-8') as f:
        json.dump(version_info, f, ensure_ascii=False, indent=2)

    print('=' * 50)
    print(f'✅ 构建完成: v{__version__}')
    print(f'   exe:    {exe_path} ({size_mb:.1f} MB)')
    print(f'   sha256: {file_hash}')
    print(f'   版本:   {version_path}')
    print()
    print('下一步:')
    print(f'   git add . && git commit -m "v{__version__}"')
    print(f'   git tag v{__version__}')
    print(f'   git push origin main --tags')


if __name__ == '__main__':
    main()
