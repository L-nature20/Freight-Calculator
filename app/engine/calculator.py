"""
运费试算核心计算引擎——10步流程
"""
from decimal import Decimal, ROUND_HALF_UP
from ..models import (
    db, DeliveryOrder, LtlApproval, Contract, ContractRate,
    TierInterval, AppConfig, VolumetricCoefficient
)
from .matcher import match_contract, match_rate, get_match_error


# ── 异常标记 ──
EXCEPTION_FIELDS = [
    '落档坎级单价', '下一坎级单价', '车次预估运费', '下一坎级最低运费',
    '车次适用运费', '交货单运费单价', '交货单运费结算金额',
    '交货单装卸费结算金额', '交货单结算总金额',
]

# ── 结果列表51列 ──
RESULT_COLUMNS = [
    '交货单号', '装运点', '装运点描述', '运输区域', '运输区域描述',
    '总重量（吨）', '总体积（m³）', '拼车单号', '运单号', '发货过账日期',
    '车牌号', '销售组织', '组织名称', '承运商名称', '承运商编码',
    '送达方名称', '送达方编码', '货物类型', '运输方式',
    '零担车次', '所在车次', '车次总重量（吨）', '车次总体积（m³）',
    '车次体积重量（吨）', '交货单体积重量（吨）', '符合按方结算',
    '车次计费重量（吨）', '落档坎级序数', '落档坎级（名称）',
    '是否零担', '下一坎级（序数）', '下一坎级（名称）',
    '下一坎级重量下限', '线路', '线路类型', '坎级数',
    '坎级1单价', '坎级2单价', '坎级3单价', '坎级4单价', '末端装卸费',
    '落档坎级单价', '下一坎级单价', '车次预估运费', '下一坎级最低运费',
    '车次适用运费', '交货单运费单价', '交货单计费重量',
    '交货单运费结算金额', '交货单装卸费结算金额', '交货单结算总金额',
]


def run_trial(conditions: dict) -> list:
    """
    执行运费试算。
    conditions 包含8个查询条件字段。
    返回结果列表（每条为 dict，含51个字段）。
    """
    # ── 获取配置 ──
    active_coeff = VolumetricCoefficient.query.filter_by(is_active=True).first()
    coeff = active_coeff.coefficient if active_coeff else float(
        AppConfig.query.get('volumetric_coefficient').value or 3.5
    )
    truck_fields_str = AppConfig.query.get('truck_unique_fields').value or '拼车单号'
    truck_fields = [f.strip() for f in truck_fields_str.split(',') if f.strip()]
    global_tiers = TierInterval.query.order_by(TierInterval.tier_order).all()

    # ── 查询交货单 ──
    orders = _filter_orders(conditions)
    if not orders:
        return []

    # ── 获取零担审批数据 ──
    ltl_map = {}  # delivery_no → LtlApproval
    for a in LtlApproval.query.all():
        ltl_map[a.delivery_no] = a

    # ── Step 5 (前置): 零担判定 ──
    # 先标记哪些交货单是零担（零担优先）
    ltl_delivery_nos = set(ltl_map.keys())

    # ── Step 1: 拼车分组 ──
    # 整车分组
    truck_groups = {}  # group_key → [DeliveryOrder]
    ltl_groups = {}    # ltl_vehicle_no → [DeliveryOrder]

    for order in orders:
        if order.delivery_no in ltl_delivery_nos:
            # 零担：归入零担车次
            approval = ltl_map[order.delivery_no]
            key = approval.ltl_vehicle_no
            if key not in ltl_groups:
                ltl_groups[key] = []
            ltl_groups[key].append(order)
        else:
            # 整车：按配置字段分组
            key_parts = []
            for field in truck_fields:
                val = getattr(order, _field_to_attr(field), '') or ''
                key_parts.append(str(val))
            key = '-'.join(key_parts)
            if key not in truck_groups:
                truck_groups[key] = []
            truck_groups[key].append(order)

    # ── 处理每个车次 ──
    all_results = []

    # 处理整车车次
    for vehicle_key, group_orders in truck_groups.items():
        results = _process_vehicle_group(
            group_orders, vehicle_key, coeff, global_tiers, False
        )
        all_results.extend(results)

    # 处理零担车次
    for ltl_vehicle_no, group_orders in ltl_groups.items():
        results = _process_vehicle_group(
            group_orders, ltl_vehicle_no, coeff, global_tiers, True
        )
        all_results.extend(results)

    return all_results


def _process_vehicle_group(orders, vehicle_key, coeff, global_tiers, is_ltl):
    """
    处理一个车次的完整计算流程（Step 2-10）。
    orders: 该车次包含的交货单列表
    vehicle_key: 车次标识
    is_ltl: 是否零担车次
    返回该车次所有交货单的试算结果列表。
    """
    if not orders:
        return []

    # ── Step 2: 车次汇总 ──
    total_weight = sum(o.total_weight for o in orders)
    total_volume = sum(o.total_volume for o in orders)
    vehicle_volume_weight = total_volume / coeff if coeff > 0 else 0

    # 各交货单体积重量
    order_volume_weights = {}
    for o in orders:
        order_volume_weights[o.id] = o.total_volume / coeff if coeff > 0 else 0

    # ── Step 3: 按方结算判定 ──
    is_volumetric = vehicle_volume_weight > total_weight

    # ── Step 4: 车次计费重量（保留4位小数，保证显示与计算一致） ──
    raw_vehicle_billing_weight = vehicle_volume_weight if is_volumetric else total_weight
    vehicle_billing_weight = round(raw_vehicle_billing_weight, 4)

    # ── Step 5: 零担标识 ──
    is_ltl_str = '是' if is_ltl else '否'

    # ── 取第一条交货单信息做费率匹配（同车次应一致） ──
    sample_order = orders[0]

    # ── Step 6: 费率匹配 ──
    contract = match_contract(sample_order.carrier_code, sample_order.post_date)
    rate = None
    exception_msg = None

    if contract:
        rate = match_rate(
            contract.id,
            sample_order.shipping_point,
            sample_order.transport_area,
            sample_order.cargo_type,
            sample_order.transport_mode,
        )
        if not rate:
            exception_msg = get_match_error(
                sample_order.carrier_code,
                sample_order.post_date,
                sample_order.shipping_point,
                sample_order.transport_area,
                sample_order.cargo_type,
                sample_order.transport_mode,
            )
    else:
        exception_msg = get_match_error(
            sample_order.carrier_code,
            sample_order.post_date,
            sample_order.shipping_point,
            sample_order.transport_area,
            sample_order.cargo_type,
            sample_order.transport_mode,
        )

    # ── Step 7: 坎级落档 ──
    tier_order = None       # 落档坎级序数
    tier_name = None        # 落档坎级名称
    tier_price = None       # 落档坎级单价
    next_tier_order = None  # 下一坎级序数
    next_tier_name = None   # 下一坎级名称
    next_tier_lower = None  # 下一坎级重量下限
    next_tier_price = None  # 下一坎级单价

    if rate and not exception_msg:
        rate_tier_count = rate.tier_count  # 当前线路的坎级数
        if is_ltl:
            # 零担：根据计费重量查找全局坎级区间，再与线路坎级数取小值
            matched_tier_order = None
            for t in global_tiers:
                if t.matches(vehicle_billing_weight):
                    matched_tier_order = t.tier_order
                    break
            if matched_tier_order is None:
                exception_msg = '超出坎级范围'
            else:
                # 落档坎级序数 = min(全局区间命中序数, 线路坎级数)
                tier_order = min(matched_tier_order, rate_tier_count)
                # 名称从全局表取
                for t in global_tiers:
                    if t.tier_order == tier_order:
                        tier_name = t.tier_name
                        break
                if tier_name is None:
                    tier_name = f'坎级{tier_order}'
                tier_price = _get_price_by_tier(rate, tier_order)
        else:
            # 整车：落档坎级序数 = 当前线路的坎级数
            if not rate_tier_count or rate_tier_count < 1:
                exception_msg = '线路无费率'
            else:
                tier_order = rate_tier_count
                tier_price = _get_price_by_tier(rate, tier_order)
                # 名称从全局表取
                for t in global_tiers:
                    if t.tier_order == tier_order:
                        tier_name = t.tier_name
                        break
                if tier_name is None:
                    tier_name = f'坎级{tier_order}'

        # 下一坎级信息
        if tier_order and tier_order < rate_tier_count:
            next_tier_order = tier_order + 1
            # 名称从全局表
            for t in global_tiers:
                if t.tier_order == next_tier_order:
                    next_tier_name = t.tier_name
                    next_tier_lower = t.lower_value
                    break
            if next_tier_name is None:
                next_tier_name = f'坎级{next_tier_order}'
                next_tier_lower = 0
            # 下一坎级单价：从费率取
            next_tier_price = _get_price_by_tier(rate, next_tier_order)

    # ── Step 8: 运费计算 ──
    estimated_freight = None     # 车次预估运费
    applicable_freight = None    # 车次适用运费
    next_min_freight = None      # 下一坎级最低运费

    if tier_price is not None and not exception_msg:
        # 用 Decimal 避免浮点精度问题
        estimated_freight = float(
            (Decimal(str(tier_price)) * Decimal(str(vehicle_billing_weight))).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        )

        if next_tier_price is None:
            # 没有下一坎级 → 适用运费 = 预估运费
            applicable_freight = estimated_freight
        else:
            next_min_freight = float(
                (Decimal(str(next_tier_price)) * Decimal(str(next_tier_lower))).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            ) if next_tier_lower else 0
            applicable_freight = min(estimated_freight, next_min_freight)
    else:
        if exception_msg:
            pass  # 已有异常
        elif tier_price is None:
            exception_msg = '落档无数据'

    # ── Step 9 & 10: 分摊 + 装卸费（按各交货单） ──
    results = []
    billing_unit_price = None
    if applicable_freight is not None and vehicle_billing_weight > 0:
        billing_unit_price = float(
            (Decimal(str(applicable_freight)) / Decimal(str(vehicle_billing_weight))).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        )

    for order in orders:
        row = _build_result_row(
            order=order,
            vehicle_key=vehicle_key,
            total_weight=total_weight,
            total_volume=total_volume,
            vehicle_volume_weight=vehicle_volume_weight,
            order_volume_weight=order_volume_weights[order.id],
            is_volumetric=is_volumetric,
            vehicle_billing_weight=vehicle_billing_weight,
            is_ltl_str=is_ltl_str,
            tier_order=tier_order,
            tier_name=tier_name,
            next_tier_order=next_tier_order,
            next_tier_name=next_tier_name,
            next_tier_lower=next_tier_lower,
            rate=rate,
            tier_price=tier_price,
            next_tier_price=next_tier_price,
            estimated_freight=estimated_freight,
            next_min_freight=next_min_freight,
            applicable_freight=applicable_freight,
            billing_unit_price=billing_unit_price,
            coeff=coeff,
            exception_msg=exception_msg,
        )
        results.append(row)

    return results


def _build_result_row(
    order, vehicle_key, total_weight, total_volume,
    vehicle_volume_weight, order_volume_weight,
    is_volumetric, vehicle_billing_weight, is_ltl_str,
    tier_order, tier_name,
    next_tier_order, next_tier_name, next_tier_lower,
    rate, tier_price, next_tier_price,
    estimated_freight, next_min_freight, applicable_freight,
    billing_unit_price, coeff, exception_msg,
):
    """构建一条交货单的51列结果"""
    row = {}

    # ── 交货单原始字段 (1-18) ──
    row['交货单号'] = order.delivery_no
    row['装运点'] = order.shipping_point
    row['装运点描述'] = order.shipping_point_desc
    row['运输区域'] = order.transport_area
    row['运输区域描述'] = order.transport_area_desc
    row['总重量（吨）'] = round(order.total_weight, 3)
    row['总体积（m³）'] = round(order.total_volume, 3)
    row['拼车单号'] = order.consolidated_no
    row['运单号'] = order.waybill_no
    row['发货过账日期'] = order.post_date
    row['车牌号'] = order.license_plate or ''
    row['销售组织'] = order.sales_org
    row['组织名称'] = order.org_name
    row['承运商名称'] = order.carrier_name
    row['承运商编码'] = order.carrier_code
    row['送达方名称'] = order.consignee_name
    row['送达方编码'] = order.consignee_code
    row['货物类型'] = order.cargo_type
    row['运输方式'] = order.transport_mode

    # ── 车次汇总字段 (19-26) ──
    row['零担车次'] = vehicle_key if is_ltl_str == '是' else ''
    row['所在车次'] = vehicle_key
    row['车次总重量（吨）'] = round(total_weight, 3)
    row['车次总体积（m³）'] = round(total_volume, 3)
    row['车次体积重量（吨）'] = round(vehicle_volume_weight, 3)
    row['交货单体积重量（吨）'] = round(order_volume_weight, 3)
    row['符合按方结算'] = '符合' if is_volumetric else '不符合'

    # 交货单计费重量
    order_billing_weight = order_volume_weight if is_volumetric else order.total_weight
    row['车次计费重量（吨）'] = vehicle_billing_weight

    # ── 坎级信息 (27-30) ──
    if exception_msg:
        row['落档坎级序数'] = exception_msg
        row['落档坎级（名称）'] = exception_msg
        row['是否零担'] = is_ltl_str
        row['下一坎级（序数）'] = exception_msg
        row['下一坎级（名称）'] = exception_msg
        row['下一坎级重量下限'] = exception_msg
    else:
        row['落档坎级序数'] = tier_order if tier_order else '--'
        row['落档坎级（名称）'] = tier_name if tier_name else '--'
        row['是否零担'] = is_ltl_str
        if next_tier_order is not None:
            row['下一坎级（序数）'] = next_tier_order
            row['下一坎级（名称）'] = next_tier_name if next_tier_name else '--'
            row['下一坎级重量下限'] = next_tier_lower if next_tier_lower is not None else '--'
        else:
            row['下一坎级（序数）'] = '--'
            row['下一坎级（名称）'] = '--'
            row['下一坎级重量下限'] = '--'

    # ── 费率信息 (31-39) ──
    if rate:
        row['线路'] = rate.route_code
        row['线路类型'] = rate.route_type
        row['坎级数'] = rate.tier_count
        row['坎级1单价'] = rate.price1
        row['坎级2单价'] = rate.price2 if rate.tier_count >= 2 else '--'
        row['坎级3单价'] = rate.price3 if rate.tier_count >= 3 else '--'
        row['坎级4单价'] = rate.price4 if rate.tier_count >= 4 else '--'
        row['末端装卸费'] = rate.terminal_fee
    else:
        for col in ['线路', '线路类型', '坎级数', '坎级1单价', '坎级2单价',
                     '坎级3单价', '坎级4单价', '末端装卸费']:
            row[col] = exception_msg if exception_msg else '--'

    # ── 运费计算结果 (40-48) ──
    if exception_msg:
        for col in EXCEPTION_FIELDS:
            row[col] = exception_msg
    else:
        row['落档坎级单价'] = tier_price if tier_price is not None else '--'
        if next_tier_order is not None and next_tier_price is not None:
            row['下一坎级单价'] = next_tier_price
        else:
            row['下一坎级单价'] = '--'
        row['车次预估运费'] = estimated_freight if estimated_freight is not None else '--'
        row['下一坎级最低运费'] = next_min_freight if next_min_freight is not None else '--'
        row['车次适用运费'] = applicable_freight if applicable_freight is not None else '--'

        # ── Step 9: 分摊 ──
        row['交货单运费单价'] = billing_unit_price if billing_unit_price is not None else '--'
        row['交货单计费重量'] = round(order_billing_weight, 3)

        if billing_unit_price is not None:
            # 用舍入后的重量计算，保证与显示一致
            rounded_weight = round(order_billing_weight, 3)
            freight_amount = float(
                Decimal(str(billing_unit_price)) * Decimal(str(rounded_weight))
            )
        else:
            freight_amount = '--'
        row['交货单运费结算金额'] = freight_amount

        # ── Step 10: 装卸费 ──
        if rate and rate.terminal_fee is not None:
            # 用舍入后的重量计算，保证与显示一致
            rounded_weight = round(order_billing_weight, 3)
            loading_fee = float(
                Decimal(str(rate.terminal_fee)) * Decimal(str(rounded_weight))
            )
        else:
            loading_fee = '--'
        row['交货单装卸费结算金额'] = loading_fee

        # ── 结算总金额（保留2位小数，四舍五入） ──
        # 加极小值抵消浮点误差（如 22.214999999... → 22.215000001... → 22.22）
        if isinstance(freight_amount, (int, float)) and isinstance(loading_fee, (int, float)):
            raw_sum = freight_amount + loading_fee
            total = Decimal(str(raw_sum + 1e-9)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            row['交货单结算总金额'] = float(total)
        else:
            row['交货单结算总金额'] = '--'

    return row


# ─────────────────────────────────────────
#  辅助函数
# ─────────────────────────────────────────
def _filter_orders(conditions: dict):
    """根据查询条件过滤交货单"""
    query = DeliveryOrder.query

    if conditions.get('delivery_no'):
        query = query.filter_by(delivery_no=conditions['delivery_no'].strip())
    if conditions.get('waybill_no'):
        query = query.filter_by(waybill_no=conditions['waybill_no'].strip())
    if conditions.get('consolidated_no'):
        query = query.filter_by(consolidated_no=conditions['consolidated_no'].strip())
    if conditions.get('post_date_start'):
        query = query.filter(DeliveryOrder.post_date >= conditions['post_date_start'].strip())
    if conditions.get('post_date_end'):
        query = query.filter(DeliveryOrder.post_date <= conditions['post_date_end'].strip())
    if conditions.get('carrier_name'):
        query = query.filter(DeliveryOrder.carrier_name.like(f'%{conditions["carrier_name"].strip()}%'))
    if conditions.get('carrier_code'):
        query = query.filter_by(carrier_code=conditions['carrier_code'].strip())
    if conditions.get('contract_code'):
        # 通过合同编码筛选：先找合同对应的承运商编码
        contract = Contract.query.filter_by(contract_code=conditions['contract_code'].strip()).first()
        if contract:
            query = query.filter_by(carrier_code=contract.carrier_code)
        else:
            return []  # 合同不存在，无结果

    return query.all()


def _field_to_attr(field_name: str) -> str:
    """将中文字段名映射为模型属性名"""
    mapping = {
        '交货单号': 'delivery_no',
        '装运点': 'shipping_point',
        '运输区域': 'transport_area',
        '拼车单号': 'consolidated_no',
        '运单号': 'waybill_no',
        '承运商编码': 'carrier_code',
        '承运商名称': 'carrier_name',
        '车牌号': 'license_plate',
        '货物类型': 'cargo_type',
        '运输方式': 'transport_mode',
    }
    return mapping.get(field_name, field_name)


def _get_nonzero_prices(rate: ContractRate):
    """
    获取费率中所有非零的坎级价格。
    返回 [(tier_order, price), ...]
    """
    prices = []
    for i, p in enumerate([rate.price1, rate.price2, rate.price3, rate.price4], 1):
        if p and p > 0:
            prices.append((i, p))
    return prices


def _get_price_by_tier(rate: ContractRate, tier_order: int):
    """根据坎级序号获取对应的单价"""
    price_map = {
        1: rate.price1,
        2: rate.price2,
        3: rate.price3,
        4: rate.price4,
    }
    val = price_map.get(tier_order)
    return val if val and val > 0 else None
