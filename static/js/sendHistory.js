const SendHistoryModule = (function() {
    let currentHistoryId = null;
    let currentRecords = [];
    let allHistories = [];
    let currentFilter = 'all';

    function init() {
        document.addEventListener('click', function(e) {
            const menu = document.getElementById('saveHistoryMenu');
            if (menu && !e.target.closest('#saveHistoryBtn') && !e.target.closest('#saveHistoryMenu')) {
                menu.classList.add('hidden');
            }
        });
    }

    function loadHistoryList() {
        fetch('/api/history/list')
            .then(r => r.json())
            .then(data => {
                allHistories = data.histories || [];
                renderHistoryList(allHistories);
                document.getElementById('savedHistoryBadge').textContent = `${allHistories.length} 条`;
            })
            .catch(() => {
                document.getElementById('savedHistoryList').innerHTML =
                    '<div class="text-center text-jd-textMuted text-sm py-8">加载失败，请重试</div>';
            });
    }

    function filterList(keyword) {
        const kw = keyword.trim().toLowerCase();
        if (!kw) {
            renderHistoryList(allHistories);
            return;
        }
        const filtered = allHistories.filter(h => {
            return h.id.toLowerCase().includes(kw) || (h.save_time || '').toLowerCase().includes(kw);
        });
        renderHistoryList(filtered);
    }

    function renderHistoryList(histories) {
        const container = document.getElementById('savedHistoryList');
        if (!histories.length) {
            container.innerHTML = '<div class="text-center text-jd-textMuted text-sm py-8">暂无保存的发送历史</div>';
            return;
        }

        container.innerHTML = histories.map(h => {
            const isActive = h.id === currentHistoryId;
            const corrupted = h.corrupted ? '<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-600 ml-1">已损坏</span>' : '';
            const timeStr = formatTime(h.save_time);
            const datePart = timeStr ? timeStr.split(' ')[0] : '';
            const timePart = timeStr ? timeStr.split(' ')[1] : '';

            return `
                <div class="rounded-lg border p-3 cursor-pointer transition-all ${isActive ? 'border-jd-primary bg-jd-primaryLight/30 shadow-sm' : 'border-jd-cardBorder bg-white hover:border-jd-cardBorder/80 hover:shadow-sm'}"
                     onclick="SendHistoryModule.viewHistory('${h.id}')">
                    <div class="flex items-start justify-between mb-2">
                        <div class="flex items-center gap-1.5 min-w-0">
                            <svg class="w-3.5 h-3.5 text-jd-primary shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                            </svg>
                            <span class="text-xs font-semibold text-jd-text truncate">${datePart || h.id.replace('history_', '')}</span>
                            ${corrupted}
                        </div>
                        <button class="w-5 h-5 rounded hover:bg-red-50 flex items-center justify-center text-jd-textMuted hover:text-red-500 transition-colors shrink-0 opacity-0 group-hover:opacity-100"
                                style="opacity:0" onmouseenter="this.style.opacity=1" onmouseleave="this.style.opacity=0"
                                onclick="event.stopPropagation(); SendHistoryModule.deleteHistory('${h.id}')" title="删除">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="flex items-center gap-2 text-[11px] text-jd-textMuted mb-2">
                        <svg class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        <span>${timePart || '未知'}</span>
                    </div>
                    <div class="flex items-center gap-1.5 text-[10px]">
                        <span class="px-1.5 py-0.5 rounded-full bg-jd-primaryLight text-jd-primary font-medium">${h.total_count} 条</span>
                        <span class="px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600">↑${h.send_count}</span>
                        <span class="px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600">↓${h.recv_count}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    function formatTime(timeStr) {
        if (!timeStr) return '';
        return timeStr.replace(/\.\d+$/, '').trim();
    }

    function viewHistory(historyId) {
        fetch(`/api/history/saved/${historyId}`)
            .then(r => {
                if (!r.ok) throw new Error('记录不存在');
                return r.json();
            })
            .then(data => {
                currentHistoryId = historyId;
                currentRecords = data.records || [];
                currentFilter = 'all';

                document.getElementById('savedHistoryEmpty').classList.add('hidden');
                document.getElementById('savedHistoryDetail').classList.remove('hidden');

                const meta = data.metadata || {};
                const timeStr = formatTime(meta.save_time || '');
                const datePart = timeStr ? timeStr.split(' ')[0] : '';
                const timePart = timeStr ? timeStr.split(' ')[1] : '';

                document.getElementById('savedHistoryTitle').textContent = `${datePart} ${timePart}`;
                document.getElementById('savedHistoryCount').textContent = `${meta.total_count || currentRecords.length} 条`;

                document.getElementById('savedHistoryMeta').innerHTML = `
                    <span class="flex items-center gap-1 text-jd-textMuted">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        保存于 ${timeStr || '未知'}
                    </span>
                    <span class="text-jd-textMuted opacity-40">|</span>
                    <span class="px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600 text-[10px]">发送 ${meta.send_count || 0}</span>
                    <span class="px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 text-[10px]">接收 ${meta.recv_count || 0}</span>
                    <span class="text-jd-textMuted opacity-40">|</span>
                    <span class="text-jd-textMuted">${meta.source || ''}</span>
                `;

                resetFilterTabs();
                renderFilteredRecords();

                renderHistoryList(allHistories);
            })
            .catch(err => {
                showToast(err.message || '加载历史详情失败', 'error');
            });
    }

    function resetFilterTabs() {
        document.querySelectorAll('#savedHistoryDetail .scene-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === 'all');
        });
    }

    function filterRecords(filter) {
        currentFilter = filter;
        document.querySelectorAll('#savedHistoryDetail .scene-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });
        renderFilteredRecords();
    }

    function renderFilteredRecords() {
        let records = currentRecords;
        if (currentFilter === 'send') {
            records = records.filter(r => (r.direction || r.history_type) === 'send');
        } else if (currentFilter === 'recv') {
            records = records.filter(r => (r.direction || r.history_type) !== 'send');
        }

        document.getElementById('savedHistoryFilterCount').textContent = `显示 ${records.length} / ${currentRecords.length} 条`;
        renderSavedRecords(records);
    }

    function renderSavedRecords(records) {
        const container = document.getElementById('savedHistoryRecords');
        if (!records.length) {
            container.innerHTML = `
                <div class="text-center text-jd-textMuted text-sm py-8">
                    <svg class="w-8 h-8 text-jd-cardBorder mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                    <p>无匹配的记录</p>
                </div>
            `;
            return;
        }

        container.innerHTML = records.map((item, idx) => {
            const direction = item.direction || item.history_type || '';
            const isSend = direction === 'send';
            const isRaw = item.history_type === 'raw' || item.data_hex;
            const label = isSend ? '发送' : '接收';
            const labelClass = isSend
                ? 'bg-emerald-50 text-emerald-600'
                : (isRaw ? 'bg-amber-50 text-amber-600' : 'bg-blue-50 text-blue-600');
            const dotClass = isSend
                ? 'bg-emerald-400'
                : (isRaw ? 'bg-amber-400' : 'bg-blue-400');

            const source = isSend ? '本机' : `${item.host || ''}:${item.port || ''}`;
            const target = isSend ? `${item.host || ''}:${item.port || ''}` : '本机';
            const protocol = (item.protocol || '').toUpperCase();
            const size = isSend ? `${item.length || 0}B` : `${(item.parsed && item.parsed.raw_length) || item.data_length || 0}B`;
            const timestamp = item.timestamp || '';
            const hex = item.hex || item.data_hex || (item.parsed && item.parsed.raw_hex) || '';

            const sceneName = item.scene_name || item.step_name || '';
            const parsedSummary = item.parsed
                ? (item.parsed.adu_summary || item.parsed.type_flag_name || item.parsed.command_name || '')
                : '';
            const sceneLabel = sceneName || parsedSummary || (isRaw ? '原始数据' : '');

            const badge = isSend ? (item.success !== false ? '成功' : '失败') : '成功';
            const badgeClass = isSend
                ? (item.success !== false ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600')
                : 'bg-emerald-50 text-emerald-600';

            const arrowSvg = isSend
                ? '<svg class="w-3 h-3 text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>'
                : '<svg class="w-3 h-3 text-blue-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M11 17l-5-5m0 0l5-5m-5 5h12"/></svg>';

            const hexDisplay = hex
                ? `<div class="raw-hex-box-wrapper mt-1"><div class="raw-hex-box text-[10px]">${hex}</div></div>`
                : '';

            return `
                <div class="history-item flex items-center gap-2.5 px-3 py-2 rounded-lg border-b border-jd-cardBorder last:border-0">
                    <span class="text-[10px] text-jd-textMuted w-6 text-right shrink-0 tabular-nums">${idx + 1}</span>
                    <div class="w-2 h-2 rounded-full ${dotClass} shrink-0"></div>
                    <span class="text-xs font-medium px-1.5 py-0.5 rounded ${labelClass} shrink-0">${label}</span>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-1.5 text-xs text-jd-textMuted flex-wrap">
                            <span class="truncate max-w-[100px]" title="${source}">${source}</span>
                            ${arrowSvg}
                            <span class="truncate max-w-[100px]" title="${target}">${target}</span>
                            <span class="text-jd-textMuted opacity-40">|</span>
                            <span class="whitespace-nowrap">${timestamp}</span>
                            <span class="text-jd-textMuted opacity-40">|</span>
                            <span>${size}</span>
                            ${protocol ? `<span class="text-jd-textMuted opacity-40">|</span><span class="px-1 py-0.5 rounded bg-slate-100 text-jd-textMuted">${protocol}</span>` : ''}
                            ${sceneLabel ? `<span class="text-jd-textMuted opacity-40">|</span><span class="font-medium ${isSend ? 'text-emerald-600' : (isRaw ? 'text-amber-600' : 'text-jd-text')}">${sceneLabel}</span>` : ''}
                        </div>
                        ${hexDisplay}
                    </div>
                    <span class="text-xs px-2 py-0.5 rounded-full shrink-0 ${badgeClass}">${badge}</span>
                </div>
            `;
        }).join('');
    }

    function deleteHistory(historyId) {
        ConfirmDialog.show({
            title: '删除历史记录',
            message: '确定要删除此历史记录吗？此操作不可恢复。',
            type: 'danger',
            confirmText: '删除'
        }).then(ok => {
            if (!ok) return;
            fetch(`/api/history/saved/${historyId}`, {method: 'DELETE'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showToast('删除成功', 'success');
                        if (currentHistoryId === historyId) {
                            currentHistoryId = null;
                            currentRecords = [];
                            document.getElementById('savedHistoryDetail').classList.add('hidden');
                            document.getElementById('savedHistoryEmpty').classList.remove('hidden');
                        }
                        loadHistoryList();
                    } else {
                        showToast(data.error || '删除失败', 'error');
                    }
                })
                .catch(() => showToast('删除请求失败', 'error'));
        });
    }

    function deleteCurrent() {
        if (!currentHistoryId) return;
        deleteHistory(currentHistoryId);
    }

    function exportCurrent(format) {
        if (!currentHistoryId) return;
        window.location.href = `/api/history/saved/${currentHistoryId}/export?format=${format}`;
    }

    return {
        init,
        loadHistoryList,
        filterList,
        viewHistory,
        filterRecords,
        backToList: loadHistoryList,
        deleteHistory,
        deleteCurrent,
        exportCurrent
    };
})();
