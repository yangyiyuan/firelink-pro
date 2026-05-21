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
        const el = document.getElementById('connectionStatus');
        el.className = 'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-jd-successLight text-jd-success';
        el.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-jd-success"></span>已连接';
    });

    socket.on('disconnect', () => {
        const el = document.getElementById('connectionStatus');
        el.className = 'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-jd-dangerLight text-jd-danger';
        el.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-jd-danger"></span>未连接';
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

    if (NetworkModule.isTargetConnected()) {
        // 通过持久连接发送
        globalSocket.emit('send_via_connection', { scene: SceneModule.getCurrentScene() });
    } else {
        // 一次性发送
        globalSocket.emit('send_packet', { scene: SceneModule.getCurrentScene(), ...cfg });
    }
}