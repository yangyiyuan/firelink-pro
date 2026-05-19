// 面板切换模块
const PanelModule = (function() {
    function showPanel(name) {
        if (name === 'network') {
            document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
            document.querySelector('a[onclick="PanelModule.showPanel(\'network\')"]')?.classList.add('active');
            document.getElementById('scenePanel').classList.add('hidden');
            document.getElementById('networkPanel').classList.remove('hidden');
            document.getElementById('mainTitle').textContent = '网络配置';
            document.getElementById('breadcrumbScene').textContent = '网络配置管理';
            document.getElementById('connectionStatus').style.display = 'none';
            NetworkModule.loadNetworkConfigList();
            showToast('已切换到网络配置', 'info');
        } else if (name === 'scene') {
            document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
            document.querySelector('a[href="#"][title="场景模拟"]')?.classList.add('active');
            document.getElementById('networkPanel').classList.add('hidden');
            document.getElementById('scenePanel').classList.remove('hidden');
            document.getElementById('mainTitle').textContent = '场景模拟';
            document.getElementById('breadcrumbScene').textContent = '单点火灾报警';
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