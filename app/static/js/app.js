/**
 * 运费试算工具 - 主逻辑
 */

// ── 全局工具函数 ──
const API = {
    async get(url) {
        const resp = await fetch(url);
        if (!resp.ok) {
            const text = await resp.text();
            try { const j = JSON.parse(text); throw new Error(j.error || text); }
            catch(e) { if (e.message) throw e; throw new Error(text || `服务器错误 ${resp.status}`); }
        }
        return resp.json();
    },
    async post(url, data) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data),
        });
        if (!resp.ok) {
            const text = await resp.text();
            try { const j = JSON.parse(text); throw new Error(j.error || text); }
            catch(e) { if (e.message) throw e; throw new Error(text || `服务器错误 ${resp.status}`); }
        }
        return resp.json();
    },
    async put(url, data) {
        const resp = await fetch(url, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data),
        });
        if (!resp.ok) {
            const text = await resp.text();
            try { const j = JSON.parse(text); throw new Error(j.error || text); }
            catch(e) { if (e.message) throw e; throw new Error(text || `服务器错误 ${resp.status}`); }
        }
        return resp.json();
    },
    async del(url) {
        const resp = await fetch(url, {method: 'DELETE'});
        if (!resp.ok) {
            const text = await resp.text();
            try { const j = JSON.parse(text); throw new Error(j.error || text); }
            catch(e) { if (e.message) throw e; throw new Error(text || `服务器错误 ${resp.status}`); }
        }
        return resp.json();
    },
    async upload(url, formData) {
        const resp = await fetch(url, {method: 'POST', body: formData});
        if (!resp.ok) {
            const text = await resp.text();
            try { const j = JSON.parse(text); throw new Error(j.error || text); }
            catch(e) { if (e.message) throw e; throw new Error(text || `服务器错误 ${resp.status}`); }
        }
        return resp.json();
    }
};

function showMsg(msg, type = 'info') {
    const container = document.querySelector('.container-fluid');
    const div = document.createElement('div');
    div.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    div.style.cssText = 'top:60px;right:20px;z-index:9999;min-width:300px;';
    div.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    container.appendChild(div);
    setTimeout(() => div.remove(), 4000);
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    if (dateStr.length === 8) {
        return `${dateStr.slice(0,4)}-${dateStr.slice(4,6)}-${dateStr.slice(6,8)}`;
    }
    return dateStr;
}

function parseDateToYYYYMMDD(inputVal) {
    // 将 input[type=date] 的 "2024-01-15" 转为 "20240115"
    if (!inputVal) return '';
    return inputVal.replace(/-/g, '');
}

// ── 导入结果弹窗（全局复用）──
window._lastImportErrors = [];

function showImportResult(resp) {
    const body = document.getElementById('import-result-body');
    let html = `<div class="alert alert-${resp.errors?.length ? 'warning' : 'success'}">${resp.message}</div>`;
    if (resp.errors?.length) {
        window._lastImportErrors = resp.errors;
        html += '<div style="max-height:300px;overflow:auto"><ul class="small">';
        resp.errors.slice(0, 50).forEach(e => html += `<li>${e}</li>`);
        if (resp.errors.length > 50) html += `<li>...共 ${resp.errors.length} 条错误</li>`;
        html += '</ul></div>';
        html += `<button class="btn btn-outline-danger btn-sm mt-2" onclick="downloadImportErrors()"><i class="bi bi-download"></i> 下载失败原因列表</button>`;
    } else {
        window._lastImportErrors = [];
    }
    body.innerHTML = html;
    new bootstrap.Modal(document.getElementById('importResultModal')).show();
}

function downloadImportErrors() {
    const errors = window._lastImportErrors || [];
    if (!errors.length) { showMsg('没有失败记录', 'warning'); return; }
    let csv = '﻿行号,错误原因\n';
    errors.forEach((e, i) => {
        csv += `"${i+1}","${String(e).replace(/"/g, '""')}"\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '导入失败原因列表.csv';
    a.click();
    URL.revokeObjectURL(url);
}

// ── 自动更新 ──
const Update = {
    _data: null,

    async check() {
        // 静默检查（页面加载时调用，不弹提示）
        try {
            const data = await API.get('/api/update/check');
            if (data.has_update) {
                this._data = data;
                document.getElementById('update-link').style.display = 'inline';
            }
        } catch(e) { /* 静默失败 */ }
    },

    async manualCheck(btn) {
        const icon = btn.querySelector('i');
        const originalText = btn.innerHTML;

        // 禁用按钮 + 旋转图标
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-arrow-repeat" style="animation: spin 1s linear infinite"></i> 检查中...';

        const startTime = Date.now();

        try {
            const resp = await fetch('/api/update/check?force=1&t=' + Date.now());
            const data = await resp.json();

            // 确保至少显示 1 秒
            const elapsed = Date.now() - startTime;
            if (elapsed < 1000) {
                await new Promise(resolve => setTimeout(resolve, 1000 - elapsed));
            }

            if (data.has_update) {
                this._data = data;
                document.getElementById('update-link').style.display = 'inline';
                showMsg(`发现新版本 v${data.version}`, 'success');
            } else {
                showMsg('当前已是最新版本', 'info');
            }
        } catch(e) {
            showMsg('检查更新失败，请检查网络连接', 'warning');
        } finally {
            // 恢复按钮
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    },

    showModal() {
        if (!this._data) return;
        document.getElementById('update-version').textContent = 'v' + this._data.version;
        const notes = this._data.notes || '';
        document.getElementById('update-notes').innerHTML = notes ? notes.replace(/\n/g, '<br>') : '无更新说明';
        document.getElementById('update-progress').style.display = 'none';
        document.getElementById('update-btn').disabled = false;
        document.getElementById('update-btn').innerHTML = '<i class="bi bi-download"></i> 立即更新';
        // 手动下载按钮
        const manualBtn = document.getElementById('manual-download-btn');
        if (this._data.raw_url) {
            manualBtn.href = this._data.raw_url;
            manualBtn.style.display = 'inline-block';
        } else {
            manualBtn.style.display = 'none';
        }
        new bootstrap.Modal(document.getElementById('updateModal')).show();
    },

    async apply() {
        const btn = document.getElementById('update-btn');
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> 下载中...';
        document.getElementById('update-progress').style.display = 'block';

        try {
            const data = await API.post('/api/update/apply');
            if (data.success) {
                document.getElementById('update-status').textContent = '下载完成，程序即将重启...';
                document.getElementById('update-bar').style.width = '100%';
                document.getElementById('update-bar').classList.add('bg-success');
                btn.innerHTML = '<i class="bi bi-check-circle"></i> 完成';
            } else {
                throw new Error(data.error || '更新失败');
            }
        } catch(e) {
            document.getElementById('update-status').textContent = '更新失败: ' + e.message;
            document.getElementById('update-bar').classList.add('bg-danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-download"></i> 重试';
        }
    },
};

// ── 应用控制 ──
const App = {
    shutdown() {
        if (!confirm('确定要退出运费试算工具吗？')) return;
        // pywebview 模式：调用 Python 的 shutdown 方法关闭窗口
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.shutdown();
        } else {
            // 开发模式（浏览器）：调用 HTTP 接口
            fetch('/api/config/shutdown', { method: 'POST' })
                .then(() => { window.close(); })
                .catch(() => { window.close(); });
        }
    },
};

// ── 页面初始化 ──
document.addEventListener('DOMContentLoaded', () => {
    Config.loadAll();
    Delivery.loadPage();
    Ltl.loadPage();
    Contract.loadPage();
    Update.check();

    // 初始化所有 popover（搜索框帮助按钮）
    document.querySelectorAll('[data-bs-toggle="popover"]').forEach(el => {
        new bootstrap.Popover(el, { container: 'body' });
    });

    // 全局日期输入：限制年份为4位，防止误输6位年份（如 200001）
    document.addEventListener('input', (e) => {
        if (e.target.tagName !== 'INPUT' || e.target.type !== 'date') return;
        const val = e.target.value;
        if (!val) return;
        const yearStr = val.split('-')[0];
        if (yearStr.length > 4) {
            const d = e.target.valueAsDate;
            if (d && !isNaN(d)) {
                const y = d.getFullYear();
                if (y > 9999 || y < 1000) {
                    e.target.value = '';
                    return;
                }
                const m = String(d.getMonth() + 1).padStart(2, '0');
                const day = String(d.getDate()).padStart(2, '0');
                e.target.value = `${String(y).padStart(4,'0')}-${m}-${day}`;
            } else {
                e.target.value = '';
            }
        }
    });
});
