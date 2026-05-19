// 自动发送模块
const AutoSendModule = (function() {
    let autoSendRunning = false;
    let socket;

    function init(socketInstance) {
        socket = socketInstance;
        setupSocketListeners();
    }

    function startAutoSend() {
        const cfg = NetworkModule.getNetworkConfig();
        const scene = document.getElementById('autoScene').value;
        const interval = parseInt(document.getElementById('autoInterval').value);
        socket.emit('start_auto_send', {scene, interval, ...cfg});
    }

    function stopAutoSend() {
        socket.emit('stop_auto_send');
    }

    function toggleAutoSend() {
        if (autoSendRunning) {
            stopAutoSend();
        } else {
            startAutoSend();
        }
    }

    function setupSocketListeners() {
        socket.on('auto_send_started', (data) => {
            autoSendRunning = true;
            const btn = document.getElementById('btnAutoSend');
            const btnText = document.getElementById('btnAutoSendText');
            if (btn) {
                btn.classList.remove('btn-success');
                btn.classList.add('btn-danger');
            }
            if (btnText) {
                btnText.textContent = '停止';
            }
            showToast(`自动发送已启动`, 'success');
        });

        socket.on('auto_send_stopped', () => {
            autoSendRunning = false;
            const btn = document.getElementById('btnAutoSend');
            const btnText = document.getElementById('btnAutoSendText');
            if (btn) {
                btn.classList.remove('btn-danger');
                btn.classList.add('btn-success');
            }
            if (btnText) {
                btnText.textContent = '开始';
            }
            showToast('自动发送已停止', 'info');
        });

        socket.on('auto_send_result', (data) => {
            if (data.success) addToAutoLog(data);
            HistoryModule.addFromAuto(data);
            StatsModule.updateStats();
        });
    }

    function addToAutoLog(data) {
        const log = document.getElementById('autoLog');
        if (!log) return;
        if (log.querySelector('span') && log.querySelector('span').textContent.includes('自动发送日志')) log.innerHTML = '';
        const sceneName = SceneModule.getSceneName(data.scene);
        const div = document.createElement('div');
        div.className = `flex items-center gap-2 ${data.success ? 'text-jd-success' : 'text-jd-danger'}`;
        div.innerHTML = `<span class="text-jd-textMuted">${data.timestamp.split(' ')[1]}</span> <span>${sceneName}</span> <span class="text-xs">${data.length}B</span>`;
        log.appendChild(div);
        while (log.children.length > 20) log.removeChild(log.firstChild);
        log.scrollTop = log.scrollHeight;
    }

    function isRunning() {
        return autoSendRunning;
    }

    return {
        init,
        startAutoSend,
        stopAutoSend,
        toggleAutoSend,
        isRunning
    };
})();