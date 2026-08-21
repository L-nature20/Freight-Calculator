from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()


# ─────────────────────────────────────────
# 交货单
# ─────────────────────────────────────────
class DeliveryOrder(db.Model):
    __tablename__ = 'delivery_order'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    delivery_no = db.Column('交货单号', db.String(50), unique=True, nullable=False)
    shipping_point = db.Column('装运点', db.String(100), nullable=False)
    shipping_point_desc = db.Column('装运点描述', db.String(100), nullable=False)
    transport_area = db.Column('运输区域', db.String(100), nullable=False)
    transport_area_desc = db.Column('运输区域描述', db.String(100), nullable=False)
    total_weight = db.Column('总重量_吨', db.Float, nullable=False)          # 吨，保留3位
    total_volume = db.Column('总体积_m3', db.Float, nullable=False)         # m³，保留3位
    consolidated_no = db.Column('拼车单号', db.String(50), nullable=True, default='')
    waybill_no = db.Column('运单号', db.String(50), nullable=True, default='')
    post_date = db.Column('发货过账日期', db.String(8), nullable=False)     # YYYYMMDD
    license_plate = db.Column('车牌号', db.String(20), nullable=True)
    sales_org = db.Column('销售组织', db.String(50), nullable=False)
    org_name = db.Column('组织名称', db.String(100), nullable=False)
    carrier_name = db.Column('承运商名称', db.String(100), nullable=False)
    carrier_code = db.Column('承运商编码', db.String(50), nullable=False)
    consignee_name = db.Column('送达方名称', db.String(100), nullable=False)
    consignee_code = db.Column('送达方编码', db.String(50), nullable=False)
    cargo_type = db.Column('货物类型', db.String(50), nullable=False, default='普货')
    transport_mode = db.Column('运输方式', db.String(50), nullable=False, default='')

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def _format_post_date(self):
        """将内部存储的日期（YYYYMMDD 或遗留的 datetime 字符串）转为 YYYY-MM-DD 显示格式。"""
        v = self.post_date or ''
        if len(v) == 8 and v.isdigit():
            return f'{v[:4]}-{v[4:6]}-{v[6:8]}'
        if len(v) >= 10 and v[4] == '-' and v[7] == '-':
            return v[:10]
        return v

    def to_dict(self):
        return {
            'id': self.id,
            '交货单号': self.delivery_no,
            '装运点': self.shipping_point,
            '装运点描述': self.shipping_point_desc,
            '运输区域': self.transport_area,
            '运输区域描述': self.transport_area_desc,
            '总重量（吨）': round(self.total_weight, 3) if self.total_weight is not None else None,
            '总体积（m³）': round(self.total_volume, 3) if self.total_volume is not None else None,
            '拼车单号': self.consolidated_no,
            '运单号': self.waybill_no,
            '发货过账日期': self._format_post_date(),
            '车牌号': self.license_plate,
            '销售组织': self.sales_org,
            '组织名称': self.org_name,
            '承运商名称': self.carrier_name,
            '承运商编码': self.carrier_code,
            '送达方名称': self.consignee_name,
            '送达方编码': self.consignee_code,
            '货物类型': self.cargo_type,
            '运输方式': self.transport_mode,
        }


# ─────────────────────────────────────────
# 零担审批
# ─────────────────────────────────────────
class LtlApproval(db.Model):
    __tablename__ = 'ltl_approval'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ltl_type = db.Column('零担类型', db.String(10), nullable=False)   # 支线/干线
    vehicle_seq = db.Column('车序号', db.String(20), nullable=False)
    ltl_vehicle_no = db.Column('零担车次', db.String(50), nullable=False)  # 零担类型&车序号
    delivery_no = db.Column('交货单号', db.String(50), nullable=False)
    approval_month = db.Column('零担审批月份', db.String(6), nullable=False)  # YYYYMM

    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            '零担车次': self.ltl_vehicle_no,
            '零担类型': self.ltl_type,
            '车序号': self.vehicle_seq,
            '交货单号': self.delivery_no,
            '零担审批月份': self.approval_month,
        }


# ─────────────────────────────────────────
# 合同
# ─────────────────────────────────────────
class Contract(db.Model):
    __tablename__ = 'contract'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contract_code = db.Column('合同编码', db.String(50), unique=True, nullable=False)
    contract_name = db.Column('合同名称', db.String(200), nullable=False)
    carrier_name = db.Column('承运商名称', db.String(100), nullable=False)
    carrier_code = db.Column('承运商编码', db.String(50), nullable=False)
    start_date = db.Column('合同有效期起始', db.String(8), nullable=False)  # YYYYMMDD
    end_date = db.Column('合同有效期截止', db.String(8), nullable=False)    # YYYYMMDD
    status = db.Column('合同状态', db.String(10), nullable=False, default='草稿')
    remark = db.Column('备注', db.Text, nullable=True)

    rates = db.relationship('ContractRate', backref='contract',
                            cascade='all, delete-orphan', lazy='dynamic')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            '合同编码': self.contract_code,
            '合同名称': self.contract_name,
            '承运商名称': self.carrier_name,
            '承运商编码': self.carrier_code,
            '合同有效期起始': self.start_date,
            '合同有效期截止': self.end_date,
            '合同状态': self.status,
            '备注': self.remark,
        }


# ─────────────────────────────────────────
# 合同费率（含坎级价格，每行=一条线路）
# ─────────────────────────────────────────
class ContractRate(db.Model):
    __tablename__ = 'contract_rate'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    route_code = db.Column('线路代码', db.String(200), nullable=False)   # 装运点&运输区域（自动生成）
    tier_count = db.Column('坎级数', db.Integer, nullable=False, default=0)
    shipping_point = db.Column('装运点', db.String(100), nullable=False)
    shipping_point_desc = db.Column('装运点描述', db.String(100), nullable=False)
    transport_area = db.Column('运输区域', db.String(100), nullable=False)
    transport_area_desc = db.Column('运输区域描述', db.String(100), nullable=False)
    province = db.Column('省_直辖市', db.String(50), nullable=False)
    city = db.Column('地级市', db.String(50), nullable=False)
    district = db.Column('县_区', db.String(50), nullable=False)
    mileage = db.Column('里程_KM', db.Float, nullable=False)
    route_type = db.Column('线路类型', db.String(50), nullable=False)
    has_terminal = db.Column('是否含末端', db.String(5), nullable=False)   # 是/否（自动判断）
    tax_rate = db.Column('增值税税率', db.Float, nullable=False)           # 如 0.09 代表 9%
    price1 = db.Column('含增值税运输价格1', db.Float, nullable=False, default=0)
    price2 = db.Column('含增值税运输价格2', db.Float, nullable=False, default=0)
    price3 = db.Column('含增值税运输价格3', db.Float, nullable=False, default=0)
    price4 = db.Column('含增值税运输价格4', db.Float, nullable=False, default=0)
    terminal_fee = db.Column('含增值税末端费用', db.Float, nullable=False, default=0)
    cargo_type = db.Column('货物类型', db.String(50), nullable=False, default='普货')
    transport_mode = db.Column('运输方式', db.String(50), nullable=False, default='')

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            '线路代码': self.route_code,
            '坎级数': self.tier_count,
            '装运点': self.shipping_point,
            '装运点描述': self.shipping_point_desc,
            '运输区域': self.transport_area,
            '运输区域描述': self.transport_area_desc,
            '省/直辖市': self.province,
            '地级市': self.city,
            '县/区': self.district,
            '里程(KM)': self.mileage,
            '线路类型': self.route_type,
            '是否含末端': self.has_terminal,
            '增值税税率': self.tax_rate,
            '含增值税运输价格1': self.price1,
            '含增值税运输价格2': self.price2,
            '含增值税运输价格3': self.price3,
            '含增值税运输价格4': self.price4,
            '含增值税末端费用': self.terminal_fee,
            '货物类型': self.cargo_type,
            '运输方式': self.transport_mode,
        }


# ─────────────────────────────────────────
# 全局坎级区间
# ─────────────────────────────────────────
class TierInterval(db.Model):
    __tablename__ = 'tier_interval'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tier_name = db.Column('坎级名称', db.String(50), nullable=False)
    tier_order = db.Column('坎级序数', db.Integer, unique=True, nullable=False)
    lower_value = db.Column('坎级下限值', db.Float, nullable=False)
    lower_inclusive = db.Column('下限含等号', db.Boolean, default=True)  # True: >=, False: >
    upper_value = db.Column('坎级上限值', db.Float, nullable=False)
    upper_inclusive = db.Column('上限含等号', db.Boolean, default=False)  # True: <=, False: <

    def to_dict(self):
        lower_op = '≥' if self.lower_inclusive else '＞'
        upper_op = '≤' if self.upper_inclusive else '＜'
        return {
            'id': self.id,
            '坎级名称': self.tier_name,
            '坎级序数': self.tier_order,
            '坎级下限': f'{lower_op}{self.lower_value}',
            '坎级上限': f'{upper_op}{self.upper_value}',
            'lower_value': self.lower_value,
            'lower_inclusive': self.lower_inclusive,
            'upper_value': self.upper_value,
            'upper_inclusive': self.upper_inclusive,
        }

    def matches(self, weight: float) -> bool:
        """判断给定重量是否落入该坎级区间"""
        if self.lower_inclusive:
            lower_ok = weight >= self.lower_value
        else:
            lower_ok = weight > self.lower_value
        if self.upper_inclusive:
            upper_ok = weight <= self.upper_value
        else:
            upper_ok = weight < self.upper_value
        return lower_ok and upper_ok


# ─────────────────────────────────────────
# 系统配置（key-value）
# ─────────────────────────────────────────
class AppConfig(db.Model):
    __tablename__ = 'app_config'

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), nullable=False)

    def to_dict(self):
        return {'key': self.key, 'value': self.value}


# ─────────────────────────────────────────
# 泡货体积重量折算系数（版本管理）
# ─────────────────────────────────────────
class VolumetricCoefficient(db.Model):
    __tablename__ = 'volumetric_coefficient'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    coefficient = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'coefficient': self.coefficient,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
