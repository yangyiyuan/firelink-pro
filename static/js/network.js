// 网络配置模块
const NetworkModule = (function() {
    let networkConfigs = [];
    let currentConfigId = null;
    let socket;
    let targetConnected = false;

    function init(socketInstance) {
        socket = socketInstance;
        loadNetworkConfigs();
        setupEventListeners();
        setupConnectionListeners();
    }

    function loadNetworkConfigs() {
        fetch('/api/network_configs').then(r => r.json()).then(data => {
            networkConfigs = data;
            const select = document.getElementById('networkConfigSelect');
            select.innerHTML = data.map(cfg => 
                `<option value="${cfg.id}" ${currentConfigId === cfg.id ? 'selected' : ''}>${cfg.name}</option>`
            ).join('');
            if (data.length > 0 && !currentConfigId) {
                currentConfigId = data[0].id;
            }
            updateConfigDisplay();
            // 刷新自定义下拉框
            const inst = CustomSelect.init(select);
            if (inst) CustomSelect.refresh(inst);
        });
    }

    function updateConfigDisplay() {
        const config = networkConfigs.find(c => c.id === currentConfigId);
        if (config) {
            document.getElementById('targetServer').textContent = `${config.host}:${config.port}`;
        }
    }

    function onConfigChange() {
        const select = document.getElementById('networkConfigSelect');
        currentConfigId = parseInt(select.value);
        updateConfigDisplay();
    }

    function getNetworkConfig() {
        const config = networkConfigs.find(c => c.id === currentConfigId);
        if (config) {
            return {
                host: config.host,
                port: config.port,
                protocol: config.protocol
            };
        }
        return { host: '127.0.0.1', port: 8080, protocol: 'tcp' };
    }

    function setupEventListeners() {
        const select = document.getElementById('networkConfigSelect');
        if (select) {
            select.addEventListener('change', onConfigChange);
        }
    }

    function loadNetworkConfigList() {
        fetch('/api/network_configs').then(r => r.json()).then(data => {
            networkConfigs = data;
            const list = document.getElementById('configList');
            if (data.length === 0) {
                list.innerHTML = '<div class="col-span-full text-center py-12 text-jd-textMuted">' +
                    '<svg class="w-12 h-12 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
                    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"/>' +
                    '</svg><p>暂无网络配置</p><p class="text-xs mt-1">点击右上角添加配置</p></div>';
                return;
            }
            list.innerHTML = data.map((cfg, i) => `
                <div class="bg-jd-card rounded-xl border border-jd-cardBorder p-4 stagger-in" style="animation-delay: ${i * 0.05}s">
                    <div class="flex items-start justify-between mb-3">
                        <div>
                            <h4 class="text-sm font-semibold text-jd-text">${cfg.name}</h4>
                            <p class="text-xs text-jd-textMuted mt-0.5">${cfg.description || '无描述'}</p>
                        </div>
                        <div class="flex items-center gap-1">
                            <button class="w-7 h-7 rounded-lg hover:bg-jd-content flex items-center justify-center text-jd-textMuted hover:text-jd-primary transition-colors" 
                                    onclick="NetworkModule.showEditConfigModal(${cfg.id})" title="编辑">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                </svg>
                            </button>
                            <button class="w-7 h-7 rounded-lg hover:bg-jd-dangerLight flex items-center justify-center text-jd-textMuted hover:text-jd-danger transition-colors" 
                                    onclick="NetworkModule.deleteConfig(${cfg.id})" title="删除">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="space-y-1.5 text-xs">
                        <div class="flex items-center gap-2">
                            <span class="text-jd-textMuted">主机:</span>
                            <span class="font-mono text-jd-text">${cfg.host}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-jd-textMuted">端口:</span>
                            <span class="font-mono text-jd-text">${cfg.port}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-jd-textMuted">协议:</span>
                            <span class="px-2 py-0.5 rounded-full bg-jd-primaryLight text-jd-primary text-[10px] font-medium">${cfg.protocol.toUpperCase()}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        });
    }

    function showAddConfigModal() {
        document.getElementById('modalTitle').textContent = '添加网络配置';
        document.getElementById('configId').value = '';
        document.getElementById('configName').value = '';
        document.getElementById('configHostInput').value = '';
        document.getElementById('configPortInput').value = '';
        document.getElementById('configProtocolInput').value = 'tcp';
        document.getElementById('configDescription').value = '';
        document.getElementById('configModal').classList.remove('hidden');
    }

    function showEditConfigModal(id) {
        const config = networkConfigs.find(c => c.id === id);
        if (config) {
            document.getElementById('modalTitle').textContent = '编辑网络配置';
            document.getElementById('configId').value = config.id;
            document.getElementById('configName').value = config.name;
            document.getElementById('configHostInput').value = config.host;
            document.getElementById('configPortInput').value = config.port;
            document.getElementById('configProtocolInput').value = config.protocol;
            document.getElementById('configDescription').value = config.description || '';
            document.getElementById('configModal').classList.remove('hidden');
        }
    }

    function closeConfigModal() {
        document.getElementById('configModal').classList.add('hidden');
    }

    function saveConfig() {
        const id = document.getElementById('configId').value;
        const name = document.getElementById('configName').value.trim();
        const host = document.getElementById('configHostInput').value.trim();
        const port = document.getElementById('configPortInput').value;
        const protocol = document.getElementById('configProtocolInput').value;
        const description = document.getElementById('configDescription').value.trim();

        if (!name || !host || !port) {
            showToast('请填写必填项', 'error');
            return;
        }

        const data = { name, host, port: parseInt(port), protocol, description };
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/network_configs/${id}` : '/api/network_configs';

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).then(r => r.json()).then(result => {
            if (result.error) {
                showToast(result.error, 'error');
            } else {
                showToast(id ? '配置已更新' : '配置已添加', 'success');
                closeConfigModal();
                loadNetworkConfigList();
                loadNetworkConfigs();
            }
        }).catch(() => {
            showToast('保存失败', 'error');
        });
    }

    function deleteConfig(id) {
        if (!confirm('确定要删除这个网络配置吗？')) return;
        fetch(`/api/network_configs/${id}`, { method: 'DELETE' })
            .then(r => r.json()).then(result => {
                if (result.success) {
                    showToast('配置已删除', 'success');
                    loadNetworkConfigList();
                    loadNetworkConfigs();
                } else {
                    showToast(result.error || '删除失败', 'error');
                }
            }).catch(() => {
                showToast('删除失败', 'error');
            });
    }

    function testConnection() {
        const host = document.getElementById('configHostInput').value.trim();
        const port = document.getElementById('configPortInput').value;
        const protocol = document.getElementById('configProtocolInput').value;

        if (!host || !port) {
            showToast('请先填写主机和端口', 'error');
            return;
        }

        const btn = document.getElementById('btnTestConn');
        const text = document.getElementById('btnTestConnText');
        const origText = text.textContent;
        text.textContent = '测试中...';
        btn.disabled = true;
        btn.classList.add('opacity-60', 'cursor-wait');

        fetch('/api/test_connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ host, port: parseInt(port), protocol })
        })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                showToast(`连接成功: ${result.host}:${result.port} (${result.protocol.toUpperCase()})`, 'success');
                btn.className = 'btn-success px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 text-white';
                text.textContent = '成功';
                setTimeout(() => {
                    btn.className = 'btn-secondary px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5';
                    text.textContent = origText;
                    btn.disabled = false;
                }, 2000);
            } else {
                showToast(`连接失败: ${result.error}`, 'error');
                btn.className = 'btn-danger px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 text-white';
                text.textContent = '失败';
                setTimeout(() => {
                    btn.className = 'btn-secondary px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5';
                    text.textContent = origText;
                    btn.disabled = false;
                }, 2000);
            }
        })
        .catch(() => {
            showToast('测试请求失败', 'error');
            text.textContent = origText;
            btn.disabled = false;
            btn.classList.remove('opacity-60', 'cursor-wait');
        });
    }

    function toggleConnection() {
        if (targetConnected) {
            disconnectFromTarget();
        } else {
            connectToTarget();
        }
    }

    function connectToTarget() {
        const cfg = getNetworkConfig();
        document.getElementById('targetServer').textContent = `${cfg.host}:${cfg.port}`;
        updateConnectButton('connecting');
        socket.emit('connect_target', { host: cfg.host, port: cfg.port, protocol: cfg.protocol });
    }

    function disconnectFromTarget() {
        socket.emit('disconnect_target');
    }

    function setupConnectionListeners() {
        socket.on('target_connected', (data) => {
            targetConnected = true;
            updateConnectButton('connected');
            updateConnectionStatus(true);
            showToast(`已连接到 ${data.host}:${data.port}`, 'success');
        });

        socket.on('target_disconnected', () => {
            targetConnected = false;
            updateConnectButton('disconnected');
            updateConnectionStatus(false);
            showToast('已断开连接', 'info');
        });

        socket.on('target_connection_error', (data) => {
            targetConnected = false;
            updateConnectButton('disconnected');
            updateConnectionStatus(false);
            showToast(`连接失败: ${data.error}`, 'error');
        });

        socket.on('target_data_received', (data) => {
            console.log('[接收事件]', data.type, data);
            if (data.type === 'disconnected') {
                targetConnected = false;
                updateConnectButton('disconnected');
                updateConnectionStatus(false);
                showToast(data.message, 'warning');
            }
        });
    }

    function updateConnectButton(state) {
        const btn = document.getElementById('btnConnect');
        const text = document.getElementById('btnConnectText');
        if (!btn || !text) return;

        if (state === 'connected') {
            btn.className = 'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md border transition-colors bg-jd-dangerLight border-red-200 text-jd-danger hover:bg-red-100';
            btn.querySelector('svg').innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>';
            text.textContent = '断开';
        } else if (state === 'connecting') {
            btn.className = 'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md border transition-colors bg-amber-50 border-amber-200 text-amber-600 cursor-wait';
            text.textContent = '连接中...';
        } else {
            btn.className = 'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md border transition-colors bg-jd-successLight border-green-200 text-jd-success hover:bg-green-100';
            btn.querySelector('svg').innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>';
            text.textContent = '连接';
        }
    }

    function updateConnectionStatus(connected) {
        const toolbar = document.querySelector('#scenePanel .h-14 #connectionStatus, #scenePanel .h-14 span#connectionStatus');
        const els = document.querySelectorAll('#connectionStatus');
        els.forEach(el => {
            if (connected) {
                el.className = 'flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-jd-successLight text-jd-success';
                el.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-jd-success"></span>已连接';
            } else {
                el.className = 'flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-jd-dangerLight text-jd-danger';
                el.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-jd-danger"></span>未连接';
            }
        });
    }

    function isTargetConnected() {
        return targetConnected;
    }

    return {
        init,
        loadNetworkConfigs,
        getNetworkConfig,
        loadNetworkConfigList,
        showAddConfigModal,
        showEditConfigModal,
        closeConfigModal,
        saveConfig,
        deleteConfig,
        testConnection,
        toggleConnection,
        connectToTarget,
        disconnectFromTarget,
        isTargetConnected
    };
})();
