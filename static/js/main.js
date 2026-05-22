// 主入口模块
// 全局 socket 引用（DOMContentLoaded 中初始化）
let globalSocket;

document.addEventListener('DOMContentLoaded', () => {
    globalSocket = io();

    // 初始化各个模块
    SceneModule.init(globalSocket);
    NetworkModule.init(globalSocket);
    AutoSendModule.init(globalSocket);
    SignalInstanceModule.init(globalSocket);
    HistoryModule.init(globalSocket);
    SendHistoryModule.init();

    // 初始化自定义下拉框
    CustomSelect.initAll();

    // 设置侧边栏切换
    initSidebarToggle();

    // 初始化 hash 路由
    PanelModule.initHashRouting();

    // 设置连接状态监听
    setupConnectionListeners(globalSocket);

    // 初始更新统计
    StatsModule.updateStats();

    // 根据 URL hash 恢复面板，若无 hash 则默认 scene
    const initialPanel = PanelModule.getPanelFromHash();
    if (initialPanel !== 'scene') {
        PanelModule.showPanel(initialPanel, true);
    }

    // 延迟选择初始模板
    setTimeout(() => SceneModule.selectScene('component_status'), 100);
});

function initSidebarToggle() {
    const toggle = document.getElementById('sidebarToggle');
    const appContainer = document.getElementById('appContainer');
    
    toggle.addEventListener('click', () => {
        appContainer.classList.toggle('sidebar-collapsed');
    });
}

function setupConnectionListeners(socket) {
    socket.on('connect', () => {
        NetworkModule.updateConnectionStatus(true);
    });

    socket.on('disconnect', () => {
        NetworkModule.updateConnectionStatus(false);
    });

    socket.on('error', (data) => showToast(data.message, 'error'));

    // 热重载: 监听模板变化自动刷新页面
    socket.on('template_changed', (data) => {
        console.log(`[热重载] 模板文件已更新: ${data.file}, 正在刷新...`);
        window.location.reload();
    });
}

// 全局发送数据包函数
function sendPacket() {
    const cfg = NetworkModule.getNetworkConfig();
    document.getElementById('targetServer').textContent = `${cfg.host}:${cfg.port}`;

    const instanceId = SceneModule.getSelectedInstanceId();
    if (instanceId) {
        globalSocket.emit('start_signal_instance', {
            instanceId: instanceId,
            network: cfg,
        });
        return;
    }

    if (NetworkModule.isTargetConnected()) {
        globalSocket.emit('send_via_connection', { scene: SceneModule.getCurrentScene() });
    } else {
        globalSocket.emit('send_packet', { scene: SceneModule.getCurrentScene(), ...cfg });
    }
}