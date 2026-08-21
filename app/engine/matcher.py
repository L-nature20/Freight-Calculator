"""合同/费率匹配逻辑"""
from ..models import Contract, ContractRate


def match_contract(carrier_code, post_date):
    """
    匹配有效合同：
    - 承运商编码匹配
    - 发货过账日期在合同有效期内
    - 合同状态=生效
    - 多份合同时取有效期起始最晚的
    返回 Contract 或 None
    """
    contracts = Contract.query.filter(
        Contract.carrier_code == carrier_code,
        Contract.status == '生效',
        Contract.start_date <= post_date,
        Contract.end_date >= post_date,
    ).order_by(Contract.start_date.desc()).all()

    return contracts[0] if contracts else None


def match_rate(contract_id, shipping_point, transport_area, cargo_type, transport_mode=''):
    """
    匹配费率：
    - 线路代码 = 装运点 & 运输区域
    - 货物类型匹配
    - 运输方式精确匹配优先，回退到通用（空值）费率
    返回 ContractRate 或 None
    """
    route_code = f'{shipping_point}&{transport_area}'
    # 1. 精确匹配运输方式（仅当 transport_mode 非空时尝试）
    if transport_mode:
        rate = ContractRate.query.filter_by(
            contract_id=contract_id,
            route_code=route_code,
            cargo_type=cargo_type,
            transport_mode=transport_mode,
        ).first()
        if rate:
            return rate
    # 2. 回退匹配 transport_mode=''（通用，兼容存量数据）
    return ContractRate.query.filter_by(
        contract_id=contract_id,
        route_code=route_code,
        cargo_type=cargo_type,
        transport_mode='',
    ).first()


def get_match_error(carrier_code, post_date, shipping_point, transport_area, cargo_type, transport_mode=''):
    """
    诊断匹配失败原因，返回错误标记文字。
    """
    # 检查承运商是否有合同
    has_any_contract = Contract.query.filter_by(carrier_code=carrier_code).first()
    if not has_any_contract:
        return '承运商无合同'

    # 检查日期是否在合同有效期内
    has_valid_date = Contract.query.filter(
        Contract.carrier_code == carrier_code,
        Contract.start_date <= post_date,
        Contract.end_date >= post_date,
    ).first()
    if not has_valid_date:
        return '合同已过期'

    # 检查生效合同中有无匹配线路
    active_contracts = Contract.query.filter(
        Contract.carrier_code == carrier_code,
        Contract.status == '生效',
        Contract.start_date <= post_date,
        Contract.end_date >= post_date,
    ).all()

    route_code = f'{shipping_point}&{transport_area}'
    for c in active_contracts:
        has_route = ContractRate.query.filter_by(
            contract_id=c.id,
            route_code=route_code,
        ).first()
        if has_route:
            # 线路存在，检查货物类型
            has_cargo = ContractRate.query.filter_by(
                contract_id=c.id,
                route_code=route_code,
                cargo_type=cargo_type,
            ).first()
            if not has_cargo:
                return '货物类型无费率'
            # 货物类型匹配，检查运输方式
            if transport_mode:
                has_tm = ContractRate.query.filter_by(
                    contract_id=c.id,
                    route_code=route_code,
                    cargo_type=cargo_type,
                    transport_mode=transport_mode,
                ).first()
                if not has_tm:
                    # 检查是否有通用费率
                    has_fallback = ContractRate.query.filter_by(
                        contract_id=c.id,
                        route_code=route_code,
                        cargo_type=cargo_type,
                        transport_mode='',
                    ).first()
                    if not has_fallback:
                        return '运输方式无费率'
            return None  # 匹配成功

    return '线路无费率'
