"""异常标记文字定义"""

# 试算异常场景 → 运费字段显示标记
EXCEPTION_MESSAGES = {
    'no_carrier_contract': '承运商无合同',
    'contract_expired': '合同已过期',
    'no_route_rate': '线路无费率',
    'no_cargo_type_rate': '货物类型无费率',
    'tier_out_of_range': '超出坎级范围',
}

# 需要显示异常标记的运费相关字段
EXCEPTION_DISPLAY_FIELDS = [
    '落档坎级单价',
    '下一坎级单价',
    '车次预估运费',
    '下一坎级最低运费',
    '车次适用运费',
    '交货单运费单价',
    '交货单运费结算金额',
    '交货单装卸费结算金额',
    '交货单结算总金额',
]
