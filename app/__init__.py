import os
import sys
from flask import Flask
from flask_cors import CORS
from .config import Config
from .models import db, AppConfig, TierInterval, VolumetricCoefficient
from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler


scheduler = BackgroundScheduler()
_app_ref = None  # 保存Flask应用引用，供定时任务使用


def create_app():
    global _app_ref

    # PyInstaller 打包后模板/静态文件在 _MEIPASS 临时目录
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        template_folder = os.path.join(base, 'app', 'templates')
        static_folder = os.path.join(base, 'app', 'static')
    else:
        template_folder = 'templates'
        static_folder = 'static'

    app = Flask(__name__,
                template_folder=template_folder,
                static_folder=static_folder)
    app.config.from_object(Config)
    CORS(app)
    _app_ref = app

    # 初始化数据库
    db.init_app(app)
    with app.app_context():
        db.create_all()
        # 数据库迁移：为已有表新增「运输方式」列（如不存在）
        for table, col in [('delivery_order', '运输方式'), ('contract_rate', '运输方式')]:
            try:
                db.session.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN '{col}' VARCHAR(50) DEFAULT ''"
                ))
                db.session.commit()
            except Exception:
                db.session.rollback()
        _init_defaults()

    # 启动时检查合同状态
    with app.app_context():
        from .services.contract_status import check_contract_status
        check_contract_status()

    # 注册蓝图
    from .routes.delivery import bp as delivery_bp
    from .routes.ltl_approval import bp as ltl_bp
    from .routes.contract import bp as contract_bp
    from .routes.trial import bp as trial_bp
    from .routes.config import bp as config_bp
    from .routes.update import bp as update_bp

    app.register_blueprint(delivery_bp, url_prefix='/api/delivery')
    app.register_blueprint(ltl_bp, url_prefix='/api/ltl-approval')
    app.register_blueprint(contract_bp, url_prefix='/api/contract')
    app.register_blueprint(trial_bp, url_prefix='/api/trial')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    app.register_blueprint(update_bp, url_prefix='/api/update')

    # 主页面
    @app.route('/')
    def index():
        from flask import render_template
        from app.version import __version__
        return render_template('index.html', version=__version__)

    # 启动定时任务（每天凌晨检查合同状态）
    if not scheduler.running:
        scheduler.add_job(
            func=_scheduled_status_check,
            trigger='cron',
            hour=Config.SCHEDULER_HOUR,
            minute=Config.SCHEDULER_MINUTE,
            id='contract_status_check',
            replace_existing=True
        )
        scheduler.start()

    return app


def _init_defaults():
    """初始化默认配置数据"""
    # 泡货系数
    if not AppConfig.query.get('volumetric_coefficient'):
        db.session.add(AppConfig(key='volumetric_coefficient', value='3.5'))
    if VolumetricCoefficient.query.count() == 0:
        db.session.add(VolumetricCoefficient(coefficient=3.5, is_active=True))

    # 整车唯一标识（默认为拼车单号）
    if not AppConfig.query.get('truck_unique_fields'):
        db.session.add(AppConfig(key='truck_unique_fields', value='拼车单号'))

    # 默认坎级区间（示例：5个坎级）
    if TierInterval.query.count() == 0:
        defaults = [
            TierInterval(tier_name='坎级1', tier_order=1,
                         lower_value=0, lower_inclusive=True,
                         upper_value=8, upper_inclusive=False),
            TierInterval(tier_name='坎级2', tier_order=2,
                         lower_value=8, lower_inclusive=True,
                         upper_value=16, upper_inclusive=False),
            TierInterval(tier_name='坎级3', tier_order=3,
                         lower_value=16, lower_inclusive=True,
                         upper_value=24, upper_inclusive=False),
            TierInterval(tier_name='坎级4', tier_order=4,
                         lower_value=24, lower_inclusive=True,
                         upper_value=999999, upper_inclusive=False),
        ]
        db.session.add_all(defaults)

    db.session.commit()


def _scheduled_status_check():
    """定时任务：检查合同状态"""
    if _app_ref is None:
        return
    with _app_ref.app_context():
        from .services.contract_status import check_contract_status
        check_contract_status()
