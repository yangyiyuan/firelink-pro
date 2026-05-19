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
        // 已迁移到 NetworkModule.testConnection()
        NetworkModule.testConnection();
    }

    return {
        showToast,
        copyHex,
        testConnection
    };
})();

// 全局 showToast 函数
function showToast(msg, type) {
    UtilsModule.showToast(msg, type);
}