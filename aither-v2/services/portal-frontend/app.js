/* Aither Portal — Stage 16 Application Logic */
(function () {
    'use strict';

    const API_URL = '/api/v1';
    let authToken = localStorage.getItem('aither_token') || null;
    let currentUser = null;
    let currentChatId = null;
    let currentAssistantId = null;

    const $ = (id) => document.getElementById(id);
    const pages = ['login','dashboard','models','api-keys','assistants','chats','profile','status'];

    // ── API ────────────────────────────────────────────────────
    async function api(path, opts = {}) {
        const headers = { 'Content-Type': 'application/json', ...opts.headers };
        if (authToken) headers['Authorization'] = 'Bearer ' + authToken;
        const res = await fetch(API_URL + path, { ...opts, headers });
        let data;
        try { data = await res.json(); } catch { data = null; }
        return { status: res.status, ok: res.ok, data };
    }

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

    function updateNav() {
        const nav = $('main-nav');
        if (authToken && currentUser) {
            nav.style.display = 'flex';
            $('nav-username').textContent = currentUser.username;
            $('nav-role-badge').textContent = currentUser.role === 'administrator' ? 'Admin' : 'User';
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
        if (!username || !password) { showAlert('login-error','Please enter username and password','danger'); return; }
        setLoading(true);
        $('login-submit').disabled = true;
        try {
            const res = await api('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password }),
            });
            if (res.ok && res.data) {
                authToken = res.data.token;
                currentUser = res.data.user;
                localStorage.setItem('aither_token', authToken);
                updateNav();
                showPage('dashboard');
                $('login-username').value = '';
                $('login-password').value = '';
                loadDashboardInfo();
            } else {
                showAlert('login-error', (res.data?.detail) || 'Login failed', 'danger');
            }
        } catch { showAlert('login-error','Network error','danger'); }
        finally { setLoading(false); $('login-submit').disabled = false; }
    }

    async function handleLogout() {
        setLoading(true);
        try { await api('/auth/logout', { method: 'POST' }); } catch {}
        authToken = null; currentUser = null;
        localStorage.removeItem('aither_token');
        currentChatId = null;
        updateNav(); showPage('login');
        setLoading(false);
    }

    // ── Dashboard ──────────────────────────────────────────────
    async function loadDashboardInfo() {
        if (!currentUser) return;
        $('dash-username').textContent = currentUser.username;
        $('dash-role').textContent = currentUser.role === 'administrator' ? 'Administrator' : 'User';
        $('dash-role').className = 'role-badge';
        try { const v = await fetch('/version').then(r=>r.json()); $('dash-version').textContent = v.version||'—'; } catch {}
        try { const h = await fetch('/health').then(r=>r.json()); $('dash-status').textContent = h.status==='ok'?'Healthy':'Degraded'; $('dash-status').className='status-indicator '+(h.status==='ok'?'ok':'warning'); } catch {}
    }

    // ── Models ─────────────────────────────────────────────────
    async function loadModels() {
        setLoading(true);
        try {
            const res = await api('/models');
            if (!res.ok) { $('models-content').innerHTML = '<p class="text-muted">Failed to load models</p>'; return; }
            const isAdmin = currentUser && currentUser.role === 'administrator';
            $('models-admin-bar').style.display = isAdmin ? 'block' : 'none';
            if (!res.data || res.data.length === 0) {
                $('models-content').innerHTML = '<p class="text-muted">No models registered. Admin can add models.</p>';
                return;
            }
            let html = '<table class="data-table"><tr><th>Name</th><th>Provider</th><th>Context</th><th>Status</th><th>Description</th></tr>';
            for (const m of res.data) {
                html += `<tr>
                    <td><strong>${m.display_name}</strong><br><code>${m.name}</code></td>
                    <td>${m.provider}</td>
                    <td>${m.context_window}</td>
                    <td class="${m.enabled ? 'badge-enabled' : 'badge-disabled'}">${m.enabled ? 'Enabled' : 'Disabled'}</td>
                    <td>${m.description || '—'}</td>
                </tr>`;
            }
            html += '</table>';
            $('models-content').innerHTML = html;
        } finally { setLoading(false); }
    }

    // ── API Keys ───────────────────────────────────────────────
    async function loadApiKeys() {
        setLoading(true);
        try {
            const res = await api('/api-keys');
            if (!res.ok) { $('apikeys-content').innerHTML = '<p class="text-muted">Failed to load API Keys</p>'; return; }
            if (!res.data || res.data.length === 0) {
                $('apikeys-content').innerHTML = '<p class="text-muted">No API Keys created yet.</p>';
                return;
            }
            let html = '<table class="data-table"><tr><th>Name</th><th>Prefix</th><th>Created</th><th>Last Used</th><th>Status</th><th></th></tr>';
            for (const k of res.data) {
                const revoked = !!k.revoked_at;
                html += `<tr>
                    <td>${k.name}</td>
                    <td><code>${k.key_prefix}...</code></td>
                    <td>${k.created_at || '—'}</td>
                    <td>${k.last_used_at || 'never'}</td>
                    <td class="${revoked ? 'badge-revoked' : 'badge-enabled'}">${revoked ? 'Revoked' : 'Active'}</td>
                    <td>${revoked ? '' : `<button class="btn btn-sm btn-danger" onclick="window._revokeKey(${k.id})">Revoke</button>`}</td>
                </tr>`;
            }
            html += '</table>';
            $('apikeys-content').innerHTML = html;
        } finally { setLoading(false); }
    }
    window._revokeKey = async function(id) {
        if (!confirm('Revoke this API Key? This cannot be undone.')) return;
        setLoading(true);
        try {
            const res = await api('/api-keys/' + id, { method: 'DELETE' });
            if (res.ok) { await loadApiKeys(); showAlert('apikeys-content','Key revoked','success'); }
            else { alert('Failed to revoke key'); }
        } finally { setLoading(false); }
    };

    // ── Assistants ────────────────────────────────────────────
    async function loadAssistants() {
        setLoading(true);
        try {
            const res = await api('/assistants');
            if (!res.ok) { $('assistants-content').innerHTML = '<p class="text-muted">Failed to load assistants</p>'; return; }
            if (!res.data || res.data.length === 0) {
                $('assistants-content').innerHTML = '<p class="text-muted">No assistants created yet.</p>';
                return;
            }
            let html = '<table class="data-table"><tr><th>Name</th><th>Model</th><th>Temp</th><th>Max Tokens</th><th>Status</th><th></th></tr>';
            for (const a of res.data) {
                html += `<tr>
                    <td><strong>${a.name}</strong></td>
                    <td>${a.model_name || 'Model #'+a.model_id}</td>
                    <td>${a.temperature}</td>
                    <td>${a.max_tokens}</td>
                    <td class="${a.enabled ? 'badge-enabled' : 'badge-disabled'}">${a.enabled ? 'Enabled' : 'Disabled'}</td>
                    <td><button class="btn btn-sm btn-outline" onclick="window._editAssistant(${a.id})">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="window._deleteAssistant(${a.id})">Delete</button></td>
                </tr>`;
            }
            html += '</table>';
            $('assistants-content').innerHTML = html;
        } finally { setLoading(false); }
    }
    window._editAssistant = async function(id) { /* placeholder — edit form in future */ };
    window._deleteAssistant = async function(id) {
        if (!confirm('Delete this assistant?')) return;
        setLoading(true);
        try {
            const res = await api('/assistants/' + id, { method: 'DELETE' });
            if (res.ok) loadAssistants();
        } finally { setLoading(false); }
    };

    // ── Chats ──────────────────────────────────────────────────
    async function loadChats() {
        setLoading(true);
        try {
            const res = await api('/conversations');
            if (!res.ok) { $('chats-list').innerHTML = '<p class="text-muted">Failed to load chats</p>'; return; }
            if (!res.data || res.data.length === 0) {
                $('chats-list').innerHTML = '<p class="text-muted">No chats yet. Create a new chat to start.</p>';
                return;
            }
            let html = '';
            for (const c of res.data) {
                html += `<div class="card" style="margin-bottom:8px;cursor:pointer;" onclick="window._openChat(${c.id})">
                    <div class="card-body" style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center;">
                        <div><strong>${c.title || 'Untitled'}</strong><br><span class="text-muted" style="font-size:12px;">${c.assistant_name || 'No assistant'} — ${c.updated_at || c.created_at}</span></div>
                        <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();window._deleteChat(${c.id})">Delete</button>
                    </div>
                </div>`;
            }
            $('chats-list').innerHTML = html;
        } finally { setLoading(false); }
    }
    window._openChat = async function(id) {
        setLoading(true);
        try {
            const res = await api('/conversations/' + id);
            if (!res.ok) return;
            currentChatId = id;
            const conv = res.data;
            $('chat-messages').style.display = 'flex';
            $('chat-input-area').style.display = 'flex';
            let html = '';
            if (conv.messages) {
                for (const m of conv.messages) {
                    html += `<div class="chat-msg ${m.role}">${escHtml(m.content)}</div>`;
                }
            }
            $('chat-messages').innerHTML = html;
            $('chat-messages').scrollTop = $('chat-messages').scrollHeight;
            // Highlight in list
        } finally { setLoading(false); }
    };
    window._deleteChat = async function(id) {
        if (!confirm('Delete this conversation?')) return;
        setLoading(true);
        try {
            const res = await api('/conversations/' + id, { method: 'DELETE' });
            if (res.ok) {
                if (currentChatId === id) { currentChatId = null; $('chat-messages').style.display = 'none'; $('chat-input-area').style.display = 'none'; }
                loadChats();
            }
        } finally { setLoading(false); }
    };

    function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

    async function sendMessage() {
        const input = $('chat-input');
        const content = input.value.trim();
        if (!content || !currentChatId) return;
        input.value = '';
        // Show user message
        const msgs = $('chat-messages');
        msgs.innerHTML += `<div class="chat-msg user">${escHtml(content)}</div>`;
        msgs.scrollTop = msgs.scrollHeight;
        // Show loading
        msgs.innerHTML += `<div class="chat-msg assistant" id="msg-waiting"><span class="text-muted">Thinking...</span></div>`;
        msgs.scrollTop = msgs.scrollHeight;
        $('btn-send-message').disabled = true;
        try {
            const res = await api('/conversations/' + currentChatId + '/messages', {
                method: 'POST',
                body: JSON.stringify({ content }),
            });
            document.getElementById('msg-waiting')?.remove();
            if (res.ok && res.data) {
                msgs.innerHTML += `<div class="chat-msg assistant">${escHtml(res.data.content)}</div>`;
            } else {
                msgs.innerHTML += `<div class="chat-msg error">${escHtml(res.data?.detail || 'Error getting response')}</div>`;
            }
        } catch {
            document.getElementById('msg-waiting')?.remove();
            msgs.innerHTML += `<div class="chat-msg error">Network error — please try again</div>`;
        }
        msgs.scrollTop = msgs.scrollHeight;
        $('btn-send-message').disabled = false;
        loadChats(); // Refresh list
    }

    // ── Create API Key Modal ───────────────────────────────────
    function showCreateApiKeyModal() {
        modal(`
            <h2>Create API Key</h2>
            <div class="form-group">
                <label>Key Name</label>
                <input type="text" id="modal-apikey-name" class="form-input" placeholder="e.g. Development">
            </div>
            <div id="modal-apikey-result" style="display:none;">
                <div class="alert alert-info" style="margin-top:12px;">
                    <strong>Save this key — it will not be shown again!</strong>
                </div>
                <div class="copy-field">
                    <input type="text" id="modal-apikey-full" readonly>
                    <button class="btn btn-sm btn-primary" onclick="const i=document.getElementById('modal-apikey-full');i.select();navigator.clipboard?.writeText(i.value);">Copy</button>
                </div>
            </div>
            <button class="btn btn-primary" id="modal-apikey-create-btn" onclick="window._createApiKey()">Create</button>
            <button class="btn btn-outline" onclick="closeModal()">Close</button>
        `);
    }
    window._createApiKey = async function() {
        const name = document.getElementById('modal-apikey-name')?.value?.trim();
        if (!name) { alert('Enter a name for the key'); return; }
        document.getElementById('modal-apikey-create-btn').disabled = true;
        setLoading(true);
        try {
            const res = await api('/api-keys', { method: 'POST', body: JSON.stringify({ name }) });
            if (res.ok && res.data) {
                document.getElementById('modal-apikey-result').style.display = 'block';
                document.getElementById('modal-apikey-full').value = res.data.full_key;
                document.getElementById('modal-apikey-create-btn').style.display = 'none';
                document.getElementById('modal-apikey-name').disabled = true;
                await loadApiKeys();
            } else {
                alert(res.data?.detail || 'Failed to create key');
            }
        } finally { setLoading(false); }
    };

    // ── Create Assistant Modal ─────────────────────────────────
    async function showCreateAssistantModal() {
        // Load models for dropdown
        const modelsRes = await api('/models');
        const models = (modelsRes.ok && modelsRes.data) ? modelsRes.data.filter(m => m.enabled) : [];
        let modelOpts = '<option value="">Select a model</option>';
        for (const m of models) {
            modelOpts += `<option value="${m.id}">${m.display_name} (${m.name})</option>`;
        }
        modal(`
            <h2>Create Assistant</h2>
            <div class="form-group"><label>Name</label><input type="text" id="modal-ast-name" class="form-input" placeholder="My Assistant"></div>
            <div class="form-group"><label>Description</label><input type="text" id="modal-ast-desc" class="form-input" placeholder="Optional description"></div>
            <div class="form-group"><label>Model</label><select id="modal-ast-model" class="form-input">${modelOpts}</select></div>
            <div class="form-group"><label>System Prompt</label><textarea id="modal-ast-prompt" class="form-input" rows="4" placeholder="You are a helpful AI assistant..."></textarea></div>
            <div style="display:flex;gap:16px;">
                <div class="form-group" style="flex:1;"><label>Temperature (0–2)</label><input type="number" id="modal-ast-temp" class="form-input" value="0.7" min="0" max="2" step="0.1"></div>
                <div class="form-group" style="flex:1;"><label>Max Tokens</label><input type="number" id="modal-ast-maxtokens" class="form-input" value="2048" min="1" max="131072"></div>
            </div>
            <div id="modal-ast-error" class="alert alert-danger" style="display:none;"></div>
            <button class="btn btn-primary" onclick="window._createAssistant()">Create</button>
            <button class="btn btn-outline" onclick="closeModal()">Cancel</button>
        `);
    }
    window._createAssistant = async function() {
        const name = document.getElementById('modal-ast-name')?.value?.trim();
        const modelId = parseInt(document.getElementById('modal-ast-model')?.value);
        if (!name) { document.getElementById('modal-ast-error').style.display='block'; document.getElementById('modal-ast-error').textContent='Name is required'; return; }
        if (!modelId) { document.getElementById('modal-ast-error').style.display='block'; document.getElementById('modal-ast-error').textContent='Please select a model'; return; }
        setLoading(true);
        try {
            const res = await api('/assistants', {
                method: 'POST',
                body: JSON.stringify({
                    name, description: document.getElementById('modal-ast-desc')?.value || '',
                    model_id: modelId,
                    system_prompt: document.getElementById('modal-ast-prompt')?.value || '',
                    temperature: parseFloat(document.getElementById('modal-ast-temp')?.value || '0.7'),
                    max_tokens: parseInt(document.getElementById('modal-ast-maxtokens')?.value || '2048'),
                }),
            });
            if (res.ok) { closeModal(); loadAssistants(); }
            else { document.getElementById('modal-ast-error').style.display='block'; document.getElementById('modal-ast-error').textContent=res.data?.detail||'Failed'; }
        } finally { setLoading(false); }
    };

    // ── Profile ────────────────────────────────────────────────
    async function loadProfile() {
        if (!currentUser) return;
        $('profile-id').textContent = currentUser.id;
        $('profile-username').textContent = currentUser.username;
        $('profile-role').textContent = currentUser.role === 'administrator' ? 'Administrator' : 'User';
        const res = await api('/auth/me');
        if (res.ok && res.data) { currentUser = res.data; updateNav(); }
    }

    // ── Status ─────────────────────────────────────────────────
    async function loadStatusPage() {
        setLoading(true);
        try {
            const res = await api('/status');
            let html = '';
            if (res.ok && res.data && res.data.services) {
                for (const [name, status] of Object.entries(res.data.services)) {
                    const healthy = typeof status === 'object' || status === 'healthy';
                    html += `<div class="service-row"><span class="service-name">${name}</span><span class="service-status ${healthy?'ok':'error'}">${healthy?'Healthy':'Unreachable'}</span></div>`;
                }
            }
            $('status-content').innerHTML = html || '<p class="text-muted">Unavailable</p>';
            try { const v = await fetch('/version').then(r=>r.json()); $('version-content').innerHTML = '<div class="info-row"><span class="info-label">Service</span><span class="info-value">'+(v.service||'—')+'</span></div><div class="info-row"><span class="info-label">Version</span><span class="info-value">'+(v.version||'—')+'</span></div><div class="info-row"><span class="info-label">Build</span><span class="info-value">'+(v.build||'—')+'</span></div>'; } catch {}
        } finally { setLoading(false); }
    }

    // ── New Chat ──────────────────────────────────────────────
    async function newChat() {
        const assistantId = parseInt($('chat-assistant-select')?.value) || null;
        setLoading(true);
        try {
            // Get available assistants for user
            const astRes = await api('/assistants');
            const assistants = (astRes.ok && astRes.data) ? astRes.data.filter(a => a.enabled) : [];
            const selectedAst = assistants.find(a => a.id === assistantId);
            const res = await api('/conversations', {
                method: 'POST',
                body: JSON.stringify({
                    assistant_id: assistantId,
                    title: selectedAst ? `Chat with ${selectedAst.name}` : 'New Chat',
                }),
            });
            if (res.ok && res.data) {
                currentChatId = res.data.id;
                $('chat-messages').innerHTML = '';
                $('chat-messages').style.display = 'flex';
                $('chat-input-area').style.display = 'flex';
                // Add system prompt if assistant has one
                if (selectedAst && selectedAst.system_prompt) {
                    $('chat-messages').innerHTML = `<div class="chat-msg system">System: ${escHtml(selectedAst.system_prompt.substring(0, 200))}${selectedAst.system_prompt.length > 200 ? '...' : ''}</div>`;
                }
                await loadChats();
            }
        } finally { setLoading(false); }
    }

    // ── Session check ──────────────────────────────────────────
    async function checkSession() {
        if (!authToken) return false;
        const res = await api('/auth/me');
        if (res.ok && res.data) {
            currentUser = res.data;
            updateNav();
            showPage('dashboard');
            loadDashboardInfo();
            // Load assistants for chat selector
            const astRes = await api('/assistants');
            if (astRes.ok && astRes.data) {
                const sel = $('chat-assistant-select');
                sel.innerHTML = '<option value="">No assistant</option>';
                for (const a of astRes.data.filter(a=>a.enabled)) {
                    sel.innerHTML += `<option value="${a.id}">${a.name}</option>`;
                }
            }
            return true;
        }
        authToken = null; currentUser = null;
        localStorage.removeItem('aither_token');
        updateNav(); showPage('login');
        return false;
    }

    // ── Init ──────────────────────────────────────────────────
    function init() {
        $('login-form').addEventListener('submit', handleLogin);
        $('btn-logout').addEventListener('click', handleLogout);
        $('btn-create-apikey').addEventListener('click', showCreateApiKeyModal);
        $('btn-create-assistant').addEventListener('click', showCreateAssistantModal);
        $('btn-new-chat').addEventListener('click', newChat);
        $('btn-send-message').addEventListener('click', sendMessage);
        $('chat-input').addEventListener('keydown', function(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });

        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                showPage(page);
                if (page === 'profile') loadProfile();
                if (page === 'status') loadStatusPage();
                if (page === 'models') loadModels();
                if (page === 'api-keys') loadApiKeys();
                if (page === 'assistants') loadAssistants();
                if (page === 'chats') loadChats();
            });
        });

        if (authToken) checkSession();
    }

    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); } else { init(); }
})();
