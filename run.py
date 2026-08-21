"""运费试算工具 - 启动入口"""
import sys
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
        # 打包模式：静默启动
        app.run(host='127.0.0.1', port=5000, debug=False)
    else:
        print('=' * 50)
        print('  运费试算工具已启动')
        print('  访问地址: http://127.0.0.1:5000')
        print('  按 Ctrl+C 停止服务')
        print('=' * 50)
        app.run(host='127.0.0.1', port=5000, debug=False)
