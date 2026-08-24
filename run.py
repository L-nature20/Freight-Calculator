"""运费试算工具 - 启动入口"""
import os
import sys
import traceback
import ctypes
import threading
import time
import socket

# 错误日志路径：exe 同级目录
if getattr(sys, 'frozen', False):
    LOG_DIR = os.path.dirname(sys.executable)
else:
    LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, 'error.log')


def _show_error(msg):
    """用 Windows 弹窗显示错误"""
    try:
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


def _is_port_in_use(port):
    """检测端口是否已被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


try:
    import webbrowser
    from app import create_app

    app = create_app()

    if __name__ == '__main__':
        def open_browser():
            """1.5秒后自动打开浏览器"""
            time.sleep(1.5)
            webbrowser.open('http://127.0.0.1:5000')

        if getattr(sys, 'frozen', False):
            # 检测端口占用：重复启动时直接打开浏览器
            if _is_port_in_use(5000):
                print('应用已在运行中，正在打开浏览器...')
                webbrowser.open('http://127.0.0.1:5000')
                time.sleep(2)
                sys.exit(0)

            # 打包模式：控制台显示 3 秒后完全隐藏
            threading.Thread(target=open_browser, daemon=True).start()
            print('运费试算工具 v1.0.0')
            print('访问地址: http://127.0.0.1:5000')
            print('浏览器将自动打开...')
            print('关闭当前窗口即退出应用')
            print('=' * 40)

            def _hide_console():
                time.sleep(3)
                try:
                    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                    if hwnd:
                        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
                except Exception:
                    pass
            threading.Thread(target=_hide_console, daemon=True).start()

            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
        else:
            threading.Thread(target=open_browser, daemon=True).start()
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
