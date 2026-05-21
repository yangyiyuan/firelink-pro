const ParseModule = (function() {
    let currentResult = null;
    const HISTORY_KEY = 'parse_history';
    const MAX_HISTORY = 50;

    function init() {
        loadHistory();
        const input = document.getElementById('parseHexInput');
        if (input) {
            input.addEventListener('input', updateInputHint);
            input.addEventListener('paste', function() {
                setTimeout(formatInput, 50);
            });
        }
    }

    function sanitizeHex(input) {
        return input.replace(/[^0-9a-fA-F]/g, '').toLowerCase();
    }

    function validateHex(hex) {
        if (!hex || hex.length === 0) return { valid: false, error: '请输入十六进制报文' };
        if (!/^[0-9a-f]+$/.test(hex)) return { valid: false, error: '包含非法字符，仅允许 0-9 和 a-f' };
        if (hex.length % 2 !== 0) return { valid: false, error: '十六进制长度必须为偶数' };
        if (hex.length < 60) return { valid: false, error: '数据包长度不足，至少需要 30 字节（60 个十六进制字符）' };
        if (!hex.startsWith('4040')) return { valid: false, error: '启动符错误，应以 40 40 开头' };
        if (!hex.endsWith('2323')) return { valid: false, error: '结束符错误，应以 23 23 结尾' };
        return { valid: true };
    }

    function formatInput() {
        const input = document.getElementById('parseHexInput');
        if (!input) return;
        const raw = input.value;
        const cleaned = sanitizeHex(raw);
        input.value = cleaned;
        updateInputHint();
        if (cleaned && cleaned !== sanitizeHex(raw)) {
            showToast('已自动清洗输入', 'info');
        }
    }

    function clearInput() {
        const input = document.getElementById('parseHexInput');
        if (input) input.value = '';
        updateInputHint();
    }

    function updateInputHint() {
        const input = document.getElementById('parseHexInput');
        const hint = document.getElementById('parseInputHint');
        if (!input || !hint) return;
        const hex = sanitizeHex(input.value);
        if (!hex) {
            hint.textContent = '';
            hint.className = 'text-xs text-jd-textMuted';
            return;
        }
        const byteCount = hex.length / 2;
        hint.textContent = `${hex.length} 字符 / ${byteCount} 字节`;
        hint.className = 'text-xs ' + (hex.length % 2 !== 0 ? 'text-jd-danger' : 'text-jd-textMuted');
    }

    async function parsePacket() {
        const input = document.getElementById('parseHexInput');
        if (!input) return;
        const hex = sanitizeHex(input.value);
        input.value = hex;

        const validation = validateHex(hex);
        if (!validation.valid) {
            showToast(validation.error, 'error');
            return;
        }

        const btn = document.getElementById('parseBtn');
        const btnText = document.getElementById('parseBtnText');
        if (btn) btn.disabled = true;
        if (btnText) btnText.textContent = '解析中...';

        try {
            const resp = await fetch('/api/parse_hex', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hex: hex })
            });

            if (!resp.ok) throw new Error('网络请求失败');

            const data = await resp.json();

            if (data.success) {
                currentResult = data.parsed;
                renderResult(data.parsed);
                saveToHistory(hex, data.parsed);
                showToast('解析成功', 'success');
            } else {
                renderError(data.error || '解析失败');
                showToast(data.error || '解析失败', 'error');
            }
        } catch (err) {
            showToast('网络错误，请检查服务是否启动', 'error');
            renderError('网络请求失败: ' + err.message);
        } finally {
            if (btn) btn.disabled = false;
            if (btnText) btnText.textContent = '解析';
        }
    }

    function escapeHtml(str) {
        if (str == null) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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

    function renderField(field) {
        const mono = field.mono ? 'font-mono' : '';
        const accent = field.accent === 'primary'
            ? 'text-jd-primary'
            : field.accent === 'danger'
                ? 'text-jd-danger'
                : field.accent === 'warning'
                    ? 'text-jd-warning'
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
        if (severity === 'alarm') return { wrap: 'border-red-200 bg-red-50/70', badge: 'bg-red-100 text-red-700', title: 'text-red-700' };
        if (severity === 'fault') return { wrap: 'border-amber-200 bg-amber-50/70', badge: 'bg-amber-100 text-amber-700', title: 'text-amber-700' };
        if (severity === 'recovery') return { wrap: 'border-emerald-200 bg-emerald-50/70', badge: 'bg-emerald-100 text-emerald-700', title: 'text-emerald-700' };
        if (severity === 'duty') return { wrap: 'border-sky-200 bg-sky-50/70', badge: 'bg-sky-100 text-sky-700', title: 'text-sky-700' };
        return { wrap: 'border-jd-cardBorder bg-jd-content/50', badge: 'bg-slate-100 text-jd-textMuted', title: 'text-jd-text' };
    }

    function renderObjectCard(obj) {
        const severity = getObjectSeverity(obj);
        const style = getObjectCardStyle(severity);
        const severityLabel = severity === 'alarm' ? '火警'
            : severity === 'fault' ? '故障'
            : severity === 'recovery' ? '恢复'
            : severity === 'duty' ? '查岗'
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

    function renderResult(parsed) {
        const emptyEl = document.getElementById('parseResultEmpty');
        const contentEl = document.getElementById('parseResultContent');
        if (emptyEl) emptyEl.classList.add('hidden');
        if (contentEl) contentEl.classList.remove('hidden');

        renderOverview(parsed);
        renderControlUnit(parsed);
        renderADU(parsed);
    }

    function renderOverview(parsed) {
        const el = document.getElementById('parseOverview');
        if (!el) return;

        const startOk = parsed.raw_hex && parsed.raw_hex.startsWith('4040');
        const endOk = parsed.raw_hex && parsed.raw_hex.endsWith('2323');

        el.innerHTML = `
            <div class="h-10 px-4 border-b border-jd-cardBorder flex items-center gap-2 shrink-0">
                <svg class="w-4 h-4 text-jd-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <h3 class="text-sm font-semibold text-jd-text">数据包总览</h3>
            </div>
            <div class="p-4 space-y-3">
                <div class="grid grid-cols-2 xl:grid-cols-4 gap-2">
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">启动符</div>
                        <div class="flex items-center gap-1.5">
                            <span class="text-sm font-mono font-medium text-jd-text">40 40</span>
                            <span class="text-[10px] px-1.5 py-0.5 rounded-full ${startOk ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}">${startOk ? '✓' : '✗'}</span>
                        </div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">结束符</div>
                        <div class="flex items-center gap-1.5">
                            <span class="text-sm font-mono font-medium text-jd-text">23 23</span>
                            <span class="text-[10px] px-1.5 py-0.5 rounded-full ${endOk ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}">${endOk ? '✓' : '✗'}</span>
                        </div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">总长度</div>
                        <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(parsed.raw_length)} 字节</div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">校验和</div>
                        <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(parsed.checksum || '-')}</div>
                    </div>
                </div>
                <div class="space-y-1">
                    <div class="text-xs text-jd-textMuted">原始报文 HEX</div>
                    <div class="raw-hex-box hex-display">${formatHex(parsed.raw_hex)}</div>
                </div>
            </div>
        `;
    }

    function renderControlUnit(parsed) {
        const el = document.getElementById('parseControlUnit');
        if (!el) return;

        el.innerHTML = `
            <div class="h-10 px-4 border-b border-jd-cardBorder flex items-center gap-2 shrink-0">
                <svg class="w-4 h-4 text-jd-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                <h3 class="text-sm font-semibold text-jd-text">控制单元 (25 字节)</h3>
            </div>
            <div class="p-4">
                <div class="grid grid-cols-2 xl:grid-cols-4 gap-2">
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">业务流水号</div>
                        <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(parsed.sequence)}</div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">协议版本</div>
                        <div class="text-sm font-mono font-medium text-jd-text">V${escapeHtml(parsed.version_major)}.${escapeHtml(parsed.version_minor)}</div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">时间标签</div>
                        <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(parsed.time_tag)}</div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">命令</div>
                        <div class="text-sm font-mono font-medium text-jd-text">0x${Number(parsed.command || 0).toString(16).padStart(2, '0')} (${escapeHtml(parsed.command_name || '未知')})</div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">源地址</div>
                        <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(parsed.source_addr)}</div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">目的地址</div>
                        <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(parsed.dest_addr)}</div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">ADU 长度</div>
                        <div class="text-sm font-mono font-medium text-jd-text">${escapeHtml(parsed.adu_length)} 字节</div>
                    </div>
                    <div class="bg-jd-content rounded-lg p-3">
                        <div class="text-xs text-jd-textMuted mb-1">类型标志</div>
                        <div class="text-sm font-mono font-medium text-jd-primary">${escapeHtml(parsed.type_flag ?? '-')} (${escapeHtml(parsed.type_flag_name || '无')})</div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderADU(parsed) {
        const el = document.getElementById('parseADU');
        if (!el) return;

        const adu = parsed.adu_parsed || null;
        if (!adu) {
            el.innerHTML = `
                <div class="h-10 px-4 border-b border-jd-cardBorder flex items-center gap-2 shrink-0">
                    <svg class="w-4 h-4 text-jd-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/>
                    </svg>
                    <h3 class="text-sm font-semibold text-jd-text">应用数据单元 (ADU)</h3>
                </div>
                <div class="p-4">
                    <div class="text-sm text-jd-textMuted text-center py-6">当前报文无 ADU 数据</div>
                </div>
            `;
            return;
        }

        const aduObjects = adu.objects || [];
        const directionName = adu.direction || parsed.direction_name || '-';
        const typeOriginLabel = adu.type_origin_label || '';
        const profileName = adu.profile_name || '';

        el.innerHTML = `
            <div class="h-10 px-4 border-b border-jd-cardBorder flex items-center justify-between shrink-0">
                <div class="flex items-center gap-2">
                    <svg class="w-4 h-4 text-jd-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/>
                    </svg>
                    <h3 class="text-sm font-semibold text-jd-text">应用数据单元 (ADU)</h3>
                    <span class="text-[11px] px-2 py-0.5 rounded-full bg-jd-primaryLight text-jd-primary">${aduObjects.length} 个对象</span>
                </div>
                <div class="flex items-center gap-1.5">
                    <span class="text-[11px] px-2 py-1 rounded-full bg-slate-100 text-jd-textMuted">${escapeHtml(directionName)}</span>
                    ${typeOriginLabel ? `<span class="text-[11px] px-2 py-1 rounded-full ${typeOriginLabel === '厂商扩展' ? 'bg-violet-50 text-violet-700' : 'bg-emerald-50 text-emerald-700'}">${escapeHtml(typeOriginLabel)}</span>` : ''}
                    ${profileName ? `<span class="text-[11px] px-2 py-1 rounded-full bg-white border border-jd-cardBorder text-jd-textMuted">${escapeHtml(profileName)}</span>` : ''}
                </div>
            </div>
            <div class="p-4 space-y-3">
                <div class="grid grid-cols-5 gap-1.5">
                    ${[
                        { label: '方向', value: directionName },
                        { label: '类型标志', value: `${adu.type_flag} / ${adu.type_flag_name}`, mono: true, accent: 'primary' },
                        { label: '类型来源', value: typeOriginLabel || '-', accent: typeOriginLabel === '厂商扩展' ? 'primary' : '' },
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
                    <div class="raw-hex-box hex-display">${formatHex(adu.payload_hex)}</div>
                </section>
                ` : ''}
            </div>
        `;
    }

    function renderError(errorMsg) {
        const emptyEl = document.getElementById('parseResultEmpty');
        const contentEl = document.getElementById('parseResultContent');
        if (emptyEl) emptyEl.classList.add('hidden');
        if (contentEl) contentEl.classList.remove('hidden');

        const overviewEl = document.getElementById('parseOverview');
        const controlEl = document.getElementById('parseControlUnit');
        const aduEl = document.getElementById('parseADU');

        if (overviewEl) overviewEl.innerHTML = '';
        if (controlEl) controlEl.innerHTML = '';
        if (aduEl) aduEl.innerHTML = '';

        if (overviewEl) {
            overviewEl.innerHTML = `
                <div class="p-5">
                    <div class="flex items-start gap-3">
                        <div class="w-9 h-9 rounded-full bg-red-50 flex items-center justify-center shrink-0">
                            <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                            </svg>
                        </div>
                        <div>
                            <h4 class="text-sm font-semibold text-red-700">解析失败</h4>
                            <p class="text-xs text-jd-textSecondary mt-1">${escapeHtml(errorMsg)}</p>
                            <p class="text-xs text-jd-textMuted mt-2">请检查报文格式是否正确，确保包含完整的启动符、控制单元、ADU、校验和和结束符。</p>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    function saveToHistory(hex, parsed) {
        let history = [];
        try {
            history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
        } catch (e) {
            history = [];
        }

        const summary = parsed.adu_summary || parsed.type_flag_name || parsed.command_name || '未知';
        const entry = {
            id: 'ph_' + Date.now(),
            hex: hex,
            summary: summary,
            type_flag_name: parsed.type_flag_name || '',
            command_name: parsed.command_name || '',
            parsed_at: new Date().toLocaleString('zh-CN', { hour12: false }),
            success: true
        };

        history.unshift(entry);
        if (history.length > MAX_HISTORY) {
            history = history.slice(0, MAX_HISTORY);
        }

        try {
            localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
        } catch (e) {
            if (history.length > 10) {
                history = history.slice(0, 10);
                localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
            }
        }

        loadHistory();
    }

    function loadHistory() {
        let history = [];
        try {
            history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
        } catch (e) {
            history = [];
        }

        const container = document.getElementById('parseHistoryList');
        if (!container) return;

        if (!history.length) {
            container.innerHTML = '<div class="text-center text-jd-textMuted text-xs py-6">暂无解析历史</div>';
            return;
        }

        container.innerHTML = history.map((item, idx) => {
            const hexShort = item.hex ? item.hex.substring(0, 16) + '...' : '';
            return `
                <div class="rounded-lg border border-jd-cardBorder bg-white p-2.5 cursor-pointer hover:border-jd-cardBorder/80 hover:shadow-sm transition-all"
                     onclick="ParseModule.loadFromHistory(${idx})">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-[10px] px-1.5 py-0.5 rounded-full ${item.success ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}">${item.success ? '成功' : '失败'}</span>
                        <span class="text-[10px] text-jd-textMuted">${escapeHtml(item.parsed_at)}</span>
                    </div>
                    <div class="text-xs font-medium text-jd-text truncate">${escapeHtml(item.summary)}</div>
                    <div class="text-[10px] font-mono text-jd-textMuted truncate mt-0.5">${escapeHtml(hexShort)}</div>
                </div>
            `;
        }).join('');
    }

    function clearHistory() {
        ConfirmDialog.show({
            title: '清空解析历史',
            message: '确定要清空所有解析历史记录吗？此操作不可恢复。',
            type: 'danger',
            confirmText: '清空'
        }).then(ok => {
            if (!ok) return;
            localStorage.removeItem(HISTORY_KEY);
            loadHistory();
            showToast('历史已清空', 'success');
        });
    }

    function loadFromHistory(index) {
        let history = [];
        try {
            history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
        } catch (e) {
            history = [];
        }

        if (index < 0 || index >= history.length) return;

        const item = history[index];
        const input = document.getElementById('parseHexInput');
        if (input) {
            input.value = item.hex || '';
            updateInputHint();
        }
        parsePacket();
    }

    function renderTypeFlagReference() {
        const el = document.getElementById('parseTypeFlagRef');
        if (!el) return;

        const typeFlags = [
            { tf: 1, name: '系统状态', dir: '上行' },
            { tf: 2, name: '上传建筑消防设施部件运行状态', dir: '上行' },
            { tf: 3, name: '上传建筑消防设施部件故障状态', dir: '上行' },
            { tf: 4, name: '上传建筑消防设施部件屏蔽状态', dir: '上行' },
            { tf: 5, name: '上传建筑消防设施部件火警状态', dir: '上行' },
            { tf: 6, name: '上传建筑消防设施部件监管报警状态', dir: '上行' },
            { tf: 7, name: '上传建筑消防设施部件反馈状态', dir: '上行' },
            { tf: 8, name: '上传建筑消防设施部件启动状态', dir: '上行' },
            { tf: 9, name: '上传建筑消防设施部件复位状态', dir: '上行' },
            { tf: 10, name: '上传建筑消防设施部件延时状态', dir: '上行' },
            { tf: 11, name: '操作信息', dir: '上行' },
            { tf: 12, name: '上传建筑消防设施软件版本', dir: '上行' },
            { tf: 13, name: '上传建筑消防设施系统配置情况', dir: '上行' },
            { tf: 14, name: '上传建筑消防设施系统部件配置情况', dir: '上行' },
            { tf: 15, name: '上传建筑消防设施系统运行状态', dir: '上行' },
            { tf: 16, name: '上传建筑消防设施部件模拟量值', dir: '上行' },
            { tf: 21, name: '确认', dir: '下行' },
            { tf: 22, name: '请求', dir: '下行' },
            { tf: 23, name: '请求更新', dir: '下行' },
            { tf: 24, name: '确认更新', dir: '上行' },
            { tf: 25, name: '确认请求', dir: '上行' },
            { tf: 31, name: '查岗请求', dir: '下行' },
            { tf: 32, name: '查岗应答', dir: '上行' },
            { tf: 33, name: '复位命令', dir: '下行' },
            { tf: 34, name: '复位应答', dir: '上行' },
            { tf: 41, name: '远程查询', dir: '下行' },
            { tf: 42, name: '远程查询应答', dir: '上行' },
            { tf: 51, name: '用户信息传输装置运行状态', dir: '上行' },
            { tf: 52, name: '用户信息传输装置操作信息', dir: '上行' },
            { tf: 53, name: '用户信息传输装置软件版本', dir: '上行' },
            { tf: 54, name: '用户信息传输装置系统配置情况', dir: '上行' },
            { tf: 55, name: '用户信息传输装置系统部件配置情况', dir: '上行' },
            { tf: 91, name: '用户信息传输装置心跳', dir: '上行' }
        ];

        el.innerHTML = typeFlags.map(tf => {
            const isUp = tf.dir === '上行';
            return `
                <div class="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-jd-content transition-colors">
                    <span class="text-[11px] font-mono font-medium text-jd-primary w-6 shrink-0">${tf.tf}</span>
                    <span class="text-[11px] text-jd-text flex-1 truncate">${escapeHtml(tf.name)}</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${isUp ? 'bg-emerald-50 text-emerald-600' : 'bg-blue-50 text-blue-600'}">${tf.dir}</span>
                </div>
            `;
        }).join('');
    }

    return {
        init,
        parsePacket,
        formatInput,
        clearInput,
        loadHistory,
        clearHistory,
        loadFromHistory,
        renderTypeFlagReference
    };
})();
