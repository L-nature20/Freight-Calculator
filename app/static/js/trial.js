/**
 * 运费试算
 */
const Trial = {
    page: 1,
    perPage: 50,
    lastResults: [],
    lastTotal: 0,
    lastColumns: [],
    allColumns: [],
    // 列自定义状态
    pinnedLeft: [],
    visible: [],
    pinnedRight: [],
    hidden: [],
    // 排序状态
    sortColumn: null,
    sortAsc: true,

    // ── 默认列顺序 ──
    defaultColumns: [
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
    ],

    // ── 初始化列状态 ──
    _initColumns() {
        // 默认：交货单号固定左侧，其余全部显示
        this.pinnedLeft = ['交货单号'];
        this.visible = this.defaultColumns.slice(1);
        this.pinnedRight = [];
        this.hidden = [];
    },

    clearConditions() {
        ['trial-delivery-no','trial-waybill-no','trial-consolidated-no',
         'trial-carrier-name','trial-carrier-code','trial-contract-code'].forEach(id => {
            document.getElementById(id).value = '';
        });
        // 默认日期为最近一个月
        this._setDefaultDates();
        document.getElementById('trial-result-status').value = '全部';
    },

    _setDefaultDates() {
        const now = new Date();
        const end = new Date(now.getFullYear(), now.getMonth() + 1, 0); // 本月末
        const start = new Date(end);
        start.setMonth(start.getMonth() - 1);
        start.setDate(1);
        const fmt = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        document.getElementById('trial-date-start').value = fmt(start);
        document.getElementById('trial-date-end').value = fmt(end);
    },

    _getConditions() {
        return {
            delivery_no: document.getElementById('trial-delivery-no').value.trim(),
            waybill_no: document.getElementById('trial-waybill-no').value.trim(),
            consolidated_no: document.getElementById('trial-consolidated-no').value.trim(),
            post_date_start: parseDateToYYYYMMDD(document.getElementById('trial-date-start').value),
            post_date_end: parseDateToYYYYMMDD(document.getElementById('trial-date-end').value),
            carrier_name: document.getElementById('trial-carrier-name').value.trim(),
            carrier_code: document.getElementById('trial-carrier-code').value.trim(),
            contract_code: document.getElementById('trial-contract-code').value.trim(),
            result_status: document.getElementById('trial-result-status').value,
        };
    },

    async calculate() {
        const btn = document.getElementById('trial-calc-btn');
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 试算中…'; }
        try {
            const conditions = this._getConditions();
            // 首次试算获取全量结果，后续翻页从缓存读取
            const data = await API.post('/api/trial/calculate', conditions);
            this.lastResults = data.data || [];
            this.lastTotal = data.total || 0;
            this.allColumns = data.columns || [];
            this.lastColumns = data.columns || [];
            this.page = 1;
            if (!this.visible.length) this._initColumns();
            this.renderTable(this.lastResults, this.lastTotal);
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-play"></i> 试算'; }
        }
    },

    // ── 获取当前显示列 ──
    _getDisplayColumns() {
        return [...this.pinnedLeft, ...this.visible, ...this.pinnedRight];
    },

    renderTable(rows, total) {
        const thead = document.getElementById('trial-thead');
        const tbody = document.getElementById('trial-tbody');
        document.getElementById('trial-total').textContent = `共 ${total} 条`;

        if (!this.allColumns.length) {
            thead.innerHTML = '';
            tbody.innerHTML = '<tr><td class="text-center text-muted py-4">请输入查询条件后点击试算</td></tr>';
            return;
        }

        const displayCols = this._getDisplayColumns();
        const exceptionKeywords = ['承运商无合同','合同已过期','线路无费率','货物类型无费率','超出坎级范围','落档无数据'];

        // 排序后的数据
        let sortedRows = rows;
        if (this.sortColumn) {
            sortedRows = [...rows].sort((a, b) => {
                let va = a[this.sortColumn], vb = b[this.sortColumn];
                if (va === null || va === undefined) va = '';
                if (vb === null || vb === undefined) vb = '';
                if (typeof va === 'number' && typeof vb === 'number') {
                    return this.sortAsc ? va - vb : vb - va;
                }
                va = String(va); vb = String(vb);
                return this.sortAsc ? va.localeCompare(vb, 'zh-CN') : vb.localeCompare(va, 'zh-CN');
            });
        }

        // 前端分页：只渲染当前页
        const start = (this.page - 1) * this.perPage;
        const pageRows = sortedRows.slice(start, start + this.perPage);

        // 渲染表头（可点击排序）
        thead.innerHTML = displayCols.map(c => {
            const sortIcon = c === this.sortColumn ? (this.sortAsc ? ' ▲' : ' ▼') : '';
            const shortName = c.length > 8 ? c.slice(0, 8) + '…' : c;
            return `<th title="${c}" onclick="Trial._sortBy('${c.replace(/'/g, "\\'")}')" style="cursor:pointer">${shortName}${sortIcon}</th>`;
        }).join('');

        tbody.innerHTML = pageRows.map((r, i) => {
            const cells = displayCols.map(c => {
                const val = r[c];
                if (val !== null && val !== undefined && exceptionKeywords.includes(String(val))) {
                    return `<td class="exception-text" title="${c}: ${val}">${val}</td>`;
                }
                return `<td>${val ?? ''}</td>`;
            }).join('');
            return `<tr>${cells}</tr>`;
        }).join('');

        const pages = Math.ceil(total / this.perPage) || 1;
        document.getElementById('trial-page-info').textContent = `第 ${this.page}/${pages} 页`;
    },

    _sortBy(col) {
        if (this.sortColumn === col) {
            this.sortAsc = !this.sortAsc;
        } else {
            this.sortColumn = col;
            this.sortAsc = true;
        }
        this.renderTable(this.lastResults, this.lastTotal);
    },

    // ── 列自定义弹窗 ──
    showColumnModal() {
        if (!this.allColumns.length) {
            showMsg('请先执行试算以加载列', 'warning');
            return;
        }
        // 同步状态
        this._renderColumnLists();
        new bootstrap.Modal(document.getElementById('columnModal')).show();
    },

    _renderColumnLists() {
        // 左侧固定
        document.getElementById('pin-left-list').innerHTML = this.pinnedLeft.map(c =>
            this._colChip(c, 'left')).join('') || '<span class="text-muted small">拖放列到此处</span>';

        // 显示列
        document.getElementById('visible-list').innerHTML = this.visible.map(c =>
            this._colChip(c, 'visible')).join('') || '<span class="text-muted small">拖放列到此处</span>';

        // 右侧固定
        document.getElementById('pin-right-list').innerHTML = this.pinnedRight.map(c =>
            this._colChip(c, 'right')).join('') || '<span class="text-muted small">拖放列到此处</span>';

        // 隐藏列
        document.getElementById('hidden-list').innerHTML = this.hidden.map(c =>
            this._colChip(c, 'hidden')).join('') || '<span class="text-muted small">无隐藏列</span>';
    },

    _colChip(col, zone) {
        const short = col.length > 12 ? col.slice(0, 12) + '…' : col;
        const buttons = {
            left: `<button class="btn btn-sm btn-outline-danger py-0 px-1" title="隐藏" onclick="Trial._moveCol('${col}','left','hidden')">×</button>
                   <button class="btn btn-sm btn-outline-secondary py-0 px-1" title="移到显示" onclick="Trial._moveCol('${col}','left','visible')">→</button>
                   <button class="btn btn-sm btn-outline-secondary py-0 px-1" title="移到右侧" onclick="Trial._moveCol('${col}','left','right')">⇥</button>`,
            visible: `<button class="btn btn-sm btn-outline-secondary py-0 px-1" title="移到左侧" onclick="Trial._moveCol('${col}','visible','left')">⇤</button>
                      <button class="btn btn-sm btn-outline-primary py-0 px-1" title="上移" onclick="Trial._moveUp('${col}')">▲</button>
                      <button class="btn btn-sm btn-outline-primary py-0 px-1" title="下移" onclick="Trial._moveDown('${col}')">▼</button>
                      <button class="btn btn-sm btn-outline-secondary py-0 px-1" title="移到右侧" onclick="Trial._moveCol('${col}','visible','right')">⇥</button>
                      <button class="btn btn-sm btn-outline-danger py-0 px-1" title="隐藏" onclick="Trial._moveCol('${col}','visible','hidden')">×</button>`,
            right: `<button class="btn btn-sm btn-outline-secondary py-0 px-1" title="移到显示" onclick="Trial._moveCol('${col}','right','visible')">←</button>
                    <button class="btn btn-sm btn-outline-danger py-0 px-1" title="隐藏" onclick="Trial._moveCol('${col}','right','hidden')">×</button>`,
            hidden: `<button class="btn btn-sm btn-outline-success py-0 px-1" title="显示" onclick="Trial._moveCol('${col}','hidden','visible')">＋</button>`,
        };
        return `<div class="d-flex justify-content-between align-items-center border rounded p-1 mb-1 bg-white">
            <span class="small" title="${col}">${short}</span>
            <div>${buttons[zone]}</div>
        </div>`;
    },

    _moveCol(col, from, to) {
        const lists = { left: this.pinnedLeft, visible: this.visible, right: this.pinnedRight, hidden: this.hidden };
        const fromList = lists[from];
        const toList = lists[to];
        const idx = fromList.indexOf(col);
        if (idx >= 0) fromList.splice(idx, 1);
        if (!toList.includes(col)) toList.push(col);
        this._renderColumnLists();
    },

    _moveUp(col) {
        const idx = this.visible.indexOf(col);
        if (idx > 0) {
            [this.visible[idx - 1], this.visible[idx]] = [this.visible[idx], this.visible[idx - 1]];
            this._renderColumnLists();
        }
    },

    _moveDown(col) {
        const idx = this.visible.indexOf(col);
        if (idx < this.visible.length - 1) {
            [this.visible[idx], this.visible[idx + 1]] = [this.visible[idx + 1], this.visible[idx]];
            this._renderColumnLists();
        }
    },

    resetColumns() {
        this._initColumns();
        this._renderColumnLists();
    },

    applyColumns() {
        // 确保所有列都被分配
        const allAssigned = [...this.pinnedLeft, ...this.visible, ...this.pinnedRight, ...this.hidden];
        const allCols = this.allColumns.length ? this.allColumns : this.defaultColumns;
        const missing = allCols.filter(c => !allAssigned.includes(c));
        if (missing.length) this.hidden.push(...missing);
        // 重新渲染
        bootstrap.Modal.getInstance(document.getElementById('columnModal')).hide();
        this.renderTable(this.lastResults, this.lastTotal);
        showMsg('列配置已应用', 'success');
    },

    // ── 导出 ──
    async exportResults() {
        const btn = document.getElementById('trial-export-btn');
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 导出中…'; }
        try {
            const conditions = this._getConditions();
            const resp = await fetch('/api/trial/export', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(conditions),
            });
            if (!resp.ok) { showMsg('导出失败', 'danger'); return; }
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '运费试算结果.xlsx';
            a.click();
            URL.revokeObjectURL(url);
            showMsg('导出成功', 'success');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-download"></i> 导出'; }
        }
    },

    prevPage() { if (this.page > 1) { this.page--; this.loadPage(); } },
    nextPage() {
        const pages = Math.ceil(this.lastTotal / this.perPage) || 1;
        if (this.page < pages) { this.page++; this.loadPage(); }
    },

    // 翻页 / 切换每页条数：从缓存渲染，不重新请求后端
    loadPage() {
        if (!this.lastResults.length && !this.lastTotal) return;
        this.renderTable(this.lastResults, this.lastTotal);
    },

    // ─ Tooltip：单元格内容溢出时悬停显示完整内容 ──
    _tooltipEl: null,
    _tooltipTimer: null,
    _initTooltip() {
        this._tooltipEl = document.getElementById('trial-cell-tooltip');
        if (!this._tooltipEl) return;
        const tbody = document.getElementById('trial-tbody');
        if (!tbody) return;
        tbody.addEventListener('mouseover', (e) => {
            const td = e.target.closest('td');
            if (!td) return;
            if (td.scrollWidth <= td.clientWidth) return; // 未溢出
            this._tooltipEl.textContent = td.textContent;
            this._tooltipEl.style.display = 'block';
            const rect = td.getBoundingClientRect();
            this._tooltipEl.style.left = rect.left + 'px';
            this._tooltipEl.style.top = (rect.bottom + 4) + 'px';
            this._tooltipTimer = setTimeout(() => {
                if (this._tooltipEl) this._tooltipEl.style.display = 'none';
            }, 5000);
        });
        tbody.addEventListener('mouseout', (e) => {
            if (this._tooltipEl) this._tooltipEl.style.display = 'none';
            clearTimeout(this._tooltipTimer);
        });
    }
};

// 页面加载后初始化试算 tooltip 和默认日期
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => Trial._initTooltip(), 100);
    Trial._setDefaultDates();
});