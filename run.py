"""运费试算工具 - 启动入口"""
import os
import sys
import traceback
import ctypes
import threading
import time

# 错误日志路径：exe 同级目录
if getattr(sys, 'frozen', False):
    LOG_DIR = os.path.dirname(sys.executable)
else:
    LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, 'error.log')

# ANSI 颜色码
GREEN = '\033[92m'
CYAN = '\033[96m'
YELLOW = '\033[93m'
DIM = '\033[90m'
BOLD = '\033[1m'
RESET = '\033[0m'


def _setup_console():
    """美化控制台窗口：标题、颜色、隐藏光标"""
    kernel32 = ctypes.windll.kernel32

    # 启用 ANSI 颜色
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 0x0004)

    # 设置窗口标题
    kernel32.SetConsoleTitleW('运费试算工具')

    # 隐藏光标
    class _CursorInfo(ctypes.Structure):
        _fields_ = [('size', ctypes.c_int), ('visible', ctypes.c_byte)]
    ci = _CursorInfo()
    ci.size = ctypes.sizeof(ci)
    ci.visible = 0
    kernel32.SetConsoleCursorInfo(kernel32.GetStdHandle(-11), ctypes.byref(ci))


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


def _print_banner():
    """打印启动画面"""
    lines = [
        '',
        f'  {GREEN}{BOLD}╔══════════════════════════════╗{RESET}',
        f'  {GREEN}{BOLD}║                              ║{RESET}',
        f'  {GREEN}{BOLD}║  {RESET}{BOLD}运费试算工具{RESET}{GREEN}{BOLD}               ║{RESET}',
        f'  {GREEN}{BOLD}║  {RESET}{DIM}Freight Calculator v1.0.0{RESET}{GREEN}{BOLD}  ║{RESET}',
        f'  {GREEN}{BOLD}║                              ║{RESET}',
        f'  {GREEN}{BOLD}╚══════════════════════════════╝{RESET}',
        '',
        f'  {CYAN}●{RESET} 服务地址: {BOLD}http://127.0.0.1:5000{RESET}',
        f'  {YELLOW}●{RESET} 浏览器将自动打开...',
        '',
        f'  {DIM}关闭当前窗口即退出应用{RESET}',
        f'  {DIM}' + '─' * 40 + f'{RESET}',
        '',
    ]
    for line in lines:
        print(line)


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
            # 打包模式：控制台显示 3 秒后完全隐藏
            _setup_console()
            _print_banner()
            threading.Thread(target=open_browser, daemon=True).start()

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
            _print_banner()
            app.run(host='127.0.0.1', port=5000, debug=False)

except Exception:
    exc_info = traceback.format_exc()
    _log_error(exc_info)
    _show_error(f'启动失败，详见 exe 同目录 error.log\n\n{exc_info}')
    sys.exit(1)
