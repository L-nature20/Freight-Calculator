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

    if __name__ == '__main__':
        splash = None

        def open_browser():
            """启动后自动打开浏览器，关闭 splash 窗口"""
            webbrowser.open('http://127.0.0.1:5000')
            if splash is not None:
                splash.destroy()

        if getattr(sys, 'frozen', False):
            # 打包模式：显示 Tkinter splash 窗口
            import tkinter as tk
            splash = tk.Tk()
            splash.title('运费试算工具')
            splash.geometry('300x120')
            splash.resizable(False, False)
            # 居中显示
            splash.update_idletasks()
            w, h = 300, 120
            x = (splash.winfo_screenwidth() - w) // 2
            y = (splash.winfo_screenheight() - h) // 2
            splash.geometry(f'{w}x{h}+{x}+{y}')
            tk.Label(splash, text='运费试算工具', font=('Microsoft YaHei', 14)).pack(pady=15)
            tk.Label(splash, text='正在启动，请稍候...', font=('Microsoft YaHei', 9), fg='gray').pack()

            def on_ready():
                webbrowser.open('http://127.0.0.1:5000')
                splash.destroy()

            splash.after(1500, on_ready)

            # Flask 放后台线程，主线程运行 tkinter 事件循环
            t = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False), daemon=True)
            t.start()
            splash.mainloop()
        else:
            threading.Timer(1.5, open_browser).start()
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
