// 自定义下拉框组件
const CustomSelect = (function() {
    const instances = new Map();

    function init(selectEl, options = {}) {
        if (instances.has(selectEl)) return instances.get(selectEl);

        const isSm = options.size === 'sm';
        const isFull = selectEl.classList.contains('w-full');
        const wrapper = document.createElement('div');
        wrapper.className = 'jd-select-wrapper' + (isFull ? ' is-full' : '');
        if (options.width) wrapper.style.width = options.width;

        const trigger = document.createElement('div');
        trigger.className = 'jd-select-trigger' + (isSm ? ' sm' : '');

        const textSpan = document.createElement('span');
        textSpan.className = 'select-text';
        trigger.appendChild(textSpan);

        const dropdown = document.createElement('div');
        dropdown.className = 'jd-select-dropdown' + (isSm ? ' sm' : '');

        // 隐藏原生 select，放入 wrapper
        selectEl.parentNode.insertBefore(wrapper, selectEl);
        wrapper.appendChild(selectEl);
        wrapper.appendChild(trigger);
        document.body.appendChild(dropdown);

        const inst = { selectEl, wrapper, trigger, dropdown, textSpan, isOpen: false };
        instances.set(selectEl, inst);

        syncFromNative(inst);
        buildOptions(inst);

        // 点击触发
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            toggle(inst);
        });

        // 原生 select 变更时同步（JS 直接设置 value 时）
        const origDescriptor = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value');
        let currentValue = selectEl.value;
        Object.defineProperty(selectEl, '_customValue', {
            get() { return this.value; },
            set(v) { this.value = v; syncFromNative(instances.get(this)); },
            configurable: true
        });

        // 监听原生 change
        selectEl.addEventListener('change', () => {
            syncFromNative(inst);
        });

        // 点击外部关闭
        document.addEventListener('click', (e) => {
            if (!wrapper.contains(e.target) && !dropdown.contains(e.target)) close(inst);
        });

        // 下拉面板内阻止滚轮冒泡，防止被父容器 overflow:hidden 吞掉
        dropdown.addEventListener('wheel', (e) => {
            e.stopPropagation();
        }, { passive: true });

        // 页面滚动时重新定位
        window.addEventListener('scroll', (e) => {
            if (dropdown.contains(e.target)) return;
            if (inst.isOpen) positionDropdown(inst);
        }, true);

        // 窗口大小变化时重新定位
        window.addEventListener('resize', () => {
            if (inst.isOpen) positionDropdown(inst);
        });

        return inst;
    }

    function buildOptions(inst) {
        const { selectEl, dropdown } = inst;
        dropdown.innerHTML = '';
        Array.from(selectEl.options).forEach(opt => {
            const item = document.createElement('div');
            item.className = 'jd-option' + (opt.selected ? ' active' : '');
            item.textContent = opt.textContent;
            item.dataset.value = opt.value;
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                selectOption(inst, opt.value);
            });
            dropdown.appendChild(item);
        });
    }

    function selectOption(inst, value) {
        const { selectEl } = inst;
        selectEl.value = value;
        selectEl.dispatchEvent(new Event('change'));
        syncFromNative(inst);
        close(inst);
    }

    function syncFromNative(inst) {
        const { selectEl, textSpan, dropdown } = inst;
        const selectedOpt = selectEl.options[selectEl.selectedIndex];
        if (selectedOpt) {
            textSpan.textContent = selectedOpt.textContent;
        }
        // 更新 active 状态
        if (dropdown) {
            dropdown.querySelectorAll('.jd-option').forEach(el => {
                el.classList.toggle('active', el.dataset.value === selectEl.value);
            });
        }
    }

    function toggle(inst) {
        inst.isOpen ? close(inst) : open(inst);
    }

    function open(inst) {
        instances.forEach(other => { if (other !== inst) close(other); });
        inst.trigger.classList.add('open');
        inst.dropdown.classList.add('open');
        inst.isOpen = true;

        positionDropdown(inst);

        const active = inst.dropdown.querySelector('.jd-option.active');
        if (active) {
            active.scrollIntoView({ block: 'nearest' });
        }
    }

    function positionDropdown(inst) {
        const { trigger, dropdown } = inst;

        const triggerRect = trigger.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;
        const spaceBelow = viewportHeight - triggerRect.bottom;
        const spaceAbove = triggerRect.top;
        const gap = 4;
        const padding = 8;

        dropdown.style.left = triggerRect.left + 'px';
        dropdown.style.minWidth = triggerRect.width + 'px';

        const dropdownHeight = dropdown.scrollHeight;

        const maxDropDown = Math.min(dropdownHeight, spaceBelow - gap - padding);
        const maxDropUp = Math.min(dropdownHeight, spaceAbove - gap - padding);

        if (maxDropDown >= dropdownHeight || maxDropDown >= maxDropUp) {
            dropdown.style.top = (triggerRect.bottom + gap) + 'px';
            dropdown.style.maxHeight = Math.max(maxDropDown, 80) + 'px';
        } else {
            dropdown.style.top = '';
            dropdown.style.bottom = (viewportHeight - triggerRect.top + gap) + 'px';
            dropdown.style.maxHeight = Math.max(maxDropUp, 80) + 'px';
        }

        if (triggerRect.left + dropdown.offsetWidth > viewportWidth) {
            dropdown.style.left = Math.max(8, viewportWidth - dropdown.offsetWidth - 8) + 'px';
        }
    }

    function close(inst) {
        inst.trigger.classList.remove('open');
        inst.dropdown.classList.remove('open');
        inst.dropdown.style.top = '';
        inst.dropdown.style.bottom = '';
        inst.dropdown.style.left = '';
        inst.dropdown.style.minWidth = '';
        inst.dropdown.style.maxHeight = '';
        inst.isOpen = false;
    }

    function refresh(inst) {
        buildOptions(inst);
        syncFromNative(inst);
    }

    function initAll() {
        // 工具栏小尺寸下拉
        document.querySelectorAll('select.jd-input.py-1').forEach(el => {
            init(el, { size: 'sm' });
        });
        // 普通尺寸下拉
        document.querySelectorAll('select.jd-input.py-2').forEach(el => {
            init(el, { size: 'md' });
        });
    }

    return { init, initAll, refresh, close };
})();
