"""运费试算工具 - 启动入口"""
import os
import sys
import socket
import ctypes
import threading
import time
import traceback
import webbrowser

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
    from app import create_app

    if __name__ == '__main__':
        if getattr(sys, 'frozen', False):
            # ── 打包模式：pywebview 原生桌面窗口 ──

            # 重复启动检测
            if _is_port_in_use(5000):
                try:
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        '应用已在运行中。\n\n如需重启，请先关闭已有实例。',
                        '运费试算工具',
                        0x40,  # MB_ICONINFORMATION
                    )
                except Exception:
                    pass
                sys.exit(0)

            # 后台启动 Flask
            app = create_app()
            threading.Thread(
                target=lambda: app.run(
                    host='127.0.0.1', port=5000,
                    debug=False, use_reloader=False,
                ),
                daemon=True,
            ).start()

            # 等待 Flask 就绪（最多 30 秒）
            for _ in range(30):
                if _is_port_in_use(5000):
                    break
                time.sleep(1)

            # 创建原生桌面窗口
            _webview_ok = False
            try:
                import webview

                class _Api:
                    """供前端 JS 调用的 Python 方法"""
                    def shutdown(self):
                        window.destroy()

                window = webview.create_window(
                    '运费试算工具',
                    'http://127.0.0.1:5000',
                    width=1280,
                    height=800,
                    min_size=(800, 600),
                    js_api=_Api(),
                )
                _webview_ok = True
                webview.start()
            except Exception as e:
                _log_error(f'pywebview 启动失败: {e}')
                _show_error(
                    '桌面窗口启动失败，已打开浏览器。\n\n'
                    f'错误: {e}\n\n详见 exe 同目录 error.log'
                )
                webbrowser.open('http://127.0.0.1:5000')

            # webview 模式：窗口关闭后退出
            # fallback 模式：浏览器已打开，等待用户关闭
            if _webview_ok:
                os._exit(0)
            else:
                # 浏览器模式：保持进程运行直到用户手动关闭
                try:
                    input('按回车键退出应用...')
                except EOFError:
                    pass
                os._exit(0)

        else:
            # ── 开发模式：浏览器方式 ──
            app = create_app()

            def open_browser():
                time.sleep(1.5)
                webbrowser.open('http://127.0.0.1:5000')

            threading.Thread(target=open_browser, daemon=True).start()
            print('=' * 50)
            print('  运费试算工具已启动（开发模式）')
            print('  访问地址: http://127.0.0.1:5000')
            print('  按 Ctrl+C 停止服务')
            print('=' * 50)
            app.run(host='127.0.0.1', port=5000, debug=False)

except Exception:
    exc_info = traceback.format_exc()
    _log_error(exc_info)
    _show_error(f'启动失败，详见 exe 同目录 error.log\n\n{exc_info}')
    sys.exit(1)
