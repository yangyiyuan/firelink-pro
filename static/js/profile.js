// 厂商配置模块
const ProfileModule = (() => {
    let currentProfile = { key: '', addr_byte_order: 'little', component_addr_byte_order: 'little' };
    let profiles = [];

    async function init() {
        // 加载可用 profiles
        try {
            const resp = await fetch('/api/profiles');
            profiles = await resp.json();
        } catch (e) {
            console.error('加载厂商配置失败:', e);
            profiles = [{ key: '', name: '默认（国标规范）', addr_byte_order: 'little', component_addr_byte_order: 'little' }];
        }

        // 渲染下拉选项
        const select = document.getElementById('profileSelect');
        if (select) {
            select.innerHTML = profiles.map(p =>
                `<option value="${p.key}" ${p.key === currentProfile.key ? 'selected' : ''}>${p.name}</option>`
            ).join('');
        }

        // 加载当前配置
        try {
            const resp = await fetch('/api/profile');
            currentProfile = await resp.json();
            if (select) select.value = currentProfile.key;
        } catch (e) {
            console.error('加载当前厂商配置失败:', e);
        }
    }

    async function onProfileChange(key) {
        try {
            const resp = await fetch('/api/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key }),
            });
            currentProfile = await resp.json();
        } catch (e) {
            console.error('切换厂商配置失败:', e);
        }
    }

    function getAddrByteOrder() {
        return currentProfile.addr_byte_order || 'little';
    }

    function getComponentAddrByteOrder() {
        return currentProfile.component_addr_byte_order || 'little';
    }

    function getCurrentKey() {
        return currentProfile.key || '';
    }

    return { init, onProfileChange, getAddrByteOrder, getComponentAddrByteOrder, getCurrentKey };
})();
