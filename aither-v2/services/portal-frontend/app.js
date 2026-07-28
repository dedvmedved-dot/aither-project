/* Aither Portal — CB-WEBUI-01 */
(function () {
    'use strict';

    const API_URL = '/api/v1';
    let authToken = localStorage.getItem('aither_token') || null;
    let currentUser = null;
    let chatHistory = []; // client-side chat history

    function getBackendUrl() {
        return '';  // same-origin — nginx proxies /v1/identity/ to identity service
    }

    const $ = (id) => document.getElementById(id);
    const pages = ['login','dashboard','chat','api-keys','docs','feedback','status','profile'];

    // Zone detection
    function detectZone() {
        const host = window.location.hostname;
        if (host.includes('10.129') || host.includes('test') || host === 'localhost') {
            return 'TEST ZONE';
        }
        return 'INTERNET';
    }
    const ZONE = detectZone();
    const ZONE_CLASS = ZONE === 'INTERNET' ? 'zone-internet' : 'zone-test';

    // ── API ────────────────────────────────────────────────────
    async function api(path, opts = {}) {
        const headers = { 'Content-Type': 'application/json', ...opts.headers };
        // Use session cookie (set by login) for web auth; Bearer token for API
        if (authToken && !path.startsWith('/auth/')) {
            headers['Authorization'] = 'Bearer ' + authToken;
        }
        try {
            const res = await fetch(API_URL + path, { ...opts, headers, credentials: 'same-origin' });
            let data;
            try { data = await res.json(); } catch { data = null; }
            return { status: res.status, ok: res.ok, data };
        } catch (e) {
            return { status: 0, ok: false, data: { detail: 'Ошибка сети — проверьте подключение' } };
        }
    }

    // ── Page Navigation ─────────────────────────────────────────
    function showPage(id) {
        pages.forEach(p => { const el = $(`page-${p}`); if (el) el.classList.remove('active'); });
        const target = $(`page-${id}`);
        if (target) target.classList.add('active');
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.page === id);
        });
    }

    function showAlert(id, msg, type) {
        const el = $(id);
        if (!el) return;
        el.textContent = msg;
        el.className = 'alert alert-' + type;
        el.style.display = 'block';
    }
    function hideAlert(id) { const el = $(id); if (el) el.style.display = 'none'; }
    function setLoading(show) { const o = $('loading-overlay'); if (o) o.style.display = show ? 'flex' : 'none'; }

    function modal(html) {
        const overlay = $('modal-overlay');
        const content = $('modal-content');
        content.innerHTML = html;
        overlay.style.display = 'flex';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.style.display = 'none'; };
    }
    function closeModal() { $('modal-overlay').style.display = 'none'; }

    function escHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function updateNav() {
        const nav = $('main-nav');
        const badge = $('zone-badge');
        if (badge) {
            badge.textContent = ZONE;
            badge.className = 'zone-badge ' + ZONE_CLASS;
        }
        if (authToken && currentUser) {
            nav.style.display = 'flex';
            $('nav-username').textContent = currentUser.username || 'Пользователь';
            $('nav-role-badge').textContent = (currentUser.role === 'administrator' || currentUser.role === 'admin') ? 'Admin' : 'User';
        } else {
            nav.style.display = 'none';
        }
    }

    // ── Login / Logout ─────────────────────────────────────────
    async function handleLogin(e) {
        e.preventDefault();
        hideAlert('login-error');
        const username = $('login-username').value.trim();
        const password = $('login-password').value;
        if (!username || !password) {
            showAlert('login-error', 'Введите имя пользователя и пароль', 'danger');
            return;
        }
        setLoading(true);
        $('login-submit').disabled = true;
        try {
            const res = await api('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password }),
            });
            if (res.ok && res.data) {
                // BFF returns {status:"ok", session_id:"..."} + sets cookie
                // Store session ID for reference; auth works via cookie
                authToken = res.data.session_id || res.data.token || 'session';
                currentUser = res.data.user || { username: username, role: 'admin' };
                localStorage.setItem('aither_token', authToken);
                updateNav();
                showPage('dashboard');
                $('login-username').value = '';
                $('login-password').value = '';
                loadDashboardInfo();
            } else {
                const msg = res.data?.detail || res.data?.error || 'Ошибка входа. Проверьте учётные данные.';
                showAlert('login-error', msg, 'danger');
            }
        } catch {
            showAlert('login-error', 'Ошибка сети. Проверьте подключение.', 'danger');
        } finally {
            setLoading(false);
            $('login-submit').disabled = false;
        }
    }

    async function handleLogout() {
        setLoading(true);
        try { await api('/auth/logout', { method: 'POST' }); } catch {}
        authToken = null; currentUser = null; chatHistory = [];
        localStorage.removeItem('aither_token');
        updateNav(); showPage('login');
        setLoading(false);
    }

    // ── Dashboard ──────────────────────────────────────────────
    async function loadDashboardInfo() {
        if (!currentUser) return;
        $('dash-username').textContent = currentUser.username || '—';
        $('dash-role').textContent = (currentUser.role === 'administrator' || currentUser.role === 'admin') ? 'Администратор' : 'Пользователь';
        $('dash-zone').textContent = ZONE;

        try {
            const v = await fetch('/version').then(r => r.json());
            $('dash-version').textContent = v.version || '—';
        } catch {}
        try {
            const h = await fetch('/health').then(r => r.json());
            const ok = h.status === 'ok';
            $('dash-status').textContent = ok ? 'Работает' : 'Деградация';
            $('dash-status').className = 'status-indicator ' + (ok ? 'ok' : 'warning');
        } catch { $('dash-status').textContent = 'Недоступен'; }

        // Load models
        try {
            const res = await api('/models');
            if (res.ok && res.data) {
                const models = res.data.data || res.data;
                let html = '';
                for (const m of (Array.isArray(models) ? models : [])) {
                    const name = m.id || m.name;
                    const desc = name === 'qwen-14b' ? 'Чат-модель' : 'Базовая модель';
                    html += `<p>✦ <strong>${name}</strong> — <span class="text-muted">${desc}</span></p>`;
                }
                $('dash-models').innerHTML = html || '<p class="text-muted">Модели не найдены</p>';
            }
        } catch {}
    }

    // ── Web Chat ────────────────────────────────────────────────
    function updateModelInfo() {
        const sel = $('chat-model-select');
        const info = $('chat-model-info');
        if (!sel) return;
        const model = sel.value;
        if (model === 'qwen-14b') {
            info.textContent = 'Чат-модель — оптимизирована для диалогов';
            info.style.color = 'var(--success)';
        } else {
            info.textContent = 'Базовая модель — продолжает текст (не чат)';
            info.style.color = 'var(--warning)';
        }
    }

    function addChatMessage(role, content, model) {
        const msgs = $('chat-messages');
        if (!msgs) return;
        let meta = '';
        if (role === 'assistant' && model) {
            meta = `<div class="msg-meta">🤖 ${model}</div>`;
        }
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-msg ' + role;
        msgDiv.innerHTML = meta + escHtml(content) +
            (role === 'assistant' ? `<div class="msg-actions"><button class="btn btn-sm btn-outline" onclick="this.closest('.chat-msg').querySelector('.msg-actions').remove();navigator.clipboard.writeText('${escHtml(content).replace(/'/g, "\\'")}')">📋 Копировать</button></div>` : '');
        msgs.appendChild(msgDiv);
        msgs.scrollTop = msgs.scrollHeight;
    }

    function showChatError(code, detail) {
        const errors = {
            401: 'Ошибка авторизации. Войдите заново.',
            403: 'Доступ запрещён. Недостаточно прав.',
            404: 'Модель или endpoint не найден.',
            422: 'Некорректный запрос.',
            429: 'Превышен лимит запросов. Подождите минуту.',
            500: 'Внутренняя ошибка сервера.',
            502: 'Ошибка шлюза.',
            503: 'Сервис временно недоступен.',
            504: 'Таймаут — модель не успела ответить.',
            0: 'Ошибка сети — проверьте подключение.',
        };
        const msg = errors[code] || `Ошибка HTTP ${code}: ${detail || 'неизвестная ошибка'}`;
        addChatMessage('error', msg);
    }

    async function sendChatMessage() {
        const input = $('chat-input');
        const model = $('chat-model-select')?.value || 'qwen-14b';
        const content = input.value.trim();
        if (!content) return;

        if (authToken === null) {
            showChatError(401);
            return;
        }

        input.value = '';
        addChatMessage('user', content);
        addChatMessage('assistant', '⏳ Генерация ответа...', model);
        $('btn-send-message').disabled = true;

        const maxTokens = parseInt($('chat-max-tokens')?.value) || 512;
        const temperature = parseFloat($('chat-temperature')?.value) || 0.7;

        // Update chat history
        chatHistory.push({ role: 'user', content: content });

        try {
            const res = await api('/chat', {
                method: 'POST',
                body: JSON.stringify({
                    model: model,
                    messages: chatHistory.slice(-20), // last 20 messages for context
                    max_tokens: maxTokens,
                    temperature: temperature,
                }),
            });

            // Remove "thinking" message
            const msgs = $('chat-messages');
            const thinking = msgs?.lastElementChild;
            if (thinking && thinking.textContent.includes('⏳')) {
                thinking.remove();
            }

            if (res.ok && res.data) {
                let reply = '';
                if (res.data.choices && res.data.choices[0]) {
                    const choice = res.data.choices[0];
                    reply = choice.message?.content || choice.text || JSON.stringify(choice);
                } else if (res.data.content) {
                    reply = res.data.content;
                } else if (res.data.response) {
                    reply = res.data.response;
                }

                if (!reply || reply.trim() === '') {
                    // Raw response from 32B
                    reply = res.data.choices?.[0]?.text || 'Пустой ответ от модели.';
                }

                chatHistory.push({ role: 'assistant', content: reply });
                addChatMessage('assistant', reply, model);
            } else {
                const detail = res.data?.detail || res.data?.error || '';
                showChatError(res.status, detail);
            }
        } catch (e) {
            const thinking = $('chat-messages')?.lastElementChild;
            if (thinking && thinking.textContent.includes('⏳')) thinking.remove();
            showChatError(0);
        } finally {
            $('btn-send-message').disabled = false;
            input.focus();
        }
    }

    function clearChat() {
        chatHistory = [];
        const msgs = $('chat-messages');
        if (msgs) {
            msgs.innerHTML = `<div class="chat-msg system">
                Выберите модель и начните диалог.<br>
                <strong>qwen-14b</strong> — чат-модель для диалогов.<br>
                <strong>qwen-32b-base</strong> — базовая модель для продолжения текста.
            </div>`;
        }
    }

    // ── API Keys ───────────────────────────────────────────────
    async function loadApiKeys() {
        setLoading(true);
        try {
            const res = await api('/tokens');
            // BFF returns {tokens: [...]}
            const tokens = res.data?.tokens || (Array.isArray(res.data) ? res.data : []);
            if (res.ok) {
                if (tokens.length === 0) {
                    $('apikeys-content').innerHTML = '<p class="text-muted">Нет созданных ключей. Нажмите «Создать новый ключ».</p>';
                    return;
                }
                let html = '<table class="data-table"><tr><th>Название</th><th>Префикс</th><th>Модели</th><th>Создан</th><th>Статус</th><th>Действия</th></tr>';
                for (const k of tokens) {
                    const revoked = k.revoked;
                    const prefix = (k.token_id || k.id || '—');
                    const scopes = (k.scopes || []).map(s => s.replace('model:', '').replace(':chat-adapter',':chat').replace(':chat','')).join(', ') || 'все';
                    html += `<tr>
                        <td>${escHtml(k.name || 'Без названия')}</td>
                        <td><code>${escHtml(prefix)}...</code></td>
                        <td><span style="font-size:11px;">${escHtml(scopes)}</span></td>
                        <td>${(k.created_at || '').substring(0, 16) || '—'}</td>
                        <td class="${revoked ? 'badge-revoked' : 'badge-enabled'}">${revoked ? 'Отозван' : 'Активен'}</td>
                        <td>${revoked ? '' : `<button class="btn btn-sm btn-danger" onclick="window._revokeToken('${k.token_id || k.id}')">Отозвать</button>
                            <button class="btn btn-sm btn-outline" onclick="window._testToken('${k.token_id || k.id}')" style="margin-left:4px;">Тест</button>`}</td>
                    </tr>`;
                }
                html += '</table>';
                $('apikeys-content').innerHTML = html;
            } else {
                $('apikeys-content').innerHTML = '<p class="text-muted">Не удалось загрузить ключи.</p>';
            }
        } finally { setLoading(false); }
    }

    window._revokeToken = async function(id) {
        if (!confirm('Отозвать этот ключ? Это действие нельзя отменить.')) return;
        setLoading(true);
        try {
            const res = await api('/tokens/' + id, { method: 'DELETE' });
            if (res.ok) {
                await loadApiKeys();
                const c = $('apikeys-content');
                if (c) { c.insertAdjacentHTML('afterbegin', '<div class="alert alert-success" style="margin-bottom:12px;">✅ Ключ отозван</div>'); }
            } else {
                alert('Не удалось отозвать ключ: ' + (res.data?.detail || res.data?.error || ''));
            }
        } finally { setLoading(false); }
    };

    window._testToken = async function(id) {
        setLoading(true);
        try {
            // Get token info to find the actual token value for testing
            const res = await api('/tokens');
            const tokens = res.data?.tokens || [];
            const token = tokens.find(t => (t.token_id || t.id) === id);
            if (!token || !token.token) {
                alert('Не удалось найти ключ для тестирования.');
                setLoading(false);
                return;
            }
            // Test the key against /v1/models
            const testRes = await fetch('/api/v1/models', {
                headers: { 'Authorization': 'Bearer ' + token.token, 'Content-Type': 'application/json' }
            });
            // Note: we don't store the full key, just test it
            let resultHtml = '';
            if (testRes.ok) {
                const data = await testRes.json();
                const models = data.data || [];
                resultHtml = `<div class="alert alert-success">✅ Ключ работает. Модели: ${models.map(m => m.id).join(', ')}</div>`;
            } else {
                resultHtml = `<div class="alert alert-danger">❌ Ошибка HTTP ${testRes.status}</div>`;
            }
            const c = $('apikeys-content');
            if (c) { c.insertAdjacentHTML('afterbegin', resultHtml); }
        } catch (e) {
            alert('Ошибка при тестировании ключа.');
        } finally { setLoading(false); }
    };

    function showCreateTokenModal() {
        modal(`
            <h2>Создать API-ключ</h2>
            <div class="form-group">
                <label>Название ключа</label>
                <input type="text" id="modal-token-name" class="form-input" placeholder="Например: Разработка">
            </div>
            <div class="form-group">
                <label>Назначение</label>
                <select id="modal-token-purpose" class="form-input">
                    <option value="api">API / Web тестирование</option>
                    <option value="agent">AI Agent</option>
                    <option value="other">Другое</option>
                </select>
            </div>
            <div class="form-group">
                <label>Модели</label>
                <select id="modal-token-models" class="form-input">
                    <option value="both">Обе модели (14B + 32B)</option>
                    <option value="qwen-14b">Только qwen-14b (Чат)</option>
                    <option value="qwen-32b-base">Только qwen-32b-base (Базовая)</option>
                </select>
            </div>
            <div id="modal-token-result" style="display:none;">
                <div class="alert alert-info" style="margin-top:12px;">
                    ⚠️ <strong>Сохраните ключ сейчас — он больше не будет показан!</strong>
                </div>
                <div class="copy-field">
                    <input type="text" id="modal-token-full" readonly>
                    <button class="btn btn-sm btn-primary" onclick="const i=document.getElementById('modal-token-full');i.select();navigator.clipboard?.writeText(i.value);this.textContent='✓ Скопировано';setTimeout(()=>this.textContent='Копировать',2000);">Копировать</button>
                </div>
                <p class="text-muted" style="margin-top:4px;">Формат: athr_... (Bearer-токен для Authorization заголовка)</p>
            </div>
            <div style="display:flex;gap:8px;margin-top:16px;">
                <button class="btn btn-primary" id="modal-token-create-btn" onclick="window._createToken()">Создать</button>
                <button class="btn btn-outline" onclick="closeModal()">Отмена</button>
            </div>
        `);
    }

    window._createToken = async function() {
        const name = document.getElementById('modal-token-name')?.value?.trim() || 'default';
        const models = document.getElementById('modal-token-models')?.value || 'both';

        let scopes = [];
        if (models === 'both' || models === 'qwen-14b') scopes.push('model:14b:chat');
        if (models === 'both' || models === 'qwen-32b-base') scopes.push('model:32b:chat-adapter', 'model:32b:completion');

        document.getElementById('modal-token-create-btn').disabled = true;
        setLoading(true);
        try {
            const res = await api('/tokens', {
                method: 'POST',
                body: JSON.stringify({ name, scopes }),
            });
            if (res.ok && res.data) {
                // BFF returns {token_id, token, name, scopes, created_at}
                const fullKey = res.data.token || res.data.key || '';
                document.getElementById('modal-token-result').style.display = 'block';
                document.getElementById('modal-token-full').value = fullKey;
                document.getElementById('modal-token-create-btn').style.display = 'none';
                document.getElementById('modal-token-name').disabled = true;
                if (document.getElementById('modal-token-models')) document.getElementById('modal-token-models').disabled = true;
                if (document.getElementById('modal-token-purpose')) document.getElementById('modal-token-purpose').disabled = true;
                await loadApiKeys();
            } else {
                alert('Не удалось создать ключ: ' + (res.data?.detail || res.data?.error || JSON.stringify(res.data)));
            }
        } finally {
            setLoading(false);
        }
    };

    // ── Status ─────────────────────────────────────────────────
    async function loadStatusPage() {
        setLoading(true);
        try {
            const res = await api('/status');
            // BFF doesn't have /status, so try /health
        } catch {}
        try {
            const h = await fetch('/health').then(r => r.json());
            let html = '<div class="info-row"><span class="info-label">Статус</span><span class="info-value" style="color:var(--success)">✓ Работает</span></div>';
            html += `<div class="info-row"><span class="info-label">Версия</span><span class="info-value">${h.version || '—'}</span></div>`;
            html += `<div class="info-row"><span class="info-label">Redis</span><span class="info-value" style="color:${h.redis==='connected'?'var(--success)':'var(--danger)'}">${h.redis || '—'}</span></div>`;
            html += `<div class="info-row"><span class="info-label">Rate Limit</span><span class="info-value">${h.rate_limit || '—'}</span></div>`;
            html += `<div class="info-row"><span class="info-label">Auth</span><span class="info-value">${h.auth || '—'}</span></div>`;
            html += `<div class="info-row"><span class="info-label">Зона</span><span class="info-value">${ZONE}</span></div>`;
            $('status-content').innerHTML = html;
        } catch {
            $('status-content').innerHTML = '<p class="text-muted">Не удалось получить статус</p>';
        }
        try {
            const v = await fetch('/version').then(r => r.json());
            $('version-content').innerHTML = `<div class="info-row"><span class="info-label">Сервис</span><span class="info-value">${v.service||'—'}</span></div><div class="info-row"><span class="info-label">Версия</span><span class="info-value">${v.version||'—'}</span></div><div class="info-row"><span class="info-label">Сборка</span><span class="info-value">${v.build||'—'}</span></div>`;
        } catch { $('version-content').innerHTML = '<p class="text-muted">—</p>'; }
        setLoading(false);
    }

    // ── Profile ────────────────────────────────────────────────
    async function loadProfile() {
        if (!currentUser) return;
        $('profile-id').textContent = currentUser.id || '—';
        $('profile-username').textContent = currentUser.username || '—';
        $('profile-role').textContent = (currentUser.role === 'administrator' || currentUser.role === 'admin') ? 'Администратор' : 'Пользователь';
        $('profile-zone').textContent = ZONE;
        try {
            const res = await api('/auth/me');
            if (res.ok && res.data) currentUser = { ...currentUser, ...res.data };
        } catch {}
    }

    // ── Session check ──────────────────────────────────────────
    async function checkSession() {
        if (!authToken) return false;
        try {
            const res = await api('/auth/me');
            if (res.ok && res.data) {
                currentUser = res.data;
                updateNav();
                showPage('dashboard');
                loadDashboardInfo();
                return true;
            }
        } catch {}
        authToken = null; currentUser = null;
        localStorage.removeItem('aither_token');
        updateNav(); showPage('login');
        return false;
    }

    // ── Init ──────────────────────────────────────────────────
    function init() {
        updateNav();
        $('login-form')?.addEventListener('submit', handleLogin);
        $('btn-logout')?.addEventListener('click', handleLogout);
        $('btn-create-apikey')?.addEventListener('click', showCreateTokenModal);
        $('btn-send-message')?.addEventListener('click', sendChatMessage);
        $('btn-clear-chat')?.addEventListener('click', clearChat);
        $('btn-submit-feedback')?.addEventListener('click', function() {
            showAlert('feedback-success', '✅ Спасибо! Ваш отзыв отправлен.', 'success');
            $('feedback-message').value = '';
        });
        $('chat-model-select')?.addEventListener('change', updateModelInfo);
        $('chat-temperature')?.addEventListener('input', function() {
            $('chat-temp-val').textContent = this.value;
        });
        $('chat-input')?.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
        });

        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                showPage(page);
                if (page === 'dashboard') loadDashboardInfo();
                if (page === 'chat') updateModelInfo();
                if (page === 'api-keys') loadApiKeys();
                if (page === 'status') loadStatusPage();
                if (page === 'profile') loadProfile();
            });
        });

        updateModelInfo();

        if (authToken) checkSession();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    /* ── OAuth Functions ──────────────────────────────────── */
    window.oauthLogin = function (provider) {
        var identityUrl = getBackendUrl();
        window.location.href = identityUrl + '/v1/identity/auth/oauth/' + provider;
    };

    window.showLdapLogin = function () {
        var username = prompt('LDAP: введите имя пользователя');
        if (!username) return;
        var password = prompt('LDAP: введите пароль');
        if (!password) return;

        setLoading(true);
        fetch(getBackendUrl() + '/v1/identity/auth/ldap', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: password })
        })
        .then(function(r) { return r.json().then(function(d) { return {ok: r.ok, data: d}; }); })
        .then(function(result) {
            setLoading(false);
            if (result.ok) {
                authToken = result.data.token;
                localStorage.setItem('aither_token', authToken);
                showPage('dashboard');
            } else {
                showLoginError(result.data.detail || 'LDAP authentication failed');
            }
        })
        .catch(function(e) {
            setLoading(false);
            showLoginError('LDAP service unavailable: ' + e.message);
        });
    };
})();
