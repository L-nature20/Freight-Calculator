"""自动更新 API"""
import os
import sys
import subprocess
from flask import Blueprint, jsonify, request

from app.updater import check_update, download_update, reset_check_cache

bp = Blueprint('update', __name__)


@bp.route('/check', methods=['GET'])
def api_check():
    """检查是否有新版本。传 ?force=1 强制重新请求 GitHub。"""
    if request.args.get('force'):
        reset_check_cache()
    has_update, version, url, raw_url, notes = check_update()
    return jsonify({
        'has_update': has_update,
        'version': version,
        'notes': notes,
        'raw_url': raw_url,  # GitHub 原始链接（供手动下载）
        'can_update': getattr(sys, 'frozen', False),
    })


@bp.route('/apply', methods=['POST'])
def api_apply():
    """下载新版 exe 并准备替换。
    下载完成后启动替换脚本，当前进程退出后自动替换。
    """
    has_update, version, url, raw_url, notes = check_update()
    if not has_update or not url:
        return jsonify({'success': False, 'error': '没有可用更新'})

    if not getattr(sys, 'frozen', False):
        return jsonify({'success': False, 'error': '开发模式不支持自动更新'})

    new_exe, error = download_update(url)
    if error:
        return jsonify({'success': False, 'error': error})

    # 创建替换脚本（Windows bat）
    current_exe = sys.executable
    bat_path = os.path.join(os.path.dirname(current_exe), '_update.bat')
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(f'''@echo off
timeout /t 2 /nobreak >nul
del "{current_exe}"
rename "{new_exe}" "{os.path.basename(current_exe)}"
start "" "{current_exe}"
del "%~f0"
''')

    # 启动替换脚本（后台）
    subprocess.Popen(
        ['cmd.exe', '/c', bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    resp = jsonify({'success': True, 'message': '下载完成，程序即将重启...'})

    # 延迟退出：给 Flask 时间返回响应，然后退出释放 exe 锁
    def _exit():
        import time
        time.sleep(0.5)
        os._exit(0)
    import threading
    threading.Thread(target=_exit, daemon=True).start()

    return resp
