import os
import sys

# PyInstaller 打包后 exe 同级目录，开发时用项目根目录
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)


class Config:
    SECRET_KEY = 'freight-calculator-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(DATA_DIR, "freight.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 上传文件大小限制 20MB
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    # APScheduler 配置
    SCHEDULER_HOUR = 0   # 凌晨0点执行定时任务
    SCHEDULER_MINUTE = 0
