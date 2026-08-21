/**
 * 交货单管理
 */
const Delivery = {
    columns: [
        '交货单号', '装运点', '装运点描述', '运输区域', '运输区域描述',
        '总重量（吨）', '总体积（m³）', '拼车单号', '运单号', '发货过账日期',
        '车牌号', '销售组织', '组织名称', '承运商名称', '承运商编码',
        '送达方名称', '送达方编码', '货物类型', '运输方式'
    ],
    page: 1,
    perPage: 50,
    editingId: null,
    _pendingImportFile: null,
    selectedIds: new Set(),
    searchParams: {},

    _getSearchParams() {
        const p = {};
        const v = id => document.getElementById(id)?.value.trim();
        if (v('delivery-search-no')) p.delivery_no = v('delivery-search-no');
        if (v('delivery-search-consolidated')) p.consolidated_no = v('delivery-search-consolidated');
        if (v('delivery-search-waybill')) p.waybill_no = v('delivery-search-waybill');
        if (v('delivery-search-date-start')) p.post_date_start = v('delivery-search-date-start').replace(/-/g, '');
        if (v('delivery-search-date-end')) p.post_date_end = v('delivery-search-date-end').replace(/-/g, '');
        if (v('delivery-search-carrier')) p.carrier_name = v('delivery-search-carrier');
        if (v('delivery-search-carrier-code')) p.carrier_code = v('delivery-search-carrier-code');
        if (v('delivery-search-cargo')) p.cargo_type = v('delivery-search-cargo');
        if (v('delivery-search-transport-mode')) p.transport_mode = v('delivery-search-transport-mode');
        return p;
    },

    async loadPage() {
        const params = new URLSearchParams({
            page: this.page,
            per_page: this.perPage,
            ...this.searchParams
        });
        const data = await API.get(`/api/delivery?${params.toString()}`);
        this.renderTable(data.data);
        this.renderPagination(data);
        this._syncSelectAll();
    },

    search() {
        this.searchParams = this._getSearchParams();
        this.page = 1;
        this.selectedIds.clear();
        this.loadPage();
    },

    clearSearch() {
        ['delivery-search-no','delivery-search-consolidated','delivery-search-waybill',
         'delivery-search-date-start','delivery-search-date-end','delivery-search-carrier',
         'delivery-search-carrier-code','delivery-search-cargo','delivery-search-transport-mode'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        this.searchParams = {};
        this.page = 1;
        this.selectedIds.clear();
        this.loadPage();
    },

    renderTable(rows) {
        const thead = document.getElementById('delivery-thead');
        const tbody = document.getElementById('delivery-tbody');
        thead.innerHTML = '<th style="width:30px"></th>' + this.columns.map(c => `<th>${c}</th>`).join('') + '<th>操作</th>';
        tbody.innerHTML = rows.map((r, i) => `<tr>
            <td><input type="checkbox" class="row-checkbox" data-id="${r.id}" ${this.selectedIds.has(r.id)?'checked':''} onchange="Delivery.toggleSelect(${r.id}, this.checked)"></td>
            ${this.columns.map(c => {
                if (c.includes('日期')) return `<td>${formatDate(r[c])}</td>`;
                return `<td>${r[c] ?? ''}</td>`;
            }).join('')}
            <td>
                <button class="btn btn-outline-primary btn-xs me-1" onclick="Delivery.showEditModal(${r.id})" title="编辑"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-outline-danger btn-xs" onclick="Delivery.delete(${r.id})" title="删除"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('') || '<tr><td colspan="' + (this.columns.length + 2) + '" class="text-center text-muted py-3">暂无数据</td></tr>';
    },

    toggleSelect(id, checked) {
        if (checked) this.selectedIds.add(id); else this.selectedIds.delete(id);
        this._updateSelectionUI();
    },

    async toggleAll(sourceCheckbox) {
        const checked = sourceCheckbox.checked;
        if (checked) {
            const params = new URLSearchParams({ select_all: '1', ...this.searchParams });
            const data = await API.get(`/api/delivery?${params.toString()}`);
            (data.all_ids || []).forEach(id => this.selectedIds.add(id));
            document.querySelectorAll('#delivery-tbody .row-checkbox').forEach(cb => cb.checked = true);
            this._updateSelectionUI();
        } else {
            this.selectedIds.clear();
            document.querySelectorAll('#delivery-tbody .row-checkbox').forEach(cb => cb.checked = false);
            this._updateSelectionUI();
        }
    },

    _syncSelectAll() {
        const cb = document.querySelector('#delivery-toolbar input[type=checkbox]');
        const rowCbs = document.querySelectorAll('#delivery-tbody .row-checkbox');
        const allChecked = rowCbs.length > 0 && [...rowCbs].every(c => this.selectedIds.has(parseInt(c.dataset.id)));
        if (cb) cb.checked = allChecked;
        rowCbs.forEach(c => { c.checked = this.selectedIds.has(parseInt(c.dataset.id)); });
        this._updateSelectionUI();
    },

    _updateSelectionUI() {
        const el = document.getElementById('delivery-selected-count');
        if (el) el.textContent = `已选 ${this.selectedIds.size} 项`;
    },

    async batchDelete() {
        if (!this.selectedIds.size) { showMsg('请先勾选要删除的记录', 'warning'); return; }
        if (!confirm(`确定删除选中的 ${this.selectedIds.size} 条交货单？`)) return;
        const btn = document.getElementById('delivery-batch-delete-btn');
        const origHTML = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 删除中...'; }
        try {
            const resp = await API.post('/api/delivery/batch-delete', { ids: [...this.selectedIds] });
            showMsg(resp.message || `已删除`, 'success');
            this.selectedIds.clear();
            this.loadPage();
        } catch(e) {
            showMsg('删除失败：' + e.message, 'danger');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = origHTML; }
        }
    },

    renderPagination(data) {
        document.getElementById('delivery-page-info').textContent =
            `共 ${data.total} 条，第 ${data.page}/${data.pages || 1} 页`;
    },

    prevPage() { if (this.page > 1) { this.page--; this.loadPage(); } },
    nextPage() { this.page++; this.loadPage(); },

    showAddModal() {
        this.editingId = null;
        document.getElementById('delivery-modal-title').textContent = '新增交货单';
        this._renderForm({});
        new bootstrap.Modal(document.getElementById('deliveryModal')).show();
    },

    async showEditModal(id) {
        this.editingId = id;
        document.getElementById('delivery-modal-title').textContent = '编辑交货单';
        const row = await API.get(`/api/delivery/${id}`);
        if (row && !row.error) this._renderForm(row);
        new bootstrap.Modal(document.getElementById('deliveryModal')).show();
    },

    _renderForm(data) {
        const form = document.getElementById('delivery-form');
        const fields = this.columns.map(col => {
            const val = data[col] ?? '';
            const type = col.includes('重量') || col.includes('体积') ? 'number' : 'text';
            const step = col.includes('重量') || col.includes('体积') ? '0.001' : '';
            const req = ['交货单号','装运点','运输区域','总重量（吨）','总体积（m³）','发货过账日期','承运商编码','运输方式'].includes(col) ? 'required' : '';
            return `<div class="mb-2"><label class="form-label">${col}${req?' *':''}</label>
                <input type="${type}" class="form-control form-control-sm" data-field="${col}" value="${val}" ${step?`step="${step}"`:''} ${req}></div>`;
        }).join('');
        form.innerHTML = `<div class="row">${fields}</div>`;
    },

    async save() {
        const inputs = document.querySelectorAll('#delivery-form input[data-field]');
        const d = {};
        inputs.forEach(inp => {
            let v = inp.value.trim();
            if (inp.type === 'number') v = v ? parseFloat(v) : null;
            d[inp.dataset.field] = v;
        });
        if (!d['交货单号']) { showMsg('交货单号不能为空', 'danger'); return; }

        if (this.editingId) {
            await API.put(`/api/delivery/${this.editingId}`, d);
            showMsg('编辑成功', 'success');
        } else {
            const resp = await API.post('/api/delivery', d);
            if (resp.error) { showMsg(resp.error, 'danger'); return; }
            showMsg('新增成功', 'success');
        }
        bootstrap.Modal.getInstance(document.getElementById('deliveryModal')).hide();
        this.loadPage();
    },

    async delete(id) {
        if (!confirm('确定删除该交货单？')) return;
        await API.del(`/api/delivery/${id}`);
        showMsg('删除成功', 'success');
        this.selectedIds.delete(id);
        this.loadPage();
    },

    // ── 导入（含重复处理弹窗）──
    importFile(input) {
        if (!input.files[0]) return;
        this._pendingImportFile = input;
        document.getElementById('duplicateModalTitle').textContent = '重复交货单处理';
        document.getElementById('duplicateModalDesc').textContent = '导入文件中存在已有的交货单号，请选择处理方式：';
        window._dupConfirmCallback = () => this.confirmImport();
        new bootstrap.Modal(document.getElementById('duplicateModal')).show();
    },

    async confirmImport() {
        const input = this._pendingImportFile;
        if (!input || !input.files[0]) return;
        const mode = document.querySelector('input[name="dup-mode"]:checked').value;
        const spinner = document.getElementById('dupImportSpinner');
        const btn = document.getElementById('duplicateModalConfirm');
        spinner.classList.remove('d-none');
        btn.disabled = true;
        try {
            const fd = new FormData();
            fd.append('file', input.files[0]);
            fd.append('on_duplicate', mode);
            const resp = await API.upload('/api/delivery/import', fd);
            bootstrap.Modal.getInstance(document.getElementById('duplicateModal')).hide();
            showImportResult(resp);
            input.value = '';
            this._pendingImportFile = null;
            this.selectedIds.clear();
            this.loadPage();
        } catch(e) {
            showMsg('导入失败：' + e.message, 'danger');
        } finally {
            spinner.classList.add('d-none');
            btn.disabled = false;
        }
    },
};
