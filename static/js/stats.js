// 统计模块
const StatsModule = (function() {
    function updateStats() {
        fetch('/api/stats').then(r => r.json()).then(data => {
            document.getElementById('totalSent').textContent = data.total_sent;
        });
    }

    return {
        updateStats
    };
})();