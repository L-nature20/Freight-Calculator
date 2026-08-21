"""运费试算工具 - 启动入口"""
import os
import sys
import traceback

# 错误日志路径：exe 同级目录
if getattr(sys, 'frozen', False):
    LOG_DIR = os.path.dirname(sys.executable)
else:
    LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, 'error.log')


def _show_error(msg):
    """用 Windows 弹窗显示错误"""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, '运费试算工具 - 启动失败', 0x10)
    except Exception:
        pass


def _log_error(exc):
    """写错误日志"""
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(traceback.format_exc())
    except Exception:
        pass


try:
    import webbrowser
    import threading
    from app import create_app

    app = create_app()

    def open_browser():
        """启动后自动打开浏览器"""
        webbrowser.open('http://127.0.0.1:5000')

    if __name__ == '__main__':
        # 1.5秒后自动打开浏览器
        threading.Timer(1.5, open_browser).start()

        if getattr(sys, 'frozen', False):
            app.run(host='127.0.0.1', port=5000, debug=False)
        else:
            print('=' * 50)
            print('  运费试算工具已启动')
            print('  访问地址: http://127.0.0.1:5000')
            print('  按 Ctrl+C 停止服务')
            print('=' * 50)
            app.run(host='127.0.0.1', port=5000, debug=False)

except Exception:
    exc_info = traceback.format_exc()
    _log_error(exc_info)
    _show_error(f'启动失败，详见 exe 同目录 error.log\n\n{exc_info}')
    sys.exit(1)
