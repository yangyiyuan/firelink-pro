// 面板切换模块
const PanelModule = (function() {
    let _skipHashSync = false;

    const VALID_PANELS = ['scene', 'network', 'autoScene', 'signalInstance', 'sendHistory', 'parse'];

    function setActiveSidebar(linkId) {
        document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
        document.getElementById(linkId)?.classList.add('active');
    }

    function hideAllPanels() {
        document.getElementById('scenePanel')?.classList.add('hidden');
        document.getElementById('networkPanel')?.classList.add('hidden');
        document.getElementById('autoScenePanel')?.classList.add('hidden');
        document.getElementById('signalInstancePanel')?.classList.add('hidden');
        document.getElementById('sendHistoryPanel')?.classList.add('hidden');
        document.getElementById('parsePanel')?.classList.add('hidden');
    }

    function showPanel(name, fromHashChange) {
        if (!fromHashChange && VALID_PANELS.includes(name)) {
            _skipHashSync = true;
            window.location.hash = name;
            requestAnimationFrame(() => { _skipHashSync = false; });
        }

        if (name === 'network') {
            setActiveSidebar('sidebarNetworkLink');
            hideAllPanels();
            document.getElementById('networkPanel').classList.remove('hidden');
            document.getElementById('mainTitle').textContent = '网络配置';
            document.getElementById('breadcrumbScene').textContent = '网络配置管理';
            document.getElementById('connectionStatus').style.display = 'none';
            NetworkModule.loadNetworkConfigList();
            showToast('已切换到网络配置', 'info');
        } else if (name === 'autoScene') {
            setActiveSidebar('sidebarAutoSceneLink');
            hideAllPanels();
            document.getElementById('autoScenePanel').classList.remove('hidden');
            document.getElementById('mainTitle').textContent = '场景编排';
            document.getElementById('breadcrumbScene').textContent = '自动发送场景编排';
            document.getElementById('connectionStatus').style.display = 'none';
            if (typeof AutoSendModule !== 'undefined' && AutoSendModule.refreshPageState) {
                AutoSendModule.refreshPageState();
            }
            showToast('已切换到场景编排', 'info');
        } else if (name === 'signalInstance') {
            setActiveSidebar('sidebarSignalInstanceLink');
            hideAllPanels();
            document.getElementById('signalInstancePanel').classList.remove('hidden');
            document.getElementById('mainTitle').textContent = '信号实例';
            document.getElementById('breadcrumbScene').textContent = '基于模板的调试实例';
            document.getElementById('connectionStatus').style.display = 'none';
            if (typeof SignalInstanceModule !== 'undefined' && SignalInstanceModule.loadInitialData) {
                SignalInstanceModule.loadInitialData();
            }
            showToast('已切换到信号实例', 'info');
        } else if (name === 'scene') {
            setActiveSidebar('sidebarSceneLink');
            hideAllPanels();
            document.getElementById('scenePanel').classList.remove('hidden');
            document.getElementById('mainTitle').textContent = '信号模板';
            document.getElementById('breadcrumbScene').textContent = '部件状态';
            document.getElementById('connectionStatus').style.display = 'flex';
            NetworkModule.loadNetworkConfigs();
        } else if (name === 'sendHistory') {
            setActiveSidebar('sidebarSendHistoryLink');
            hideAllPanels();
            document.getElementById('sendHistoryPanel').classList.remove('hidden');
            document.getElementById('mainTitle').textContent = '发送历史';
            document.getElementById('breadcrumbScene').textContent = '已保存的通信记录';
            document.getElementById('connectionStatus').style.display = 'none';
            SendHistoryModule.loadHistoryList();
            showToast('已切换到发送历史', 'info');
        } else if (name === 'parse') {
            setActiveSidebar('sidebarParseLink');
            hideAllPanels();
            document.getElementById('parsePanel').classList.remove('hidden');
            document.getElementById('mainTitle').textContent = '数据包解析';
            document.getElementById('breadcrumbScene').textContent = 'GB/T 26875.3 报文逆向解析';
            document.getElementById('connectionStatus').style.display = 'none';
            if (typeof ParseModule !== 'undefined') {
                ParseModule.init();
                ParseModule.renderTypeFlagReference();
            }
            showToast('已切换到数据包解析', 'info');
        } else {
            showToast(`切换到 ${name} 面板`, 'info');
        }
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
