const SignalInstanceModule = (function() {
    let socket;
    let instances = [];
    let templates = [];
    let meta = null;
    let selectedInstance = null;
    let editMode = false;
    let editData = null;
    let instancePreview = [];
    let keyword = '';

    function init(socketInstance) {
        socket = socketInstance;
        setupSocketListeners();
    }

    async function loadInitialData() {
        try {
            const [instResp, tplResp, metaResp] = await Promise.all([
                fetch('/api/signal_instances'),
                fetch('/api/scenes'),
                fetch('/api/auto_send/meta'),
            ]);
            instances = await instResp.json();
            templates = await tplResp.json();
            meta = await metaResp.json();
            renderAll();
        } catch (error) {
            console.error(error);
            showToast('信号实例数据加载失败', 'error');
        }
    }

    async function reloadInstances() {
        try {
            const resp = await fetch('/api/signal_instances');
            instances = await resp.json();
            renderAll();
            if (typeof SceneModule !== 'undefined' && SceneModule.loadSidebarInstances) {
                SceneModule.loadSidebarInstances();
            }
        } catch (error) {
            console.error(error);
        }
    }

    async function reloadTemplates() {
        try {
            const resp = await fetch('/api/scenes');
            templates = await resp.json();
            renderInstanceList();
        } catch (error) {
            console.error(error);
        }
    }

    function renderAll() {
        renderInstanceList();
        renderDetailPanel();
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getTemplateById(id) {
        return templates.find(t => t.id === id);
    }

    function getTemplateLabel(id) {
        const tpl = getTemplateById(id);
        return tpl ? tpl.name : (selectedInstance?.templateSnapshot?.name || '未知模板');
    }

    function getGroupLabel(value) {
        const groupMap = { facility: '消防设施状态', device: '传输装置状态', tool: '快捷工具' };
        return groupMap[value] || value || '其他';
    }

    function renderInstanceList() {
        const list = document.getElementById('signalInstanceList');
        if (!list) return;

        const kw = keyword.trim().toLowerCase();
        const filtered = instances.filter(item => {
            if (!kw) return true;
            return `${item.name || ''} ${item.description || ''} ${(item.tags || []).join(' ')}`.toLowerCase().includes(kw);
        });

        if (!filtered.length) {
            list.innerHTML = `<div class="text-center text-jd-textMuted text-sm py-8">${kw ? '未找到匹配实例' : '暂无信号实例'}</div>`;
            return;
        }

        list.innerHTML = filtered.map(inst => {
            const active = selectedInstance?.id === inst.id;
            const tagHtml = (inst.tags || []).map(t =>
                `<span class="text-[10px] px-1.5 py-px rounded bg-slate-100 text-slate-500">${escapeHtml(t)}</span>`
            ).join('');
            return `
                <button type="button" class="auto-template-item w-full text-left rounded-xl border px-3 py-3 transition-colors ${active ? 'border-jd-primary bg-jd-primaryLight/40' : 'border-jd-cardBorder bg-white hover:border-jd-primaryBorder'}" onclick="SignalInstanceModule.selectInstance('${inst.id}')">
                    <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0">
                            <div class="text-sm font-medium ${active ? 'text-jd-primary' : 'text-jd-text'} truncate">${escapeHtml(inst.name || '未命名实例')}</div>
                            <div class="text-xs text-jd-textMuted mt-1 line-clamp-1">${escapeHtml(inst.description || '无描述')}</div>
                        </div>
                        <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 shrink-0">实例</span>
                    </div>
                    <div class="flex items-center gap-2 mt-2 text-[11px] text-jd-textMuted flex-wrap">
                        <span>${escapeHtml(getTemplateLabel(inst.templateId))}</span>
                        <span>·</span>
                        <span>${escapeHtml(inst.deviceParams?.sourceAddr || '')}</span>
                        ${tagHtml ? `<span>·</span>${tagHtml}` : ''}
                        ${inst.useCount ? `<span>·</span><span>已用${inst.useCount}次</span>` : ''}
                    </div>
                </button>
            `;
        }).join('');
    }

    function renderDetailPanel() {
        const panel = document.getElementById('signalInstanceDetail');
        if (!panel) return;

        if (editMode) {
            renderEditForm();
            return;
        }

        if (!selectedInstance) {
            panel.innerHTML = `
                <div class="text-center text-jd-textMuted text-sm py-10">
                    选择或创建一个信号实例
                </div>
            `;
            return;
        }

        const inst = selectedInstance;
        const tpl = getTemplateById(inst.templateId);
        const tplMissing = !tpl && !!inst.templateId;
        const tagHtml = (inst.tags || []).map(t =>
            `<span class="text-[10px] px-1.5 py-px rounded bg-slate-100 text-slate-500">${escapeHtml(t)}</span>`
        ).join(' ');

        panel.innerHTML = `
            <div class="space-y-4">
                <div class="flex items-center justify-between">
                    <h4 class="text-sm font-semibold text-jd-text">${escapeHtml(inst.name)}</h4>
                    <div class="flex items-center gap-2">
                        <button class="btn-secondary px-2.5 py-1 rounded-md text-xs" onclick="SignalInstanceModule.startEdit()">编辑</button>
                        <button class="btn-secondary px-2.5 py-1 rounded-md text-xs" onclick="SignalInstanceModule.duplicateInstance('${inst.id}')">复制</button>
                        <button class="btn-secondary px-2.5 py-1 rounded-md text-xs text-red-500 hover:text-red-600" onclick="SignalInstanceModule.confirmDelete('${inst.id}')">删除</button>
                    </div>
                </div>
                ${inst.description ? `<p class="text-xs text-jd-textMuted">${escapeHtml(inst.description)}</p>` : ''}
                ${tplMissing ? `<div class="text-xs px-2.5 py-2 rounded-lg bg-amber-50 text-amber-700 border border-amber-200">⚠ 关联模板已不存在，请重新绑定或编辑此实例</div>` : ''}
                <div class="space-y-2">
                    <div class="flex items-center gap-2 text-xs">
                        <span class="text-jd-textMuted">关联模板</span>
                        <span class="text-jd-text font-medium">${escapeHtml(getTemplateLabel(inst.templateId))}</span>
                        ${tpl ? `<span class="text-[10px] px-1.5 py-px rounded bg-jd-primaryLight text-jd-primary">${escapeHtml(getGroupLabel(tpl.group))}</span>` : ''}
                    </div>
                    ${tagHtml ? `<div class="flex items-center gap-1.5 text-xs flex-wrap"><span class="text-jd-textMuted">标签</span>${tagHtml}</div>` : ''}
                </div>
                <div class="border-t border-jd-cardBorder pt-3">
                    <h5 class="text-xs font-semibold text-jd-textSecondary mb-2">设备参数</h5>
                    <div class="grid grid-cols-2 gap-2">
                        ${renderDeviceParamDisplay('源地址', inst.deviceParams?.sourceAddr)}
                        ${renderDeviceParamDisplay('目标地址', inst.deviceParams?.destAddr)}
                        ${renderDeviceParamDisplay('系统类型', inst.deviceParams?.systemType, meta?.systemTypes)}
                        ${renderDeviceParamDisplay('系统地址', inst.deviceParams?.systemAddr)}
                        ${inst.deviceParams?.componentType != null ? renderDeviceParamDisplay('部件类型', inst.deviceParams.componentType, meta?.componentTypes) : ''}
                        ${inst.deviceParams?.zoneNo != null ? renderDeviceParamDisplay('区号', inst.deviceParams.zoneNo) : ''}
                        ${inst.deviceParams?.bitNo != null ? renderDeviceParamDisplay('位号', inst.deviceParams.bitNo) : ''}
                        ${(() => {
                            const statusInfo = getStatusFieldForTemplate(inst.templateId);
                            if (!statusInfo) return '';
                            const val = inst.deviceParams?.[statusInfo.field];
                            if (val == null || val === '') return '';
                            const presets = meta?.statusPresets?.[statusInfo.presetKey] || [];
                            const found = presets.find(item => Number(item.value) === Number(val));
                            return renderDeviceParamDisplay(statusInfo.label, found ? `${found.label} (${val})` : String(val));
                        })()}
                    </div>
                </div>
                <div class="flex items-center gap-2 pt-2">
                    <button class="btn-primary px-4 py-2 rounded-lg text-xs font-medium" onclick="SignalInstanceModule.previewInstance()" ${tplMissing ? 'disabled' : ''}>预览报文</button>
                    <button class="btn-success px-4 py-2 rounded-lg text-xs font-medium" onclick="SignalInstanceModule.startSend()" ${tplMissing ? 'disabled' : ''}>发送</button>
                </div>
                <div id="instancePreviewArea"></div>
            </div>
        `;
    }

    function getStatusFieldForTemplate(templateId) {
        const map = {
            'component_status': { field: 'componentStatus', label: '部件状态', presetKey: 'component_status' },
            'system_status': { field: 'systemStatus', label: '系统状态', presetKey: 'system_status' },
            'device_status': { field: 'statusByte', label: '装置状态', presetKey: 'device_status' },
        };
        return map[templateId] || null;
    }

    function renderStatusSelect(templateId, currentValue) {
        const statusInfo = getStatusFieldForTemplate(templateId);
        if (!statusInfo) return '';
        const presets = meta?.statusPresets?.[statusInfo.presetKey] || [];
        return `
            <div>
                <label class="block text-xs text-jd-textSecondary mb-1">${statusInfo.label}</label>
                <select class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instStatusInput">
                    <option value="">不覆盖</option>
                    ${presets.map(item => `<option value="${item.value}" ${Number(item.value) === Number(currentValue) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('')}
                </select>
            </div>
        `;
    }

    function renderDeviceParamDisplay(label, value, enumList) {
        if (value == null || value === '') return '';
        let displayValue = value;
        if (enumList) {
            const found = enumList.find(item => Number(item.value) === Number(value));
            if (found) displayValue = found.label;
        }
        return `
            <div class="bg-jd-content rounded-lg px-3 py-2">
                <div class="text-[11px] text-jd-textMuted">${label}</div>
                <div class="text-xs font-medium text-jd-text mt-0.5 font-mono">${escapeHtml(String(displayValue))}</div>
            </div>
        `;
    }

    function renderEditForm() {
        const panel = document.getElementById('signalInstanceDetail');
        if (!panel) return;

        const isNew = !editData?.id;
        const d = editData || {};
        const dp = d.deviceParams || {};
        const tplOptions = templates.filter(t => t.group !== 'tool').map(t =>
            `<option value="${t.id}" ${t.id === d.templateId ? 'selected' : ''}>${escapeHtml(t.name)} (${escapeHtml(getGroupLabel(t.group))})</option>`
        ).join('');
        const statusInfo = getStatusFieldForTemplate(d.templateId);
        let statusValue = '';
        if (statusInfo) {
            statusValue = dp[statusInfo.field] ?? '';
        }

        panel.innerHTML = `
            <div class="space-y-3">
                <h4 class="text-sm font-semibold text-jd-text">${isNew ? '创建信号实例' : '编辑信号实例'}</h4>
                <div class="space-y-2">
                    <div>
                        <label class="block text-xs text-jd-textSecondary mb-1">实例名称 <span class="text-red-400">*</span></label>
                        <input type="text" class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instNameInput" value="${escapeHtml(d.name || '')}" placeholder="例如：1号楼传输装置-单点报警" maxlength="80">
                    </div>
                    <div>
                        <label class="block text-xs text-jd-textSecondary mb-1">关联模板 <span class="text-red-400">*</span></label>
                        <select class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instTemplateInput" onchange="SignalInstanceModule.onTemplateChange(this.value)">${tplOptions}</select>
                    </div>
                    <div>
                        <label class="block text-xs text-jd-textSecondary mb-1">描述</label>
                        <input type="text" class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instDescInput" value="${escapeHtml(d.description || '')}" placeholder="可选描述" maxlength="300">
                    </div>
                    <div>
                        <label class="block text-xs text-jd-textSecondary mb-1">标签（逗号分隔）</label>
                        <input type="text" class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instTagsInput" value="${escapeHtml((d.tags || []).join(','))}" placeholder="例如：A厂,1号楼" maxlength="100">
                    </div>
                </div>
                <div class="border-t border-jd-cardBorder pt-2">
                    <h5 class="text-xs font-semibold text-jd-textSecondary mb-1.5">设备参数 <span class="text-red-400">*</span></h5>
                    <div class="grid grid-cols-2 gap-2">
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1">源地址 <span class="text-red-400">*</span></label>
                            <input type="text" class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white font-mono" id="instSourceAddrInput" value="${escapeHtml(dp.sourceAddr || '0x000000000001')}" placeholder="0x...">
                        </div>
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1">目标地址 <span class="text-red-400">*</span></label>
                            <input type="text" class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white font-mono" id="instDestAddrInput" value="${escapeHtml(dp.destAddr || '0x000000000002')}" placeholder="0x...">
                        </div>
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1">系统类型</label>
                            <select class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instSystemTypeInput" onchange="SignalInstanceModule.onSystemTypeChange(this.value)">
                                ${(meta?.systemTypes || []).map(item => `<option value="${item.value}" ${Number(item.value) === Number(dp.systemType) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('')}
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1">系统地址</label>
                            <input type="number" min="0" class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instSystemAddrInput" value="${dp.systemAddr ?? 1}">
                        </div>
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1">部件类型</label>
                            <select class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instComponentTypeInput">
                                <option value="">不覆盖</option>
                                ${(getFilteredComponentTypes(dp.systemType)).map(item => `<option value="${item.value}" ${Number(item.value) === Number(dp.componentType) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('')}
                            </select>
                        </div>
                        <div id="instStatusContainer">${renderStatusSelect(d.templateId, statusValue)}</div>
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1">区号</label>
                            <input type="number" min="0" class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instZoneNoInput" value="${dp.zoneNo ?? ''}" placeholder="不覆盖">
                        </div>
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1">位号</label>
                            <input type="number" min="0" class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" id="instBitNoInput" value="${dp.bitNo ?? ''}" placeholder="不覆盖">
                        </div>
                    </div>
                </div>
                <div class="flex items-center gap-2 pt-1">
                    <button class="btn-primary px-4 py-2 rounded-lg text-xs font-medium" onclick="SignalInstanceModule.saveEdit()">${isNew ? '创建实例' : '保存修改'}</button>
                    <button class="btn-secondary px-4 py-2 rounded-lg text-xs" onclick="SignalInstanceModule.cancelEdit()">取消</button>
                </div>
            </div>
        `;

        if (typeof CustomSelect !== 'undefined') {
            panel.querySelectorAll('select.jd-input.py-2').forEach(sel => {
                const inst = CustomSelect.init(sel);
                if (inst) CustomSelect.refresh(inst);
            });
        }
    }

    function selectInstance(instanceId) {
        const inst = instances.find(i => i.id === instanceId);
        if (!inst) return;
        selectedInstance = JSON.parse(JSON.stringify(inst));
        editMode = false;
        editData = null;
        instancePreview = [];
        renderAll();
    }

    async function startCreate() {
        if (!templates.length || !meta) {
            await loadInitialData();
        }
        editData = {
            name: '',
            templateId: templates[0]?.id || '',
            description: '',
            tags: [],
            deviceParams: {
                sourceAddr: '0x000000000001',
                destAddr: '0x000000000002',
                systemType: 1,
                systemAddr: 1,
            },
        };
        editMode = true;
        selectedInstance = null;
        instancePreview = [];
        renderAll();
    }

    async function startCreateFromTemplate(templateId) {
        if (!templates.length || !meta) {
            await loadInitialData();
        }
        const tpl = getTemplateById(templateId);
        editData = {
            name: (tpl?.name || '') + ' - 实例',
            templateId: templateId,
            description: tpl?.desc || '',
            tags: [],
            deviceParams: {
                sourceAddr: '0x000000000001',
                destAddr: '0x000000000002',
                systemType: 1,
                systemAddr: 1,
            },
        };
        editMode = true;
        selectedInstance = null;
        instancePreview = [];
        renderAll();
    }

    async function startEdit() {
        if (!selectedInstance) return;
        if (!templates.length || !meta) {
            await loadInitialData();
        }
        editData = JSON.parse(JSON.stringify(selectedInstance));
        editMode = true;
        renderDetailPanel();
    }

    function cancelEdit() {
        editMode = false;
        editData = null;
        renderDetailPanel();
    }

    function getFilteredComponentTypes(systemType) {
        const allTypes = meta?.componentTypes || [];
        const map = meta?.systemTypeComponentMap;
        if (!map || systemType === undefined || systemType === '') return allTypes;
        const allowed = map[String(systemType)];
        if (!allowed) return allTypes;
        const allowedSet = new Set(allowed.map(v => Number(v)));
        return allTypes.filter(item => allowedSet.has(Number(item.value)));
    }

    function _refreshCustomSelect(selectEl) {
        if (typeof CustomSelect === 'undefined' || !selectEl) return;
        const wrapper = selectEl.closest('.jd-select-wrapper');
        if (wrapper) {
            const inst = CustomSelect.init(selectEl);
            if (inst) CustomSelect.refresh(inst);
        } else {
            const inst = CustomSelect.init(selectEl);
            if (inst) CustomSelect.refresh(inst);
        }
    }

    function onSystemTypeChange(systemType) {
        if (!editData) return;
        const dp = editData.deviceParams || {};
        dp.systemType = Number(systemType);
        const filtered = getFilteredComponentTypes(systemType);
        const currentVal = Number(dp.componentType);
        if (currentVal && !filtered.some(item => Number(item.value) === currentVal)) {
            dp.componentType = filtered[0]?.value ?? '';
        }
        const select = document.getElementById('instComponentTypeInput');
        if (select) {
            const selectedVal = dp.componentType ?? '';
            select.innerHTML = `<option value="">不覆盖</option>` +
                filtered.map(item => `<option value="${item.value}" ${Number(item.value) === Number(selectedVal) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('');
            _refreshCustomSelect(select);
        }
    }

    function onTemplateChange(templateId) {
        if (!editData) return;
        editData.templateId = templateId;
        if (editData.deviceParams) {
            delete editData.deviceParams.componentStatus;
            delete editData.deviceParams.systemStatus;
            delete editData.deviceParams.statusByte;
        }
        const statusContainer = document.getElementById('instStatusContainer');
        if (statusContainer) {
            statusContainer.innerHTML = renderStatusSelect(templateId, '') || '';
            const statusSelect = document.getElementById('instStatusInput');
            if (statusSelect) _refreshCustomSelect(statusSelect);
        }
    }

    function collectEditData() {
        const name = document.getElementById('instNameInput')?.value?.trim() || '';
        const templateId = document.getElementById('instTemplateInput')?.value || '';
        const description = document.getElementById('instDescInput')?.value?.trim() || '';
        const tagsRaw = document.getElementById('instTagsInput')?.value?.trim() || '';
        const tags = tagsRaw.split(/[,，]/).map(t => t.trim()).filter(Boolean);
        const sourceAddr = document.getElementById('instSourceAddrInput')?.value?.trim() || '';
        const destAddr = document.getElementById('instDestAddrInput')?.value?.trim() || '';
        const systemType = document.getElementById('instSystemTypeInput')?.value;
        const systemAddr = document.getElementById('instSystemAddrInput')?.value;
        const componentType = document.getElementById('instComponentTypeInput')?.value;
        const zoneNo = document.getElementById('instZoneNoInput')?.value;
        const bitNo = document.getElementById('instBitNoInput')?.value;

        const deviceParams = {
            sourceAddr,
            destAddr,
            systemType: systemType != null ? Number(systemType) : undefined,
            systemAddr: systemAddr !== '' ? Number(systemAddr) : undefined,
        };
        if (componentType !== '') deviceParams.componentType = Number(componentType);
        if (zoneNo !== '') deviceParams.zoneNo = Number(zoneNo);
        if (bitNo !== '') deviceParams.bitNo = Number(bitNo);

        const statusInfo = getStatusFieldForTemplate(templateId);
        if (statusInfo) {
            const statusVal = document.getElementById('instStatusInput')?.value;
            if (statusVal !== '' && statusVal != null) {
                deviceParams[statusInfo.field] = Number(statusVal);
            }
        }

        return { name, templateId, description, tags, deviceParams };
    }

    async function saveEdit() {
        const data = collectEditData();
        if (!data.name) { showToast('请输入实例名称', 'error'); return; }
        if (!data.templateId) { showToast('请选择关联模板', 'error'); return; }
        if (!data.deviceParams.sourceAddr) { showToast('请输入源地址', 'error'); return; }
        if (!data.deviceParams.destAddr) { showToast('请输入目标地址', 'error'); return; }

        const isNew = !editData?.id;
        const url = isNew ? '/api/signal_instances' : `/api/signal_instances/${editData.id}`;
        const method = isNew ? 'POST' : 'PUT';

        try {
            const resp = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            const result = await resp.json();
            if (!resp.ok || result.error) {
                showToast(result.error || '保存失败', 'error');
                return;
            }
            editMode = false;
            editData = null;
            await reloadInstances();
            selectedInstance = instances.find(i => i.id === result.id) || null;
            renderAll();
            showToast(isNew ? '实例已创建' : '实例已更新', 'success');
        } catch (error) {
            console.error(error);
            showToast('保存请求失败', 'error');
        }
    }

    async function duplicateInstance(instanceId) {
        const inst = instances.find(i => i.id === instanceId);
        if (!inst) return;
        editData = {
            name: inst.name + ' 副本',
            templateId: inst.templateId,
            description: inst.description,
            tags: [...(inst.tags || [])],
            deviceParams: JSON.parse(JSON.stringify(inst.deviceParams || {})),
        };
        editMode = true;
        selectedInstance = null;
        instancePreview = [];
        renderAll();
    }

    function confirmDelete(instanceId) {
        if (!confirm('确定要删除此信号实例吗？')) return;
        doDelete(instanceId);
    }

    async function doDelete(instanceId) {
        try {
            const resp = await fetch(`/api/signal_instances/${instanceId}`, { method: 'DELETE' });
            const result = await resp.json();
            if (!resp.ok || result.error) {
                showToast(result.error || '删除失败', 'error');
                return;
            }
            if (selectedInstance?.id === instanceId) {
                selectedInstance = null;
                instancePreview = [];
            }
            await reloadInstances();
            showToast('实例已删除', 'success');
        } catch (error) {
            console.error(error);
            showToast('删除请求失败', 'error');
        }
    }

    async function previewInstance() {
        if (!selectedInstance) return;
        try {
            const resp = await fetch(`/api/signal_instances/${selectedInstance.id}/preview`, { method: 'POST' });
            const result = await resp.json();
            if (!result.success) {
                showToast(result.error || '预览失败', 'error');
                return;
            }
            instancePreview = result.steps || [];
            renderPreviewArea();
            if (instancePreview[0]?.packetView) {
                if (typeof HistoryModule !== 'undefined' && HistoryModule.renderPacketDetail) {
                    HistoryModule.renderPacketDetail(instancePreview[0].packetView);
                }
                window.currentHex = instancePreview[0].packetHex;
            }
            showToast(`预览成功，共 ${instancePreview.length} 步`, 'success');
        } catch (error) {
            console.error(error);
            showToast('预览请求失败', 'error');
        }
    }

    function renderPreviewArea() {
        const area = document.getElementById('instancePreviewArea');
        if (!area) return;
        if (!instancePreview.length) {
            area.innerHTML = '';
            return;
        }
        area.innerHTML = instancePreview.map((step, index) => `
            <div class="mt-3 rounded-xl border border-jd-cardBorder bg-white p-3 space-y-2">
                <div class="flex items-center gap-2">
                    <span class="text-[11px] px-2 py-0.5 rounded-full bg-jd-primaryLight text-jd-primary">步骤 ${index + 1}</span>
                    <span class="text-sm font-medium text-jd-text">${escapeHtml(step.name)}</span>
                </div>
                <div class="grid grid-cols-3 gap-2">
                    <div class="bg-jd-content rounded-lg px-2.5 py-1.5">
                        <div class="text-[10px] text-jd-textMuted">类型标志</div>
                        <div class="text-xs font-medium text-jd-text mt-0.5">${escapeHtml(step.packetView?.type_flag_name || `TF=${step.typeFlag}`)}</div>
                    </div>
                    <div class="bg-jd-content rounded-lg px-2.5 py-1.5">
                        <div class="text-[10px] text-jd-textMuted">包长度</div>
                        <div class="text-xs font-mono font-semibold text-jd-text mt-0.5">${step.packetLength}B</div>
                    </div>
                    <div class="bg-jd-content rounded-lg px-2.5 py-1.5">
                        <div class="text-[10px] text-jd-textMuted">对象数</div>
                        <div class="text-xs font-mono font-semibold text-jd-text mt-0.5">${step.objectCount}</div>
                    </div>
                </div>
                <div>
                    <div class="text-[10px] text-jd-textMuted mb-1">HEX</div>
                    <div class="raw-hex-box hex-display text-[11px]">${SceneModule.formatHex(step.packetHex)}</div>
                </div>
            </div>
        `).join('');
    }

    async function startSend() {
        if (!selectedInstance) return;
        if (typeof NetworkModule !== 'undefined' && !NetworkModule.isTargetConnected()) {
            showToast('请先连接目标服务器', 'error');
            return;
        }
        const network = typeof NetworkModule !== 'undefined' ? NetworkModule.getNetworkConfig() : {};
        socket.emit('start_signal_instance', {
            instanceId: selectedInstance.id,
            network,
        });
    }

    function setupSocketListeners() {
        socket.on('signal_instance_error', (data) => {
            showToast(data.message || '实例执行失败', 'error');
        });
    }

    function filterInstances(kw) {
        keyword = kw || '';
        renderInstanceList();
    }

    function getSelectedInstance() {
        return selectedInstance;
    }

    return {
        init,
        loadInitialData,
        selectInstance,
        startCreate,
        startCreateFromTemplate,
        startEdit,
        cancelEdit,
        onTemplateChange,
        onSystemTypeChange,
        saveEdit,
        duplicateInstance,
        confirmDelete,
        previewInstance,
        startSend,
        filterInstances,
        getSelectedInstance,
        reloadInstances,
        reloadTemplates,
    };
})();
