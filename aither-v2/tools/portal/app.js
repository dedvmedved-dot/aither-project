/* Aither Portal — MVP Application Logic */
(function() {
    'use strict';

    const API = '/api/v1';

    // State
    let state = {
        sessionId: null,
        username: null,
        tokens: [],
        models: [],
        chatModel: '14b',
        rawToken: null,
    };

    // DOM refs
    const $ = (id) => document.getElementById(id);
    const pages = ['login-page', 'tokens-page', 'chat-page', 'api-guide-page', 'status-page'];
    const navLinks = ['nav-login', 'nav-tokens', 'nav-chat', 'nav-guide', 'nav-status'];

    // --- Utility ---
    async function apiReq(path, opts = {}) {
        const url = API + path;
        const headers = { 'Content-Type': 'application/json', ...opts.headers };
        const res = await fetch(url, { ...opts, headers, credentials: 'include' });
        let data;
        try { data = await res.json(); } catch { data = null; }
        return { status: res.status, ok: res.ok, data };
    }

    function showPage(id) {
        pages.forEach(p => document.getElementById(p).classList.remove('active'));
        navLinks.forEach(l => document.getElementById(l).classList.remove('active'));
        document.getElementById(id).classList.add('active');
        const linkMap = {
            'login-page': 'nav-login', 'tokens-page': 'nav-tokens',
            'chat-page': 'nav-chat', 'api-guide-page': 'nav-guide',
            'status-page': 'nav-status'
        };
        const link = document.getElementById(linkMap[id]);
        if (link) link.classList.add('active');
    }

    function showAlert(id, msg, type) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = msg;
        el.className = 'alert alert-' + type;
        el.style.display = 'block';
    }

    function clearAlert(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    }

    function formatDate(ts) {
        if (!ts || ts === '0' || ts === 0) return '—';
        return new Date(parseInt(ts) * 1000).toLocaleString();
    }

    // --- Auth ---
    async function checkSession() {
        const r = await apiReq('/auth/me');
        if (r.ok && r.data && r.data.username) {
            state.sessionId = 'active';
            state.username = r.data.username;
            return true;
        }
        return false;
    }

    async function doLogin() {
        clearAlert('login-alert');
        const username = $('login-user').value.trim();
        const password = $('login-pass').value.trim();
        if (!username || !password) {
            showAlert('login-alert', 'Please enter username and password.', 'warning');
            return;
        }
        const r = await apiReq('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        if (r.ok && r.data && r.data.session_id) {
            state.sessionId = r.data.session_id;
            state.username = username;
            $('login-user').value = '';
            $('login-pass').value = '';
            await onAuth();
        } else {
            showAlert('login-alert', r.data && r.data.detail ? r.data.detail : 'Login failed: HTTP ' + r.status, 'error');
        }
    }

    async function doLogout() {
        await apiReq('/auth/logout', { method: 'POST' });
        state.sessionId = null;
        state.username = null;
        state.rawToken = null;
        onUnauth();
    }

    // --- Navigation after auth ---
    async function onAuth() {
        $('nav-username').textContent = state.username;
        document.querySelectorAll('.auth-only').forEach(el => el.style.display = '');
        document.querySelectorAll('.no-auth').forEach(el => el.style.display = 'none');
        $('login-alert').style.display = 'none';
        await loadTokens();
        await loadModels();
        showPage('tokens-page');
    }

    function onUnauth() {
        state.tokens = [];
        state.models = [];
        $('nav-username').textContent = '';
        document.querySelectorAll('.auth-only').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.no-auth').forEach(el => el.style.display = '');
        showPage('login-page');
    }

    // --- Tokens ---
    async function loadTokens() {
        const r = await apiReq('/tokens');
        if (r.ok && Array.isArray(r.data)) {
            state.tokens = r.data;
            renderTokens();
        }
    }

    function renderTokens() {
        const tbody = $('token-list-body');
        if (!tbody) return;
        if (state.tokens.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="color:var(--text-muted);text-align:center;padding:24px;">No tokens yet. Create one above.</td></tr>';
            return;
        }
        tbody.innerHTML = state.tokens.map(t => `
            <tr>
                <td><code>${t.token_id || '—'}</code></td>
                <td>${t.name || '—'}</td>
                <td>${Array.isArray(t.scopes) ? t.scopes.join(', ') : (t.scopes || '—')}</td>
                <td>${t.revoked === true || t.revoked === 'true' || t.revoked === 1 || t.revoked === '1'
                    ? '<span style="color:var(--danger)">Revoked</span>'
                    : '<span style="color:var(--success)">Active</span>'}</td>
                <td>
                    ${(t.revoked === true || t.revoked === 'true' || t.revoked === 1 || t.revoked === '1')
                        ? '<span style="color:var(--text-muted);font-size:0.8rem;">Revoked</span>'
                        : `<button class="btn btn-danger btn-sm" onclick="App.revokeToken('${t.token_id}')">Revoke</button>`}
                </td>
            </tr>
        `).join('');
    }

    async function createToken() {
        clearAlert('token-alert');
        const name = $('token-name').value.trim();
        const scopesInput = $('token-scopes').value.trim();
        if (!name) { showAlert('token-alert', 'Token name is required.', 'warning'); return; }
        let scopes = ['model:14b:chat'];
        if (scopesInput) {
            scopes = scopesInput.split(',').map(s => s.trim()).filter(Boolean);
        }
        const r = await apiReq('/tokens', {
            method: 'POST',
            body: JSON.stringify({ name, scopes })
        });
        if (r.ok && r.data && r.data.token) {
            state.rawToken = r.data.token;
            $('raw-token-display').style.display = 'flex';
            $('raw-token-value').textContent = state.rawToken;
            $('token-name').value = '';
            $('token-scopes').value = '';
            showAlert('token-alert', 'Token created! Copy it now — it will not be shown again.', 'success');
            await loadTokens();
        } else {
            const err = r.data && r.data.detail ? r.data.detail : 'Failed: HTTP ' + r.status;
            showAlert('token-alert', err, 'error');
        }
    }

    async function revokeToken(tokenId) {
        if (!confirm('Revoke token ' + tokenId + '? This cannot be undone.')) return;
        const r = await apiReq('/tokens/' + tokenId, { method: 'DELETE' });
        if (r.ok) {
            state.rawToken = null;
            $('raw-token-display').style.display = 'none';
            await loadTokens();
        } else {
            showAlert('token-alert', 'Revoke failed: HTTP ' + r.status, 'error');
        }
    }

    function copyToken() {
        const val = $('raw-token-value').textContent;
        if (val && val !== '—') {
            navigator.clipboard.writeText(val).then(() => {
                const btn = document.querySelector('.copy-btn');
                btn.textContent = 'Copied!';
                setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
            });
        }
    }

    function dismissToken() {
        state.rawToken = null;
        $('raw-token-display').style.display = 'none';
    }

    // --- Models ---
    async function loadModels() {
        const r = await apiReq('/models');
        if (r.ok && Array.isArray(r.data)) {
            state.models = r.data;
            renderModels();
        }
    }

    function renderModels() {
        const el = $('model-select');
        if (!el) return;
        el.innerHTML = state.models.map(m => {
            const id = m.id || m.model || '';
            const label = id + (m.description ? ' — ' + m.description : '');
            return `<option value="${id}">${label}</option>`;
        }).join('');
    }

    // --- Chat ---
    async function sendChat() {
        clearAlert('chat-alert');
        const text = $('chat-input').value.trim();
        if (!text) return;
        const modelId = $('model-select').value || '14b';
        appendChatMsg('user', text);
        $('chat-input').value = '';

        const r = await apiReq('/chat', {
            method: 'POST',
            body: JSON.stringify({ model: modelId, messages: [{ role: 'user', content: text }] })
        });
        if (r.ok && r.data) {
            const reply = r.data.choices && r.data.choices[0]
                ? (r.data.choices[0].message || r.data.choices[0].text || '')
                : (r.data.response || r.data.content || JSON.stringify(r.data));
            const modelLabel = modelId.includes('32b') ? '32B (chat adapter)' : modelId + ' chat';
            appendChatMsg('assistant', reply, modelLabel);
        } else {
            const errDetail = r.data && r.data.detail ? r.data.detail : 'HTTP ' + r.status;
            appendChatMsg('assistant', 'Upstream error: ' + errDetail, modelId, true);
        }
    }

    function appendChatMsg(role, text, label, isError) {
        const box = $('chat-messages');
        if (!box) return;
        const div = document.createElement('div');
        div.className = 'chat-msg';
        const sender = document.createElement('div');
        sender.className = 'sender' + (role === 'user' ? ' user' : '');
        sender.textContent = role === 'user' ? 'You' : (label || 'Assistant');
        div.appendChild(sender);
        const txt = document.createElement('div');
        txt.className = 'text' + (isError ? ' error' : '');
        txt.textContent = text;
        div.appendChild(txt);
        box.appendChild(div);
        box.scrollTop = box.scrollHeight;
    }

    // --- Health / Status ---
    async function loadStatus() {
        try {
            const res = await fetch('/health');
            const data = await res.json();
            $('status-content').textContent = JSON.stringify(data, null, 2);
        } catch (e) {
            $('status-content').textContent = 'Error loading status: ' + e.message;
        }
    }

    // --- Init ---
    async function init() {
        // Expose functions to global scope for inline onclick
        window.App = {
            doLogin, doLogout, createToken, revokeToken, copyToken, dismissToken,
            sendChat, loadStatus
        };

        // Check session
        const hasSession = await checkSession();
        if (hasSession) {
            await onAuth();
        } else {
            onUnauth();
        }

        // Load status on page show
        loadStatus();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
