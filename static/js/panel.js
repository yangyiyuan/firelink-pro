// 面板导航模块（编排器）
// 依赖: NetworkModule, SignalInstanceModule, SendHistoryModule, ParseModule
const PanelModule = (function() {
    let _skipHashSync = false;

    const PANEL_CONFIG = {
        scene: {
            sidebarId: 'sidebarSceneLink',
            panelId: 'scenePanel',
            title: '信号模板',
            breadcrumb: '部件状态',
            showConnection: true,
            onEnter: function() { NetworkModule.loadNetworkConfigs(); },
            toast: null,
        },
        network: {
            sidebarId: 'sidebarNetworkLink',
            panelId: 'networkPanel',
            title: '网络配置',
            breadcrumb: '网络配置管理',
            showConnection: false,
            onEnter: function() { NetworkModule.loadNetworkConfigList(); },
            toast: '已切换到网络配置',
        },
        autoScene: {
            sidebarId: 'sidebarAutoSceneLink',
            panelId: 'autoScenePanel',
            title: '场景编排',
            breadcrumb: '自动发送场景编排',
            showConnection: false,
            onEnter: function() { if (typeof AutoSendModule !== 'undefined' && AutoSendModule.refreshPageState) AutoSendModule.refreshPageState(); },
            toast: '已切换到场景编排',
        },
        signalInstance: {
            sidebarId: 'sidebarSignalInstanceLink',
            panelId: 'signalInstancePanel',
            title: '信号实例',
            breadcrumb: '基于模板的调试实例',
            showConnection: false,
            onEnter: function() { if (typeof SignalInstanceModule !== 'undefined' && SignalInstanceModule.loadInitialData) SignalInstanceModule.loadInitialData(); },
            toast: '已切换到信号实例',
        },
        sendHistory: {
            sidebarId: 'sidebarSendHistoryLink',
            panelId: 'sendHistoryPanel',
            title: '发送历史',
            breadcrumb: '已保存的通信记录',
            showConnection: false,
            onEnter: function() { SendHistoryModule.loadHistoryList(); },
            toast: '已切换到发送历史',
        },
        parse: {
            sidebarId: 'sidebarParseLink',
            panelId: 'parsePanel',
            title: '数据包解析',
            breadcrumb: 'GB/T 26875.3 报文逆向解析',
            showConnection: false,
            onEnter: function() { if (typeof ParseModule !== 'undefined') { ParseModule.init(); ParseModule.renderTypeFlagReference(); } },
            toast: '已切换到数据包解析',
        },
    };

    const VALID_PANELS = Object.keys(PANEL_CONFIG);

    function setActiveSidebar(linkId) {
        document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
        document.getElementById(linkId)?.classList.add('active');
    }

    function hideAllPanels() {
        VALID_PANELS.forEach(key => {
            document.getElementById(PANEL_CONFIG[key].panelId)?.classList.add('hidden');
        });
    }

    function showPanel(name, fromHashChange) {
        if (!fromHashChange && VALID_PANELS.includes(name)) {
            _skipHashSync = true;
            window.location.hash = name;
            requestAnimationFrame(() => { _skipHashSync = false; });
        }

        const cfg = PANEL_CONFIG[name];
        if (!cfg) {
            showToast(`切换到 ${name} 面板`, 'info');
            return;
        }

        setActiveSidebar(cfg.sidebarId);
        hideAllPanels();
        document.getElementById(cfg.panelId)?.classList.remove('hidden');
        document.getElementById('mainTitle').textContent = cfg.title;
        document.getElementById('breadcrumbScene').textContent = cfg.breadcrumb;
        document.getElementById('connectionStatus').style.display = cfg.showConnection ? 'flex' : 'none';

        if (cfg.onEnter) cfg.onEnter();
        if (cfg.toast) showToast(cfg.toast, 'info');
    }

    function initHashRouting() {
        window.addEventListener('hashchange', () => {
            if (_skipHashSync) return;
            const hash = window.location.hash.slice(1);
            if (VALID_PANELS.includes(hash)) {
                showPanel(hash, true);
            }
        });
    }

    function getPanelFromHash() {
        const hash = window.location.hash.slice(1);
        return VALID_PANELS.includes(hash) ? hash : 'scene';
    }

    function closeNetworkPanel() {
        showPanel('scene');
    }

    return {
        showPanel,
        closeNetworkPanel,
        initHashRouting,
        getPanelFromHash
    };
})();
