/**
 * 零担审批管理
 */
const Ltl = {
    columns: ['零担车次', '零担类型', '车序号', '交货单号', '零担审批月份'],
    page: 1,
    perPage: 50,
    editingId: null,
    selectedIds: new Set(),
    searchParams: {},

    _getSearchParams() {
        const p = {};
        const v = id => document.getElementById(id)?.value.trim();
        if (v('ltl-search-delivery-no')) p.delivery_no = v('ltl-search-delivery-no');
        if (v('ltl-search-vehicle-no')) p.ltl_vehicle_no = v('ltl-search-vehicle-no');
        if (v('ltl-search-type')) p.ltl_type = v('ltl-search-type');
        if (v('ltl-search-month')) p.approval_month = v('ltl-search-month').replace(/-/g, '');
        return p;
    },

    async loadPage() {
        const params = new URLSearchParams({
            page: this.page,
            per_page: this.perPage,
            ...this.searchParams
        });
        const data = await API.get(`/api/ltl-approval?${params.toString()}`);
        this.renderTable(data.data);
        document.getElementById('ltl-page-info').textContent =
            `共 ${data.total} 条，第 ${data.page}/${data.pages || 1} 页`;
        this._syncSelectAll();
    },

    search() {
        this.searchParams = this._getSearchParams();
        this.page = 1;
        this.selectedIds.clear();
        this.loadPage();
    },

    clearSearch() {
        ['ltl-search-delivery-no','ltl-search-vehicle-no','ltl-search-type','ltl-search-month']
            .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
        this.searchParams = {};
        this.page = 1;
        this.selectedIds.clear();
        this.loadPage();
    },

    renderTable(rows) {
        const thead = document.getElementById('ltl-thead');
        const tbody = document.getElementById('ltl-tbody');
        thead.innerHTML = '<th style="width:30px"></th>' + this.columns.map(c => `<th>${c}</th>`).join('') + '<th>操作</th>';
        tbody.innerHTML = rows.map((r, i) => `<tr>
            <td><input type="checkbox" class="row-checkbox" data-id="${r.id}" ${this.selectedIds.has(r.id)?'checked':''} onchange="Ltl.toggleSelect(${r.id}, this.checked)"></td>
            ${this.columns.map(c => `<td>${r[c] ?? ''}</td>`).join('')}
            <td>
                <button class="btn btn-outline-primary btn-xs me-1" onclick="Ltl.showEditModal(${r.id})" title="编辑"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-outline-danger btn-xs" onclick="Ltl.delete(${r.id})" title="删除"><i class="bi bi-trash"></i></button>
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
            const data = await API.get(`/api/ltl-approval?${params.toString()}`);
            (data.all_ids || []).forEach(id => this.selectedIds.add(id));
            document.querySelectorAll('#ltl-tbody .row-checkbox').forEach(cb => cb.checked = true);
            this._updateSelectionUI();
        } else {
            this.selectedIds.clear();
            document.querySelectorAll('#ltl-tbody .row-checkbox').forEach(cb => cb.checked = false);
            this._updateSelectionUI();
        }
    },

    _syncSelectAll() {
        const cb = document.querySelector('#ltl-toolbar input[type=checkbox]');
        const rowCbs = document.querySelectorAll('#ltl-tbody .row-checkbox');
        const allChecked = rowCbs.length > 0 && [...rowCbs].every(c => this.selectedIds.has(parseInt(c.dataset.id)));
        if (cb) cb.checked = allChecked;
        rowCbs.forEach(c => { c.checked = this.selectedIds.has(parseInt(c.dataset.id)); });
        this._updateSelectionUI();
    },

    _updateSelectionUI() {
        const el = document.getElementById('ltl-selected-count');
        if (el) el.textContent = `已选 ${this.selectedIds.size} 项`;
    },

    async batchDelete() {
        if (!this.selectedIds.size) { showMsg('请先勾选要删除的记录', 'warning'); return; }
        if (!confirm(`确定删除选中的 ${this.selectedIds.size} 条零担审批？`)) return;
        const btn = document.getElementById('ltl-batch-delete-btn');
        const origHTML = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 删除中...'; }
        try {
            const resp = await API.post('/api/ltl-approval/batch-delete', { ids: [...this.selectedIds] });
            showMsg(resp.message || `已删除`, 'success');
            this.selectedIds.clear();
            this.loadPage();
        } catch(e) {
            showMsg('删除失败：' + e.message, 'danger');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = origHTML; }
        }
    },

    showAddModal() {
        this.editingId = null;
        document.getElementById('ltl-modal-title').textContent = '新增零担审批';
        document.getElementById('ltl-type').value = '支线';
        document.getElementById('ltl-vehicle-seq').value = '';
        document.getElementById('ltl-delivery-no').value = '';
        document.getElementById('ltl-month').value = '';
        new bootstrap.Modal(document.getElementById('ltlModal')).show();
    },

    async showEditModal(id) {
        this.editingId = id;
        document.getElementById('ltl-modal-title').textContent = '编辑零担审批';
        const row = await API.get(`/api/ltl-approval/${id}`);
        if (row && !row.error) {
            document.getElementById('ltl-type').value = row['零担类型'];
            document.getElementById('ltl-vehicle-seq').value = row['车序号'];
            document.getElementById('ltl-delivery-no').value = row['交货单号'];
            document.getElementById('ltl-month').value = row['零担审批月份'];
        }
        new bootstrap.Modal(document.getElementById('ltlModal')).show();
    },

    async save() {
        const d = {
            '零担类型': document.getElementById('ltl-type').value,
            '车序号': document.getElementById('ltl-vehicle-seq').value.trim(),
            '交货单号': document.getElementById('ltl-delivery-no').value.trim(),
            '零担审批月份': document.getElementById('ltl-month').value.trim(),
        };
        let resp;
        if (this.editingId) {
            resp = await API.put(`/api/ltl-approval/${this.editingId}`, d);
        } else {
            resp = await API.post('/api/ltl-approval', d);
        }
        if (resp.error) { showMsg(resp.error, 'danger'); return; }
        if (resp.warning) showMsg(resp.warning, 'warning');
        showMsg(this.editingId ? '编辑成功' : '新增成功', 'success');
        bootstrap.Modal.getInstance(document.getElementById('ltlModal')).hide();
        this.loadPage();
    },

    async delete(id) {
        if (!confirm('确定删除？')) return;
        await API.del(`/api/ltl-approval/${id}`);
        showMsg('删除成功', 'success');
        this.selectedIds.delete(id);
        this.loadPage();
    },

    importFile(input) {
        if (!input.files[0]) return;
        this._pendingImportFile = input;
        document.getElementById('duplicateModalTitle').textContent = '重复零担审批处理';
        document.getElementById('duplicateModalDesc').textContent = '导入文件中存在已有审批记录的交货单号，请选择处理方式：';
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
            const resp = await API.upload('/api/ltl-approval/import', fd);
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

    prevPage() { if (this.page > 1) { this.page--; this.loadPage(); } },
    nextPage() { this.page++; this.loadPage(); }
};
