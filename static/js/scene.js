// 场景模拟模块
const SceneModule = (function() {
    // 场景分组定义
    const sceneGroups = [
        { id: 'fire', label: '火警报警', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z"/></svg>`, color: 'text-red-500' },
        { id: 'status', label: '状态监控', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>`, color: 'text-blue-500' },
        { id: 'tool', label: '快捷工具', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>`, color: 'text-violet-500' },
    ];

    const scenes = [
        // 火警报警组
        { id: 'single_fire', name: '单点火灾', desc: '单个探测器火警', level: 'warning', group: 'fire',
          typeFlag: '部件运行状态', packets: 1, component: '光电感烟',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/></svg>` },
        { id: 'confirmed_fire', name: '确认火警', desc: '多点同时报警', level: 'danger', group: 'fire',
          typeFlag: '部件运行状态', packets: 1, component: '烟感+温感+手报',
          icon: `<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>` },
        { id: 'composite', name: '复合报警', desc: '火警+故障同时发生', level: 'danger', group: 'fire',
          typeFlag: '部件运行状态', packets: 1, component: '烟感+温感',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>` },
        { id: 'system_fire', name: '系统级火警', desc: '整个系统火警状态', level: 'danger', group: 'fire',
          typeFlag: '系统状态', packets: 1, component: '火灾报警系统',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>` },
        { id: 'device_fire', name: '装置火警', desc: '传输装置火警状态', level: 'danger', group: 'fire',
          typeFlag: '装置运行状态', packets: 1, component: '传输装置',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>` },
        { id: 'full_fire', name: '完整火灾场景', desc: '4包序列模拟全流程', level: 'danger', group: 'fire',
          typeFlag: '多类型', packets: 4, component: '系统+装置+部件+模拟量',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>` },
        // 状态监控组
        { id: 'normal', name: '正常状态', desc: '设备正常监视状态', level: 'info', group: 'status',
          typeFlag: '装置运行状态', packets: 1, component: '传输装置',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>` },
        { id: 'fault', name: '故障报警', desc: '设备故障或离线', level: 'warning', group: 'status',
          typeFlag: '部件运行状态', packets: 1, component: '光电感烟',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>` },
        { id: 'analog', name: '模拟量超限', desc: '温度/烟雾浓度超限', level: 'warning', group: 'status',
          typeFlag: '部件模拟量值', packets: 1, component: '温感+烟感',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>` },
        // 工具组
        { id: 'random', name: '随机场景', desc: '随机生成一种场景', level: 'info', group: 'tool',
          typeFlag: '随机', packets: 1, component: '随机',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>` },
    ];

    let currentScene = 'single_fire';
    let socket;

    function init(socketInstance) {
        socket = socketInstance;
        initSceneList();
        setupSocketListeners();
    }

    function initSceneList() {
        renderSceneSidebarList();
    }

    function renderSceneSidebarList() {
        const list = document.getElementById('sceneList');
        if (!list) return;

        const levelStyles = {
            'info': { bg: 'bg-blue-50', text: 'text-blue-600', border: 'border-blue-100', dot: 'bg-blue-400', badge: 'bg-blue-100 text-blue-600', hoverAccent: 'hover:border-blue-200' },
            'warning': { bg: 'bg-amber-50', text: 'text-amber-600', border: 'border-amber-100', dot: 'bg-amber-400', badge: 'bg-amber-100 text-amber-600', hoverAccent: 'hover:border-amber-200' },
            'danger': { bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-100', dot: 'bg-red-400', badge: 'bg-red-100 text-red-600', hoverAccent: 'hover:border-red-200' },
        };

        const levelLabels = { 'info': '正常', 'warning': '警告', 'danger': '危险' };

        let html = '';

        sceneGroups.forEach(group => {
            // 应用筛选
            if (activeFilter !== 'all' && group.id !== activeFilter) return;
            const groupScenes = scenes.filter(s => s.group === group.id);
            if (groupScenes.length === 0) return;

            // 分组标题
            html += `
                <div class="scene-group-header flex items-center gap-1.5 px-1 py-1.5 mt-${group.id === 'fire' ? '0' : '3'} mb-1.5">
                    <span class="${group.color}">${group.icon}</span>
                    <span class="text-[11px] font-semibold text-jd-textMuted uppercase tracking-wider">${group.label}</span>
                    <span class="text-[10px] text-jd-textMuted/60 ml-auto">${groupScenes.length}</span>
                </div>
            `;

            // 场景卡片
            groupScenes.forEach((scene, idx) => {
                const isActive = scene.id === currentScene;
                const style = levelStyles[scene.level];

                html += `
                <div 
                    class="scene-card group relative flex items-start gap-2.5 p-2.5 rounded-lg cursor-pointer transition-all duration-200 mb-1.5 ${isActive ? 'scene-card-active ring-1 ring-jd-primary/30 bg-jd-primaryLight' : 'bg-white border border-jd-cardBorder ' + style.hoverAccent + ' hover:shadow-sm'}"
                    onclick="SceneModule.selectScene('${scene.id}')"
                    style="animation: fadeInUp 0.3s ease-out ${idx * 0.04}s both"
                >
                    <!-- 图标 -->
                    <div class="w-8 h-8 rounded-lg ${isActive ? 'bg-jd-primary/10 text-jd-primary' : style.bg + ' ' + style.text} flex items-center justify-center shrink-0 transition-colors">
                        ${scene.icon}
                    </div>
                    <!-- 内容 -->
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-1.5 mb-0.5">
                            <span class="text-[13px] font-medium ${isActive ? 'text-jd-primary' : 'text-jd-text'} truncate">${scene.name}</span>
                            ${scene.packets > 1 ? `<span class="text-[10px] px-1.5 py-px rounded ${style.badge} font-medium">${scene.packets}包</span>` : ''}
                        </div>
                        <div class="text-[11px] text-jd-textMuted truncate mb-1">${scene.desc}</div>
                        <div class="flex items-center gap-1.5">
                            <span class="text-[10px] px-1.5 py-px rounded bg-slate-50 text-slate-400 font-medium">${scene.typeFlag}</span>
                            <span class="text-[10px] text-slate-300">·</span>
                            <span class="text-[10px] text-slate-400 truncate">${scene.component}</span>
                        </div>
                    </div>
                    <!-- 等级指示点 -->
                    <div class="absolute top-2.5 right-2.5 flex items-center gap-1">
                        ${isActive ? `<svg class="w-3.5 h-3.5 text-jd-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>` : `<span class="w-1.5 h-1.5 rounded-full ${style.dot}"></span>`}
                    </div>
                </div>
                `;
            });
        });

        list.innerHTML = html;
    }

    function selectScene(sceneId) {
        currentScene = sceneId;
        const scene = scenes.find(s => s.id === sceneId);
        document.getElementById('breadcrumbScene').textContent = scene.name;
        const label = document.getElementById('currentSceneName');
        label.textContent = scene.name;
        label.className = 'text-xs px-2 py-0.5 rounded-full bg-jd-primaryLight text-jd-primary';

        // 更新侧边栏场景列表选中状态
        updateSceneSidebarSelection(sceneId);

        socket.emit('generate_packet', {scene: sceneId});
        showToast(`已选择: ${scene.name}`, 'info');
    }

    function updateSceneSidebarSelection(sceneId) {
        // 重新渲染整个列表以保持一致性
        renderSceneSidebarList();
    }

    function setupSocketListeners() {
        socket.on('packet_generated', (data) => {
            if (typeof HistoryModule !== 'undefined' && HistoryModule.renderPacketDetail) {
                HistoryModule.renderPacketDetail(data);
            }
            window.currentHex = data.raw_hex;
        });
    }

    function formatHex(hex) {
        return hex.match(/.{1,2}/g).map((b, i) => {
            let color = '#94A3B8';
            if (i < 2) color = '#10B981';
            else if (i >= hex.length/2 - 2) color = '#EF4444';
            else if (i >= 2 && i < 27) color = '#2563EB';
            return `<span style="color: ${color}">${b}</span>`;
        }).join(' ');
    }

    function getCurrentScene() {
        return currentScene;
    }

    let activeFilter = 'all';

    function filterScenes(filter) {
        activeFilter = filter;
        // 更新筛选按钮状态
        document.querySelectorAll('.scene-filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });
        // 更新场景计数徽章
        const filteredCount = filter === 'all' ? scenes.length : scenes.filter(s => s.group === filter).length;
        const badge = document.getElementById('sceneCountBadge');
        if (badge) badge.textContent = `${filteredCount}个场景`;
        renderSceneSidebarList();
    }

    function getSceneName(sceneId) {
        return scenes.find(s => s.id === sceneId)?.name || sceneId;
    }

    return {
        init,
        selectScene,
        getCurrentScene,
        getSceneName,
        formatHex,
        filterScenes
    };
})();
