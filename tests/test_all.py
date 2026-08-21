"""
运费试算工具 - 自动化测试脚本
对照需求逐条验证核心功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.models import (
    db, DeliveryOrder, LtlApproval, Contract, ContractRate,
    TierInterval, AppConfig, VolumetricCoefficient
)
from app.engine.calculator import run_trial
from app.services.contract_status import check_contract_status

# 测试使用内存数据库，不污染真实数据
from app.config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

app = create_app()

passed = 0
failed = 0

def test(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f'  ✓ {name}')
    else:
        failed += 1
        print(f'  ✗ {name}  {detail}')


def setup_data():
    """初始化测试数据"""
    with app.app_context():
        # 清空数据
        DeliveryOrder.query.delete()
        LtlApproval.query.delete()
        Contract.query.delete()
        ContractRate.query.delete()
        VolumetricCoefficient.query.delete()
        db.session.commit()

        # 确保有生效的泡货系数
        if VolumetricCoefficient.query.filter_by(is_active=True).count() == 0:
            db.session.add(VolumetricCoefficient(coefficient=3.5, is_active=True))
        db.session.commit()

        # ── 交货单 ──
        orders = [
            # 整车：同拼车单号的两张单
            DeliveryOrder(
                delivery_no='D001', shipping_point='2010', shipping_point_desc='广州仓',
                transport_area='Z019000097', transport_area_desc='广东-南沙大润发',
                total_weight=3.0, total_volume=10.0,
                consolidated_no='PC001', waybill_no='W001',
                post_date='20250115', license_plate='粤A12345',
                sales_org='S01', org_name='华南分公司',
                carrier_name='顺丰速运', carrier_code='SF001',
                consignee_name='南沙大润发', consignee_code='C001',
                cargo_type='普货',
            ),
            DeliveryOrder(
                delivery_no='D002', shipping_point='2010', shipping_point_desc='广州仓',
                transport_area='Z019000097', transport_area_desc='广东-南沙大润发',
                total_weight=5.0, total_volume=8.0,
                consolidated_no='PC001', waybill_no='W002',
                post_date='20250115', license_plate='粤A12345',
                sales_org='S01', org_name='华南分公司',
                carrier_name='顺丰速运', carrier_code='SF001',
                consignee_name='南沙大润发', consignee_code='C001',
                cargo_type='普货',
            ),
            # 零担：有审批记录
            DeliveryOrder(
                delivery_no='D003', shipping_point='2010', shipping_point_desc='广州仓',
                transport_area='Z019000097', transport_area_desc='广东-南沙大润发',
                total_weight=2.0, total_volume=5.0,
                consolidated_no='PC002', waybill_no='W003',
                post_date='20250115', license_plate='',
                sales_org='S01', org_name='华南分公司',
                carrier_name='顺丰速运', carrier_code='SF001',
                consignee_name='南沙大润发', consignee_code='C001',
                cargo_type='普货',
            ),
            # 无匹配费率的交货单（不同货物类型）
            DeliveryOrder(
                delivery_no='D004', shipping_point='3010', shipping_point_desc='上海仓',
                transport_area='Z021000001', transport_area_desc='上海-浦东',
                total_weight=4.0, total_volume=3.0,
                consolidated_no='PC003', waybill_no='W004',
                post_date='20250115', license_plate='',
                sales_org='S02', org_name='华东分公司',
                carrier_name='中通物流', carrier_code='ZT001',
                consignee_name='浦东沃尔玛', consignee_code='C002',
                cargo_type='冷链',
            ),
        ]
        db.session.add_all(orders)

        # ── 零担审批 ──
        ltl = LtlApproval(
            ltl_type='支线', vehicle_seq='A001',
            ltl_vehicle_no='支线-A001',
            delivery_no='D003', approval_month='202501',
        )
        db.session.add(ltl)

        # ── 合同（有效期需覆盖测试日期2026-08-17）──
        contract = Contract(
            contract_code='CT-2025-001', contract_name='顺丰2025年合同',
            carrier_name='顺丰速运', carrier_code='SF001',
            start_date='20250101', end_date='20271231',
            status='生效',
        )
        db.session.add(contract)
        db.session.flush()  # 先获取ID

        # ── 费率（依赖合同ID）──
        # 广州仓 & 广东-南沙大润发，普货，3个坎级
        rate = ContractRate(
            contract_id=contract.id,
            route_code='2010&Z019000097',
            tier_count=3,
            shipping_point='2010', shipping_point_desc='广州仓',
            transport_area='Z019000097', transport_area_desc='广东-南沙大润发',
            province='广东', city='广州', district='南沙',
            mileage=47, route_type='KA', has_terminal='是',
            tax_rate=0.09,
            price1=84.3, price2=72.2, price3=60.2, price4=0,
            terminal_fee=46.9,
            cargo_type='普货',
        )
        db.session.add(rate)

        db.session.commit()
        return contract.id


def test_basic_config():
    """测试基础配置"""
    print('\n[1] 基础配置')
    with app.app_context():
        coeff = AppConfig.query.get('volumetric_coefficient')
        test('泡货系数默认值=3.5', coeff and coeff.value == '3.5')
        active_vc = VolumetricCoefficient.query.filter_by(is_active=True).first()
        test('泡货系数版本管理-存在生效版本', active_vc is not None and active_vc.coefficient == 3.5)

        truck_fields = AppConfig.query.get('truck_unique_fields')
        test('整车标识默认值=拼车单号', truck_fields and truck_fields.value == '拼车单号')

        tiers = TierInterval.query.order_by(TierInterval.tier_order).all()
        test(f'默认坎级区间={len(tiers)}个', len(tiers) >= 3, f'实际{len(tiers)}个')
        test('坎级1: ≥0 且 <8',
             tiers[0].lower_value == 0 and tiers[0].lower_inclusive and
             tiers[0].upper_value == 8 and not tiers[0].upper_inclusive)


def test_contract_status():
    """测试合同状态管理"""
    print('\n[2] 合同状态管理')
    with app.app_context():
        # 创建过期合同
        c_expired = Contract(
            contract_code='CT-EXPIRED', contract_name='已过期合同',
            carrier_name='测试', carrier_code='TEST',
            start_date='20240101', end_date='20240630',
            status='生效',
        )
        db.session.add(c_expired)

        # 创建草稿（已到生效日期，且未过期）
        c_draft = Contract(
            contract_code='CT-DRAFT', contract_name='草稿合同',
            carrier_name='测试', carrier_code='TEST',
            start_date='20250101', end_date='20271231',
            status='草稿',
        )
        db.session.add(c_draft)
        db.session.commit()

        changed = check_contract_status()
        test(f'启动检查更新{changed}个合同', changed >= 2, f'实际{changed}')

        c_expired = Contract.query.filter_by(contract_code='CT-EXPIRED').first()
        test('过期合同 → 失效', c_expired.status == '失效', f'实际{c_expired.status}')

        c_draft = Contract.query.filter_by(contract_code='CT-DRAFT').first()
        test('草稿合同(已到起始) → 生效', c_draft.status == '生效', f'实际{c_draft.status}')

        # 测试作废不可恢复
        c_void = Contract(
            contract_code='CT-VOID', contract_name='作废合同',
            carrier_name='测试', carrier_code='TEST',
            start_date='20250101', end_date='20271231',
            status='作废',
        )
        db.session.add(c_void)
        db.session.commit()
        test('作废合同存在', c_void.status == '作废')


def test_calculation_engine():
    """测试10步计算流程"""
    print('\n[3] 计算引擎 - 10步流程')
    with app.app_context():
        results = run_trial({})
        test(f'试算返回结果数={len(results)}', len(results) == 4, f'实际{len(results)}')

        # D001 & D002: 同拼车单号 PC001，整车
        r_d001 = next((r for r in results if r['交货单号'] == 'D001'), None)
        r_d002 = next((r for r in results if r['交货单号'] == 'D002'), None)
        r_d003 = next((r for r in results if r['交货单号'] == 'D003'), None)
        r_d004 = next((r for r in results if r['交货单号'] == 'D004'), None)

        test('D001存在', r_d001 is not None)
        test('D002存在', r_d002 is not None)

        if r_d001:
            # Step 1: 拼车分组 - D001和D002同属PC001
            test('Step1 D001所在车次=PC001', r_d001['所在车次'] == 'PC001',
                 f'实际{r_d001["所在车次"]}')

            # Step 2: 车次汇总
            test('Step2 车次总重量=8.0', r_d001['车次总重量（吨）'] == 8.0,
                 f'实际{r_d001["车次总重量（吨）"]}')
            test('Step2 车次总体积=18.0', r_d001['车次总体积（m³）'] == 18.0,
                 f'实际{r_d001["车次总体积（m³）"]}')
            # 体积重量 = 18.0 / 3.5 = 5.1429
            vol_weight = r_d001['车次体积重量（吨）']
            test(f'Step2 车次体积重量≈5.14', abs(vol_weight - 5.1429) < 0.01,
                 f'实际{vol_weight}')

            # Step 3: 按方判定 - 5.14 < 8.0 → 不符合
            test('Step3 不符合按方(5.14<8.0)', r_d001['符合按方结算'] == '不符合',
                 f'实际{r_d001["符合按方结算"]}')

            # Step 4: 计费重量 = 总重量 = 8.0
            test('Step4 车次计费重量=8.0', r_d001['车次计费重量（吨）'] == 8.0,
                 f'实际{r_d001["车次计费重量（吨）"]}')

            # Step 5: 零担判定
            test('Step5 D001非零担', r_d001['是否零担'] == '否',
                 f'实际{r_d001["是否零担"]}')

            # Step 6: 费率匹配 - 应匹配到
            test('Step6 线路匹配成功', r_d001['线路'] == '2010&Z019000097',
                 f'实际{r_d001["线路"]}')
            test('Step6 坎级数=3', r_d001['坎级数'] == 3)

            # Step 7: 坎级落档 - 整车：取非零价格最小值
            # P1=84.3, P2=72.2, P3=60.2 → min=60.2 → 坎级3
            test('Step7 整车落档坎级=3', r_d001['落档坎级序数'] == 3,
                 f'实际{r_d001["落档坎级序数"]}')

            # Step 8: 运费计算
            # 预估 = 60.2 × 8.0 = 481.60
            est = r_d001['车次预估运费']
            test(f'Step8 预估运费=481.6', est == 481.6, f'实际{est}')
            # 落档=3>1, 上一坎级=2, 上一坎级单价=P2=72.2, 上一坎级下限=8(新坎级)
            # 上一坎级最低 = 72.2 × 8 = 577.6
            prev_min = r_d001['上一坎级最低运费']
            test(f'Step8 上一坎级最低=577.6', prev_min == 577.6, f'实际{prev_min}')
            # 适用运费 = min(481.6, 577.6) = 481.6
            app_freight = r_d001['车次适用运费']
            test(f'Step8 适用运费=481.6', app_freight == 481.6, f'实际{app_freight}')

            # Step 9: 交货单分摊
            # 计费单价 = 481.6 / 8.0 = 60.2
            unit_price = r_d001.get('交货单计费单价')
            test(f'Step9 计费单价=60.2', unit_price == 60.2, f'实际{unit_price}')
            # D001计费重量 = 3.0（不符合按方 → 取总重量）
            billing_wt = r_d001.get('交货单计费重量')
            test(f'Step9 D001计费重量=3.0',
                 billing_wt == 3.0,
                 f'实际{billing_wt}')
            # D001运费结算 = 60.2 × 3.0 = 180.6
            freight_amt = r_d001.get('交货单运费结算金额')
            test(f'Step9 D001运费结算=180.6', freight_amt == 180.6,
                 f'实际{freight_amt}')

            # Step 10: 装卸费
            # 末端费用 = 46.9, 装卸费 = 46.9 × 3.0 = 140.7
            loading = r_d001.get('交货单装卸费结算金额')
            test(f'Step10 D001装卸费=140.7', loading == 140.7, f'实际{loading}')
            # 总金额 = 180.6 + 140.7 = 321.3
            total = r_d001.get('交货单结算总金额')
            test(f'Step10 D001结算总金额=321.3', total == 321.3, f'实际{total}')

        if r_d003:
            # D003: 零担（有审批记录）
            test('Step5 D003是零担', r_d003['是否零担'] == '是',
                 f'实际{r_d003["是否零担"]}')
            test('零担车次=支线-A001', r_d003['零担车次'] == '支线-A001',
                 f'实际{r_d003["零担车次"]}')
            # 零担：计费重量=2.0（不符合按方，2/3.5=0.571 < 2.0）
            test(f'D003车次计费重量=2.0',
                 r_d003['车次计费重量（吨）'] == 2.0,
                 f'实际{r_d003["车次计费重量（吨）"]}')
            # 零担坎级落档：2.0在坎级1(≥0且<8)内
            test('Step7 零担落档坎级=1', r_d003['落档坎级序数'] == 1,
                 f'实际{r_d003["落档坎级序数"]}')
            # 落档=1 → 上一坎级="--"
            test('落档=1时上一坎级=--', r_d003['上一坎级（序数）'] == '--',
                 f'实际{r_d003["上一坎级（序数）"]}')

        if r_d004:
            # D004: 无匹配费率
            test('异常:承运商无合同/线路无费率',
                 r_d004['落档坎级序数'] in ('承运商无合同', '线路无费率', '货物类型无费率'),
                 f'实际{r_d004["落档坎级序数"]}')
            test('异常:结算总金额为标记文字',
                 r_d004['交货单结算总金额'] in ('承运商无合同', '线路无费率', '货物类型无费率'),
                 f'实际{r_d004["交货单结算总金额"]}')


def test_result_columns():
    """测试结果列表51列"""
    print('\n[4] 结果列表字段')
    with app.app_context():
        results = run_trial({})
        if results:
            r = results[0]
            expected_cols = [
                '交货单号', '装运点', '装运点描述', '运输区域', '运输区域描述',
                '总重量（吨）', '总体积（m³）', '拼车单号', '运单号', '发货过账日期',
                '车牌号', '销售组织', '组织名称', '承运商名称', '承运商编码',
                '送达方名称', '送达方编码', '货物类型', '运输方式',
                '零担车次', '所在车次', '车次总重量（吨）', '车次总体积（m³）',
                '车次体积重量（吨）', '交货单体积重量（吨）', '符合按方结算',
                '车次计费重量（吨）', '落档坎级序数', '落档坎级（名称）',
                '是否零担', '上一坎级（序数）', '上一坎级（名称）',
                '上一坎级重量下限', '线路', '线路类型', '坎级数',
                '坎级1单价', '坎级2单价', '坎级3单价', '坎级4单价', '末端装卸费',
                '落档坎级单价', '上一坎级单价', '车次预估运费', '上一坎级最低运费',
                '车次适用运费', '交货单计费单价', '交货单计费重量',
                '交货单运费结算金额', '交货单装卸费结算金额', '交货单结算总金额',
            ]
            missing = [c for c in expected_cols if c not in r]
            extra = [c for c in r if c not in expected_cols]
            test(f'结果字段数={len(expected_cols)}', len(r) == len(expected_cols),
                 f'实际{len(r)}个字段')
            if missing:
                test(f'缺少字段', False, f'缺少: {missing}')
            else:
                test('所有必需字段存在', True)


def test_exception_handling():
    """测试异常处理"""
    print('\n[5] 异常处理')
    with app.app_context():
        # 添加过期合同的交货单
        c2 = Contract(
            contract_code='CT-OVERDUE', contract_name='过期合同',
            carrier_name='圆通快递', carrier_code='YT001',
            start_date='20240101', end_date='20240630',
            status='失效',
        )
        db.session.add(c2)
        d5 = DeliveryOrder(
            delivery_no='D005', shipping_point='2010', shipping_point_desc='广州仓',
            transport_area='Z019000097', transport_area_desc='广东-南沙大润发',
            total_weight=5.0, total_volume=3.0,
            consolidated_no='PC005', waybill_no='W005',
            post_date='20240801', license_plate='',
            sales_org='S01', org_name='华南分公司',
            carrier_name='圆通快递', carrier_code='YT001',
            consignee_name='测试', consignee_code='C099',
            cargo_type='普货',
        )
        db.session.add(d5)
        db.session.commit()

        results = run_trial({'delivery_no': 'D005'})
        if results:
            r = results[0]
            # D005: 承运商YT001只有过期合同，且post_date=20240801不在有效期内
            test('过期合同 → 异常标记',
                 str(r.get('落档坎级序数', '')) in ('合同已过期', '承运商无合同'),
                 f'实际{r.get("落档坎级序数")}')
            # 非运费字段正常显示
            test('异常时交货单号正常显示', r['交货单号'] == 'D005')
            test('异常时承运商名称正常显示', r['承运商名称'] == '圆通快递')


def test_transport_mode():
    """测试运输方式匹配逻辑"""
    print('\n[6] 运输方式匹配')
    from app.engine.matcher import match_rate
    with app.app_context():
        # 获取已有合同
        contract = Contract.query.filter_by(carrier_code='YT001').first()
        if not contract:
            test('需要 YT001 合同', False, '测试数据缺失')
            return

        # 新增两条同线路不同运输方式的费率
        sp, ta = '2010', 'Z019000097'
        rate_qy = ContractRate(
            contract_id=contract.id, route_code=f'{sp}&{ta}', tier_count=4,
            shipping_point=sp, shipping_point_desc='广州仓',
            transport_area=ta, transport_area_desc='广东-南沙大润发',
            province='广东', city='广州', district='南沙',
            mileage=10, route_type='KA', has_terminal='否',
            tax_rate=0.09, price1=90, price2=80, price3=70, price4=60,
            terminal_fee=0, cargo_type='普货', transport_mode='汽运',
        )
        rate_gen = ContractRate(
            contract_id=contract.id, route_code=f'{sp}&{ta}', tier_count=4,
            shipping_point=sp, shipping_point_desc='广州仓',
            transport_area=ta, transport_area_desc='广东-南沙大润发',
            province='广东', city='广州', district='南沙',
            mileage=10, route_type='KA', has_terminal='否',
            tax_rate=0.09, price1=80, price2=70, price3=60, price4=50,
            terminal_fee=0, cargo_type='普货', transport_mode='',
        )
        db.session.add(rate_qy)
        db.session.add(rate_gen)
        db.session.commit()

        # 测试1: 精确匹配汽运
        r1 = match_rate(contract.id, sp, ta, '普货', '汽运')
        test('精确匹配汽运', r1 and r1.price1 == 90,
             f'实际 price1={r1.price1 if r1 else None}')

        # 测试2: 铁路无精确匹配，回退到通用
        r2 = match_rate(contract.id, sp, ta, '普货', '铁路')
        test('铁路回退通用', r2 and r2.price1 == 80,
             f'实际 price1={r2.price1 if r2 else None}')

        # 测试3: 空运输方式匹配通用
        r3 = match_rate(contract.id, sp, ta, '普货', '')
        test('空值匹配通用', r3 and r3.price1 == 80,
             f'实际 price1={r3.price1 if r3 else None}')

        # 清理
        db.session.delete(rate_qy)
        db.session.delete(rate_gen)
        db.session.commit()


# ── 运行测试 ──
print('=' * 60)
print('  运费试算工具 - 自动化测试')
print('=' * 60)

with app.app_context():
    setup_data()

test_basic_config()
test_contract_status()
test_calculation_engine()
test_result_columns()
test_exception_handling()
test_transport_mode()

print('\n' + '=' * 60)
print(f'  测试结果: {passed} 通过, {failed} 失败')
print('=' * 60)

sys.exit(0 if failed == 0 else 1)
