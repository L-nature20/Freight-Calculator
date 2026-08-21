/**
 * 基础配置
 */
const Config = {
    editingTierId: null,

    async loadAll() {
        // 加载泡货系数
        await this.loadCoefficient();
        // 加载整车标识
        await this.loadTruckFields();
        // 加载坎级
        this.loadTiers();
    },

    // ── 泡货系数（简单数值配置）──
    async loadCoefficient() {
        const cfg = await API.get('/api/config');
        const val = parseFloat(cfg['volumetric_coefficient'] || 3.5);
        document.getElementById('config-coefficient').value = val;
    },

    async saveCoefficient() {
        const val = document.getElementById('config-coefficient').value;
        if (!val || parseFloat(val) <= 0) { showMsg('系数必须大于0', 'danger'); return; }
        const resp = await API.put('/api/config/volumetric_coefficient', { value: val });
        if (resp.error) { showMsg(resp.error, 'danger'); return; }
        showMsg('系数已保存', 'success');
    },

    // ── 整车标识字段选择器 ──
    async loadTruckFields() {
        const cfg = await API.get('/api/config');
        const selected = (cfg['truck_unique_fields'] || '拼车单号').split(',').map(s => s.trim()).filter(Boolean);
        const availableFields = [
            '交货单号', '装运点', '装运点描述', '运输区域', '运输区域描述',
            '拼车单号', '运单号', '车牌号', '承运商编码', '承运商名称',
            '销售组织', '组织名称', '送达方名称', '送达方编码', '货物类型'
        ];
        const container = document.getElementById('truck-fields-selector');
        container.innerHTML = availableFields.map(f => {
            const checked = selected.includes(f) ? 'checked' : '';
            return `<div class="form-check form-check-inline">
                <input class="form-check-input truck-field-cb" type="checkbox" value="${f}" ${checked}>
                <label class="form-check-label small">${f}</label>
            </div>`;
        }).join('');
    },

    async saveTruckFields() {
        const cbs = document.querySelectorAll('.truck-field-cb:checked');
        const fields = Array.from(cbs).map(cb => cb.value);
        if (!fields.length) { showMsg('请至少选择一个字段', 'danger'); return; }
        await API.put('/api/config/truck_unique_fields', { value: fields.join(',') });
        showMsg('整车标识已保存', 'success');
    },

    // ── 坎级区间 ──
    async loadTiers() {
        const tiers = await API.get('/api/config/tier-intervals');
        const tbody = document.getElementById('tier-tbody');
        tbody.innerHTML = tiers.map(t => `<tr>
            <td><b>${t['坎级名称']}</b></td>
            <td><span class="badge bg-secondary">${t['坎级序数']}</span></td>
            <td>${t['坎级下限']}</td>
            <td>${t['坎级上限']}</td>
            <td>
                <button class="btn btn-outline-primary btn-xs me-1" onclick="Config.showEditTierModal(${t.id})" title="编辑"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-outline-danger btn-xs" onclick="Config.deleteTier(${t.id})" title="删除"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('') || '<tr><td colspan="5" class="text-center text-muted py-3">暂无坎级配置</td></tr>';
    },

    showAddTierModal() {
        this.editingTierId = null;
        document.getElementById('tier-modal-title').textContent = '新增坎级';
        document.getElementById('tier-name').value = '';
        document.getElementById('tier-order').value = '';
        document.getElementById('tier-lower-val').value = '';
        document.getElementById('tier-upper-val').value = '';
        document.getElementById('tier-lower-op').value = 'true';
        document.getElementById('tier-upper-op').value = 'false';
        new bootstrap.Modal(document.getElementById('tierModal')).show();
    },

    async showEditTierModal(id) {
        this.editingTierId = id;
        document.getElementById('tier-modal-title').textContent = '编辑坎级';
        const tiers = await API.get('/api/config/tier-intervals');
        const t = tiers.find(x => x.id === id);
        if (!t) return;
        document.getElementById('tier-name').value = t['坎级名称'];
        document.getElementById('tier-order').value = t['坎级序数'];
        // 解析下限
        const lowerStr = t['坎级下限'];
        document.getElementById('tier-lower-op').value = lowerStr.startsWith('≥') ? 'true' : 'false';
        document.getElementById('tier-lower-val').value = t.lower_value;
        // 解析上限
        const upperStr = t['坎级上限'];
        document.getElementById('tier-upper-op').value = upperStr.startsWith('≤') ? 'true' : 'false';
        document.getElementById('tier-upper-val').value = t.upper_value;
        new bootstrap.Modal(document.getElementById('tierModal')).show();
    },

    async saveTier() {
        const d = {
            '坎级名称': document.getElementById('tier-name').value.trim(),
            '坎级序数': parseInt(document.getElementById('tier-order').value),
            lower_value: parseFloat(document.getElementById('tier-lower-val').value),
            lower_inclusive: document.getElementById('tier-lower-op').value === 'true',
            upper_value: parseFloat(document.getElementById('tier-upper-val').value),
            upper_inclusive: document.getElementById('tier-upper-op').value === 'true',
        };
        if (!d['坎级名称'] || !d['坎级序数']) { showMsg('请填写完整', 'danger'); return; }

        if (this.editingTierId) {
            const resp = await API.put(`/api/config/tier-intervals/${this.editingTierId}`, d);
            if (resp.error) { showMsg(resp.error, 'danger'); return; }
        } else {
            const resp = await API.post('/api/config/tier-intervals', d);
            if (resp.error) { showMsg(resp.error, 'danger'); return; }
        }
        showMsg('保存成功', 'success');
        bootstrap.Modal.getInstance(document.getElementById('tierModal')).hide();
        this.loadTiers();
    },

    async deleteTier(id) {
        if (!confirm('确定删除该坎级？')) return;
        await API.del(`/api/config/tier-intervals/${id}`);
        showMsg('删除成功', 'success');
        this.loadTiers();
    },

    async validateTiers() {
        const data = await API.get('/api/config/tier-intervals/validate');
        if (data.valid) {
            showMsg('坎级区间配置正确', 'success');
        } else {
            showMsg('坎级区间存在问题：' + data.issues.join('；'), 'danger');
        }
    }
};