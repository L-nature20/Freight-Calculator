/**
 * 合同管理
 */
const Contract = {
    columns: ['合同编码', '合同名称', '承运商名称', '承运商编码', '合同有效期起始', '合同有效期截止', '合同状态'],
    rateColumns: ['线路代码','坎级数','装运点','运输区域','线路类型','是否含末端','增值税税率',
                  '含增值税运输价格1','含增值税运输价格2','含增值税运输价格3','含增值税运输价格4',
                  '含增值税末端费用','货物类型','运输方式'],
    allRateColumns: ['合同编码','合同名称','承运商名称','线路代码','坎级数','装运点','运输区域',
                     '线路类型','是否含末端','增值税税率','含增值税运输价格1','含增值税运输价格2',
                     '含增值税运输价格3','含增值税运输价格4','含增值税末端费用','货物类型','运输方式',
                     '合同有效期起始','合同有效期截止'],
    page: 1,
    perPage: 50,
    allRatesPage: 1,
    ratePage: 1,
    editingId: null,
    selectedContractId: null,
    selectedIds: new Set(),
    selectedRateIds: new Set(),
    searchParams: {},
    allRatesSearchParams: {},

    _getSearchParams() {
        const p = {};
        const v = id => document.getElementById(id)?.value.trim();
        if (v('contract-search-code')) p.contract_code = v('contract-search-code');
        if (v('contract-search-name')) p.contract_name = v('contract-search-name');
        if (v('contract-search-carrier')) p.carrier_name = v('contract-search-carrier');
        if (v('contract-search-carrier-code')) p.carrier_code = v('contract-search-carrier-code');
        if (v('contract-search-status')) p.status = v('contract-search-status');
        return p;
    },

    _getAllRatesSearchParams() {
        const p = {};
        const v = id => document.getElementById(id)?.value.trim();
        if (v('allrates-search-contract')) p.contract_code = v('allrates-search-contract');
        if (v('allrates-search-carrier')) p.carrier_name = v('allrates-search-carrier');
        if (v('allrates-search-shipping')) p.shipping_point = v('allrates-search-shipping');
        if (v('allrates-search-area')) p.transport_area = v('allrates-search-area');
        if (v('allrates-search-cargo')) p.cargo_type = v('allrates-search-cargo');
        if (v('allrates-search-route-type')) p.route_type = v('allrates-search-route-type');
        if (v('allrates-search-transport-mode')) p.transport_mode = v('allrates-search-transport-mode');
        return p;
    },

    async loadPage() {
        const search = document.getElementById('contract-search').value;
        const data = await API.get(`/api/contract?page=${this.page}&per_page=${this.perPage}&search=${encodeURIComponent(search)}`);
        this.renderTable(data.data);
        document.getElementById('contract-page-info').textContent =
            `共 ${data.total} 条，第 ${data.page}/${data.pages || 1} 页`;
        this._syncSelectAll();
    },

    renderTable(rows) {
        const thead = document.getElementById('contract-thead');
        const tbody = document.getElementById('contract-tbody');
        thead.innerHTML = '<th style="width:26px"></th>' + this.columns.map(c => `<th>${c}</th>`).join('') + '<th>操作</th>';
        tbody.innerHTML = rows.map((r, i) => {
            const statusColor = {'草稿':'text-secondary','生效':'text-success','失效':'text-warning','作废':'text-danger'}[r['合同状态']] || '';
            const selected = r.id === this.selectedContractId ? 'selected-row' : '';
            return `<tr class="clickable-row ${selected}" onclick="Contract.selectContract(${r.id},'${(r['合同名称']||'').replace(/'/g,"\\'")}')">
                <td onclick="event.stopPropagation()"><input type="checkbox" class="row-checkbox" data-id="${r.id}" ${this.selectedIds.has(r.id)?'checked':''} onchange="Contract.toggleSelect(${r.id}, this.checked)"></td>
                ${this.columns.map(c => {
                    if (c === '合同状态') return `<td class="${statusColor}" style="font-weight:500">${r[c]}</td>`;
                    if (c.includes('日期')) return `<td>${formatDate(r[c])}</td>`;
                    return `<td>${r[c] ?? ''}</td>`;
                }).join('')}
                <td onclick="event.stopPropagation()">
                    <button class="btn btn-outline-primary btn-xs" onclick="Contract.showEditModal(${r.id})" title="编辑"><i class="bi bi-pencil"></i></button>
                </td>
            </tr>`;
        }).join('') || '<tr><td colspan="' + (this.columns.length + 2) + '" class="text-center text-muted py-3">暂无数据</td></tr>';
    },

    toggleSelect(id, checked) {
        if (checked) this.selectedIds.add(id); else this.selectedIds.delete(id);
        this._updateSelectionUI();
    },

    async toggleAll(sourceCheckbox) {
        const checked = sourceCheckbox.checked;
        if (checked) {
            const search = document.getElementById('contract-search')?.value || '';
            const data = await API.get(`/api/contract?select_all=1&search=${encodeURIComponent(search)}`);
            (data.all_ids || []).forEach(id => this.selectedIds.add(id));
            document.querySelectorAll('#contract-tbody .row-checkbox').forEach(cb => cb.checked = true);
            this._updateSelectionUI();
        } else {
            this.selectedIds.clear();
            document.querySelectorAll('#contract-tbody .row-checkbox').forEach(cb => cb.checked = false);
            this._updateSelectionUI();
        }
    },

    _syncSelectAll() {
        const cb = document.querySelector('#contract-toolbar input[type=checkbox]');
        const rowCbs = document.querySelectorAll('#contract-tbody .row-checkbox');
        const allChecked = rowCbs.length > 0 && [...rowCbs].every(c => this.selectedIds.has(parseInt(c.dataset.id)));
        if (cb) cb.checked = allChecked;
        // 同步当前页行checkbox状态
        rowCbs.forEach(c => { c.checked = this.selectedIds.has(parseInt(c.dataset.id)); });
        this._updateSelectionUI();
    },

    _updateSelectionUI() {
        const el = document.getElementById('contract-selected-count');
        if (el) el.textContent = `已选 ${this.selectedIds.size} 项`;
    },

    async _batchStatusChange(action, label, btnId) {
        if (!this.selectedIds.size) { showMsg('请先勾选记录', 'warning'); return; }
        if (!confirm(`确定将选中的 ${this.selectedIds.size} 个合同${label}？`)) return;
        const btn = document.getElementById(btnId);
        const origHTML = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${label}中...`; }
        try {
            let ok = 0;
            for (const id of this.selectedIds) {
                const r = await API.post(`/api/contract/${id}/${action}`, {});
                if (!r.error) ok++;
            }
            showMsg(`已${label} ${ok} 个`, 'success');
            this.loadPage();
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = origHTML; }
        }
    },

    batchActivate()     { return this._batchStatusChange('activate', '生效', 'contract-batch-activate-btn'); },
    batchInvalidate()   { return this._batchStatusChange('invalidate', '失效', 'contract-batch-invalidate-btn'); },
    batchVoid()         { return this._batchStatusChange('void', '作废', 'contract-batch-void-btn'); },

    async batchDelete() {
        if (!this.selectedIds.size) { showMsg('请先勾选记录', 'warning'); return; }
        if (!confirm(`确定删除选中的 ${this.selectedIds.size} 个合同及其费率？`)) return;
        const btn = document.getElementById('contract-batch-delete-btn');
        const origHTML = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 删除中...'; }
        try {
            const resp = await API.post('/api/contract/batch-delete', { ids: [...this.selectedIds] });
            showMsg(resp.message || `已删除`, 'success');
            this.selectedIds.clear();
            this.loadPage();
        } catch(e) {
            showMsg('删除失败：' + e.message, 'danger');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = origHTML; }
        }
    },

    async selectContract(id, name) {
        this.selectedContractId = id;
        this.ratePage = 1;
        document.getElementById('rate-contract-name').textContent = name;
        document.getElementById('btn-add-rate').style.display = '';
        document.getElementById('btn-import-rate').style.display = '';
        document.getElementById('rate-search').value = '';
        await this.loadRates(id);
        this.loadPage();
    },

    async loadRates(contractId) {
        this.selectedRateIds.clear();
        document.getElementById('rate-toolbar').style.display = '';
        const search = document.getElementById('rate-search')?.value.trim() || '';
        const params = new URLSearchParams({
            page: this.ratePage,
            per_page: this.perPage,
            search: search
        });
        const data = await API.get(`/api/contract/${contractId}/rates?${params.toString()}`);
        const thead = document.getElementById('rate-thead');
        const tbody = document.getElementById('rate-tbody');
        thead.innerHTML = '<th style="width:26px"></th>' + this.rateColumns.map(c => `<th>${c}</th>`).join('') + '<th>操作</th>';
        tbody.innerHTML = (data.rates || []).map((r, i) => `<tr>
            <td><input type="checkbox" class="row-checkbox" data-id="${r.id}" onchange="Contract.toggleRateSelect(${r.id}, this.checked)"></td>
            ${this.rateColumns.map(c => `<td>${r[c] ?? ''}</td>`).join('')}
            <td><button class="btn btn-outline-danger btn-xs" onclick="Contract.deleteRate(${r.id})"><i class="bi bi-trash"></i></button></td>
        </tr>`).join('') || `<tr><td colspan="${this.rateColumns.length + 2}" class="text-center text-muted py-3">暂无费率，请导入或新增</td></tr>`;
        document.getElementById('rate-page-info').textContent =
            `共 ${data.total} 条，第 ${data.page}/${data.pages || 1} 页`;
        this._syncRateSelectAll();
    },

    toggleRateSelect(id, checked) {
        if (checked) this.selectedRateIds.add(id); else this.selectedRateIds.delete(id);
        this._updateRateSelectionUI();
    },

    async toggleAllRates(sourceCheckbox) {
        const checked = sourceCheckbox.checked;
        if (checked) {
            const search = document.getElementById('rate-search')?.value.trim() || '';
            const data = await API.get(`/api/contract/${this.selectedContractId}/rates?select_all=1&search=${encodeURIComponent(search)}`);
            (data.all_ids || []).forEach(id => this.selectedRateIds.add(id));
            document.querySelectorAll('#rate-tbody .row-checkbox').forEach(cb => cb.checked = true);
            this._updateRateSelectionUI();
        } else {
            this.selectedRateIds.clear();
            document.querySelectorAll('#rate-tbody .row-checkbox').forEach(cb => cb.checked = false);
            this._updateRateSelectionUI();
        }
    },

    _syncRateSelectAll() {
        const cb = document.querySelector('#rate-toolbar input[type=checkbox]');
        const rowCbs = document.querySelectorAll('#rate-tbody .row-checkbox');
        const allChecked = rowCbs.length > 0 && [...rowCbs].every(c => this.selectedRateIds.has(parseInt(c.dataset.id)));
        if (cb) cb.checked = allChecked;
        rowCbs.forEach(c => { c.checked = this.selectedRateIds.has(parseInt(c.dataset.id)); });
        this._updateRateSelectionUI();
    },

    _updateRateSelectionUI() {
        const el = document.getElementById('rate-selected-count');
        if (el) el.textContent = `已选 ${this.selectedRateIds.size} 项`;
    },

    async batchDeleteRate() {
        if (!this.selectedRateIds.size) { showMsg('请先勾选要删除的费率', 'warning'); return; }
        if (!confirm(`确定删除选中的 ${this.selectedRateIds.size} 条费率？`)) return;
        const btn = document.getElementById('rate-batch-delete-btn');
        const origHTML = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 删除中...'; }
        try {
            const resp = await API.post('/api/contract/rate-batch-delete', { ids: [...this.selectedRateIds] });
            showMsg(resp.message || `已删除`, 'success');
            this.selectedRateIds.clear();
            this.ratePage = 1;
            this.loadRates(this.selectedContractId);
        } catch(e) {
            showMsg('删除失败：' + e.message, 'danger');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = origHTML; }
        }
    },

    // ── 费率明细（独立列表）──
    async loadAllRates() {
        const params = new URLSearchParams({
            page: this.allRatesPage,
            per_page: this.perPage,
            ...this.allRatesSearchParams
        });
        const data = await API.get(`/api/contract/all-rates?${params.toString()}`);
        const thead = document.getElementById('allrates-thead');
        const tbody = document.getElementById('allrates-tbody');
        thead.innerHTML = this.allRateColumns.map(c => `<th>${c}</th>`).join('');
        tbody.innerHTML = (data.data || []).map((r, i) => `<tr>
            ${this.allRateColumns.map(c => {
                if (c.includes('日期')) return `<td>${formatDate(r[c])}</td>`;
                return `<td>${r[c] ?? ''}</td>`;
            }).join('')}
        </tr>`).join('') || `<tr><td colspan="${this.allRateColumns.length}" class="text-center text-muted py-3">暂无数据</td></tr>`;
        document.getElementById('allrates-page-info').textContent =
            `共 ${data.total} 条，第 ${data.page}/${data.pages || 1} 页`;
    },

    searchAllRates() {
        this.allRatesSearchParams = this._getAllRatesSearchParams();
        this.allRatesPage = 1;
        this.loadAllRates();
    },

    clearAllRatesSearch() {
        ['allrates-search-contract','allrates-search-carrier','allrates-search-shipping',
         'allrates-search-area','allrates-search-cargo','allrates-search-route-type',
         'allrates-search-transport-mode']
            .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
        this.allRatesSearchParams = {};
        this.allRatesPage = 1;
        this.loadAllRates();
    },

    allRatesPrevPage() { if (this.allRatesPage > 1) { this.allRatesPage--; this.loadAllRates(); } },
    allRatesNextPage() { this.allRatesPage++; this.loadAllRates(); },

    showAddModal() {
        this.editingId = null;
        document.getElementById('contract-modal-title').textContent = '新增合同';
        this._renderForm({});
        new bootstrap.Modal(document.getElementById('contractModal')).show();
    },

    async showEditModal(id) {
        this.editingId = id;
        document.getElementById('contract-modal-title').textContent = '编辑合同';
        const row = await API.get(`/api/contract/${id}`);
        if (row && !row.error) this._renderForm(row);
        new bootstrap.Modal(document.getElementById('contractModal')).show();
    },

    _renderForm(data) {
        const fields = [
            {name:'合同编码', type:'text', req:true, readonly:!!this.editingId},
            {name:'合同名称', type:'text', req:true},
            {name:'承运商名称', type:'text', req:true},
            {name:'承运商编码', type:'text', req:true},
            {name:'合同有效期起始', type:'date', req:true},
            {name:'合同有效期截止', type:'date', req:true},
        ];
        document.getElementById('contract-form').innerHTML = fields.map(f => {
            let val = data[f.name] || '';
            if (f.type === 'date' && val) val = formatDate(val);
            return `<div class="mb-2"><label class="form-label">${f.name}${f.req?' *':''}</label>
                <input type="${f.type}" class="form-control form-control-sm" data-field="${f.name}" value="${val}" ${f.readonly?'readonly':''} ${f.type==='date'?'min="1900-01-01" max="2099-12-31"':''}></div>`;
        }).join('') + `<div class="mb-2"><label class="form-label">备注</label>
            <textarea class="form-control form-control-sm" data-field="备注">${data['备注']||''}</textarea></div>`;
    },

    async save() {
        const inputs = document.querySelectorAll('#contract-form [data-field]');
        const d = {};
        inputs.forEach(inp => {
            let v = inp.value.trim();
            if (inp.type === 'date' && v) v = v.replace(/-/g, '');
            d[inp.dataset.field] = v;
        });
        if (this.editingId) {
            await API.put(`/api/contract/${this.editingId}`, d);
        } else {
            const resp = await API.post('/api/contract', d);
            if (resp.error) { showMsg(resp.error, 'danger'); return; }
        }
        showMsg('保存成功', 'success');
        bootstrap.Modal.getInstance(document.getElementById('contractModal')).hide();
        this.loadPage();
    },

    async delete(id) {
        if (!confirm('确定删除该合同及其所有费率？')) return;
        await API.del(`/api/contract/${id}`);
        showMsg('删除成功', 'success');
        this.loadPage();
    },

    showAddRateModal() {
        if (!this.selectedContractId) { showMsg('请先选择一个合同', 'warning'); return; }
        this._renderRateForm({});
        new bootstrap.Modal(document.getElementById('rateModal')).show();
    },

    _renderRateForm(data) {
        const fields = [
            '装运点','装运点描述','运输区域','运输区域描述',
            '省/直辖市','地级市','县/区','里程(KM)','线路类型','增值税税率',
            '含增值税运输价格1','含增值税运输价格2','含增值税运输价格3','含增值税运输价格4',
            '含增值税末端费用','货物类型','运输方式'
        ];
        document.getElementById('rate-form').innerHTML = '<div class="row">' + fields.map(f => {
            const isNum = f.includes('KM') || f.includes('价格') || f.includes('费用') || f.includes('税率');
            const val = data[f] ?? '';
            return `<div class="col-md-4 mb-2"><label class="form-label">${f}</label>
                <input type="${isNum?'number':'text'}" class="form-control form-control-sm" data-field="${f}" value="${val}" ${isNum?'step="0.01"':''}></div>`;
        }).join('') + '</div>';
    },

    async saveRate() {
        const inputs = document.querySelectorAll('#rate-form input[data-field]');
        const d = {};
        inputs.forEach(inp => {
            let v = inp.value.trim();
            if (inp.type === 'number') v = v ? parseFloat(v) : 0;
            d[inp.dataset.field] = v;
        });
        await API.post(`/api/contract/${this.selectedContractId}/rates`, d);
        showMsg('费率添加成功', 'success');
        bootstrap.Modal.getInstance(document.getElementById('rateModal')).hide();
        this.ratePage = 1;
        this.loadRates(this.selectedContractId);
    },

    async deleteRate(rateId) {
        if (!confirm('确定删除该费率？')) return;
        await API.del(`/api/contract/rate/${rateId}`);
        showMsg('删除成功', 'success');
        this.ratePage = 1;
        this.loadRates(this.selectedContractId);
    },

    async importFile(input) {
        if (!input.files[0]) return;
        const btn = input.parentElement.querySelector('.btn-success');
        const origHTML = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 导入中...'; }
        try {
            const fd = new FormData();
            fd.append('file', input.files[0]);
            const resp = await API.upload('/api/contract/import', fd);
            showImportResult(resp);
            input.value = '';
            this.selectedIds.clear();
            this.loadPage();
        } catch(e) {
            showMsg('导入失败：' + e.message, 'danger');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = origHTML; }
        }
    },

    async importRateFile(input) {
        if (!input.files[0]) return;
        if (!this.selectedContractId) { showMsg('请先选择合同', 'warning'); input.value=''; return; }
        const btn = input.parentElement.querySelector('#btn-import-rate');
        const origHTML = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 导入中...'; }
        try {
            const fd = new FormData();
            fd.append('file', input.files[0]);
            const resp = await API.upload(`/api/contract/${this.selectedContractId}/rates/import`, fd);
            showImportResult(resp);
            input.value = '';
            this.ratePage = 1;
            this.loadRates(this.selectedContractId);
        } catch(e) {
            showMsg('导入失败：' + e.message, 'danger');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = origHTML; }
        }
    },

    prevPage() { if (this.page > 1) { this.page--; this.loadPage(); } },
    nextPage() { this.page++; this.loadPage(); },

    ratePrevPage() { if (this.ratePage > 1) { this.ratePage--; this.loadRates(this.selectedContractId); } },
    rateNextPage() { this.ratePage++; this.loadRates(this.selectedContractId); }
};
