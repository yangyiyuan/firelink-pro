const AduCommon = (function() {

    const ADU_HEADER_LAYOUT = [
        { label: '类型标志', start: 0, end: 1 },
        { label: '信息对象数', start: 1, end: 2 },
    ];

    const ADU_BYTE_LAYOUTS = {
        1: {
            object: [
                { label: '系统类型', start: 0, end: 1 },
                { label: '系统地址', start: 1, end: 2 },
                { label: '系统状态值', start: 2, end: 4 },
                { label: '状态时间', start: 4, end: 10 },
            ],
            objectSize: 10,
        },
        2: {
            object: [
                { label: '系统类型', start: 0, end: 1 },
                { label: '系统地址', start: 1, end: 2 },
                { label: '部件类型', start: 2, end: 3 },
                { label: '部件地址', start: 3, end: 7 },
                { label: '部件状态值', start: 7, end: 9 },
                { label: '部件说明', start: 9, end: 40 },
                { label: '状态时间', start: 40, end: 46 },
            ],
            objectSize: 46,
        },
        3: {
            object: [
                { label: '系统类型', start: 0, end: 1 },
                { label: '系统地址', start: 1, end: 2 },
                { label: '部件类型', start: 2, end: 3 },
                { label: '部件地址', start: 3, end: 7 },
                { label: '模拟量类型', start: 7, end: 8 },
                { label: '模拟量原始值', start: 8, end: 10 },
                { label: '采样时间', start: 10, end: 16 },
            ],
            objectSize: 16,
        },
        4: {
            object: [
                { label: '系统类型', start: 0, end: 1 },
                { label: '系统地址', start: 1, end: 2 },
                { label: '操作信息值', start: 2, end: 3 },
                { label: '操作员编号', start: 3, end: 4 },
                { label: '记录时间', start: 4, end: 10 },
            ],
            objectSize: 10,
        },
        5: {
            object: [
                { label: '系统类型', start: 0, end: 1 },
                { label: '系统地址', start: 1, end: 2 },
                { label: '软件版本', start: 2, end: 4 },
                { label: '版本时间', start: 4, end: 10 },
            ],
            objectSize: 10,
        },
        7: {
            object: [
                { label: '系统类型', start: 0, end: 1 },
                { label: '系统地址', start: 1, end: 2 },
                { label: '部件类型', start: 2, end: 3 },
                { label: '部件地址', start: 3, end: 7 },
                { label: '部件说明', start: 7, end: 38 },
                { label: '配置时间', start: 38, end: 44 },
            ],
            objectSize: 44,
        },
        8: {
            object: [
                { label: '系统类型', start: 0, end: 1 },
                { label: '系统地址', start: 1, end: 2 },
                { label: '系统时间', start: 2, end: 8 },
                { label: '上报时间', start: 8, end: 14 },
            ],
            objectSize: 14,
        },
        21: {
            object: [
                { label: '状态值', start: 0, end: 1 },
                { label: '状态发生时间', start: 1, end: 7 },
                { label: '时间标签', start: 7, end: 13 },
            ],
            objectSize: 13,
        },
        22: {
            object: [
                { label: '操作信息值', start: 0, end: 1 },
                { label: '操作员编号', start: 1, end: 2 },
                { label: '记录时间', start: 2, end: 8 },
            ],
            objectSize: 8,
        },
        24: {
            object: [
                { label: '操作信息值', start: 0, end: 1 },
                { label: '操作员编号', start: 1, end: 2 },
                { label: '记录时间', start: 2, end: 8 },
                { label: '时间标签', start: 8, end: 14 },
            ],
            objectSize: 14,
        },
        25: {
            object: [
                { label: '软件版本', start: 0, end: 2 },
                { label: '版本时间', start: 2, end: 8 },
            ],
            objectSize: 8,
        },
        28: {
            object: [
                { label: '传输装置系统时间', start: 0, end: 6 },
                { label: '时间标签', start: 6, end: 12 },
            ],
            objectSize: 12,
        },
        61: {
            object: [
                { label: '系统类型', start: 0, end: 1 },
                { label: '系统地址', start: 1, end: 2 },
            ],
            objectSize: 2,
        },
        62: {
            object: [
                { label: '系统类型', start: 0, end: 1 },
                { label: '系统地址', start: 1, end: 2 },
                { label: '部件地址', start: 2, end: 6 },
            ],
            objectSize: 6,
        },
    };

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function escapeAttr(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function formatHexInteractive(hex) {
        if (!hex) return '';
        const bytes = hex.match(/.{1,2}/g) || [];
        return bytes.map((b, i) => {
            let color = '#94A3B8';
            if (i < 2) color = '#10B981';
            else if (i >= bytes.length - 2) color = '#EF4444';
            else if (i >= 2 && i < 27) color = '#2563EB';
            return `<span class="hex-byte" data-byte-idx="${i}" style="color:${color}">${b}</span>`;
        }).join(' ');
    }

    function formatHex(hex) {
        if (!hex) return '';
        return hex.match(/.{1,2}/g).map((b, i) => {
            let color = '#94A3B8';
            if (i < 2) color = '#10B981';
            else if (i >= hex.length / 2 - 2) color = '#EF4444';
            else if (i >= 2 && i < 27) color = '#2563EB';
            return `<span style="color: ${color}">${b}</span>`;
        }).join(' ');
    }

    function getByteRangeForHeaderField(label) {
        const entry = ADU_HEADER_LAYOUT.find(e => e.label === label);
        return entry ? [entry.start, entry.end] : null;
    }

    function getByteRangeForObjectField(typeFlag, objIdx, fieldLabel) {
        const layout = ADU_BYTE_LAYOUTS[typeFlag];
        if (!layout) return null;
        const entry = layout.object.find(e => e.label === fieldLabel);
        if (!entry) return null;
        const objOffset = 2 + objIdx * layout.objectSize;
        return [objOffset + entry.start, objOffset + entry.end];
    }

    function createHighlightManager(containerSelector) {
        let _activeFieldEl = null;

        function highlightBytes(startIdx, endIdx) {
            clearHexHighlight();
            const container = document.querySelector(containerSelector);
            if (!container) return;
            container.querySelectorAll('.hex-byte').forEach(el => {
                const idx = parseInt(el.dataset.byteIdx, 10);
                if (idx >= startIdx && idx < endIdx) {
                    el.classList.add('hex-byte-hl');
                }
            });
        }

        function clearHexHighlight() {
            const container = document.querySelector(containerSelector);
            if (container) {
                container.querySelectorAll('.hex-byte-hl').forEach(el => el.classList.remove('hex-byte-hl'));
            }
            if (_activeFieldEl) {
                _activeFieldEl.classList.remove('adu-field-active');
                _activeFieldEl = null;
            }
        }

        function handleFieldClick(el, startIdx, endIdx) {
            if (_activeFieldEl === el) {
                clearHexHighlight();
                return;
            }
            clearHexHighlight();
            el.classList.add('adu-field-active');
            _activeFieldEl = el;
            highlightBytes(startIdx, endIdx);
        }

        function reset() {
            _activeFieldEl = null;
        }

        return { highlightBytes, clearHexHighlight, handleFieldClick, reset };
    }

    function renderField(field, byteRange, clickHandler) {
        const mono = field.mono ? 'font-mono' : '';
        const accent = field.accent === 'primary'
            ? 'text-jd-primary'
            : field.accent === 'danger'
                ? 'text-jd-danger'
                : field.accent === 'warning'
                    ? 'text-jd-warning'
                    : field.accent === 'success'
                        ? 'text-emerald-600'
                        : 'text-jd-text';
        const interactive = byteRange && clickHandler
            ? `onclick="${clickHandler}(this,${byteRange[0]},${byteRange[1]})" data-clickable="1"`
            : '';
        return `
            <div class="bg-white rounded-lg border border-jd-cardBorder px-3 py-1.5 adu-field-card" ${interactive}>
                <div class="text-[11px] text-jd-textMuted mb-0.5">${escapeHtml(field.label)}</div>
                <div class="text-sm ${mono} font-medium ${accent} break-all">${escapeHtml(field.value)}</div>
            </div>
        `;
    }

    function renderFlags(flags) {
        if (!flags || !flags.length) return '';
        const hasActive = flags.some(f => f.active);
        return `
            <div class="space-y-1">
                <div class="text-xs font-medium text-jd-text">状态位解码</div>
                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-1">
                    ${flags.map(flag => {
                        const isNormalHighlight = !hasActive && flag.bit === 0 && !flag.active;
                        const cardStyle = flag.active
                            ? 'border-amber-200 bg-amber-50'
                            : isNormalHighlight
                                ? 'border-emerald-200 bg-emerald-50'
                                : 'border-jd-cardBorder bg-white';
                        const badgeStyle = flag.active
                            ? 'bg-amber-100 text-amber-700'
                            : isNormalHighlight
                                ? 'bg-emerald-100 text-emerald-700'
                                : 'bg-slate-100 text-jd-textMuted';
                        const textStyle = flag.active
                            ? 'text-amber-700'
                            : isNormalHighlight
                                ? 'text-emerald-700'
                                : 'text-jd-text';
                        return `
                        <div class="rounded-lg border px-3 py-1.5 ${cardStyle}">
                            <div class="flex items-center justify-between gap-2">
                                <span class="text-[11px] text-jd-textMuted">bit${flag.bit} · ${escapeHtml(flag.label)}</span>
                                <span class="text-[10px] px-1.5 py-0.5 rounded-full ${badgeStyle}">${flag.active ? '1' : '0'}</span>
                            </div>
                            <div class="text-sm font-medium ${textStyle} mt-0.5">${escapeHtml(flag.text)}</div>
                        </div>
                    `;}).join('')}
                </div>
            </div>
        `;
    }

    function getObjectSeverity(obj) {
        const active = (obj?.status_flags || []).filter(flag => flag.active).map(flag => flag.on);
        const keywords = active.join(' ');
        if (/火警|报警/.test(keywords)) return 'alarm';
        if (/故障/.test(keywords)) return 'fault';
        if (/恢复/.test(keywords)) return 'recovery';
        if (/查岗/.test(keywords)) return 'duty';
        if (active.length === 0) return 'normal';
        return '';
    }

    function getObjectCardStyle(severity) {
        if (severity === 'alarm') return { wrap: 'border-red-200 bg-red-50/70', badge: 'bg-red-100 text-red-700', title: 'text-red-700' };
        if (severity === 'fault') return { wrap: 'border-amber-200 bg-amber-50/70', badge: 'bg-amber-100 text-amber-700', title: 'text-amber-700' };
        if (severity === 'recovery') return { wrap: 'border-emerald-200 bg-emerald-50/70', badge: 'bg-emerald-100 text-emerald-700', title: 'text-emerald-700' };
        if (severity === 'duty') return { wrap: 'border-sky-200 bg-sky-50/70', badge: 'bg-sky-100 text-sky-700', title: 'text-sky-700' };
        if (severity === 'normal') return { wrap: 'border-emerald-200 bg-emerald-50/70', badge: 'bg-emerald-100 text-emerald-700', title: 'text-emerald-700' };
        return { wrap: 'border-jd-cardBorder bg-jd-content/50', badge: 'bg-slate-100 text-jd-textMuted', title: 'text-jd-text' };
    }

    function renderObjectCard(obj, objIdx, typeFlag, clickHandler) {
        const severity = getObjectSeverity(obj);
        const style = getObjectCardStyle(severity);
        const severityLabel = severity === 'alarm' ? '火警'
            : severity === 'fault' ? '故障'
            : severity === 'recovery' ? '恢复'
            : severity === 'duty' ? '查岗'
            : severity === 'normal' ? '正常'
            : '信息';
        const fieldsHtml = (obj.fields || []).map(f => {
            const br = getByteRangeForObjectField(typeFlag, objIdx, f.label);
            return renderField(f, br, clickHandler);
        }).join('');
        return `
            <section class="rounded-xl border p-3 space-y-2 ${style.wrap}">
                <div class="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                        <div class="flex items-center gap-2 flex-wrap">
                            <h4 class="text-sm font-semibold ${style.title}">${escapeHtml(obj.title || '信息对象')}</h4>
                            <span class="text-[10px] px-1.5 py-0.5 rounded-full ${style.badge}">${severityLabel}</span>
                        </div>
                        <p class="text-xs text-jd-textSecondary mt-0.5">${escapeHtml(obj.summary || '-')}</p>
                    </div>
                    ${obj.occurred_at ? `<span class="text-[11px] px-2 py-1 rounded-full bg-white border border-jd-cardBorder text-jd-textMuted font-mono">${escapeHtml(obj.occurred_at)}</span>` : ''}
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-1.5">
                    ${fieldsHtml}
                </div>
                ${renderFlags(obj.status_flags || [])}
            </section>
        `;
    }

    function renderNotes(notes) {
        if (!notes || !notes.length) return '';
        return `
            <section class="space-y-1">
                <div class="text-xs font-medium text-jd-text">解析说明</div>
                <div class="space-y-1">
                    ${notes.map(note => `
                        <div class="rounded-lg border border-jd-primaryBorder bg-jd-primaryLight px-3 py-1.5 text-xs text-jd-textSecondary">
                            ${escapeHtml(note)}
                        </div>
                    `).join('')}
                </div>
            </section>
        `;
    }

    function renderAduHeaderFields(adu, clickHandler) {
        const fields = [
            { label: '方向', value: adu.direction },
            { label: '类型标志', value: `${adu.type_flag} / ${adu.type_flag_name}`, mono: true, accent: 'primary' },
            { label: '类型来源', value: adu.type_origin_label || '-', accent: adu.type_origin_label === '厂商扩展' ? 'primary' : '' },
            { label: '信息对象数', value: adu.info_count, mono: true },
            { label: '负载长度', value: `${adu.payload_length}B`, mono: true }
        ];
        return fields.map(f => renderField(f, getByteRangeForHeaderField(f.label), clickHandler)).join('');
    }

    function renderAduHexSection(adu) {
        const aduHex = adu.adu_full_hex || adu.payload_hex || '';
        if (!aduHex) return '';
        return `
            <section class="space-y-1">
                <div class="flex items-center gap-2">
                    <span class="text-xs text-jd-textMuted">ADU 数据 HEX</span>
                    <span class="text-[10px] text-jd-textMuted opacity-60">点击上方字段可高亮对应字节</span>
                </div>
                <div class="raw-hex-box hex-display hex-display-interactive">${formatHexInteractive(aduHex)}</div>
            </section>
        `;
    }

    return {
        ADU_HEADER_LAYOUT,
        ADU_BYTE_LAYOUTS,
        escapeHtml,
        escapeAttr,
        formatHexInteractive,
        formatHex,
        getByteRangeForHeaderField,
        getByteRangeForObjectField,
        createHighlightManager,
        renderField,
        renderFlags,
        getObjectSeverity,
        getObjectCardStyle,
        renderObjectCard,
        renderNotes,
        renderAduHeaderFields,
        renderAduHexSection,
    };
})();
