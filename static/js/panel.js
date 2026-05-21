// 面板切换模块
const PanelModule = (function() {
    function setActiveSidebar(linkId) {
        document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
        document.getElementById(linkId)?.classList.add('active');
    }

    function hideAllPanels() {
        document.getElementById('scenePanel')?.classList.add('hidden');
        document.getElementById('networkPanel')?.classList.add('hidden');
        document.getElementById('autoScenePanel')?.classList.add('hidden');
        document.getElementById('signalInstancePanel')?.classList.add('hidden');
    }

    function showPanel(name) {
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
        } else {
            showToast(`切换到 ${name} 面板`, 'info');
        }
    }

    function closeNetworkPanel() {
        showPanel('scene');
    }

    return {
        showPanel,
        closeNetworkPanel
    };
})();
