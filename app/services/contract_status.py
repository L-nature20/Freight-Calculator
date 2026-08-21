"""合同状态自动管理：启动时检查 + 定时任务"""
from datetime import date
from ..models import db, Contract


def check_contract_status():
    """
    扫描所有合同，按规则自动更新状态：
    - 草稿 + 当前日期 >= 生效日期 → 生效
    - 生效 + 当前日期 > 失效日期 → 失效
    - 作废的合同不做处理
    """
    today = date.today().strftime('%Y%m%d')
    changed = 0

    # 草稿 → 生效
    drafts = Contract.query.filter_by(status='草稿').all()
    for c in drafts:
        if today >= c.start_date:
            c.status = '生效'
            changed += 1

    # 生效 → 失效
    active = Contract.query.filter_by(status='生效').all()
    for c in active:
        if today > c.end_date:
            c.status = '失效'
            changed += 1

    if changed > 0:
        db.session.commit()

    return changed
