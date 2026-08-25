"""合同管理路由"""
import io
from flask import Blueprint, request, jsonify, send_file
from ..models import db, Contract, ContractRate
from ..services.excel_io import (
    import_contracts, import_rates,
    create_contract_template, create_rate_template
)
from ..services.contract_status import check_contract_status

bp = Blueprint('contract', __name__)


# ─────────────────────────────────────────
#  合同列表
# ─────────────────────────────────────────
@bp.route('', methods=['GET'])
def list_contracts():
    """查询合同列表（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '', type=str)
    select_all = request.args.get('select_all', '', type=str)

    query = Contract.query
    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                Contract.contract_code.like(like),
                Contract.contract_name.like(like),
                Contract.carrier_name.like(like),
                Contract.carrier_code.like(like),
            )
        )

    query = query.order_by(Contract.id.desc())

    if select_all == '1':
        all_ids = [r.id for r in query.with_entities(Contract.id).all()]
        return jsonify({'all_ids': all_ids})

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'data': [c.to_dict() for c in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@bp.route('/<int:id>', methods=['GET'])
def get_contract(id):
    """按ID查询单个合同"""
    c = Contract.query.get_or_404(id)
    return jsonify(c.to_dict())


@bp.route('', methods=['POST'])
def create_contract():
    """新增合同"""
    d = request.json
    code = str(d.get('合同编码', '')).strip()
    if not code:
        return jsonify({'error': '合同编码不能为空'}), 400
    if Contract.query.filter_by(contract_code=code).first():
        return jsonify({'error': f'合同编码"{code}"已存在'}), 409

    c = Contract(
        contract_code=code,
        contract_name=str(d.get('合同名称', '')).strip(),
        carrier_name=str(d.get('承运商名称', '')).strip(),
        carrier_code=str(d.get('承运商编码', '')).strip(),
        start_date=str(d.get('合同有效期起始', '')).strip(),
        end_date=str(d.get('合同有效期截止', '')).strip(),
        status='草稿',
        remark=d.get('备注', ''),
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@bp.route('/<int:id>', methods=['PUT'])
def update_contract(id):
    """编辑合同"""
    c = Contract.query.get_or_404(id)
    d = request.json
    c.contract_name = str(d.get('合同名称', c.contract_name)).strip()
    c.carrier_name = str(d.get('承运商名称', c.carrier_name)).strip()
    c.carrier_code = str(d.get('承运商编码', c.carrier_code)).strip()
    c.start_date = str(d.get('合同有效期起始', c.start_date)).strip()
    c.end_date = str(d.get('合同有效期截止', c.end_date)).strip()
    c.remark = d.get('备注', c.remark)
    db.session.commit()
    return jsonify(c.to_dict())


@bp.route('/batch-delete', methods=['POST'])
def batch_delete_contracts():
    """批量删除合同"""
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'error': '未选择记录'}), 400
    count = Contract.query.filter(Contract.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'message': f'已删除 {count} 个', 'count': count})


@bp.route('/<int:id>', methods=['DELETE'])
def delete_contract(id):
    """删除合同"""
    c = Contract.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'message': '删除成功'})


# ─────────────────────────────────────────
#  合同状态管理
# ─────────────────────────────────────────
@bp.route('/<int:id>/activate', methods=['POST'])
def activate_contract(id):
    """置为生效"""
    c = Contract.query.get_or_404(id)
    if c.status == '作废':
        return jsonify({'error': '已作废合同不可再置为生效'}), 400
    c.status = '生效'
    db.session.commit()
    return jsonify(c.to_dict())


@bp.route('/<int:id>/invalidate', methods=['POST'])
def invalidate_contract(id):
    """置为失效"""
    c = Contract.query.get_or_404(id)
    if c.status == '作废':
        return jsonify({'error': '已作废合同不可操作'}), 400
    c.status = '失效'
    db.session.commit()
    return jsonify(c.to_dict())


@bp.route('/<int:id>/void', methods=['POST'])
def void_contract(id):
    """置为作废"""
    c = Contract.query.get_or_404(id)
    c.status = '作废'
    db.session.commit()
    return jsonify(c.to_dict())


# ─────────────────────────────────────────
#  合同费率
# ─────────────────────────────────────────
@bp.route('/<int:id>/rates', methods=['GET'])
def list_rates(id):
    """查询合同费率（分页）"""
    contract = Contract.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '', type=str)
    select_all = request.args.get('select_all', '', type=str)
    query = ContractRate.query.filter_by(contract_id=id)
    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                ContractRate.route_code.like(like),
                ContractRate.shipping_point_desc.like(like),
                ContractRate.transport_area_desc.like(like),
            )
        )
    query = query.order_by(ContractRate.id)

    if select_all == '1':
        all_ids = [r.id for r in query.with_entities(ContractRate.id).all()]
        return jsonify({
            'contract': contract.to_dict(),
            'all_ids': all_ids,
        })

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'contract': contract.to_dict(),
        'rates': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/<int:id>/rates', methods=['POST'])
def add_rate(id):
    """新增单条费率"""
    contract = Contract.query.get_or_404(id)
    d = request.json

    sp = str(d.get('装运点', '')).strip()
    ta = str(d.get('运输区域', '')).strip()
    route_code = f'{sp}&{ta}'

    prices = [
        float(d.get('含增值税运输价格1', 0) or 0),
        float(d.get('含增值税运输价格2', 0) or 0),
        float(d.get('含增值税运输价格3', 0) or 0),
        float(d.get('含增值税运输价格4', 0) or 0),
    ]
    # 坎级数
    tier_count = 0
    for p in prices:
        if p > 0:
            tier_count += 1
        else:
            break

    terminal_fee = float(d.get('含增值税末端费用', 0) or 0)
    has_terminal = '是' if terminal_fee > 0 else '否'
    cargo_type = str(d.get('货物类型', '') or '').strip() or '普货'
    transport_mode = str(d.get('运输方式', '') or '').strip()
    if not transport_mode:
        return jsonify({'error': '运输方式不能为空'}), 400

    rate = ContractRate(
        contract_id=id,
        route_code=route_code,
        tier_count=tier_count,
        shipping_point=sp,
        shipping_point_desc=str(d.get('装运点描述', '')).strip(),
        transport_area=ta,
        transport_area_desc=str(d.get('运输区域描述', '')).strip(),
        province=str(d.get('省/直辖市', '')).strip(),
        city=str(d.get('地级市', '')).strip(),
        district=str(d.get('县/区', '')).strip(),
        mileage=float(d.get('里程(KM)', 0) or 0),
        route_type=str(d.get('线路类型', '')).strip(),
        has_terminal=has_terminal,
        tax_rate=float(d.get('增值税税率', 0) or 0),
        price1=prices[0],
        price2=prices[1],
        price3=prices[2],
        price4=prices[3],
        terminal_fee=terminal_fee,
        cargo_type=cargo_type,
        transport_mode=transport_mode,
    )
    db.session.add(rate)
    db.session.commit()
    return jsonify(rate.to_dict()), 201


@bp.route('/rate-batch-delete', methods=['POST'])
def batch_delete_rates():
    """批量删除费率"""
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'error': '未选择记录'}), 400
    count = ContractRate.query.filter(ContractRate.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'message': f'已删除 {count} 条', 'count': count})


@bp.route('/rate/<int:rate_id>', methods=['DELETE'])
def delete_rate(rate_id):
    """删除单条费率"""
    rate = ContractRate.query.get_or_404(rate_id)
    db.session.delete(rate)
    db.session.commit()
    return jsonify({'message': '删除成功'})


@bp.route('/<int:id>/rates/import', methods=['POST'])
def import_rates_data(id):
    """导入合同费率"""
    if 'file' not in request.files:
        return jsonify({'error': '请上传文件'}), 400
    file = request.files['file']
    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': '仅支持 .xlsx 格式'}), 400

    success, errors = import_rates(id, file.stream)
    return jsonify({
        'success': success,
        'errors': errors,
        'message': f'成功导入 {success} 条费率' + (f'，{len(errors)} 条失败' if errors else ''),
    })


# ─────────────────────────────────────────
#  合同导入/导出
# ─────────────────────────────────────────
@bp.route('/import', methods=['POST'])
def import_contracts_data():
    """导入合同列表"""
    if 'file' not in request.files:
        return jsonify({'error': '请上传文件'}), 400
    file = request.files['file']
    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': '仅支持 .xlsx 格式'}), 400

    success, errors = import_contracts(file.stream)
    # 导入成功后立即触发状态规则，使符合条件的合同自动变为"生效"
    if success:
        check_contract_status()
    return jsonify({
        'success': success,
        'errors': errors,
        'message': f'成功导入 {success} 条' + (f'，{len(errors)} 条失败' if errors else ''),
    })


@bp.route('/template', methods=['GET'])
def download_template():
    """下载合同导入模板"""
    buf = create_contract_template()
    return send_file(buf, as_attachment=True,
                     download_name='合同导入模板.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@bp.route('/rate-template', methods=['GET'])
def download_rate_template():
    """下载费率导入模板"""
    buf = create_rate_template()
    return send_file(buf, as_attachment=True,
                     download_name='费率导入模板.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@bp.route('/all-rates', methods=['GET'])
def list_all_rates():
    """费率明细：查询所有合同费率（全局视图）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    select_all = request.args.get('select_all', '', type=str)
    args = request.args

    query = db.session.query(ContractRate, Contract).join(
        Contract, ContractRate.contract_id == Contract.id
    )

    # 精确匹配
    for key, table, field in [
        ('contract_code', Contract, 'contract_code'),
        ('shipping_point', ContractRate, 'shipping_point'),
        ('transport_area', ContractRate, 'transport_area'),
        ('cargo_type', ContractRate, 'cargo_type'),
        ('route_type', ContractRate, 'route_type'),
        ('transport_mode', ContractRate, 'transport_mode'),
    ]:
        val = args.get(key, '', type=str).strip()
        if val:
            query = query.filter(getattr(table, field) == val)

    # 模糊匹配
    carrier = args.get('carrier_name', '', type=str).strip()
    if carrier:
        query = query.filter(Contract.carrier_name.like(f'%{carrier}%'))

    query = query.order_by(ContractRate.id.desc())

    if select_all == '1':
        all_ids = [r.id for r in query.with_entities(ContractRate.id).all()]
        return jsonify({'all_ids': all_ids})

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    result = []
    for rate, contract in pagination.items:
        item = rate.to_dict()
        item['合同编码'] = contract.contract_code
        item['合同名称'] = contract.contract_name
        item['合同有效期起始'] = contract.start_date
        item['合同有效期截止'] = contract.end_date
        item['承运商名称'] = contract.carrier_name
        item['承运商编码'] = contract.carrier_code
        result.append(item)

    return jsonify({
        'data': result,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@bp.route('/status-summary', methods=['GET'])
def status_summary():
    """合同状态统计"""
    counts = {}
    for status in ['草稿', '生效', '失效', '作废']:
        counts[status] = Contract.query.filter_by(status=status).count()
    counts['合计'] = sum(counts.values())
    return jsonify(counts)
