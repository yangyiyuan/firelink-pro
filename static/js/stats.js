// 统计模块（无外部依赖）
const StatsModule = (function() {
    function updateStats() {
        fetch('/api/stats').then(r => r.json()).then(data => {
            const totalSentEl = document.getElementById('totalSent');
            if (totalSentEl) totalSentEl.textContent = data.total_sent;
            const seqEl = document.getElementById('currentSequence');
            if (seqEl) seqEl.textContent = data.sequence !== undefined ? data.sequence : '-';
        });
    }

    return {
        updateStats
    };
})();