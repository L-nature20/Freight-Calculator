"""测试交货单导入是否为全有或全无模式"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.models import db, DeliveryOrder
from app.services.excel_io import import_delivery_orders
from openpyxl import Workbook
import io

# 创建应用并使用内存数据库
from app.config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
app = create_app()

with app.app_context():
    # 初始化数据库
    db.create_all()

    # 创建测试Excel文件：5行数据，第3行有错误（缺少必填字段）
    wb = Workbook()
    ws = wb.active

    # 表头
    headers = ['交货单号', '装运点', '装运点描述', '运输区域', '运输区域描述',
               '总重量（吨）', '总体积（m³）', '拼车单号', '运单号', '发货过账日期',
               '车牌号', '销售组织', '组织名称', '承运商名称', '承运商编码',
               '送达方名称', '送达方编码', '货物类型', '运输方式']
    ws.append(headers)

    # 第1行：正常数据
    ws.append(['D001', 'SP01', '装运点1', 'TA01', '区域1', 10.5, 5.2, '', '', '20240101',
               '车牌1', 'SO01', '组织1', '承运商1', 'C001', '送达方1', 'CD001', '普货', '汽运'])

    # 第2行：正常数据
    ws.append(['D002', 'SP02', '装运点2', 'TA02', '区域2', 8.0, 4.0, '', '', '20240102',
               '车牌2', 'SO02', '组织2', '承运商2', 'C002', '送达方2', 'CD002', '普货', '汽运'])

    # 第3行：错误数据（缺少装运点）
    ws.append(['D003', '', '装运点3', 'TA03', '区域3', 12.0, 6.0, '', '', '20240103',
               '车牌3', 'SO03', '组织3', '承运商3', 'C003', '送达方3', 'CD003', '普货', '汽运'])

    # 第4行：正常数据
    ws.append(['D004', 'SP04', '装运点4', 'TA04', '区域4', 15.0, 7.5, '', '', '20240104',
               '车牌4', 'SO04', '组织4', '承运商4', 'C004', '送达方4', 'CD004', '普货', '汽运'])

    # 第5行：正常数据
    ws.append(['D005', 'SP05', '装运点5', 'TA05', '区域5', 9.0, 4.5, '', '', '20240105',
               '车牌5', 'SO05', '组织5', '承运商5', 'C005', '送达方5', 'CD005', '普货', '汽运'])

    # 保存为BytesIO
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    print("测试前数据库记录数:", DeliveryOrder.query.count())

    # 执行导入
    success_count, errors = import_delivery_orders(buf, on_duplicate='skip')

    print("\n导入结果:")
    print(f"  成功导入: {success_count} 条")
    print(f"  错误数量: {len(errors)} 条")
    if errors:
        print("  错误详情:")
        for err in errors:
            print(f"    - {err}")

    print("\n测试后数据库记录数:", DeliveryOrder.query.count())

    # 验证
    if success_count == 0 and DeliveryOrder.query.count() == 0:
        print("\n✓ 符合预期：全有或全无模式生效，有错误则整批拒绝")
    elif success_count > 0:
        print(f"\n✗ 不符合预期：部分导入了 {success_count} 条，但应该全部拒绝")
    else:
        print("\n? 情况不明")
