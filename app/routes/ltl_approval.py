"""零担审批管理路由"""
from flask import Blueprint, request, jsonify, send_file
from ..models import db, LtlApproval, DeliveryOrder
from ..services.excel_io import import_ltl_approvals, create_ltl_template

bp = Blueprint('ltl_approval', __name__)


@bp.route('', methods=['GET'])
def list_approvals():
    """查询零担审批（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    select_all = request.args.get('select_all', '', type=str)
    args = request.args

    query = LtlApproval.query

    # 精确匹配
    for key in ['delivery_no', 'ltl_vehicle_no', 'ltl_type', 'approval_month']:
        val = args.get(key, '', type=str).strip()
        if val:
            query = query.filter_by(**{key: val})

    query = query.order_by(LtlApproval.id.desc())

    if select_all == '1':
        all_ids = [r.id for r in query.with_entities(LtlApproval.id).all()]
        return jsonify({'all_ids': all_ids})

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'data': [a.to_dict() for a in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@bp.route('', methods=['POST'])
def create_approval():
    """新增零担审批"""
    d = request.json
    delivery_no = str(d.get('交货单号', '')).strip()
    ltl_type = str(d.get('零担类型', '')).strip()
    vehicle_seq = str(d.get('车序号', '')).strip()
    approval_month = str(d.get('零担审批月份', '')).strip()

    if not delivery_no or not ltl_type or not vehicle_seq or not approval_month:
        return jsonify({'error': '交货单号、零担类型、车序号、审批月份不能为空'}), 400
    if ltl_type not in ('支线', '干线'):
        return jsonify({'error': '零担类型必须为支线/干线'}), 400
    if LtlApproval.query.filter_by(delivery_no=delivery_no).first():
        return jsonify({'error': f'交货单号"{delivery_no}"已有审批记录'}), 409
    # 验证交货单存在
    if not DeliveryOrder.query.filter_by(delivery_no=delivery_no).first():
        return jsonify({'warning': f'交货单号"{delivery_no}"不存在于交货单数据中'}), 201

    ltl_vehicle_no = f'{ltl_type}-{vehicle_seq}'
    rec = LtlApproval(
        ltl_type=ltl_type,
        vehicle_seq=vehicle_seq,
        ltl_vehicle_no=ltl_vehicle_no,
        delivery_no=delivery_no,
        approval_month=approval_month,
    )
    db.session.add(rec)
    db.session.commit()
    return jsonify(rec.to_dict()), 201


@bp.route('/<int:id>', methods=['GET'])
def get_approval(id):
    """按ID查询单条零担审批"""
    rec = LtlApproval.query.get_or_404(id)
    return jsonify(rec.to_dict())


@bp.route('/<int:id>', methods=['PUT'])
def update_approval(id):
    """编辑零担审批"""
    rec = LtlApproval.query.get_or_404(id)
    d = request.json
    ltl_type = str(d.get('零担类型', '')).strip()
    vehicle_seq = str(d.get('车序号', '')).strip()
    delivery_no = str(d.get('交货单号', '')).strip()
    approval_month = str(d.get('零担审批月份', '')).strip()

    if not delivery_no or not ltl_type or not vehicle_seq or not approval_month:
        return jsonify({'error': '交货单号、零担类型、车序号、审批月份不能为空'}), 400
    if ltl_type not in ('支线', '干线'):
        return jsonify({'error': '零担类型必须为支线/干线'}), 400
    # 检查交货单号唯一（排除自身）
    dup = LtlApproval.query.filter(
        LtlApproval.delivery_no == delivery_no,
        LtlApproval.id != id
    ).first()
    if dup:
        return jsonify({'error': f'交货单号"{delivery_no}"已有审批记录'}), 409

    rec.ltl_type = ltl_type
    rec.vehicle_seq = vehicle_seq
    rec.ltl_vehicle_no = f'{ltl_type}-{vehicle_seq}'
    rec.delivery_no = delivery_no
    rec.approval_month = approval_month
    db.session.commit()
    return jsonify(rec.to_dict())


@bp.route('/<int:id>', methods=['DELETE'])
def delete_approval(id):
    """删除零担审批"""
    rec = LtlApproval.query.get_or_404(id)
    db.session.delete(rec)
    db.session.commit()
    return jsonify({'message': '删除成功'})


@bp.route('/batch-delete', methods=['POST'])
def batch_delete():
    """批量删除零担审批"""
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'error': '未选择记录'}), 400
    count = LtlApproval.query.filter(LtlApproval.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'message': f'已删除 {count} 条', 'count': count})


@bp.route('/import', methods=['POST'])
def import_data():
    """Excel导入零担审批"""
    if 'file' not in request.files:
        return jsonify({'error': '请上传文件'}), 400
    file = request.files['file']
    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': '仅支持 .xlsx 格式'}), 400

    on_duplicate = request.form.get('on_duplicate', 'skip')
    success, errors = import_ltl_approvals(file.stream, on_duplicate)
    return jsonify({
        'success': success,
        'errors': errors,
        'message': f'成功导入 {success} 条' + (f'，{len(errors)} 条失败' if errors else ''),
    })


@bp.route('/template', methods=['GET'])
def download_template():
    """下载导入模板"""
    buf = create_ltl_template()
    return send_file(buf, as_attachment=True,
                     download_name='零担审批导入模板.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
