"""交货单管理路由"""
import io
from flask import Blueprint, request, jsonify, send_file
from ..models import db, DeliveryOrder
from ..services.excel_io import (
    import_delivery_orders, create_delivery_template,
    _normalize_date_str
)

bp = Blueprint('delivery', __name__)


@bp.route('', methods=['GET'])
def list_delivery_orders():
    """查询交货单（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    select_all = request.args.get('select_all', '', type=str)
    args = request.args

    query = DeliveryOrder.query

    # 精确匹配
    for field, key in [('delivery_no', 'delivery_no'), ('consolidated_no', 'consolidated_no'),
                       ('waybill_no', 'waybill_no'), ('carrier_code', 'carrier_code'),
                       ('cargo_type', 'cargo_type'), ('transport_mode', 'transport_mode')]:
        val = args.get(key, '', type=str).strip()
        if val:
            query = query.filter_by(**{field: val})

    # 模糊匹配
    carrier = args.get('carrier_name', '', type=str).strip()
    if carrier:
        query = query.filter(DeliveryOrder.carrier_name.like(f'%{carrier}%'))

    # 日期范围
    date_start = args.get('post_date_start', '', type=str).strip()
    if date_start:
        query = query.filter(DeliveryOrder.post_date >= date_start)
    date_end = args.get('post_date_end', '', type=str).strip()
    if date_end:
        query = query.filter(DeliveryOrder.post_date <= date_end)

    query = query.order_by(DeliveryOrder.id.desc())

    if select_all == '1':
        all_ids = [r.id for r in query.with_entities(DeliveryOrder.id).all()]
        return jsonify({'all_ids': all_ids})

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'data': [o.to_dict() for o in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@bp.route('/<int:id>', methods=['GET'])
def get_delivery_order(id):
    """按ID查询单条交货单"""
    order = DeliveryOrder.query.get_or_404(id)
    return jsonify(order.to_dict())


@bp.route('', methods=['POST'])
def create_delivery_order():
    """新增交货单"""
    d = request.json
    if not d.get('交货单号'):
        return jsonify({'error': '交货单号不能为空'}), 400
    if not str(d.get('运输方式', '') or '').strip():
        return jsonify({'error': '运输方式不能为空'}), 400

    if DeliveryOrder.query.filter_by(delivery_no=d['交货单号']).first():
        return jsonify({'error': f'交货单号"{d["交货单号"]}"已存在'}), 409

    order = DeliveryOrder()
    _fill(order, d)
    db.session.add(order)
    db.session.commit()
    return jsonify(order.to_dict()), 201


@bp.route('/<int:id>', methods=['PUT'])
def update_delivery_order(id):
    """编辑交货单"""
    order = DeliveryOrder.query.get_or_404(id)
    d = request.json
    # 检查交货单号唯一
    new_no = d.get('交货单号', order.delivery_no)
    if new_no != order.delivery_no:
        if DeliveryOrder.query.filter_by(delivery_no=new_no).first():
            return jsonify({'error': f'交货单号"{new_no}"已存在'}), 409
    _fill(order, d)
    db.session.commit()
    return jsonify(order.to_dict())


@bp.route('/<int:id>', methods=['DELETE'])
def delete_delivery_order(id):
    """删除交货单"""
    order = DeliveryOrder.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({'message': '删除成功'})


@bp.route('/batch-delete', methods=['POST'])
def batch_delete():
    """批量删除交货单"""
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'error': '未选择记录'}), 400
    count = DeliveryOrder.query.filter(DeliveryOrder.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'message': f'已删除 {count} 条', 'count': count})


@bp.route('/clear', methods=['POST'])
def clear_delivery_orders():
    """清空所有交货单"""
    DeliveryOrder.query.delete()
    db.session.commit()
    return jsonify({'message': '已清空所有交货单'})


@bp.route('/import', methods=['POST'])
def import_data():
    """Excel导入交货单"""
    if 'file' not in request.files:
        return jsonify({'error': '请上传文件'}), 400
    file = request.files['file']
    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': '仅支持 .xlsx 格式'}), 400

    on_duplicate = request.form.get('on_duplicate', 'skip')
    success, errors = import_delivery_orders(file.stream, on_duplicate)
    return jsonify({
        'success': success,
        'errors': errors,
        'message': f'成功导入 {success} 条' + (f'，{len(errors)} 条失败' if errors else ''),
    })


@bp.route('/template', methods=['GET'])
def download_template():
    """下载导入模板"""
    buf = create_delivery_template()
    return send_file(buf, as_attachment=True,
                     download_name='交货单导入模板.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def _fill(order, d):
    order.delivery_no = str(d.get('交货单号', '')).strip()
    order.shipping_point = str(d.get('装运点', '')).strip()
    order.shipping_point_desc = str(d.get('装运点描述', '')).strip()
    order.transport_area = str(d.get('运输区域', '')).strip()
    order.transport_area_desc = str(d.get('运输区域描述', '')).strip()
    order.total_weight = float(d.get('总重量（吨）', 0) or 0)
    order.total_volume = float(d.get('总体积（m³）', 0) or 0)
    order.consolidated_no = str(d.get('拼车单号', '')).strip()
    order.waybill_no = str(d.get('运单号', '')).strip()
    order.post_date = _normalize_date_str(d.get('发货过账日期', ''))
    order.license_plate = str(d.get('车牌号', '') or '').strip()
    order.sales_org = str(d.get('销售组织', '')).strip()
    order.org_name = str(d.get('组织名称', '')).strip()
    order.carrier_name = str(d.get('承运商名称', '')).strip()
    order.carrier_code = str(d.get('承运商编码', '')).strip()
    order.consignee_name = str(d.get('送达方名称', '')).strip()
    order.consignee_code = str(d.get('送达方编码', '')).strip()
    order.cargo_type = str(d.get('货物类型', '普货') or '普货').strip()
    order.transport_mode = str(d.get('运输方式', '') or '').strip()
