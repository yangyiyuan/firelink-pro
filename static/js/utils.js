// 工具函数模块
const UtilsModule = (function() {
    function showToast(msg, type) {
        const toast = document.getElementById('toast');
        toast.textContent = msg;
        toast.style.background = type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#2563EB';
        toast.style.transform = 'translateX(0)';
        toast.style.opacity = '1';
        
        setTimeout(() => {
            toast.style.transform = 'translateX(calc(100% + 20px))';
            toast.style.opacity = '0';
        }, 2500);
    }

    function copyHex() {
        if (window.currentHex) {
            navigator.clipboard.writeText(window.currentHex);
            showToast('HEX 已复制', 'success');
        }
    }

    function testConnection() {
        NetworkModule.testConnection();
    }

    return {
        showToast,
        copyHex,
        testConnection
    };
})();

function showToast(msg, type) {
    UtilsModule.showToast(msg, type);
}

const ConfirmDialog = (function() {
    let _resolve = null;

    const ICON_MAP = {
        danger: {
            bg: 'bg-red-50',
            color: 'text-red-500',
            svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>'
        },
        warning: {
            bg: 'bg-amber-50',
            color: 'text-amber-500',
            svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'
        },
        info: {
            bg: 'bg-blue-50',
            color: 'text-blue-500',
            svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'
        }
    };

    function show(options) {
        const opts = Object.assign({
            title: '确认操作',
            message: '确定要执行此操作吗？',
            type: 'danger',
            confirmText: '确定',
            cancelText: '取消',
            confirmClass: ''
        }, options);

        const dialog = document.getElementById('confirmDialog');
        const iconEl = document.getElementById('confirmDialogIcon');
        const iconCfg = ICON_MAP[opts.type] || ICON_MAP.danger;

        iconEl.className = `w-9 h-9 rounded-full ${iconCfg.bg} flex items-center justify-center shrink-0`;
        iconEl.innerHTML = `<svg class="w-5 h-5 ${iconCfg.color}" fill="none" stroke="currentColor" viewBox="0 0 24 24">${iconCfg.svg}</svg>`;

        document.getElementById('confirmDialogTitle').textContent = opts.title;
        document.getElementById('confirmDialogMessage').textContent = opts.message;

        const confirmBtn = document.getElementById('confirmDialogConfirmBtn');
        confirmBtn.textContent = opts.confirmText;
        if (opts.confirmClass) {
            confirmBtn.className = opts.confirmClass;
        } else if (opts.type === 'danger') {
            confirmBtn.className = 'px-4 py-1.5 rounded-lg text-sm font-medium text-white bg-red-500 hover:bg-red-600 transition-colors';
        } else {
            confirmBtn.className = 'btn-primary px-4 py-1.5 rounded-lg text-sm font-medium';
        }

        document.getElementById('confirmDialogCancelBtn').textContent = opts.cancelText;

        dialog.classList.remove('hidden');

        return new Promise(resolve => {
            _resolve = resolve;
        });
    }

    function confirm() {
        const dialog = document.getElementById('confirmDialog');
        dialog.classList.add('hidden');
        if (_resolve) {
            _resolve(true);
            _resolve = null;
        }
    }

    function cancel() {
        const dialog = document.getElementById('confirmDialog');
        dialog.classList.add('hidden');
        if (_resolve) {
            _resolve(false);
            _resolve = null;
        }
    }

    return { show, confirm, cancel };
})();