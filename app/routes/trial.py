"""试算路由"""
import io
from flask import Blueprint, request, jsonify, send_file
from ..engine.calculator import run_trial, RESULT_COLUMNS
from ..services.excel_io import export_trial_results

bp = Blueprint('trial', __name__)


@bp.route('/calculate', methods=['POST'])
def calculate():
    """执行试算（返回全量结果，前端自行分页）"""
    conditions = request.json or {}
    results = run_trial(conditions)

    # 应用结果状态过滤
    status_filter = conditions.get('result_status', '全部')
    if status_filter == '已匹配':
        results = [r for r in results if r.get('落档坎级单价') not in
                   ('承运商无合同', '合同已过期', '线路无费率', '货物类型无费率', '超出坎级范围', '落档无数据')]
    elif status_filter == '无法匹配':
        results = [r for r in results if r.get('落档坎级单价') in
                   ('承运商无合同', '合同已过期', '线路无费率', '货物类型无费率', '超出坎级范围', '落档无数据')]

    return jsonify({
        'data': results,
        'total': len(results),
        'columns': RESULT_COLUMNS,
    })


@bp.route('/export', methods=['POST'])
def export_results():
    """导出试算结果为Excel（始终全量重算）"""
    conditions = request.json or {}
    results = run_trial(conditions)

    # 应用结果状态过滤
    status_filter = conditions.get('result_status', '全部')
    if status_filter == '已匹配':
        results = [r for r in results if r.get('落档坎级单价') not in
                   ('承运商无合同', '合同已过期', '线路无费率', '货物类型无费率', '超出坎级范围', '落档无数据')]
    elif status_filter == '无法匹配':
        results = [r for r in results if r.get('落档坎级单价') in
                   ('承运商无合同', '合同已过期', '线路无费率', '货物类型无费率', '超出坎级范围', '落档无数据')]

    buf = export_trial_results(results, RESULT_COLUMNS)
    return send_file(
        buf, as_attachment=True,
        download_name='运费试算结果.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
