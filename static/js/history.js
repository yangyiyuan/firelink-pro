// 历史记录模块
const HistoryModule = (function() {
    let socket;
    let hasRealtimeUpdates = false;
    let recvRawTimers = new Map();
    let historyPacketHexSet = new Set();

    function init(socketInstance) {
        socket = socketInstance;
        setupSocketListeners();
        loadHistory();
    }

    function setupSocketListeners() {
        socket.on('send_result', (data) => {
            hasRealtimeUpdates = true;
            if (data.success) {
                if (data.results) {
                    showToast(`发送成功 (${data.results.length} 个数据包)`, 'success');
                    data.results.forEach(r => addSent(r));
                } else {
                    showToast(`发送成功 (${data.length} 字节)`, 'success');
                    addSent(data);
                }
            } else {
                showToast(`发送失败: ${data.error}`, 'error');
            }
            StatsModule.updateStats();
        });

        socket.on('target_data_received', (data) => {
            hasRealtimeUpdates = true;
            if (data.type === 'packet') {
                cancelPendingRaw(data);
                addReceived(data);
            } else if (data.type === 'raw') {
                scheduleRawRecord(data);
            }
        });
    }

    // ==================== 方向箭头 SVG ====================
    const ARROW_RIGHT = `<svg class="w-3 h-3 text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>`;
    const ARROW_LEFT  = `<svg class="w-3 h-3 text-blue-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M11 17l-5-5m0 0l5-5m-5 5h12"/></svg>`;

    // ==================== 统一渲染 ====================
    function renderItem(opts) {
        /* opts: { direction, label, labelClass, dotClass, source, target, protocol, size, sceneLabel, sceneLabelColor, timestamp, hex, badge, badgeClass, extra } */
        const list = document.getElementById('historyList');
        if (list.querySelector('.text-center')) list.innerHTML = '';

        const arrow = ARROW_RIGHT;
        const item = document.createElement('div');
        item.className = 'history-item flex items-center gap-2.5 px-3 py-2 rounded-lg border-b border-jd-cardBorder last:border-0';
        item.innerHTML = `
            <div class="w-2 h-2 rounded-full ${opts.dotClass} shrink-0"></div>
            <span class="text-xs font-medium px-1.5 py-0.5 rounded ${opts.labelClass} shrink-0">${opts.label}</span>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5 text-xs text-jd-textMuted flex-wrap">
                    <span class="truncate" title="${opts.source}">${opts.source}</span>
                    ${arrow}
                    <span class="truncate" title="${opts.target}">${opts.target}</span>
                    <span class="text-jd-textMuted opacity-40">|</span>
                    <span class="whitespace-nowrap text-jd-textMuted">${opts.timestamp}</span>
                    <span class="text-jd-textMuted opacity-40">|</span>
                    <span>${opts.size}</span>
                    ${opts.protocol ? `<span class="text-jd-textMuted opacity-40">|</span><span class="px-1 py-0.5 rounded bg-slate-100 text-jd-textMuted">${opts.protocol}</span>` : ''}
                    ${opts.extra || ''}
                    ${opts.sceneLabel ? `<span class="text-jd-textMuted opacity-40">|</span><span class="font-medium ${opts.sceneLabelColor || 'text-jd-textMuted'}">${opts.sceneLabel}</span>` : ''}
                </div>
                ${opts.hex ? `<div class="raw-hex-box-wrapper mt-1">
                    <div class="raw-hex-box text-[10px]">${opts.hex}<div class="raw-hex-actions">
                        <button class="raw-hex-copy-btn" title="复制HEX" onclick="HistoryModule.copyHex(this)">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                        </button>
                        <button class="raw-hex-apply-btn" title="应用到数据包详情" onclick="HistoryModule.applyHex(this)">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
                        </button>
                    </div></div>
                </div>` : ''}
            </div>
            <span class="text-xs px-2 py-0.5 rounded-full shrink-0 ${opts.badgeClass}">${opts.badge}</span>
        `;
        list.insertBefore(item, list.firstChild);
        document.getElementById('historyCount').textContent = `(${list.children.length})`;
    }

    function setEmptyState() {
        document.getElementById('historyList').innerHTML = '<div class="text-center text-jd-textMuted text-sm py-8">暂无收发记录</div>';
        document.getElementById('historyCount').textContent = '(0)';
    }

    function getReceiveKey(data) {
        const hex = data?.data_hex || data?.parsed?.raw_hex || '';
        return `${data.host || ''}:${data.port || ''}:${hex}`;
    }

    function scheduleRawRecord(data) {
        const key = getReceiveKey(data);
        if (!key) {
            addReceivedRaw(data);
            return;
        }

        cancelPendingRaw(data);
        const timerId = window.setTimeout(() => {
            recvRawTimers.delete(key);
            addReceivedRaw(data);
        }, 120);
        recvRawTimers.set(key, timerId);
    }

    function cancelPendingRaw(data) {
        const key = getReceiveKey(data);
        const timerId = recvRawTimers.get(key);
        if (timerId) {
            window.clearTimeout(timerId);
            recvRawTimers.delete(key);
        }
    }

    // ==================== 发送记录 ====================
    function addSent(data) {
        const sceneName = data.scene_name || data.step_name || SceneModule.getSceneName(data.scene);
        const hex = data.hex ? SceneModule.formatHex(data.hex) : '';
        renderItem({
            direction: 'send',
            label: '发送',
            labelClass: 'bg-emerald-50 text-emerald-600',
            dotClass: data.success ? 'bg-emerald-400' : 'bg-red-400',
            source: '本机',
            target: `${data.host}:${data.port}`,
            protocol: data.protocol ? data.protocol.toUpperCase() : '',
            size: `${data.length}B`,
            timestamp: data.timestamp,
            sceneLabel: sceneName,
            sceneLabelColor: 'text-emerald-600',
            hex,
            badge: data.success ? '成功' : '失败',
            badgeClass: data.success ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
        });
    }

    // ==================== 接收记录 ====================
    function addReceived(data) {
        const parsed = data.parsed || {};
        const hex = parsed.raw_hex ? SceneModule.formatHex(parsed.raw_hex) : '';
        const commandName = parsed.command_name || '';
        const summary = parsed.adu_summary || parsed.type_flag_name || commandName || '未知类型';
        const typeOriginLabel = parsed.adu_parsed?.type_origin_label || '';
        const activeStatuses = (parsed.adu_parsed?.objects || [])
            .flatMap(obj => (obj.status_flags || []).filter(flag => flag.active).map(flag => flag.on))
            .slice(0, 3);
        const extra = [
            commandName ? `<span class="text-jd-textMuted opacity-40">|</span><span class="px-1 py-0.5 rounded bg-slate-100 text-jd-textMuted">${commandName}</span>` : '',
            typeOriginLabel ? `<span class="text-jd-textMuted opacity-40">|</span><span class="px-1 py-0.5 rounded ${typeOriginLabel === '厂商扩展' ? 'bg-violet-50 text-violet-700' : 'bg-emerald-50 text-emerald-700'}">${typeOriginLabel}</span>` : '',
            activeStatuses.length ? `<span class="text-jd-textMuted opacity-40">|</span><span class="text-amber-600">${activeStatuses.join(' / ')}</span>` : ''
        ].join('');
        renderItem({
            direction: 'recv',
            label: '接收',
            labelClass: 'bg-blue-50 text-blue-600',
            dotClass: 'bg-blue-400',
            source: `${data.host}:${data.port}`,
            target: '本机',
            protocol: data.protocol ? data.protocol.toUpperCase() : '',
            size: `${parsed.raw_length || 0}B`,
            timestamp: data.timestamp,
            sceneLabel: summary,
            sceneLabelColor: summary !== '未知类型' ? 'text-emerald-600' : 'text-amber-600',
            hex,
            extra,
            badge: '成功',
            badgeClass: 'bg-emerald-50 text-emerald-600'
        });
    }

    function addReceivedRaw(data) {
        const hex = data.data_hex
            ? SceneModule.formatHex(data.data_hex)
            : '';
        renderItem({
            direction: 'recv',
            label: '接收',
            labelClass: 'bg-amber-50 text-amber-600',
            dotClass: 'bg-amber-400',
            source: `${data.host}:${data.port}`,
            target: '本机',
            protocol: data.protocol ? data.protocol.toUpperCase() : '',
            size: `${data.data_length}B`,
            timestamp: data.timestamp,
            sceneLabel: '原始数据',
            sceneLabelColor: 'text-amber-600',
            hex,
            badge: '成功',
            badgeClass: 'bg-emerald-50 text-emerald-600'
        });
    }

    function renderHistoryEntry(item) {
        const direction = item.direction || item.history_type;
        if (item.history_type === 'raw' || item.data_hex) {
            const matchedPacket = item.data_hex && historyPacketHexSet.has(item.data_hex);
            if (matchedPacket) return;
            addReceivedRaw(item);
            return;
        }
        if (direction === 'recv' || item.history_type === 'packet' || item.parsed) {
            addReceived(item);
            return;
        }
        addSent(item);
    }

    // ==================== 通用方法 ====================
    function addFromAuto(data) {
        addSent(data);
    }

    function loadHistory(force) {
        fetch('/api/history?limit=200').then(r => r.json()).then(data => {
            const list = document.getElementById('historyList');

            // 手动刷新时强制重新加载；自动加载时如果已有实时数据则跳过
            if (!force && hasRealtimeUpdates && list.querySelector('.history-item')) {
                document.getElementById('historyCount').textContent = `(${list.children.length})`;
                return;
            }

            if (data.length === 0) {
                setEmptyState();
                return;
            }
            historyPacketHexSet = new Set(
                data
                    .filter(item => item.history_type === 'packet' && item.parsed?.raw_hex)
                    .map(item => item.parsed.raw_hex)
            );
            list.innerHTML = '';
            data.forEach(item => renderHistoryEntry(item));
        });
    }

    function clearHistory() {
        fetch('/api/clear_history', {method: 'POST'}).then(() => {
            recvRawTimers.forEach(timerId => window.clearTimeout(timerId));
            recvRawTimers.clear();
            historyPacketHexSet = new Set();
            setEmptyState();
            showToast('历史已清空', 'info');
        });
    }

    // ==================== 应用HEX到数据包详情 ====================
    function applyHex(btn) {
        const hexBox = btn.closest('.raw-hex-box-wrapper').querySelector('.raw-hex-box');
        const hexText = hexBox.textContent.trim().replace(/\s+/g, '');
        if (!hexText) {
            showToast('无HEX数据', 'error');
            return;
        }
        fetch('/api/parse_hex', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({hex: hexText})
        })
        .then(r => r.json())
        .then(result => {
            if (result.success) {
                const data = result.parsed;
                renderPacketDetail(data);
                window.currentHex = data.raw_hex;
                // 滚动到数据包详情区域
                document.getElementById('packetDetails').scrollIntoView({behavior: 'smooth', block: 'start'});
                showToast('已应用到数据包详情', 'success');
            } else {
                showToast(`解析失败: ${result.error}`, 'error');
            }
        })
        .catch(() => showToast('解析请求失败', 'error'));
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function renderField(field) {
        const mono = field.mono ? 'font-mono' : '';
        const accent = field.accent === 'primary'
            ? 'text-jd-primary'
            : field.accent === 'danger'
                ? 'text-jd-danger'
                : 'text-jd-text';
        return `
            <div class="bg-white rounded-lg border border-jd-cardBorder px-3 py-1.5">
                <div class="text-[11px] text-jd-textMuted mb-0.5">${escapeHtml(field.label)}</div>
                <div class="text-sm ${mono} font-medium ${accent} break-all">${escapeHtml(field.value)}</div>
            </div>
        `;
    }

    function renderFlags(flags) {
        if (!flags || !flags.length) return '';
        return `
            <div class="space-y-1">
                <div class="text-xs font-medium text-jd-text">状态位解码</div>
                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-1">
                    ${flags.map(flag => `
                        <div class="rounded-lg border px-3 py-1.5 ${flag.active ? 'border-amber-200 bg-amber-50' : 'border-jd-cardBorder bg-white'}">
                            <div class="flex items-center justify-between gap-2">
                                <span class="text-[11px] text-jd-textMuted">bit${flag.bit} · ${escapeHtml(flag.label)}</span>
                                <span class="text-[10px] px-1.5 py-0.5 rounded-full ${flag.active ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-jd-textMuted'}">${flag.active ? '1' : '0'}</span>
                            </div>
                            <div class="text-sm font-medium ${flag.active ? 'text-amber-700' : 'text-jd-text'} mt-0.5">${escapeHtml(flag.text)}</div>
                        </div>
                    `).join('')}
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
        return 'normal';
    }

    function getObjectCardStyle(severity) {
        if (severity === 'alarm') {
            return {
                wrap: 'border-red-200 bg-red-50/70',
                badge: 'bg-red-100 text-red-700',
                title: 'text-red-700'
            };
        }
        if (severity === 'fault') {
            return {
                wrap: 'border-amber-200 bg-amber-50/70',
                badge: 'bg-amber-100 text-amber-700',
                title: 'text-amber-700'
            };
        }
        if (severity === 'recovery') {
            return {
                wrap: 'border-emerald-200 bg-emerald-50/70',
                badge: 'bg-emerald-100 text-emerald-700',
                title: 'text-emerald-700'
            };
        }
        if (severity === 'duty') {
            return {
                wrap: 'border-sky-200 bg-sky-50/70',
                badge: 'bg-sky-100 text-sky-700',
                title: 'text-sky-700'
            };
        }
        return {
            wrap: 'border-jd-cardBorder bg-jd-content/50',
            badge: 'bg-slate-100 text-jd-textMuted',
            title: 'text-jd-text'
        };
    }

    function renderObjectCard(obj) {
        const severity = getObjectSeverity(obj);
        const style = getObjectCardStyle(severity);
        const severityLabel = severity === 'alarm'
            ? '火警'
            : severity === 'fault'
                ? '故障'
                : severity === 'recovery'
                    ? '恢复'
                    : severity === 'duty'
                        ? '查岗'
                        : '信息';
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
                    ${(obj.fields || []).map(renderField).join('')}
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

    // 当前缓存的 ADU 数据（供弹窗使用）
    let cachedAduData = null;

    function openAduModal() {
        if (!cachedAduData) return;
        const adu = cachedAduData;
        const aduObjects = adu.objects || [];
        const modal = document.getElementById('aduModal');
        const title = document.getElementById('aduModalTitle');
        const badge = document.getElementById('aduModalBadge');
        const content = document.getElementById('aduModalContent');

        title.textContent = adu.type_flag_name || '应用数据单元';
        badge.textContent = `${aduObjects.length} 个对象`;

        content.innerHTML = `
            <div class="space-y-2">
                <div class="grid grid-cols-5 gap-1.5">
                    ${[
                        { label: '方向', value: adu.direction },
                        { label: '类型标志', value: `${adu.type_flag} / ${adu.type_flag_name}`, mono: true, accent: 'primary' },
                        { label: '类型来源', value: adu.type_origin_label || '-', accent: adu.type_origin_label === '厂商扩展' ? 'primary' : '' },
                        { label: '信息对象数', value: adu.info_count, mono: true },
                        { label: '负载长度', value: `${adu.payload_length}B`, mono: true }
                    ].map(renderField).join('')}
                </div>
                ${aduObjects.length ? `
                    <div class="space-y-2">
                        ${aduObjects.map(renderObjectCard).join('')}
                    </div>
                ` : `
                    <div class="rounded-lg border border-jd-cardBorder bg-white px-3 py-2 text-sm text-jd-textMuted">
                        当前 ADU 无信息对象，常见于确认、否认或保留命令。
                    </div>
                `}
                ${renderNotes(adu.notes)}
                ${adu.payload_hex ? `
                <section class="space-y-1">
                    <div class="text-xs text-jd-textMuted">ADU 负载 HEX</div>
                    <div class="raw-hex-box hex-display">${SceneModule.formatHex(adu.payload_hex)}</div>
                </section>
                ` : ''}
            </div>
        `;

        modal.classList.remove('hidden');
    }

    function closeAduModal() {
        document.getElementById('aduModal').classList.add('hidden');
    }

    function renderPacketDetail(data) {
        const sceneLabel = document.getElementById('currentSceneName');
        const titleName = data.type_flag_name || data.command_name || '未知';
        if (sceneLabel) {
            sceneLabel.textContent = titleName;
            if (titleName === '未知' || titleName.startsWith('未知')) {
                sceneLabel.className = 'text-xs px-1 py-0.5 rounded bg-slate-100 text-jd-textMuted';
            } else {
                sceneLabel.className = 'text-xs px-2 py-0.5 rounded-full bg-jd-primaryLight text-jd-primary';
            }
        }
        const details = document.getElementById('packetDetails');
        const adu = data.adu_parsed || null;
        const summary = adu?.summary_short || data.command_name || data.type_flag_name || '无 ADU';
        const directionName = data.direction_name || adu?.direction || '-';
        const typeOriginLabel = adu?.type_origin_label || '';

        // 缓存 ADU 数据供弹窗使用
        cachedAduData = adu;
        const hasAdu = !!adu;
        details.innerHTML = `
            <div class="space-y-5">
                <section class="space-y-3">
                    <div class="flex items-center justify-between gap-3 flex-wrap">
                        <div>
                            <div class="text-xs text-jd-textMuted">控制单元</div>
                            <div class="text-sm font-semibold text-jd-text mt-1">${escapeHtml(summary)}</div>
                        </div>
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-[11px] px-2 py-1 rounded-full bg-slate-100 text-jd-textMuted">${escapeHtml(directionName)}</span>
                            <span class="text-[11px] px-2 py-1 rounded-full bg-jd-primaryLight text-jd-primary">${escapeHtml(data.command_name || '未知命令')}</span>
                            ${typeOriginLabel ? `<span class="text-[11px] px-2 py-1 rounded-full ${typeOriginLabel === '厂商扩展' ? 'bg-violet-50 text-violet-700' : 'bg-emerald-50 text-emerald-700'}">${escapeHtml(typeOriginLabel)}</span>` : ''}
                            <span class="text-[11px] px-2 py-1 rounded-full bg-white border border-jd-cardBorder text-jd-textMuted">ADU ${data.adu_length || 0}B</span>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 xl:grid-cols-4 gap-2">
                        <div class="bg-jd-content rounded-lg p-3">
                            <div class="text-xs text-jd-textMuted mb-1">业务流水号</div>
                            <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(data.sequence)}</div>
                        </div>
                        <div class="bg-jd-content rounded-lg p-3">
                            <div class="text-xs text-jd-textMuted mb-1">协议版本</div>
                            <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(`${data.version_major}.${data.version_minor}`)}</div>
                        </div>
                        <div class="bg-jd-content rounded-lg p-3">
                            <div class="text-xs text-jd-textMuted mb-1">时间标签</div>
                            <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(data.time_tag)}</div>
                        </div>
                        <div class="bg-jd-content rounded-lg p-3">
                            <div class="text-xs text-jd-textMuted mb-1">命令字节</div>
                            <div class="text-sm font-mono font-medium text-jd-text">0x${Number(data.command || 0).toString(16).padStart(2, '0')} (${escapeHtml(data.command_name || '未知')})</div>
                        </div>
                        <div class="bg-jd-content rounded-lg p-3">
                            <div class="text-xs text-jd-textMuted mb-1">源地址</div>
                            <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(data.source_addr)}</div>
                        </div>
                        <div class="bg-jd-content rounded-lg p-3">
                            <div class="text-xs text-jd-textMuted mb-1">目的地址</div>
                            <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(data.dest_addr)}</div>
                        </div>
                        <div class="bg-jd-content rounded-lg p-3">
                            <div class="text-xs text-jd-textMuted mb-1">类型标志</div>
                            <div class="text-sm font-mono font-medium text-jd-primary">${escapeHtml(`${data.type_flag ?? '-'} (${data.type_flag_name || '无'})`)}</div>
                        </div>
                        <div class="${hasAdu ? 'bg-jd-primaryLight border border-jd-primaryBorder cursor-pointer hover:bg-blue-100 transition-colors' : 'bg-jd-content'} rounded-lg p-3" ${hasAdu ? `onclick="HistoryModule.openAduModal()" title="点击查看应用数据单元详情"` : ''}>
                            <div class="text-xs ${hasAdu ? 'text-jd-primary' : 'text-jd-textMuted'} mb-1">信息对象数${hasAdu ? ' ↗' : ''}</div>
                            <div class="flex items-center gap-1.5">
                                <span class="text-sm font-mono font-semibold ${hasAdu ? 'text-jd-primary' : 'text-jd-text'}">${escapeHtml(data.info_count ?? 0)}</span>
                                ${hasAdu ? '<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-jd-primary/10 text-jd-primary font-medium">查看ADU</span>' : ''}
                            </div>
                            ${(() => { const _l = (adu?.objects || []).flatMap(o => (o.status_flags || []).filter(f => f.active).map(f => f.on)).slice(0, 3); return _l.length ? `<div class="text-[10px] text-amber-600 mt-1.5 truncate">${_l.map(s => escapeHtml(s)).join(' / ')}</div>` : ''; })()}
                        </div>
                    </div>
                </section>

                <section class="space-y-2">
                    <div class="text-xs text-jd-textMuted">原始报文 (${escapeHtml(data.raw_length)} 字节)</div>
                    <div class="raw-hex-box hex-display">${SceneModule.formatHex(data.raw_hex)}</div>
                </section>
            </div>
        `;
    }

    // ==================== 复制HEX ====================
    function copyHex(btn) {
        const hexBox = btn.closest('.raw-hex-box-wrapper').querySelector('.raw-hex-box');
        const text = hexBox.textContent.trim();
        navigator.clipboard.writeText(text).then(() => {
            showToast('HEX已复制', 'success');
        }).catch(() => {
            // fallback
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            showToast('HEX已复制', 'success');
        });
    }

    function toggleSaveMenu(event) {
        event.stopPropagation();
        const menu = document.getElementById('saveHistoryMenu');
        menu.classList.toggle('hidden');
    }

    function saveHistory() {
        document.getElementById('saveHistoryMenu').classList.add('hidden');
        fetch('/api/history/save', {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showToast(`保存成功，共 ${data.total_count} 条记录`, 'success');
                } else {
                    showToast(data.error || '保存失败', 'error');
                }
            })
            .catch(() => showToast('保存请求失败', 'error'));
    }

    function exportHistory(format) {
        document.getElementById('saveHistoryMenu').classList.add('hidden');
        window.location.href = `/api/history/export?format=${format}`;
    }

    return {
        init,
        loadHistory,
        clearHistory,
        addFromAuto,
        addReceived,
        addReceivedRaw,
        copyHex,
        applyHex,
        renderPacketDetail,
        openAduModal,
        closeAduModal,
        toggleSaveMenu,
        saveHistory,
        exportHistory
    };
})();
