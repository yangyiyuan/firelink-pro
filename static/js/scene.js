// 信号模板模块
const SceneModule = (function() {
    // 模板分组定义（按协议类型标志分组）
    const templateGroups = [
        { id: 'facility', label: '消防设施状态', subtitle: 'TF 1~8', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z"/></svg>`, color: 'text-red-500' },
        { id: 'device', label: '传输装置状态', subtitle: 'TF 21~28', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>`, color: 'text-blue-500' },
        { id: 'ack', label: '确认应答', subtitle: 'TF 134~136', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`, color: 'text-green-500' },
        { id: 'tool', label: '快捷工具', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>`, color: 'text-violet-500' },
    ];

    const templates = [
        // ── 消防设施状态组 (TF 1~8) ──
        { id: 'system_status', name: '系统状态', desc: '建筑消防设施系统状态', level: 'danger', group: 'facility',
          typeFlag: 'TF=1 系统状态', packets: 1, component: '火灾报警系统',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>` },
        { id: 'component_status', name: '部件状态', desc: '部件运行状态（火警/故障/屏蔽/监管/恢复）', level: 'warning', group: 'facility',
          typeFlag: 'TF=2 部件状态', packets: 1, component: '烟感/温感/手报',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/></svg>` },
        { id: 'analog_value', name: '模拟量值', desc: '部件模拟量值（温度/烟雾/压力）', level: 'warning', group: 'facility',
          typeFlag: 'TF=3 模拟量值', packets: 1, component: '温感/烟感',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>` },
        { id: 'operation_info', name: '操作信息', desc: '消防设施操作信息（启动/反馈）', level: 'info', group: 'facility',
          typeFlag: 'TF=4 操作信息', packets: 1, component: '操作信息位',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>` },
        { id: 'system_version', name: '软件版本', desc: '消防设施软件版本信息', level: 'info', group: 'facility',
          typeFlag: 'TF=5 软件版本', packets: 1, component: '版本号',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/></svg>` },
        { id: 'system_config', name: '系统配置', desc: '消防设施系统配置情况', level: 'info', group: 'facility',
          typeFlag: 'TF=6 系统配置', packets: 1, component: '配置数据',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>` },
        { id: 'system_time', name: '系统时间', desc: '消防设施系统时间', level: 'info', group: 'facility',
          typeFlag: 'TF=8 系统时间', packets: 1, component: '时间标签',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>` },
        // ── 传输装置状态组 (TF 21~28) ──
        { id: 'device_status', name: '装置运行状态', desc: '传输装置运行状态（正常/火警/故障/屏蔽）', level: 'info', group: 'device',
          typeFlag: 'TF=21 装置状态', packets: 1, component: '传输装置',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>` },
        { id: 'device_operation', name: '装置操作信息', desc: '传输装置操作信息', level: 'info', group: 'device',
          typeFlag: 'TF=24 装置操作', packets: 1, component: '操作信息位',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>` },
        { id: 'device_config', name: '装置配置', desc: '传输装置配置情况', level: 'info', group: 'device',
          typeFlag: 'TF=26 装置配置', packets: 1, component: '配置数据',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>` },
        // ── 确认应答组 (TF 134~136) ──
        { id: 'ack_system', name: '系统状态确认', desc: '系统状态确认应答', level: 'info', group: 'ack',
          typeFlag: 'TF=134 系统确认', packets: 1, component: '确认应答',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>` },
        { id: 'ack_component', name: '部件状态确认', desc: '部件状态确认应答', level: 'info', group: 'ack',
          typeFlag: 'TF=135 部件确认', packets: 1, component: '确认应答',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>` },
        { id: 'ack_device', name: '装置状态确认', desc: '装置运行状态恢复确认', level: 'info', group: 'ack',
          typeFlag: 'TF=136 装置确认', packets: 1, component: '确认应答',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>` },
        // ── 快捷工具组 ──
        { id: 'random', name: '随机模板', desc: '随机生成一种信号', level: 'info', group: 'tool',
          typeFlag: '随机', packets: 1, component: '随机',
          icon: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>` },
    ];

    let currentScene = 'component_status';
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

        templateGroups.forEach((group, groupIdx) => {
            // 应用筛选
            if (activeFilter !== 'all' && group.id !== activeFilter) return;
            const groupTemplates = templates.filter(s => s.group === group.id);
            if (groupTemplates.length === 0) return;

            // 分组标题
            html += `
                <div class="scene-group-header flex items-center gap-1.5 px-1 py-1.5 ${groupIdx === 0 ? '' : 'mt-3'} mb-1.5">
                    <span class="${group.color}">${group.icon}</span>
                    <span class="text-[11px] font-semibold text-jd-textMuted uppercase tracking-wider">${group.label}</span>
                    ${group.subtitle ? `<span class="text-[9px] text-jd-textMuted/50 font-mono">${group.subtitle}</span>` : ''}
                    <span class="text-[10px] text-jd-textMuted/60 ml-auto">${groupTemplates.length}</span>
                </div>
            `;

            // 模板卡片
            groupTemplates.forEach((tmpl, idx) => {
                const isActive = tmpl.id === currentScene;
                const style = levelStyles[tmpl.level];

                html += `
                <div 
                    class="scene-card group relative flex items-start gap-2.5 p-2.5 rounded-lg cursor-pointer transition-all duration-200 mb-1.5 ${isActive ? 'scene-card-active ring-1 ring-jd-primary/30 bg-jd-primaryLight' : 'bg-white border border-jd-cardBorder ' + style.hoverAccent + ' hover:shadow-sm'}"
                    onclick="SceneModule.selectScene('${tmpl.id}')"
                    style="animation: fadeInUp 0.3s ease-out ${idx * 0.04}s both"
                >
                    <!-- 图标 -->
                    <div class="w-8 h-8 rounded-lg ${isActive ? 'bg-jd-primary/10 text-jd-primary' : style.bg + ' ' + style.text} flex items-center justify-center shrink-0 transition-colors">
                        ${tmpl.icon}
                    </div>
                    <!-- 内容 -->
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-1.5 mb-0.5">
                            <span class="text-[13px] font-medium ${isActive ? 'text-jd-primary' : 'text-jd-text'} truncate">${tmpl.name}</span>
                            ${tmpl.packets > 1 ? `<span class="text-[10px] px-1.5 py-px rounded ${style.badge} font-medium">${tmpl.packets}包</span>` : ''}
                        </div>
                        <div class="text-[11px] text-jd-textMuted truncate mb-1">${tmpl.desc}</div>
                        <div class="flex items-center gap-1.5">
                            <span class="text-[10px] px-1.5 py-px rounded bg-slate-50 text-slate-400 font-medium">${tmpl.typeFlag}</span>
                            <span class="text-[10px] text-slate-300">·</span>
                            <span class="text-[10px] text-slate-400 truncate">${tmpl.component}</span>
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
        const tmpl = templates.find(s => s.id === sceneId);
        document.getElementById('breadcrumbScene').textContent = tmpl.name;
        const label = document.getElementById('currentSceneName');
        label.textContent = tmpl.name;
        label.className = 'text-xs px-2 py-0.5 rounded-full bg-jd-primaryLight text-jd-primary';

        // 更新侧边栏模板列表选中状态
        updateSceneSidebarSelection(sceneId);

        socket.emit('generate_packet', {scene: sceneId});
        showToast(`已选择: ${tmpl.name}`, 'info');
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
        // 更新模板计数徽章
        const filteredCount = filter === 'all' ? templates.length : templates.filter(s => s.group === filter).length;
        const badge = document.getElementById('sceneCountBadge');
        if (badge) badge.textContent = `${filteredCount}个模板`;
        renderSceneSidebarList();
    }

    function getSceneName(sceneId) {
        return templates.find(s => s.id === sceneId)?.name || sceneId;
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
