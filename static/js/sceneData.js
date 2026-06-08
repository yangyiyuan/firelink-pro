// 场景公共数据模块 — 集中定义模板分组、标签映射、数据转换等共享数据与工具
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

    // ---------- 场景数据转换工具（从 autoSend.js 提取） ----------

    function generateId(prefix) {
        return `${prefix}_${Math.random().toString(16).slice(2, 10)}`;
    }

    function createObject(objectType = 'component_status') {
        const fields = objectType === 'system_status'
            ? { systemType: 1, systemAddr: 1, systemStatus: 0, occurredAtMode: 'now', occurredAt: '' }
            : objectType === 'analog_value'
                ? { systemType: 1, systemAddr: 1, componentType: 31, bitNo: 1, zoneNo: 1, analogType: 3, analogValue: 850, occurredAtMode: 'now', occurredAt: '' }
                : objectType === 'device_status'
                    ? { statusByte: 0, occurredAtMode: 'now', occurredAt: '' }
                    : { systemType: 1, systemAddr: 1, componentType: 42, bitNo: 1, zoneNo: 1, componentStatus: 2, description: '', occurredAtMode: 'now', occurredAt: '' };
        return {
            id: generateId('obj'),
            objectType,
            fields
        };
    }

    function migrateStep(step) {
        if (!step.object && step.objects) {
            step.object = Array.isArray(step.objects) && step.objects.length > 0
                ? step.objects[0]
                : createObject();
            delete step.objects;
        } else if (!step.object) {
            step.object = createObject();
        }
        return step;
    }

    /**
     * 创建一个新步骤。
     *
     * @param {Object} opts - 运行时依赖项
     * @param {number|null} opts.typeFlag - 指定 typeFlag，null 时从 defaults 推算
     * @param {Object|null} opts.defaults - categoryDefaults（如 meta.categoryDefaults[category]）
     * @param {number} opts.stepIndex - 步骤序号（用于命名）
     * @param {Object|null} opts.meta - 协议元数据（用于 objectType 兼容性查询）
     */
    function createStep(opts = {}) {
        const { typeFlag = null, defaults = null, stepIndex = 1, meta = null } = opts;
        const effectiveTypeFlag = typeFlag ?? (defaults?.typeFlag ?? 2);
        const effectiveCommand = defaults?.command ?? 2;
        const compatibility = meta?.compatibility?.[String(effectiveTypeFlag)] || meta?.compatibility?.[effectiveTypeFlag];
        const primaryObjectType = (compatibility || ['component_status'])[0];
        return {
            id: generateId('step'),
            name: `步骤${stepIndex}`,
            delayAfterSec: 5,
            packetHeader: {
                sourceAddr: '0x000000000001',
                destAddr: '0x000000000002',
                command: effectiveCommand,
                typeFlag: effectiveTypeFlag
            },
            object: createObject(primaryObjectType)
        };
    }

    /**
     * 创建默认回退场景。
     *
     * @param {Object} opts - 运行时依赖项（与 createStep 相同）
     */
    function createFallbackScene(opts = {}) {
        return {
            id: '',
            name: '未命名场景',
            category: 'custom',
            description: '',
            source: 'draft',
            version: 2,
            loop: true,
            steps: [createStep(opts), createStep({ ...opts, stepIndex: 2 })]
        };
    }

    function cloneScene(scene, opts = {}) {
        const value = JSON.parse(JSON.stringify(scene || createFallbackScene(opts)));
        value.steps = (value.steps || []).map((step, idx) => {
            migrateStep(step);
            return {
                ...step,
                id: step.id || generateId('step'),
                object: { ...step.object, id: step.object.id || generateId('obj') }
            };
        });
        return value;
    }

    return {
        GROUP_MAP, TEMPLATE_GROUPS, getGroupLabel,
        generateId, createObject, migrateStep, createStep,
        createFallbackScene, cloneScene
    };
})();