// 自动发送场景编排模块
const AutoSendModule = (function() {
    let socket;
    let meta = null;
    let templates = [];
    let templateKeyword = '';
    let currentScene = null;
    let previewSteps = [];
    let autoSendRunning = false;

    function isSystemTemplate() {
        return currentScene?.source === 'system';
    }


    // 默认分类（meta加载后由后端覆盖）
    let categoryOptions = [
        { value: 'fire', label: '火警报警', desc: '类型标志2·部件状态火警' },
        { value: 'fault', label: '故障报警', desc: '类型标志2·部件状态故障' },
        { value: 'restore', label: '状态恢复', desc: '类型标志135·部件状态恢复' },
        { value: 'linkage', label: '联动控制', desc: '类型标志2·启动/反馈' },
        { value: 'supervise', label: '监管报警', desc: '类型标志2·部件状态监管' },
        { value: 'analog', label: '模拟量监控', desc: '类型标志3·温度/烟雾/压力' },
        { value: 'device', label: '传输装置', desc: '类型标志21·装置运行状态' },
        { value: 'shield', label: '屏蔽管理', desc: '类型标志2·部件状态屏蔽' },
        { value: 'sequence', label: '序列场景', desc: '多步骤时序组合' },
        { value: 'custom', label: '自定义', desc: '用户自定义场景' },
    ];

    // 分类→协议默认值映射（meta加载后由后端覆盖）
    let categoryDefaults = {
        'fire':     { typeFlag: 2, command: 2, objectType: 'component_status' },
        'fault':    { typeFlag: 2, command: 2, objectType: 'component_status' },
        'restore':  { typeFlag: 135, command: 2, objectType: 'component_status' },
        'linkage':  { typeFlag: 2, command: 2, objectType: 'component_status' },
        'supervise': { typeFlag: 2, command: 2, objectType: 'component_status' },
        'analog':   { typeFlag: 3, command: 2, objectType: 'analog_value' },
        'device':   { typeFlag: 21, command: 2, objectType: 'device_status' },
        'shield':   { typeFlag: 2, command: 2, objectType: 'component_status' },
    };

    function getCategoryLabel(value) {
        return categoryOptions.find(item => item.value === value)?.label || value;
    }

    function syncCategorySelect() {
        const select = document.getElementById('autoSceneCategoryInput');
        if (!select) return;
        const currentVal = select.value;
        select.innerHTML = categoryOptions.map(opt =>
            `<option value="${opt.value}">${opt.label}</option>`
        ).join('');
        if (categoryOptions.some(item => item.value === currentVal)) {
            select.value = currentVal;
        }
    }

    const numericObjectFields = new Set([
        'systemType',
        'systemAddr',
        'componentType',
        'bitNo',
        'zoneNo',
        'componentStatus',
        'systemStatus',
        'analogType',
        'analogValue',
        'statusByte'
    ]);

    function init(socketInstance) {
        socket = socketInstance;
        setupSocketListeners();
        loadInitialData();
    }

    async function loadInitialData() {
        try {
            const [metaResp, templateResp] = await Promise.all([
                fetch('/api/auto_send/meta'),
                fetch('/api/auto_send/templates')
            ]);
            meta = await metaResp.json();
            templates = await templateResp.json();
            // 从后端meta加载分类选项
            if (meta?.categories?.length) {
                categoryOptions = meta.categories;
                syncCategorySelect();
            }
            if (meta?.categoryDefaults) {
                categoryDefaults = meta.categoryDefaults;
            }
            currentScene = cloneScene(templates[0] || meta.defaultScene || createFallbackScene());
            renderAll();
        } catch (error) {
            console.error(error);
            showToast('自动发送配置加载失败', 'error');
        }
    }

    function refreshPageState() {
        renderAll();
    }



    function createFallbackScene() {
        return {
            id: '',
            name: '未命名场景',
            category: 'custom',
            description: '',
            source: 'draft',
            version: 1,
            loop: true,
            steps: [createStep()]
        };
    }

    function generateId(prefix) {
        return `${prefix}_${Math.random().toString(16).slice(2, 10)}`;
    }

    function cloneScene(scene) {
        const value = JSON.parse(JSON.stringify(scene || createFallbackScene()));
        value.steps = (value.steps || []).map(step => ({
            ...step,
            id: step.id || generateId('step'),
            objects: (step.objects || []).map(obj => ({
                ...obj,
                id: obj.id || generateId('obj')
            }))
        }));
        return value;
    }

    function createObject(objectType = 'component_status') {
        const fields = objectType === 'system_status'
            ? { systemType: 1, systemAddr: 1, systemStatus: 0, occurredAtMode: 'now', occurredAt: '' }
            : objectType === 'analog_value'
                ? { systemType: 1, systemAddr: 1, componentType: 31, bitNo: 1, zoneNo: 1, analogType: 3, analogValue: 850, occurredAtMode: 'now', occurredAt: '' }
                : objectType === 'device_status'
                    ? { statusByte: 0, occurredAtMode: 'now', occurredAt: '' }
                    : { systemType: 1, systemAddr: 1, componentType: 42, bitNo: 1, zoneNo: 1, componentStatus: 1, description: '', occurredAtMode: 'now', occurredAt: '' };
        return {
            id: generateId('obj'),
            objectType,
            fields
        };
    }

    function createStep(typeFlag = null) {
        // 如果当前分类有默认推导值，使用推导的 typeFlag
        const defaults = categoryDefaults[currentScene?.category];
        const effectiveTypeFlag = typeFlag ?? (defaults?.typeFlag ?? 2);
        const effectiveCommand = defaults?.command ?? 2;
        const primaryObjectType = getAllowedObjectTypes(effectiveTypeFlag)[0] || 'component_status';
        return {
            id: generateId('step'),
            name: `步骤${(currentScene?.steps?.length || 0) + 1}`,
            delayAfterSec: 5,
            packetHeader: {
                sourceAddr: '0x000000000001',
                destAddr: '0x000000000002',
                command: effectiveCommand,
                typeFlag: effectiveTypeFlag
            },
            objects: [createObject(primaryObjectType)]
        };
    }

    function getAllowedObjectTypes(typeFlag) {
        return meta?.compatibility?.[String(typeFlag)] || meta?.compatibility?.[typeFlag] || ['component_status'];
    }

    function getObjectTypeLabel(objectType) {
        return meta?.objectTypes?.find(item => item.value === objectType)?.label || objectType;
    }

    function getTypeFlagLabel(typeFlag) {
        return meta?.typeFlags?.find(item => Number(item.value) === Number(typeFlag))?.label || `类型${typeFlag}`;
    }

    function getCommandLabel(command) {
        return meta?.commands?.find(item => Number(item.value) === Number(command))?.label || `命令${command}`;
    }

    function syncSceneHeaderInputs() {
        const locked = isSystemTemplate();
        const nameEl = document.getElementById('autoSceneNameInput');
        const categoryEl = document.getElementById('autoSceneCategoryInput');
        const loopEl = document.getElementById('autoSceneLoopInput');
        const descEl = document.getElementById('autoSceneDescriptionInput');
        if (nameEl) { nameEl.value = currentScene?.name || ''; nameEl.disabled = locked; }
        if (categoryEl) {
            const val = currentScene?.category || 'custom';
            categoryEl.value = categoryOptions.some(item => item.value === val) ? val : 'custom';
            categoryEl.disabled = locked;
        }
        if (loopEl) { loopEl.checked = !!currentScene?.loop; loopEl.disabled = locked; }
        if (descEl) { descEl.value = currentScene?.description || ''; descEl.disabled = locked; }
    }

    function renderAll() {
        renderToolbarState();
        renderTemplateList();
        syncSceneHeaderInputs();
        renderSteps();
        renderPreview();
        
    }

    function renderToolbarState() {
        const summary = document.getElementById('autoSceneSummary');
        const status = document.getElementById('autoRunStatus');
        const btn = document.getElementById('btnAutoSend');
        const btnText = document.getElementById('btnAutoSendText');

        if (summary && summary.tagName === 'SELECT') {
            const prevValue = summary.value;
            summary.innerHTML = templates.map(t =>
                `<option value="${t.id}"${t.id === currentScene?.id ? ' selected' : ''}>${t.name || '未命名场景'}</option>`
            ).join('');
            if (currentScene?.id) summary.value = currentScene.id;
            else if (prevValue) summary.value = prevValue;
            // 首次初始化 change 事件
            if (!summary._autoSceneBound) {
                summary._autoSceneBound = true;
                summary.addEventListener('change', (e) => {
                    selectTemplate(e.target.value);
                });
            }
            if (typeof CustomSelect !== 'undefined') {
                const inst = CustomSelect.init(summary, { size: 'sm' });
                if (inst) CustomSelect.refresh(inst);
            }
        }

        if (status) {
            status.className = autoSendRunning
                ? 'text-[11px] px-2 py-1 rounded-full bg-red-50 text-red-600'
                : 'text-[11px] px-2 py-1 rounded-full bg-slate-100 text-jd-textMuted';
            status.textContent = autoSendRunning ? '运行中' : '空闲';
        }

        if (btn && btnText) {
            if (autoSendRunning) {
                btn.classList.remove('btn-success');
                btn.classList.add('btn-danger');
                btnText.textContent = '停止';
            } else {
                btn.classList.remove('btn-danger');
                btn.classList.add('btn-success');
                btnText.textContent = '开始';
            }
        }

        // 系统模板时禁用保存模板和新增步骤按钮
        const locked = isSystemTemplate();
        const btnSave = document.getElementById('btnSaveTemplate');
        const btnAddStep = document.getElementById('btnAddStep');
        if (btnSave) btnSave.disabled = locked;
        if (btnAddStep) btnAddStep.disabled = locked;
    }


    function renderTemplateList() {
        const list = document.getElementById('autoTemplateList');
        if (!list) return;

        const keyword = templateKeyword.trim().toLowerCase();
        const filtered = templates.filter(item => {
            if (!keyword) return true;
            return `${item.name || ''} ${item.description || ''}`.toLowerCase().includes(keyword);
        });

        if (!filtered.length) {
            list.innerHTML = '<div class="text-center text-jd-textMuted text-sm py-8">未找到匹配模板</div>';
            return;
        }

        list.innerHTML = filtered.map(template => {
            const active = currentScene?.id && template.id === currentScene.id;
            const sourceClass = template.source === 'system'
                ? 'bg-jd-primaryLight text-jd-primary'
                : 'bg-emerald-50 text-emerald-700';
            return `
                <button type="button" class="auto-template-item w-full text-left rounded-xl border px-3 py-3 transition-colors ${active ? 'border-jd-primary bg-jd-primaryLight/40' : 'border-jd-cardBorder bg-white hover:border-jd-primaryBorder'}" onclick="AutoSendModule.selectTemplate('${template.id}')">
                    <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0">
                            <div class="text-sm font-medium ${active ? 'text-jd-primary' : 'text-jd-text'} truncate">${escapeHtml(template.name || '未命名模板')}</div>
                            <div class="text-xs text-jd-textMuted mt-1 line-clamp-2">${escapeHtml(template.description || '无描述')}</div>
                        </div>
                        <span class="text-[10px] px-1.5 py-0.5 rounded-full ${sourceClass} shrink-0">${template.source === 'system' ? '系统' : '本地'}</span>
                    </div>
                    <div class="flex items-center gap-2 mt-2 text-[11px] text-jd-textMuted">
                        <span>${escapeHtml(getCategoryLabel(template.category || 'custom'))}</span>
                        <span>·</span>
                        <span>${(template.steps || []).length} 步</span>
                        <span>·</span>
                        <span>${template.loop ? '循环' : '单轮'}</span>
                    </div>
                </button>
            `;
        }).join('');
    }

    function renderSteps() {
        const container = document.getElementById('autoSceneSteps');
        if (!container) return;
        const steps = currentScene?.steps || [];
        if (!steps.length) {
            container.innerHTML = '<div class="text-center text-jd-textMuted text-sm py-8">暂无步骤</div>';
            return;
        }
        container.innerHTML = steps.map((step, index) => renderStepCard(step, index)).join('');
        initFlatpickrInstances();
    }

    function initFlatpickrInstances() {
        document.querySelectorAll('.fp-datetime').forEach(el => {
            const stepIndex = parseInt(el.id.split('-')[1]);
            const objectIndex = parseInt(el.id.split('-')[2]);
            const isDisabled = el.hasAttribute('disabled');
            const savedValue = el.dataset.value;
            // 销毁旧实例
            if (el._flatpickr) el._flatpickr.destroy();
            if (typeof flatpickr === 'undefined') return;
            el._flatpickr = flatpickr(el, {
                locale: 'zh',
                enableTime: true,
                dateFormat: 'Y-m-d H:i:S',
                time_24hr: true,
                allowInput: false,
                defaultDate: savedValue || null,
                disabled: isDisabled,
                onChange: function(selectedDates, dateStr) {
                    if (!isDisabled) {
                        AutoSendModule.updateObjectField(stepIndex, objectIndex, 'occurredAt', dateStr);
                    }
                },
            });
        });
    }

    function isDefaultStepName(name) {
        if (!name) return true;
        return /^步骤\d+$/.test(name);
    }

    function renderStepCard(step, stepIndex) {
        const autoDerived = isAutoDerivedCategory();
        const locked = isSystemTemplate();
        const dis = locked ? ' disabled' : '';
        const disBg = locked ? 'bg-jd-content text-jd-text cursor-default' : 'bg-white';
        const typeFlagOptions = (meta?.typeFlags || []).map(item => (
            `<option value="${item.value}" ${Number(item.value) === Number(step.packetHeader.typeFlag) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`
        )).join('');
        const commandOptions = (meta?.commands || []).map(item => (
            `<option value="${item.value}" ${Number(item.value) === Number(step.packetHeader.command) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`
        )).join('');
        const typeFlagBadge = escapeHtml(getTypeFlagLabel(step.packetHeader.typeFlag));
        const commandBadge = escapeHtml(getCommandLabel(step.packetHeader.command));
        // 自动推导时：命令字和类型标志用只读badge展示；否则显示下拉框；系统模板时全部只读badge
        const commandField = (autoDerived || locked)
            ? `<div><label class="block text-xs text-jd-textSecondary mb-1.5">命令字</label><div class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-jd-content text-jd-text">${commandBadge}</div></div>`
            : `<div><label class="block text-xs text-jd-textSecondary mb-1.5">命令字</label><select class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" onchange="AutoSendModule.updateStepField(${stepIndex}, 'command', this.value)">${commandOptions}</select></div>`;
        const typeFlagField = (autoDerived || locked)
            ? `<div><label class="block text-xs text-jd-textSecondary mb-1.5">类型标志</label><div class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-jd-content text-jd-text">${typeFlagBadge}</div></div>`
            : `<div><label class="block text-xs text-jd-textSecondary mb-1.5">类型标志</label><select class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" onchange="AutoSendModule.updateStepField(${stepIndex}, 'typeFlag', this.value)">${typeFlagOptions}</select></div>`;
        return `
            <section class="rounded-xl border border-jd-cardBorder bg-white overflow-hidden">
                <div class="px-4 py-3 border-b border-jd-cardBorder flex items-center justify-between gap-3 flex-wrap">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-[11px] px-2 py-0.5 rounded-full bg-jd-primaryLight text-jd-primary">步骤 ${stepIndex + 1}</span>
                        <span class="text-sm font-semibold text-jd-text">${escapeHtml(isDefaultStepName(step.name) ? `步骤${stepIndex + 1}` : step.name)}</span>
                        <span class="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-jd-textMuted">${escapeHtml(getTypeFlagLabel(step.packetHeader.typeFlag))}</span>
                    </div>
                    <div class="flex items-center gap-2">
                        ${locked ? '' : `<button class="btn-secondary px-2.5 py-1 rounded-md text-xs" onclick="AutoSendModule.duplicateStep(${stepIndex})">复制</button>
                        <button class="btn-secondary px-2.5 py-1 rounded-md text-xs" onclick="AutoSendModule.removeStep(${stepIndex})">删除</button>`}
                    </div>
                </div>
                <div class="p-4 space-y-4">
                    <div class="grid grid-cols-4 gap-3">
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1.5">步骤名称</label>
                            <input type="text" class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" value="${escapeHtml(step.name || '')}"${dis} oninput="AutoSendModule.updateStepField(${stepIndex}, 'name', this.value)">
                        </div>
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1.5 flex items-center gap-1">等待秒数<span class="relative group cursor-help"><svg class="w-3 h-3 text-jd-textMuted" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg><span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1.5 rounded-lg bg-slate-700 text-white text-[11px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">0 表示不等待，立即执行下一步</span></span></label>
                            <input type="number" min="0" class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" value="${Number(step.delayAfterSec ?? 0)}"${dis} oninput="AutoSendModule.updateStepField(${stepIndex}, 'delayAfterSec', this.value)">
                        </div>
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1.5">源地址</label>
                            <input type="text" class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" value="${escapeHtml(step.packetHeader.sourceAddr || '')}"${dis} oninput="AutoSendModule.updateStepField(${stepIndex}, 'sourceAddr', this.value)">
                        </div>
                        <div>
                            <label class="block text-xs text-jd-textSecondary mb-1.5">目的地址</label>
                            <input type="text" class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" value="${escapeHtml(step.packetHeader.destAddr || '')}"${dis} oninput="AutoSendModule.updateStepField(${stepIndex}, 'destAddr', this.value)">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>${(autoDerived || locked)
            ? `<label class="block text-xs text-jd-textSecondary mb-1.5">命令字</label><div class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-jd-content text-jd-text">${commandBadge}</div>`
            : `<label class="block text-xs text-jd-textSecondary mb-1.5">命令字</label><select class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" onchange="AutoSendModule.updateStepField(${stepIndex}, 'command', this.value)">${commandOptions}</select>`}</div>
                        <div>${(autoDerived || locked)
            ? `<label class="block text-xs text-jd-textSecondary mb-1.5">类型标志</label><div class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-jd-content text-jd-text">${typeFlagBadge}</div>`
            : `<label class="block text-xs text-jd-textSecondary mb-1.5">类型标志</label><select class="jd-input w-full px-3 py-2 rounded-lg text-sm bg-white" onchange="AutoSendModule.updateStepField(${stepIndex}, 'typeFlag', this.value)">${typeFlagOptions}</select>`}</div>
                    </div>
                    <div class="flex items-center justify-between">
                        <div>
                            <h5 class="text-sm font-semibold text-jd-text">信息对象</h5>
                            <p class="text-xs text-jd-textMuted mt-1">当前类型标志支持 ${getAllowedObjectTypes(step.packetHeader.typeFlag).map(getObjectTypeLabel).join(' / ')}</p>
                        </div>
                        <button class="btn-primary px-3 py-1.5 rounded-lg text-xs font-medium" onclick="AutoSendModule.addObject(${stepIndex})"${dis}>新增对象</button>
                    </div>
                    <div class="space-y-3">
                        ${(step.objects || []).map((obj, objectIndex) => renderObjectCard(step, stepIndex, obj, objectIndex)).join('')}
                    </div>
                </div>
            </section>
        `;
    }

    function renderObjectCard(step, stepIndex, obj, objectIndex) {
        const locked = isSystemTemplate();
        return `
            <div class="rounded-xl border border-jd-cardBorder bg-jd-content/50 p-4 space-y-3">
                <div class="flex items-center justify-between gap-3 flex-wrap">
                    <div class="flex items-center gap-2">
                        <span class="text-[11px] px-2 py-0.5 rounded-full bg-white border border-jd-cardBorder text-jd-textMuted">对象 ${objectIndex + 1}</span>
                        <span class="text-sm font-medium text-jd-text">${escapeHtml(getObjectTypeLabel(obj.objectType))}</span>
                    </div>
                    ${locked ? '' : `<button class="btn-secondary px-2.5 py-1 rounded-md text-xs" onclick="AutoSendModule.removeObject(${stepIndex}, ${objectIndex})">删除</button>`}
                </div>
                ${renderObjectFields(obj, stepIndex, objectIndex)}
            </div>
        `;
    }

    function renderObjectFields(obj, stepIndex, objectIndex) {
        const locked = isSystemTemplate();
        const dis = locked ? ' disabled' : '';
        const disBg = locked ? 'bg-jd-content text-jd-text cursor-default' : 'bg-white';
        const fields = obj.fields || {};
        const commonTimeFields = `
            <div>
                <label class="block text-xs text-jd-textSecondary mb-1.5">时间模式</label>
                <select class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" onchange="AutoSendModule.updateObjectField(${stepIndex}, ${objectIndex}, 'occurredAtMode', this.value)"${dis}>
                    <option value="now" ${fields.occurredAtMode !== 'fixed' ? 'selected' : ''}>执行时取当前时间</option>
                    <option value="fixed" ${fields.occurredAtMode === 'fixed' ? 'selected' : ''}>固定时间</option>
                </select>
            </div>
            <div>
                <label class="block text-xs text-jd-textSecondary mb-1.5">固定时间</label>
                <input type="text" id="fp-${stepIndex}-${objectIndex}" class="jd-input fp-datetime w-full px-3 py-2 rounded-lg text-sm ${disBg}" placeholder="点击选择日期时间" data-value="${escapeHtml(fields.occurredAt || '')}" ${fields.occurredAtMode === 'fixed' ? '' : 'disabled'}${dis}>
            </div>
        `;

        if (obj.objectType === 'system_status') {
            return `
                <div class="grid grid-cols-2 xl:grid-cols-3 gap-3">
                    ${renderSystemTypeSelect(fields.systemType, stepIndex, objectIndex)}
                    ${renderNumberInput('系统地址', fields.systemAddr, stepIndex, objectIndex, 'systemAddr')}
                    ${renderPresetSelect('系统状态', 'system_status', fields.systemStatus, stepIndex, objectIndex, 'systemStatus')}
                    ${commonTimeFields}
                </div>
            `;
        }

        if (obj.objectType === 'analog_value') {
            return `
                <div class="grid grid-cols-2 xl:grid-cols-3 gap-3">
                    ${renderSystemTypeSelect(fields.systemType, stepIndex, objectIndex)}
                    ${renderNumberInput('系统地址', fields.systemAddr, stepIndex, objectIndex, 'systemAddr')}
                    ${renderComponentTypeSelect(fields.componentType, stepIndex, objectIndex, fields.systemType)}
                    ${renderNumberInput('位号', fields.bitNo, stepIndex, objectIndex, 'bitNo')}
                    ${renderNumberInput('区号', fields.zoneNo, stepIndex, objectIndex, 'zoneNo')}
                    ${renderAnalogTypeSelect(fields.analogType, stepIndex, objectIndex)}
                    ${renderNumberInput('模拟量值', fields.analogValue, stepIndex, objectIndex, 'analogValue')}
                    ${commonTimeFields}
                </div>
            `;
        }

        if (obj.objectType === 'device_status') {
            return `
                <div class="grid grid-cols-2 xl:grid-cols-3 gap-3">
                    ${renderPresetSelect('装置状态', 'device_status', fields.statusByte, stepIndex, objectIndex, 'statusByte')}
                    ${commonTimeFields}
                </div>
            `;
        }

        return `
            <div class="grid grid-cols-2 xl:grid-cols-3 gap-3">
                ${renderSystemTypeSelect(fields.systemType, stepIndex, objectIndex)}
                ${renderNumberInput('系统地址', fields.systemAddr, stepIndex, objectIndex, 'systemAddr')}
                ${renderComponentTypeSelect(fields.componentType, stepIndex, objectIndex, fields.systemType)}
                ${renderNumberInput('位号', fields.bitNo, stepIndex, objectIndex, 'bitNo')}
                ${renderNumberInput('区号', fields.zoneNo, stepIndex, objectIndex, 'zoneNo')}
                ${renderPresetSelect('部件状态', 'component_status', fields.componentStatus, stepIndex, objectIndex, 'componentStatus')}
                <div>
                    <label class="block text-xs text-jd-textSecondary mb-1.5">描述</label>
                    <input type="text" class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" value="${escapeHtml(fields.description || '')}"${dis} oninput="AutoSendModule.updateObjectField(${stepIndex}, ${objectIndex}, 'description', this.value)">
                </div>
                ${commonTimeFields}
            </div>
        `;
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

    function renderSystemTypeSelect(value, stepIndex, objectIndex) {
        const locked = isSystemTemplate();
        const dis = locked ? ' disabled' : '';
        const disBg = locked ? 'bg-jd-content text-jd-text cursor-default' : 'bg-white';
        return `
            <div>
                <label class="block text-xs text-jd-textSecondary mb-1.5">系统类型</label>
                <select class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" onchange="AutoSendModule.updateObjectField(${stepIndex}, ${objectIndex}, 'systemType', this.value)"${dis}>
                    ${(meta?.systemTypes || []).map(item => `<option value="${item.value}" ${Number(item.value) === Number(value) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('')}
                </select>
            </div>
        `;
    }

    function renderComponentTypeSelect(value, stepIndex, objectIndex, systemType) {
        const locked = isSystemTemplate();
        const dis = locked ? ' disabled' : '';
        const disBg = locked ? 'bg-jd-content text-jd-text cursor-default' : 'bg-white';
        const filtered = getFilteredComponentTypes(systemType);
        const currentVal = Number(value);
        const validValue = filtered.some(item => Number(item.value) === currentVal) ? value : (filtered[0]?.value ?? value);
        return `
            <div>
                <label class="block text-xs text-jd-textSecondary mb-1.5">部件类型</label>
                <select class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" onchange="AutoSendModule.updateObjectField(${stepIndex}, ${objectIndex}, 'componentType', this.value)"${dis}>
                    ${filtered.map(item => `<option value="${item.value}" ${Number(item.value) === Number(validValue) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('')}
                </select>
            </div>
        `;
    }

    function renderAnalogTypeSelect(value, stepIndex, objectIndex) {
        const locked = isSystemTemplate();
        const dis = locked ? ' disabled' : '';
        const disBg = locked ? 'bg-jd-content text-jd-text cursor-default' : 'bg-white';
        return `
            <div>
                <label class="block text-xs text-jd-textSecondary mb-1.5">模拟量类型</label>
                <select class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" onchange="AutoSendModule.updateObjectField(${stepIndex}, ${objectIndex}, 'analogType', this.value)"${dis}>
                    ${(meta?.analogTypes || []).map(item => `<option value="${item.value}" ${Number(item.value) === Number(value) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('')}
                </select>
            </div>
        `;
    }

    function renderPresetSelect(label, presetKey, value, stepIndex, objectIndex, fieldName) {
        const locked = isSystemTemplate();
        const dis = locked ? ' disabled' : '';
        const disBg = locked ? 'bg-jd-content text-jd-text cursor-default' : 'bg-white';
        return `
            <div>
                <label class="block text-xs text-jd-textSecondary mb-1.5">${label}</label>
                <select class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" onchange="AutoSendModule.updateObjectField(${stepIndex}, ${objectIndex}, '${fieldName}', this.value)"${dis}>
                    ${(meta?.statusPresets?.[presetKey] || []).map(item => `<option value="${item.value}" ${Number(item.value) === Number(value) ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('')}
                </select>
            </div>
        `;
    }

    function renderNumberInput(label, value, stepIndex, objectIndex, fieldName) {
        const locked = isSystemTemplate();
        const dis = locked ? ' disabled' : '';
        const disBg = locked ? 'bg-jd-content text-jd-text cursor-default' : 'bg-white';
        return `
            <div>
                <label class="block text-xs text-jd-textSecondary mb-1.5">${label}</label>
                <input type="number" min="0" step="1" class="jd-input w-full px-3 py-2 rounded-lg text-sm ${disBg}" value="${Number(value || 0)}"${dis} oninput="AutoSendModule.updateObjectField(${stepIndex}, ${objectIndex}, '${fieldName}', this.value)">
            </div>
        `;
    }

    function renderPreview() {
        const panel = document.getElementById('autoScenePreviewPanel');
        const status = document.getElementById('autoScenePreviewStatus');
        if (!panel || !status) return;

        if (!previewSteps.length) {
            panel.innerHTML = `
                <div class="rounded-xl border border-dashed border-jd-cardBorder bg-jd-content/50 px-4 py-10 text-center text-sm text-jd-textMuted">
                    点击“预览”查看每个步骤生成的数据包
                </div>
            `;
            status.className = 'text-[11px] px-2 py-1 rounded-full bg-slate-100 text-jd-textMuted';
            status.textContent = '未预览';
            return;
        }

        status.className = 'text-[11px] px-2 py-1 rounded-full bg-emerald-50 text-emerald-700';
        status.textContent = `已预览 ${previewSteps.length} 步`;
        panel.innerHTML = previewSteps.map((step, index) => `
            <section class="rounded-xl border border-jd-cardBorder bg-white p-4 space-y-3">
                <div class="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-[11px] px-2 py-0.5 rounded-full bg-jd-primaryLight text-jd-primary">步骤 ${index + 1}</span>
                            <h5 class="text-sm font-semibold text-jd-text">${escapeHtml(step.name)}</h5>
                        </div>
                        <p class="text-xs text-jd-textMuted mt-1">${escapeHtml(step.packetView?.adu_summary || step.packetView?.type_flag_name || '无摘要')}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 xl:grid-cols-4 gap-2">
                    <div class="bg-jd-content rounded-lg px-3 py-2">
                        <div class="text-[11px] text-jd-textMuted">命令字</div>
                        <div class="text-xs font-medium text-jd-text mt-1">${escapeHtml(step.packetView?.command_name || getCommandLabel(step.command))}</div>
                    </div>
                    <div class="bg-jd-content rounded-lg px-3 py-2">
                        <div class="text-[11px] text-jd-textMuted">类型标志</div>
                        <div class="text-xs font-medium text-jd-text mt-1">${escapeHtml(step.packetView?.type_flag_name || getTypeFlagLabel(step.typeFlag))}</div>
                    </div>
                    <div class="bg-jd-content rounded-lg px-3 py-2">
                        <div class="text-[11px] text-jd-textMuted">包长度</div>
                        <div class="text-xs font-mono font-semibold text-jd-text mt-1">${step.packetLength}B</div>
                    </div>
                    <div class="${step.packetView?.adu_parsed ? 'bg-jd-primaryLight border border-jd-primaryBorder cursor-pointer hover:bg-blue-100 transition-colors' : 'bg-jd-content'} rounded-lg px-3 py-2" ${step.packetView?.adu_parsed ? `onclick="HistoryModule.openAduModal()" title="点击查看应用数据单元详情"` : ''}>
                        <div class="text-[11px] ${step.packetView?.adu_parsed ? 'text-jd-primary' : 'text-jd-textMuted'} mb-0.5">信息对象数${step.packetView?.adu_parsed ? ' ↗' : ''}</div>
                        <div class="flex items-center gap-1.5">
                            <span class="text-xs font-mono font-semibold ${step.packetView?.adu_parsed ? 'text-jd-primary' : 'text-jd-text'}">${step.objectCount}</span>
                            ${step.packetView?.adu_parsed ? '<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-jd-primary/10 text-jd-primary font-medium">查看ADU</span>' : ''}
                        </div>
                        ${(() => { const _l = (step.packetView?.adu_parsed?.objects || []).flatMap(o => (o.status_flags || []).filter(f => f.active).map(f => f.on)).slice(0, 3); return _l.length ? `<div class="text-[10px] text-amber-600 mt-1 truncate">${_l.map(s => escapeHtml(s)).join(' / ')}</div>` : ''; })()}
                    </div>
                </div>
                <div>
                    <div class="text-[11px] text-jd-textMuted mb-1.5">HEX 预览</div>
                    <div class="raw-hex-box hex-display">${SceneModule.formatHex(step.packetHex)}</div>
                </div>
            </section>
        `).join('');
    }

    function openConfigModal() {
        if (window.PanelModule?.showPanel) {
            window.PanelModule.showPanel('autoScene');

        }
        renderAll();
    }

    function closeConfigModal() {
        if (window.PanelModule?.showPanel) {
            window.PanelModule.showPanel('scene');
        }
    }

    function filterTemplates(keyword) {
        templateKeyword = keyword || '';
        renderTemplateList();
    }

    function selectTemplate(templateId) {
        const template = templates.find(item => item.id === templateId);
        if (!template) return;
        currentScene = cloneScene(template);
        previewSteps = [];
        renderAll();
    }

    function createBlankScene() {
        currentScene = cloneScene(meta?.defaultScene || createFallbackScene());
        currentScene.id = '';
        currentScene.source = 'draft';
        currentScene.name = '未命名场景';
        previewSteps = [];
        renderAll();
    }

    /** 判断当前分类是否可自动推导命令字和类型标志 */
    function isAutoDerivedCategory() {
        const cat = currentScene?.category;
        return cat && cat !== 'sequence' && cat !== 'custom' && categoryDefaults[cat];
    }

    function updateSceneField(field, value) {
        if (!currentScene) return;
        currentScene[field] = value;
        // 分类变更时自动推导命令字、类型标志和信息对象
        if (field === 'category' && value !== 'sequence' && value !== 'custom' && categoryDefaults[value]) {
            const defaults = categoryDefaults[value];
            currentScene.steps.forEach(step => {
                step.packetHeader.typeFlag = defaults.typeFlag;
                step.packetHeader.command = defaults.command;
                reconcileStepObjects(step);
            });
        }
        previewSteps = [];
        renderAll();
    }

    function updateStepField(stepIndex, field, value) {
        const step = currentScene?.steps?.[stepIndex];
        if (!step) return;
        if (field === 'name') {
            step.name = value;
            previewSteps = [];
            return;
        } else if (field === 'delayAfterSec') {
            step.delayAfterSec = Math.max(0, Number(value || 0));
            previewSteps = [];
            renderToolbarState();
            
            return;
        } else if (field === 'typeFlag') {
            step.packetHeader.typeFlag = Number(value);
            reconcileStepObjects(step);
        } else if (field === 'command') {
            step.packetHeader.command = Number(value);
        } else if (field === 'sourceAddr' || field === 'destAddr') {
            step.packetHeader[field] = value;
            previewSteps = [];
            return;
        } else {
            step.packetHeader[field] = value;
        }
        previewSteps = [];
        renderSteps();
        renderToolbarState();
        
    }

    function reconcileStepObjects(step) {
        const allowed = getAllowedObjectTypes(step.packetHeader.typeFlag);
        step.objects = (step.objects || []).filter(item => allowed.includes(item.objectType));
        if (!step.objects.length) {
            step.objects = [createObject(allowed[0] || 'component_status')];
        }
    }

    function addStep() {
        if (!currentScene || isSystemTemplate()) return;
        currentScene.steps.push(createStep());
        previewSteps = [];
        renderSteps();
        renderToolbarState();
        
    }

    function duplicateStep(stepIndex) {
        const source = currentScene?.steps?.[stepIndex];
        if (!source) return;
        const cloned = JSON.parse(JSON.stringify(source));
        cloned.id = generateId('step');
        cloned.name = `${source.name || `步骤${stepIndex + 1}`} 副本`;
        cloned.objects = (cloned.objects || []).map(obj => ({ ...obj, id: generateId('obj') }));
        currentScene.steps.splice(stepIndex + 1, 0, cloned);
        previewSteps = [];
        renderSteps();
        renderToolbarState();
        
    }

    function removeStep(stepIndex) {
        if (!currentScene?.steps?.[stepIndex]) return;
        if (currentScene.steps.length === 1) {
            showToast('至少保留 1 个步骤', 'error');
            return;
        }
        currentScene.steps.splice(stepIndex, 1);
        previewSteps = [];
        renderSteps();
        renderToolbarState();
        
    }

    function addObject(stepIndex) {
        const step = currentScene?.steps?.[stepIndex];
        if (!step) return;
        const objectType = getAllowedObjectTypes(step.packetHeader.typeFlag)[0] || 'component_status';
        step.objects.push(createObject(objectType));
        previewSteps = [];
        renderSteps();
    }

    function removeObject(stepIndex, objectIndex) {
        const step = currentScene?.steps?.[stepIndex];
        if (!step?.objects?.[objectIndex]) return;
        if (step.objects.length === 1) {
            showToast('每个步骤至少保留 1 个对象', 'error');
            return;
        }
        step.objects.splice(objectIndex, 1);
        previewSteps = [];
        renderSteps();
    }

    function updateObjectType(stepIndex, objectIndex, objectType) {
        const step = currentScene?.steps?.[stepIndex];
        const obj = step?.objects?.[objectIndex];
        if (!obj) return;
        obj.objectType = objectType;
        obj.fields = createObject(objectType).fields;
        previewSteps = [];
        renderSteps();
    }

    function updateObjectField(stepIndex, objectIndex, field, value) {
        const obj = currentScene?.steps?.[stepIndex]?.objects?.[objectIndex];
        if (!obj) return;
        if (numericObjectFields.has(field)) {
            obj.fields[field] = value === '' ? '' : Number(value);
        } else if (field === 'occurredAtMode') {
            obj.fields[field] = value;
            if (value !== 'fixed') {
                obj.fields.occurredAt = '';
            }
            renderSteps();
        } else {
            obj.fields[field] = value;
        }
        // 系统类型变更时，联动重置部件类型
        if (field === 'systemType') {
            const filtered = getFilteredComponentTypes(obj.fields.systemType);
            const currentCT = Number(obj.fields.componentType);
            if (!filtered.some(item => Number(item.value) === currentCT) && filtered.length > 0) {
                obj.fields.componentType = Number(filtered[0].value);
            }
            renderSteps();
        }
        previewSteps = [];
    }

    async function previewCurrentScene() {
        if (!currentScene) return;
        try {
            const response = await fetch('/api/auto_send/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scene: currentScene })
            });
            const result = await response.json();
            if (!result.success) {
                showToast(result.error || '预览失败', 'error');
                return false;
            }
            previewSteps = result.steps || [];
            renderPreview();
            
            if (previewSteps[0]) {
                applyPreview(0);
            }
            showToast(`预览成功，共 ${previewSteps.length} 步`, 'success');
            return true;
        } catch (error) {
            console.error(error);
            showToast('预览请求失败', 'error');
            return false;
        }
    }

    function applyPreview(stepIndex) {
        const step = previewSteps?.[stepIndex];
        if (!step?.packetView) return;
        if (HistoryModule?.renderPacketDetail) {
            HistoryModule.renderPacketDetail(step.packetView);
        }
        window.currentHex = step.packetHex;
        showToast(`已应用预览: ${step.name}`, 'success');
    }

    async function reloadTemplates() {
        const response = await fetch('/api/auto_send/templates');
        templates = await response.json();
        renderTemplateList();
    }

    async function saveTemplate() {
        if (!currentScene) return;
        if (!currentScene.name || !currentScene.name.trim()) {
            showToast('请先填写场景名称', 'error');
            return;
        }
        const isUserTemplate = currentScene.source === 'user' && currentScene.id;
        const url = isUserTemplate ? `/api/auto_send/templates/${currentScene.id}` : '/api/auto_send/templates';
        const method = isUserTemplate ? 'PUT' : 'POST';
        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scene: currentScene })
            });
            const result = await response.json();
            if (!response.ok || result.error) {
                showToast(result.error || '模板保存失败', 'error');
                return;
            }
            currentScene = cloneScene(result);
            await reloadTemplates();
            renderAll();
            showToast(isUserTemplate ? '模板已更新' : '模板已保存', 'success');
        } catch (error) {
            console.error(error);
            showToast('模板保存失败', 'error');
        }
    }

    async function startAutoSend() {
        if (autoSendRunning) {
            stopAutoSend();
            return;
        }
        const valid = await previewCurrentScene();
        if (!valid) return;
        const network = NetworkModule.getNetworkConfig();
        socket.emit('start_auto_scene', { scene: currentScene, network });
    }

    function stopAutoSend() {
        socket.emit('stop_auto_scene');
    }

    function toggleAutoSend() {
        if (autoSendRunning) {
            stopAutoSend();
        } else {
            if (typeof NetworkModule !== 'undefined' && !NetworkModule.isTargetConnected()) {
                showToast('请先连接目标服务器', 'error');
                return;
            }
            startAutoSend();
        }
    }

    function setupSocketListeners() {
        socket.on('auto_scene_started', (data) => {
            autoSendRunning = true;
            renderToolbarState();
            showToast(`自动发送已启动: ${data.scene_name}`, 'success');
        });

        socket.on('auto_scene_step_result', (data) => {
            if (data.success) {
                previewSteps = previewSteps.map(step => step.id === data.step_id
                    ? { ...step, packetView: data.packet_view, packetHex: data.hex, packetLength: data.length }
                    : step);
                HistoryModule.addFromAuto(data);
                if (data.packet_view) {
                    HistoryModule.renderPacketDetail(data.packet_view);
                    window.currentHex = data.hex;
                }
            }
            StatsModule.updateStats();
            const status = document.getElementById('autoRunStatus');
            if (status) {
                status.className = 'text-[11px] px-2 py-1 rounded-full bg-red-50 text-red-600';
                status.textContent = `执行 ${data.step_index}`;
            }
        });

        socket.on('auto_scene_completed', (data) => {
            if (autoSendRunning) {
                const status = document.getElementById('autoRunStatus');
                if (status) {
                    status.className = 'text-[11px] px-2 py-1 rounded-full bg-amber-50 text-amber-700';
                    status.textContent = `已完成第 ${data.cycle_index} 轮`;
                }
            }
        });

        socket.on('auto_scene_stopped', () => {
            autoSendRunning = false;
            renderToolbarState();
            showToast('自动发送已停止', 'info');
        });

        socket.on('auto_scene_error', (data) => {
            autoSendRunning = false;
            renderToolbarState();
            showToast(data.message || '自动发送失败', 'error');
        });
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function isRunning() {
        return autoSendRunning;
    }

    return {
        init,
        refreshPageState,
        openConfigModal,
        closeConfigModal,
        filterTemplates,
        selectTemplate,
        createBlankScene,
        updateSceneField,
        updateStepField,
        addStep,
        duplicateStep,
        removeStep,
        addObject,
        removeObject,
        updateObjectType,
        updateObjectField,
        previewCurrentScene,
        applyPreview,
        saveTemplate,
        startAutoSend,
        stopAutoSend,
        toggleAutoSend,
        isRunning
    };
})();
