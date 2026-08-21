"""基础配置路由"""
import os
import sys
from flask import Blueprint, request, jsonify
from ..models import db, AppConfig, TierInterval, VolumetricCoefficient

bp = Blueprint('config', __name__)


# ─────────────────────────────────────────
#  系统配置
# ─────────────────────────────────────────
@bp.route('', methods=['GET'])
def get_config():
    """获取所有配置"""
    configs = AppConfig.query.all()
    return jsonify({c.key: c.value for c in configs})


@bp.route('/<key>', methods=['PUT'])
def update_config(key):
    """修改配置项"""
    d = request.json
    value = str(d.get('value', '')).strip()

    # 泡货系数校验
    if key == 'volumetric_coefficient':
        try:
            v = float(value)
            if v <= 0:
                return jsonify({'error': '系数必须大于0'}), 400
        except ValueError:
            return jsonify({'error': '系数必须为数值'}), 400

    cfg = AppConfig.query.get(key)
    if cfg:
        cfg.value = value
    else:
        cfg = AppConfig(key=key, value=value)
        db.session.add(cfg)
    db.session.commit()
    return jsonify({'key': key, 'value': value})


# ─────────────────────────────────────────
#  坎级区间
# ─────────────────────────────────────────
@bp.route('/tier-intervals', methods=['GET'])
def list_tiers():
    """查询坎级区间"""
    tiers = TierInterval.query.order_by(TierInterval.tier_order).all()
    return jsonify([t.to_dict() for t in tiers])


@bp.route('/tier-intervals', methods=['POST'])
def create_tier():
    """新增坎级区间"""
    d = request.json
    tier = TierInterval(
        tier_name=str(d.get('坎级名称', '')).strip(),
        tier_order=int(d.get('坎级序数', 0)),
        lower_value=float(d.get('lower_value', 0)),
        lower_inclusive=d.get('lower_inclusive', True),
        upper_value=float(d.get('upper_value', 0)),
        upper_inclusive=d.get('upper_inclusive', False),
    )

    # 序数唯一性检查
    if TierInterval.query.filter_by(tier_order=tier.tier_order).first():
        return jsonify({'error': f'坎级序数{tier.tier_order}已存在'}), 409

    db.session.add(tier)
    db.session.commit()
    return jsonify(tier.to_dict()), 201


@bp.route('/tier-intervals/<int:id>', methods=['PUT'])
def update_tier(id):
    """编辑坎级区间"""
    tier = TierInterval.query.get_or_404(id)
    d = request.json
    tier.tier_name = str(d.get('坎级名称', tier.tier_name)).strip()
    if '坎级序数' in d:
        new_order = int(d['坎级序数'])
        if new_order != tier.tier_order:
            if TierInterval.query.filter_by(tier_order=new_order).first():
                return jsonify({'error': f'坎级序数{new_order}已存在'}), 409
        tier.tier_order = new_order
    if 'lower_value' in d:
        tier.lower_value = float(d['lower_value'])
    if 'lower_inclusive' in d:
        tier.lower_inclusive = d['lower_inclusive']
    if 'upper_value' in d:
        tier.upper_value = float(d['upper_value'])
    if 'upper_inclusive' in d:
        tier.upper_inclusive = d['upper_inclusive']
    db.session.commit()
    return jsonify(tier.to_dict())


@bp.route('/tier-intervals/<int:id>', methods=['DELETE'])
def delete_tier(id):
    """删除坎级区间"""
    tier = TierInterval.query.get_or_404(id)
    db.session.delete(tier)
    db.session.commit()
    return jsonify({'message': '删除成功'})


@bp.route('/tier-intervals/validate', methods=['GET'])
def validate_tiers():
    """校验坎级区间完整性"""
    tiers = TierInterval.query.order_by(TierInterval.tier_order).all()
    issues = []

    if not tiers:
        issues.append('未配置任何坎级区间')
        return jsonify({'valid': False, 'issues': issues})

    # 序数连续性
    orders = [t.tier_order for t in tiers]
    expected = list(range(1, len(tiers) + 1))
    if orders != expected:
        issues.append(f'坎级序数不连续，当前序数: {orders}，期望: {expected}')

    # 首坎级下限须覆盖最小重量值（0）
    first_tier = tiers[0]
    if first_tier.lower_value > 0 or (first_tier.lower_value == 0 and not first_tier.lower_inclusive):
        issues.append(f'首坎级({first_tier.tier_name})下限须覆盖最小重量值(≥0)')

    # 区间覆盖检查
    for i, tier in enumerate(tiers):
        # 上下限合理性
        if tier.lower_value > tier.upper_value:
            issues.append(f'{tier.tier_name}: 下限({tier.lower_value})大于上限({tier.upper_value})')

        # 连续性检查（与下一坎级衔接）
        if i < len(tiers) - 1:
            next_tier = tiers[i + 1]
            # 检查是否有缺口：当前上限应与下一坎级下限无缝衔接
            gap = False
            if tier.upper_value != next_tier.lower_value:
                gap = True
            elif tier.upper_inclusive == next_tier.lower_inclusive:
                # 两者同时含等号或同时不含等号，则存在重叠或缺口
                gap = True
            if gap:
                issues.append(
                    f'{tier.tier_name}与{next_tier.tier_name}区间不连续或有重叠'
                    f'（{tier.tier_name}上限={tier.upper_value}，{next_tier.tier_name}下限={next_tier.lower_value}）'
                )

    return jsonify({'valid': len(issues) == 0, 'issues': issues})


# ─────────────────────────────────────────
#  泡货系数版本管理
# ─────────────────────────────────────────
@bp.route('/coefficient', methods=['GET'])
def get_coefficient_history():
    """获取泡货系数历史版本"""
    records = VolumetricCoefficient.query.order_by(VolumetricCoefficient.id.desc()).all()
    return jsonify([r.to_dict() for r in records])


@bp.route('/coefficient', methods=['POST'])
def add_coefficient():
    """新增泡货系数（旧值自动失效）"""
    d = request.json
    try:
        val = float(d.get('coefficient', 0))
        if val <= 0:
            return jsonify({'error': '系数必须大于0'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': '系数必须为数值'}), 400

    # 旧值置为失效
    VolumetricCoefficient.query.filter_by(is_active=True).update({'is_active': False})
    # 新增
    new_coeff = VolumetricCoefficient(coefficient=val, is_active=True)
    db.session.add(new_coeff)
    # 同步更新 AppConfig
    cfg = AppConfig.query.get('volumetric_coefficient')
    if cfg:
        cfg.value = str(val)
    else:
        db.session.add(AppConfig(key='volumetric_coefficient', value=str(val)))
    db.session.commit()
    return jsonify(new_coeff.to_dict()), 201


# ─────────────────────────────────────────
#  退出应用
# ─────────────────────────────────────────
@bp.route('/shutdown', methods=['POST'])
def api_shutdown():
    """退出应用（仅打包模式）"""
    if not getattr(sys, 'frozen', False):
        return jsonify({'success': False, 'error': '开发模式不支持退出'})
    os._exit(0)
