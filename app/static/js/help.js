/**
 * 帮助模块 - 左侧目录点击切换右侧章节
 */
const Help = {
    showSection(id, el) {
        // 隐藏所有章节
        document.querySelectorAll('.help-section-card').forEach(c => c.style.display = 'none');
        // 显示目标章节
        const target = document.getElementById(id);
        if (target) target.style.display = 'block';
        // 更新目录高亮
        document.querySelectorAll('.help-toc a').forEach(a => a.classList.remove('active'));
        if (el) el.classList.add('active');
    },
};
