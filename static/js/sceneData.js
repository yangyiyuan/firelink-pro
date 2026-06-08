// 场景公共数据模块 — 集中定义模板分组、标签映射等共享数据
const SceneDataModule = (function() {
    // 模板分组标签（统一来源，消除 scene.js / signalInstance.js 中的不一致）
    const GROUP_MAP = {
        facility: '消防设施状态',
        device: '传输装置状态',
        tool: '快捷工具',
    };

    // 模板分组定义（含图标、颜色，从 scene.js templateGroups 提取）
    const TEMPLATE_GROUPS = [
        { id: 'facility', label: '消防设施状态', subtitle: 'TF 1~8', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z"/></svg>`, color: 'text-red-500' },
        { id: 'device', label: '传输装置状态', subtitle: 'TF 21~28', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>`, color: 'text-blue-500' },
        { id: 'tool', label: '快捷工具', icon: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>`, color: 'text-violet-500' },
    ];

    function getGroupLabel(value) {
        return GROUP_MAP[value] || value || '其他';
    }

    return { GROUP_MAP, TEMPLATE_GROUPS, getGroupLabel };
})();