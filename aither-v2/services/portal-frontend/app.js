/* Aither Portal — CB-WEBUI-01 */
(function () {
    'use strict';

    const API_URL = '/api/v1';
    let authToken = localStorage.getItem('aither_token') || null;
    let currentUser = null;
    let chatSessions = []; // all saved chat sessions
    let currentSessionId = null; // active session ID

    function getBackendUrl() {
        return '';  // same-origin — nginx proxies /v1/identity/ to identity service
    }

    const $ = (id) => document.getElementById(id);
    const pages = ['login','dashboard','chat','api-keys','docs','feedback','status','profile','admin','tariffs','billing','usage','wiki','rag','monitoring'];

    // generate a simple unique ID
    function uid() {
        return Date.now().toString(36) + '-' + Math.random().toString(36).substr(2, 9);
    }

    // ── Multi-session Chat Model ─────────────────────────────────
    function getCurrentSession() {
        if (!currentSessionId) {
            // Create a new session if none active
            currentSessionId = uid();
            var s = { id: currentSessionId, title: 'Новый чат', timestamp: new Date().toISOString(), model: DEFAULT_MODEL_ID, history: [], tokens: 0, requests: 0 };
            chatSessions.unshift(s);
            saveChatSessions();
            return s;
        }
        var found = null;
        for (var i = 0; i < chatSessions.length; i++) {
            if (chatSessions[i].id === currentSessionId) { found = chatSessions[i]; break; }
        }
        if (!found) {
            found = { id: currentSessionId, title: 'Новый чат', timestamp: new Date().toISOString(), model: DEFAULT_MODEL_ID, history: [], tokens: 0, requests: 0 };
            chatSessions.unshift(found);
            saveChatSessions();
        }
        return found;
    }

    function getChatHistory() { return getCurrentSession().history; }
    function getChatTokens() { return getCurrentSession().tokens; }
    function getChatRequests() { return getCurrentSession().requests; }

    function findSession(id) {
        for (var i = 0; i < chatSessions.length; i++) {
            if (chatSessions[i].id === id) return chatSessions[i];
        }
        return null;
    }

    function ensureGeneration(s) {
        if (!s.generation) {
            s.generation = { status: 'idle', request_id: null, answer_id: null, model: null, finish_reason: null };
        }
        return s.generation;
    }

    function findAnswerItem(s, answerId) {
        var h = s.history || [];
        for (var i = h.length - 1; i >= 0; i--) {
            if (h[i].role === 'assistant' && h[i].answer_id === answerId) return h[i];
        }
        return null;
    }

    // ── Server-side chat persistence ─────────────────────────────
    function _chatPersistWarning(show) {
        var el = $('chat-save-warning');
        if (el) el.style.display = show ? 'block' : 'none';
    }

    // Per-chat serialized persistence queue (BLOCKER 7).
    // Writes for the same chat are chained FIFO so a stale older write can never
    // overwrite a newer state, even across fire-and-forget async persistence paths.
    var _persistQueues = {};

    async function _doServerPersist(session, snapshot) {
        if (authToken === null) return;
        var payload = {
            title: snapshot.title || 'Новый чат',
            model: snapshot.model || DEFAULT_MODEL_ID,
            tokens: snapshot.tokens || 0,
            requests: snapshot.requests || 0,
            legacy_client_id: session.legacy_client_id || session.id,
            messages: snapshot.messages
        };
        try {
            var res;
            if (session.server_id) {
                res = await api('/chats/' + encodeURIComponent(session.server_id), { method: 'PUT', body: JSON.stringify(payload) });
            } else {
                // Canonical id is server-generated (BLOCKER 4); browser id is only legacy_client_id.
                res = await api('/chats', { method: 'POST', body: JSON.stringify(payload) });
                if (res.ok && res.data && res.data.id) {
                    session.server_id = res.data.id;
                }
            }
            if (!res.ok) _chatPersistWarning(true);
        } catch (e) {
            _chatPersistWarning(true);
        }
    }

    function enqueueServerPersist(session) {
        if (authToken === null) return Promise.resolve();
        var key = session.id || session.server_id || 'default';
        // Immutable snapshot (deep-copied messages) taken at enqueue time.
        var snapshot = {
            title: session.title,
            model: session.model,
            tokens: session.tokens,
            requests: session.requests,
            messages: (session.history || []).map(function(m) {
                return { role: m.role, content: m.content, model: m.model, answer_id: m.answer_id };
            })
        };
        var prev = _persistQueues[key] || Promise.resolve();
        var task = prev.then(function() {
            return _doServerPersist(session, snapshot);
        });
        // Never-rejecting tail so one failed write cannot break the chain.
        _persistQueues[key] = task.then(function(){}, function(){});
        return task;
    }

    async function serverDeleteChat(session) {
        if (authToken === null) return;
        var sid = session.server_id || session.id;
        try { await api('/chats/' + encodeURIComponent(sid), { method: 'DELETE' }); } catch (e) {}
    }

    async function loadServerChats() {
        if (authToken === null) return;
        try {
            var listRes = await api('/chats');
            if (!listRes.ok || !listRes.data || !listRes.data.chats) return;
            var serverChats = [];
            for (var i = 0; i < listRes.data.chats.length; i++) {
                var meta = listRes.data.chats[i];
                var dRes = await api('/chats/' + encodeURIComponent(meta.id));
                var history = [];
                if (dRes.ok && dRes.data && dRes.data.messages) {
                    history = dRes.data.messages.map(function(m) {
                        return { role: m.role, content: m.content, model: m.model, answer_id: m.answer_id };
                    });
                }
                serverChats.push({
                    id: meta.legacy_client_id || meta.id,
                    server_id: meta.id,
                    legacy_client_id: meta.legacy_client_id || null,
                    title: meta.title || 'Новый чат', timestamp: meta.updated_at || meta.created_at,
                    model: meta.model || DEFAULT_MODEL_ID, history: history,
                    tokens: meta.tokens || 0, requests: meta.requests || 0,
                    generation: { status: 'idle', request_id: null, answer_id: null, model: null, finish_reason: null }
                });
            }
            chatSessions = serverChats;
            currentSessionId = chatSessions.length > 0 ? chatSessions[0].id : null;
            localStorage.setItem('aither_current_chat', currentSessionId || '');
            renderChatList();
            if (currentSessionId) {
                window._switchChat(currentSessionId);
            } else {
                var msgs = $('chat-messages');
                if (msgs) msgs.innerHTML = '';
                updateTokenCounters();
            }
        } catch (e) {}
    }

    async function importLegacyChats(sessions) {
        if (authToken === null) return { imported: 0, skipped: 0 };
        try {
            var res = await api('/chats/import-legacy', { method: 'POST', body: JSON.stringify({ sessions: sessions }) });
            if (res.ok && res.data) return { imported: res.data.imported || 0, skipped: res.data.skipped || 0 };
        } catch (e) {}
        return { imported: 0, skipped: 0 };
    }

    window._exportHistory = async function() {
        if (authToken === null) return;
        try {
            var res = await fetch(API_URL + '/chats/export', { headers: { 'Authorization': 'Bearer ' + authToken } });
            if (!res.ok) { showAlert('chat-save-warning', 'Не удалось экспортировать историю', 'danger'); return; }
            var blob = await res.blob();
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            var cd = res.headers.get('Content-Disposition') || '';
            var m = cd.match(/filename="?([^"]+)"?/);
            a.download = m ? m[1] : 'Aither_chat_history.zip';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch (e) {
            showAlert('chat-save-warning', 'Не удалось экспортировать историю', 'danger');
        }
    };

    async function maybeMigrateLegacy() {
        try {
            var legacy = null;
            var rawMulti = localStorage.getItem('aither_chats');
            var rawSingle = localStorage.getItem('aither_chat');
            if (rawMulti) legacy = JSON.parse(rawMulti);
            else if (rawSingle) {
                var old = JSON.parse(rawSingle);
                if (old && old.history && old.history.length > 0) legacy = [old];
            }
            if (!legacy || !Array.isArray(legacy) || legacy.length === 0) return;
            var confirmed = window.confirm('Найдена локальная история из предыдущей версии: ' + legacy.length + ' чат(ов). Импортировать её в ваш аккаунт?');
            if (!confirmed) return;
            var r = await importLegacyChats(legacy);
            if (r.imported > 0) {
                localStorage.removeItem('aither_chats');
                localStorage.removeItem('aither_chat');
                await loadServerChats();
            }
        } catch (e) {}
    }

    function saveChatSessions() {
        try {
            // Keep max 30 sessions, trim oldest
            if (chatSessions.length > 30) chatSessions = chatSessions.slice(0, 30);
            localStorage.setItem('aither_chats', JSON.stringify(chatSessions));
            localStorage.setItem('aither_current_chat', currentSessionId || '');
        } catch(e) {}
    }

    function loadChatSessions() {
        try {
            var raw = localStorage.getItem('aither_chats');
            if (raw) {
                chatSessions = JSON.parse(raw);
                if (!Array.isArray(chatSessions)) chatSessions = [];
            }
            // Migrate from old single-chat format
            if (chatSessions.length === 0) {
                var oldRaw = localStorage.getItem('aither_chat');
                if (oldRaw) {
                    var old = JSON.parse(oldRaw);
                    if (old && old.history && old.history.length > 0) {
                        var sid = uid();
                        chatSessions = [{
                            id: sid, title: titleFromHistory(old.history),
                            timestamp: new Date().toISOString(), model: DEFAULT_MODEL_ID,
                            history: old.history, tokens: old.tokens || 0, requests: old.requests || 0
                        }];
                        localStorage.removeItem('aither_chat');
                    }
                }
            }
            // Migrate sessions missing generation state to idle (preserve history)
            for (var gi = 0; gi < chatSessions.length; gi++) {
                if (!chatSessions[gi].generation) {
                    chatSessions[gi].generation = { status: 'idle', request_id: null, answer_id: null, model: null, finish_reason: null };
                }
            }
            var savedId = localStorage.getItem('aither_current_chat') || '';
            currentSessionId = savedId || (chatSessions.length > 0 ? chatSessions[0].id : null);
        } catch(e) {
            chatSessions = [];
            currentSessionId = null;
        }
    }

    function titleFromHistory(history) {
        if (!history || history.length === 0) return 'Новый чат';
        for (var i = 0; i < history.length; i++) {
            if (history[i].role === 'user') {
                var t = history[i].content || '';
                return t.length > 50 ? t.substring(0, 47) + '...' : t;
            }
        }
        return 'Новый чат';
    }

    function updateTokenCounters() {
        var s = getCurrentSession();
        if ($('chat-token-count')) $('chat-token-count').textContent = (s.tokens || 0).toLocaleString();
        if ($('chat-request-count')) $('chat-request-count').textContent = s.requests || 0;
    }

    function renderChatList() {
        var list = $('chat-list');
        if (!list) return;
        if (chatSessions.length === 0) {
            list.innerHTML = '<p class="text-muted chat-list-empty">Нет сохранённых чатов</p>';
            return;
        }
        var html = '';
        for (var i = 0; i < chatSessions.length; i++) {
            var s = chatSessions[i];
            var isActive = s.id === currentSessionId;
            var dateStr = '';
            try { dateStr = new Date(s.timestamp).toLocaleDateString('ru-RU', {day:'numeric',month:'short'}); } catch(e) {}
            html += '<div class="chat-list-item' + (isActive ? ' active' : '') + '" data-sid="' + escAttr(s.id) + '" onclick="window._switchChat(\'' + escAttr(s.id) + '\')">' +
                '<div class="chat-list-title">' + escHtml(s.title || 'Новый чат') + '</div>' +
                '<div class="chat-list-meta">' + (dateStr || '—') + ' · ' + (s.history ? s.history.length : 0) + ' сообщ.</div>' +
                '<button class="btn-chat-delete" onclick="event.stopPropagation();window._deleteChat(\'' + escAttr(s.id) + '\')" title="Удалить">×</button>' +
                '</div>';
        }
        list.innerHTML = html;
    }

    function escAttr(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/\"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#39;');
    }

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

    // ── Active Model Catalog ────────────────────────────────────
    // Source of Truth: the accepted active backend catalog is exactly
    // qwen3-32b and qwen3.8-27b, both covered by the model:qwen3:chat
    // scope. The chat selector is populated from the authenticated
    // /api/v1/models response and filtered through this allowlist, so a
    // retired/stale model ID is never presented or used. If the catalog
    // cannot be loaded the UI fails closed (sending disabled).
    var ACTIVE_MODEL_IDS = ['qwen3-32b', 'qwen3.8-27b'];
    var MODEL_LABELS = { 'qwen3-32b': 'Qwen3-32B', 'qwen3.8-27b': 'Qwen3.8-27B' };
    var DEFAULT_MODEL_ID = 'qwen3-32b';
    var modelCatalog = [];
    var modelCatalogLoaded = false;
    var modelCatalogError = null;

    function isActiveModel(id) {
        return ACTIVE_MODEL_IDS.indexOf(id) !== -1;
    }

    function modelLabel(id) {
        return MODEL_LABELS[id] || id;
    }

    function resolveActiveModel(id) {
        if (id && isActiveModel(id)) return id;
        return DEFAULT_MODEL_ID;
    }

    function renderModelSelect() {
        var sel = $('chat-model-select');
        if (!sel) return;
        sel.innerHTML = '';
        if (!modelCatalog.length) {
            sel.disabled = true;
            var opt = document.createElement('option');
            opt.value = '';
            opt.textContent = modelCatalogError || 'Модели не загружены';
            sel.appendChild(opt);
            return;
        }
        for (var i = 0; i < modelCatalog.length; i++) {
            var o = document.createElement('option');
            o.value = modelCatalog[i];
            o.textContent = modelLabel(modelCatalog[i]);
            sel.appendChild(o);
        }
        sel.disabled = false;
        var s = getCurrentSession();
        if (s && s.model && isActiveModel(s.model)) {
            sel.value = s.model;
        } else {
            sel.value = DEFAULT_MODEL_ID;
        }
        updateModelInfo();
    }

    async function loadModelCatalog() {
        modelCatalog = [];
        modelCatalogLoaded = false;
        modelCatalogError = null;
        try {
            var res = await api('/models');
            if (res.ok && res.data) {
                var list = res.data.data || res.data;
                var returned = [];
                for (var i = 0; i < (Array.isArray(list) ? list : []).length; i++) {
                    var name = list[i].id || list[i].name;
                    if (name && isActiveModel(name) && returned.indexOf(name) === -1) returned.push(name);
                }
                for (var j = 0; j < ACTIVE_MODEL_IDS.length; j++) {
                    if (returned.indexOf(ACTIVE_MODEL_IDS[j]) !== -1) modelCatalog.push(ACTIVE_MODEL_IDS[j]);
                }
            }
            if (!modelCatalog.length) {
                modelCatalogError = 'Не удалось загрузить каталог моделей';
                var s1 = $('chat-model-select'); if (s1) s1.disabled = true;
                var b1 = $('btn-send-message'); if (b1) b1.disabled = true;
                var i1 = $('chat-model-info');
                if (i1) { i1.innerHTML = '⚠️ Каталог моделей недоступен — отправка отключена'; i1.style.color = 'var(--danger)'; }
                renderModelSelect();
                return;
            }
            modelCatalogLoaded = true;
            renderModelSelect();
            var b2 = $('btn-send-message'); if (b2) b2.disabled = false;
        } catch (e) {
            modelCatalogError = 'Не удалось загрузить каталог моделей';
            var s2 = $('chat-model-select'); if (s2) s2.disabled = true;
            var b3 = $('btn-send-message'); if (b3) b3.disabled = true;
            renderModelSelect();
        }
    }

    // ── API ────────────────────────────────────────────────────
    async function api(path, opts = {}) {
        const headers = { 'Content-Type': 'application/json', ...opts.headers };
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
        // Persist current page
        try { localStorage.setItem('aither_page', id); } catch(e) {}
        if (id === 'docs') renderDocCards();
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
    window.closeModal = closeModal;

    function escHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    // ── Code syntax highlighting (VS Code Dark+ theme) ───────────
    const SYNTAX_KEYWORDS = {
        python: ['def','class','import','from','return','if','elif','else','for','while','try','except','finally','with','as','yield','raise','pass','break','continue','and','or','not','in','is','None','True','False','async','await','lambda','global','nonlocal','assert','del','print','len','range','int','str','list','dict','set','tuple','bool','float','type','open','enumerate','zip','map','filter','sorted','reversed','any','all','super','self'],
        bash: ['if','then','else','elif','fi','for','while','do','done','case','esac','function','export','local','return','exit','echo','source','set','unset','read','declare','eval','exec','trap','cd','ls','mkdir','rm','cp','mv','chmod','chown','grep','awk','sed','cat','curl','wget','git','docker','kubectl','python','pip','npm','node'],
        js: ['function','var','let','const','if','else','for','while','return','try','catch','throw','new','class','extends','import','export','default','async','await','this','null','undefined','true','false','typeof','instanceof','console','document','window','Promise','async','require','module'],
        json: ['true','false','null'],
        sql: ['SELECT','FROM','WHERE','INSERT','INTO','UPDATE','DELETE','CREATE','TABLE','ALTER','DROP','JOIN','LEFT','RIGHT','INNER','ON','AND','OR','NOT','NULL','AS','ORDER','BY','GROUP','HAVING','LIMIT','OFFSET','SET','VALUES','INDEX','UNIQUE','PRIMARY','KEY','FOREIGN','REFERENCES','DEFAULT','CHECK','COUNT','SUM','AVG','MAX','MIN','EXISTS','BETWEEN','LIKE','IN','CASE','WHEN','THEN','ELSE','END','UNION','ALL','DISTINCT']
    };
    const BUILTIN_WORDS = {
        python: ['print','len','range','int','str','list','dict','set','tuple','bool','float','type','open','enumerate','zip','map','filter','sorted','reversed','any','all','super','self','Exception','ValueError','TypeError','KeyError','IndexError','RuntimeError','StopIteration','OSError','FileNotFoundError'],
        bash: ['echo','cd','ls','mkdir','rm','cp','mv','chmod','chown','grep','awk','sed','cat','curl','wget','git','docker','kubectl','python','pip','npm','node','exit','export','source'],
        js: ['console','document','window','Promise','fetch','JSON','Math','Array','Object','String','Number','Boolean','Date','RegExp','Error','Map','Set','setTimeout','setInterval','clearTimeout','clearInterval','parseInt','parseFloat'],
    };

    function highlightCode(code, lang) {
        var escaped = escHtml(code);
        // Normalize language
        if (lang === 'py') lang = 'python';
        if (lang === 'sh' || lang === 'shell') lang = 'bash';
        if (lang === 'javascript' || lang === 'js') lang = 'js';
        if (lang === 'ts' || lang === 'typescript') lang = 'js';
        if (lang === 'yaml' || lang === 'yml') lang = 'yaml';
        if (lang === 'html') lang = 'html';
        if (lang === 'css') lang = 'css';

        var keywords = SYNTAX_KEYWORDS[lang] || [];
        var builtins = BUILTIN_WORDS[lang] || [];

        if (keywords.length === 0 && builtins.length === 0 && lang !== 'yaml' && lang !== 'html' && lang !== 'css') {
            // Still highlight strings/comments/numbers for unknown languages
            escaped = highlightBase(escaped, lang);
            return escaped;
        }

        // 1. Strings (single, double, backtick) — orange
        escaped = escaped.replace(/(`[^`]*`)/g, '<span class="syn-string">$1</span>');
        escaped = escaped.replace(/(&quot;[^&]*&quot;|&#39;[^&]*&#39;)/g, '<span class="syn-string">$1</span>');
        escaped = escaped.replace(/(["][^"]*["]|['][^']*['])/g, '<span class="syn-string">$1</span>');

        // 2. Comments — green
        if (lang === 'python' || lang === 'bash' || lang === 'yaml') {
            escaped = escaped.replace(/([ \t]*#.*)/g, '<span class="syn-comment">$1</span>');
        }
        if (lang === 'js' || lang === 'css') {
            escaped = escaped.replace(/(\/\/.*)/g, '<span class="syn-comment">$1</span>');
            escaped = escaped.replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="syn-comment">$1</span>');
        }
        if (lang === 'sql') {
            escaped = escaped.replace(/(--.*)/g, '<span class="syn-comment">$1</span>');
        }
        if (lang === 'html') {
            escaped = escaped.replace(/(&lt;!--[\s\S]*?--&gt;)/g, '<span class="syn-comment">$1</span>');
        }

        // 3. Keywords — blue
        keywords.forEach(function(kw) {
            var re = new RegExp('\\b(' + kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')\\b', 'g');
            escaped = escaped.replace(re, '<span class="syn-keyword">$1</span>');
        });

        // 4. Built-in functions — yellow
        builtins.forEach(function(fn) {
            var re = new RegExp('\\b(' + fn.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')\\b', 'g');
            escaped = escaped.replace(re, '<span class="syn-builtin">$1</span>');
        });

        // 5. Numbers — light green
        escaped = escaped.replace(/\b(\d+\.?\d*[eE]?[+-]?\d*)\b/g, '<span class="syn-number">$1</span>');

        // 6. Decorators — yellow
        escaped = escaped.replace(/(@\w+)/g, '<span class="syn-decorator">$1</span>');

        // 7. Function calls — yellow (word followed by parenthesis)
        escaped = escaped.replace(/\b([a-zA-Z_]\w*)(?=\s*\()/g, function(match) {
            // Don't re-highlight already highlighted spans
            if (match.indexOf('span') !== -1) return match;
            return '<span class="syn-function">' + match + '</span>';
        });

        return escaped;
    }

    function highlightBase(escaped, lang) {
        escaped = escaped.replace(/(`[^`]*`)/g, '<span class="syn-string">$1</span>');
        escaped = escaped.replace(/(&quot;[^&]*&quot;|&#39;[^&]*&#39;)/g, '<span class="syn-string">$1</span>');
        escaped = escaped.replace(/([\"][^\"]*\"]|['][^']*['])/g, '<span class="syn-string">$1</span>');
        escaped = escaped.replace(/\b(\d+\.?\d*)\b/g, '<span class="syn-number">$1</span>');
        return escaped;
    }

    // ── Markdown renderer (tables, lists, code, headers) ─────────
    function normalizeDocPath(url) {
        var clean = String(url).split('#')[0].split('?')[0].trim();
        if (!clean || clean.indexOf('..') !== -1 || clean.indexOf('\\') !== -1) return null;
        var name = clean.split('/').pop();
        if (!name || !/\.md$/i.test(name)) return null;
        if (!/^[\w-]+\.md$/i.test(name)) return null;
        return name;
    }

    function slugifyHeading(text) {
        var slug = String(text || '')
            .trim()
            .toLowerCase()
            .replace(/[^\p{L}\p{N}\s-]/gu, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .replace(/^-+|-+$/g, '');
        return slug;
    }

    const DOC_CATALOG = [
        { file: '00_INDEX.md', title: 'Все документы', icon: '📚', desc: 'Индекс документации', category: 'Основное' },
        { file: '01_WELCOME.md', title: 'Добро пожаловать', icon: '👋', desc: 'Приветствие, цели тестирования', category: 'Основное' },
        { file: '02_QUICK_START.md', title: 'Быстрый старт', icon: '🚀', desc: 'Первый диалог за 5 минут', category: 'Основное' },
        { file: '03_USER_GUIDE.md', title: 'Руководство пользователя', icon: '📘', desc: 'Полное руководство (Web UI + API)', category: 'Основное' },
        { file: '04_API_GUIDE.md', title: 'API Guide', icon: '🔌', desc: 'API с примерами curl и Python', category: 'Разработчикам' },
        { file: '08_FAQ.md', title: 'FAQ', icon: '❓', desc: 'Часто задаваемые вопросы', category: 'Основное' },
        { file: '09_SECURITY_RULES.md', title: 'Правила безопасности', icon: '🔒', desc: 'Безопасность ключей и агентов', category: 'Основное' },
        { file: '10_KNOWN_LIMITATIONS.md', title: 'Известные ограничения', icon: '⚠️', desc: 'Ограничения системы', category: 'Основное' },
        { file: '13_WEB_UI_GUIDE.md', title: 'Web UI Guide', icon: '🖥', desc: 'Полное руководство по Web UI', category: 'Основное' },
        { file: '14_API_KEY_USER_GUIDE.md', title: 'API-ключи', icon: '🔑', desc: 'Создание и управление ключами', category: 'Основное' },
        { file: '15_DUAL_ZONE_ACCESS_GUIDE.md', title: 'Двухзонный доступ', icon: '🌐', desc: 'Internet и Test Zone', category: 'Основное' },
        { file: '16_AI_AGENT_CONNECTION_PRIMER.md', title: 'Подключение AI-агентов', icon: '🤖', desc: 'Настройка агентов', category: 'Разработчикам' },
        { file: '17_MODEL_USAGE_GUIDE.md', title: 'Работа с моделями', icon: '🧠', desc: 'Выбор модели, API-ключи', category: 'Основное' },
        { file: '05_TEST_ASSIGNMENT.md', title: 'Тестовые задания', icon: '✅', desc: 'Обязательные задания', category: 'Тестирование' },
        { file: '06_BUG_REPORT_TEMPLATE.md', title: 'Шаблон отчёта об ошибке', icon: '🐞', desc: 'Форма баг-репорта', category: 'Тестирование' },
        { file: '07_USER_FEEDBACK_FORM.md', title: 'Форма обратной связи', icon: '💬', desc: 'Обратная связь', category: 'Тестирование' },
        { file: '11_ACCEPTANCE_CHECKLIST.md', title: 'Чек-лист приёмки', icon: '📋', desc: 'Чек-лист участника', category: 'Тестирование' },
        { file: '12_OWNER_HANDOVER.md', title: 'Инструкция владельцу', icon: '👑', desc: 'Handover для владельца', category: 'Тестирование' },
    ];

    function renderDocCards() {
        var grid = $('docs-grid');
        if (!grid) return;
        grid.innerHTML = '';
        var cats = ['Основное', 'Разработчикам', 'Тестирование'];
        cats.forEach(function(cat) {
            DOC_CATALOG.filter(function(d) { return d.category === cat; }).forEach(function(d) {
                var card = document.createElement('div');
                card.className = 'card';
                card.style.cursor = 'pointer';
                card.innerHTML = '<div style="font-size:28px;">' + d.icon + '</div>' +
                    '<h3>' + escHtml(d.title) + '</h3>' +
                    '<p style="font-size:12px;color:var(--muted,#888);">' + escHtml(d.desc) + '</p>';
                card.addEventListener('click', function() { showDoc('/docs/' + d.file); });
                grid.appendChild(card);
            });
        });
    }

    function renderMathInElement(el) {
        if (!el || typeof window.renderMathInElement !== 'function') return;
        try {
            window.renderMathInElement(el, {
                delimiters: [
                    { left: '$$', right: '$$', display: true },
                    { left: '\\[', right: '\\]', display: true },
                    { left: '$', right: '$', display: false },
                    { left: '\\(', right: '\\)', display: false },
                ],
                throwOnError: false,
                trust: false,
                ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
                preProcess: function(math) {
                    return math.replace(/\\_/g, '_');
                },
            });
        } catch (e) {
            // malformed math must not break the portal
        }
    }

    document.addEventListener('click', function(e) {
        var t = e.target;
        if (!t || !t.closest) return;
        var link = t.closest('.md-doc-link');
        if (link) {
            var norm = normalizeDocPath(link.getAttribute('data-doc-path'));
            if (norm) {
                e.preventDefault();
                showDoc('/docs/' + norm);
            }
            return;
        }
        // Anchor links inside the doc modal: scroll within the document, no page navigation.
        var a = t.closest('a[href^="#"]');
        if (a) {
            var href = a.getAttribute('href');
            if (href && href.length > 1) {
                var id = href.slice(1).toLowerCase().replace(/-+/g, '-').replace(/^-+|-+$/g, '');
                var target = document.getElementById(id);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
                // target missing -> fail safe (no crash)
            }
        }
    });

    function renderMarkdown(md) {
        if (!md) return '';
        var html = md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

        // Fenced code blocks
        var codeBlocks = [];
        html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, function(m, lang, code) {
            var idx = codeBlocks.length;
            codeBlocks.push({lang: lang || 'text', code: code.replace(/\n$/, '')});
            return '\x00CB' + idx + '\x00';
        });

        // Tables
        html = html.replace(/^\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)+)/gm, function(m, header, rows) {
            var hcols = header.split('|').map(function(c) { return '<th>' + c.trim() + '</th>'; }).join('');
            var rhtml = '';
            rows.split('\n').forEach(function(r) {
                if (!r.trim()) return;
                var cols = r.split('|').filter(function(c) { return c !== ''; }).map(function(c) { return '<td>' + c.trim() + '</td>'; }).join('');
                rhtml += '<tr>' + cols + '</tr>';
            });
            return '<table class="md-table"><thead><tr>' + hcols + '</tr></thead><tbody>' + rhtml + '</tbody></table>';
        });

        // Headers — deterministic anchor ids (duplicates get -2, -3 suffixes)
        var usedHeadings = {};
        html = html.replace(/^(#{1,4}) (.+)$/gm, function(m, hashes, text) {
            var level = hashes.length + 1; // # -> h2, ## -> h3, ### -> h4, #### -> h5
            var base = slugifyHeading(text) || 'section';
            var slug = base;
            var n = 2;
            while (usedHeadings[slug]) { slug = base + '-' + n; n++; }
            usedHeadings[slug] = true;
            return '<h' + level + ' id="' + slug + '">' + text + '</h' + level + '>';
        });

        // Bold, italic
        html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<b><i>$1</i></b>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
        html = html.replace(/\*(.+?)\*/g, '<i>$1</i>');
        html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

        // Links — route local .md references through the doc viewer (no 404)
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(m, label, url) {
            if (/^(https?:\/\/|mailto:)/i.test(url)) {
                return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + label + '</a>';
            }
            if (url.charAt(0) === '#') {
                return '<a href="' + url + '">' + label + '</a>';
            }
            var doc = normalizeDocPath(url);
            if (doc) {
                return '<a href="#" class="md-doc-link" data-doc-path="' + escHtml(doc) + '">' + label + '</a>';
            }
            return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + label + '</a>';
        });

        // Horizontal rules
        html = html.replace(/^---$/gm, '<hr>');

        // Lists
        html = html.replace(/^(\s*)[-*+] (.+)$/gm, '<li>$2</li>');
        html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
        html = html.replace(/<\/ul>\s*<ul>/g, '');

        html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
        html = html.replace(/((?:<li>[\s\S]*?<\/li>\s*)+)/g, function(m) {
            if (m.indexOf('<ul>') !== -1) return m;
            return '<ol>' + m + '</ol>';
        });

        // Paragraphs
        html = '<p>' + html.replace(/\n\n+/g, '</p><p>') + '</p>';
        html = html.replace(/<p>\s*<\/p>/g, '');

        // Restore code blocks
        html = html.replace(/\x00CB(\d+)\x00/g, function(m, idx) {
            var cb = codeBlocks[parseInt(idx)];
            var highlighted = highlightCode(cb.code, cb.lang);
            return '<div class="code-block"><div class="code-header"><span class="code-lang">' + escHtml(cb.lang) + '</span></div><pre><code>' + highlighted + '</code></pre></div>';
        });

        return html;
    }

    function formatMarkdown(txt) {
        txt = txt.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
        txt = txt.replace(/\*(.+?)\*/g, '<i>$1</i>');
        txt = txt.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
        txt = txt.replace(/\n/g, '<br>');
        return txt;
    }


    function renderChatTable(html) {
        return html.replace(/^\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)+)/gm, function(m, header, rows) {
            var hcols = header.split('|').map(function(c) { return '<th>' + c.trim() + '</th>'; }).join('');
            var rhtml = '';
            rows.split('\n').forEach(function(r) {
                if (!r.trim()) return;
                var cols = r.split('|').filter(function(c) { return c !== ''; }).map(function(c) { return '<td>' + c.trim() + '</td>'; }).join('');
                rhtml += '<tr>' + cols + '</tr>';
            });
            return '<table class="md-table"><thead><tr>' + hcols + '</tr></thead><tbody>' + rhtml + '</tbody></table>';
        });
    }

    function renderChatCodeBlock(rawCode, lang, blockIdx) {
        var highlighted = highlightCode(rawCode, lang);
        var blockId = 'cb' + blockIdx;
        return '<div class="code-block">' +
            '<div class="code-header">' +
            '<span class="code-lang">' + escHtml(lang) + '</span>' +
            '<button class="btn btn-sm btn-copy-code" onclick="var el=document.getElementById(\'' + blockId + '\');var txt=el.textContent;navigator.clipboard.writeText(txt).then(function(){var b=document.getElementById(\'' + blockId + '-btn\');b.textContent=\'✓ Скопировано\';setTimeout(function(){b.textContent=\'📋 Копировать\';},2000);});" id="' + blockId + '-btn">📋 Копировать</button>' +
            '</div>' +
            '<pre><code id="' + blockId + '">' + highlighted + '</code></pre>' +
            '</div>';
    }

    function formatMessage(text) {
        if (!text) return '';
        var codeBlocks = [];
        var inlineCodes = [];
        var mathBlocks = [];

        // 0. Normalize math-intent fenced blocks (latex/tex/math/katex) to display math,
        //    BEFORE generic fenced-code extraction, so KaTeX renders them instead of code.
        var html = text.replace(/```(latex|tex|math|katex)\n?([\s\S]*?)```/g, function(m, lang, code) {
            var inner = code.replace(/\s+$/, '').trim();
            if (/(\$\$|\\\[)/.test(inner)) return inner;
            return '$$\n' + inner + '\n$$';
        });

        // 1. Protect fenced code blocks
        html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, function(m, lang, code) {
            var idx = codeBlocks.length;
            codeBlocks.push(renderChatCodeBlock(code.replace(/\n$/, ''), (lang || 'text'), idx));
            return '\x00CB' + idx + '\x00';
        });

        // 2. Protect inline code
        html = html.replace(/`([^`\n]+)`/g, function(m, code) {
            var idx = inlineCodes.length;
            inlineCodes.push(escHtml(code));
            return '\x00IC' + idx + '\x00';
        });

        // 3. Protect math fragments (multiline-capable, before newline conversion)
        html = html.replace(/(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\\\([^\n]*?\\\)|\$[^\n$]*?\$)/g, function(m) {
            var idx = mathBlocks.length;
            mathBlocks.push(m);
            return '\x00MB' + idx + '\x00';
        });

        // 4. Escape remaining text
        html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

        // 5. Tables
        html = renderChatTable(html);

        // 6. Bold / italic
        html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<b><i>$1</i></b>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
        html = html.replace(/\*(.+?)\*/g, '<i>$1</i>');

        // 7. Newlines -> <br> (code/math placeholders unaffected)
        html = html.replace(/\n/g, '<br>');

        // 8. Restore inline code
        html = html.replace(/\x00IC(\d+)\x00/g, function(m, idx) {
            return '<code class="inline-code">' + inlineCodes[parseInt(idx)] + '</code>';
        });

        // 9. Restore code blocks
        html = html.replace(/\x00CB(\d+)\x00/g, function(m, idx) {
            return codeBlocks[parseInt(idx)];
        });

        // 10. Restore math (escaped for safe DOM; KaTeX renders after insert)
        html = html.replace(/\x00MB(\d+)\x00/g, function(m, idx) {
            return mathBlocks[parseInt(idx)].replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        });

        return html;
    }

    async function updateNav() {
        const nav = $('main-nav');
        const badge = $('zone-badge');
        if (badge) {
            badge.textContent = ZONE;
            badge.className = 'zone-badge ' + ZONE_CLASS;
        }
        if (authToken && currentUser) {
            nav.style.display = 'flex';
            $('nav-username').textContent = currentUser.username || 'Пользователь';
            $('nav-role-badge').textContent = (currentUser.role === 'administrator' || currentUser.role === 'admin') ? 'Admin' : (currentUser.role === 'operator' ? 'Operator' : 'User');
            // Admin tab: visible only for admin/administrator
            const isAdmin = currentUser.role === 'administrator' || currentUser.role === 'admin';
            if ($('nav-admin')) $('nav-admin').style.display = isAdmin ? '' : 'none';
            // Monitoring tab: visible for admin or operator
            const canMonitor = isAdmin || currentUser.role === 'operator';
            if ($('nav-mon')) $('nav-mon').style.display = canMonitor ? '' : 'none';
            // Wiki and RAG: always visible for authenticated users
            if ($('nav-wiki')) $('nav-wiki').style.display = '';
            if ($('nav-rag')) $('nav-rag').style.display = '';
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
                authToken = res.data.session_id || res.data.token || 'session';
                // Fetch user info from /auth/me to get real role, tier, scopes
                currentUser = res.data.user || null;
                if (!currentUser || !currentUser.role) {
                    const meRes = await api('/auth/me');
                    if (meRes.ok && meRes.data) {
                        currentUser = meRes.data;
                    } else {
                        currentUser = { username: username, role: 'user' };
                    }
                }
                localStorage.setItem('aither_token', authToken);
                updateNav();
                loadModelCatalog();
                loadServerChats().then(maybeMigrateLegacy);
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
        authToken = null; currentUser = null;
        chatSessions = [];
        currentSessionId = null;
        localStorage.removeItem('aither_token');
        localStorage.removeItem('aither_chats');
        localStorage.removeItem('aither_current_chat');
        localStorage.removeItem('aither_chat');
        localStorage.removeItem('aither_page');
        updateNav(); showPage('login');
        setLoading(false);
    }

    // ── Registration with email verification ───────────────────────
    var regToken = null;
    var regTimer = null;
    var regSecondsLeft = 0;

    window.showRegisterForm = function() {
        $('login-form').style.display = 'none';
        $('register-form').style.display = 'block';
        $('register-step1').style.display = 'block';
        $('register-step2').style.display = 'none';
        hideAlert('login-error');
        hideAlert('register-error');
        hideAlert('register-info');
        // Copy username from login field if filled
        var loginUser = $('login-username').value.trim();
        if (loginUser && !$('reg-username').value) $('reg-username').value = loginUser;
    };

    window.hideRegisterForm = function() {
        $('login-form').style.display = 'block';
        $('register-form').style.display = 'none';
        stopRegTimer();
    };

    window.cancelRegistration = function() {
        stopRegTimer();
        regSecondsLeft = 0;
        regToken = null;
        $('login-form').style.display = 'block';
        $('register-form').style.display = 'none';
        $('register-step1').style.display = 'block';
        $('register-step2').style.display = 'none';
        hideAlert('register-error');
        hideAlert('register-info');
    };

    function stopRegTimer() {
        if (regTimer) { clearInterval(regTimer); regTimer = null; }
    }

    async function handleRegisterStart() {
        hideAlert('register-error');
        hideAlert('register-info');
        var username = $('reg-username').value.trim();
        var email = $('reg-email').value.trim();
        var pass = $('reg-password').value;
        var pass2 = $('reg-password2').value;

        if (!username || username.length < 3) {
            showAlert('register-error', 'Имя пользователя должно быть не менее 3 символов', 'danger');
            return;
        }
        if (!email || email.indexOf('@') === -1) {
            showAlert('register-error', 'Введите корректный email', 'danger');
            return;
        }
        if (!pass || pass.length < 16) {
            showAlert('register-error', 'Пароль должен содержать не менее 16 символов, заглавные и строчные буквы, цифры и спецсимволы', 'danger');
            return;
        }
        if (pass !== pass2) {
            showAlert('register-error', 'Пароли не совпадают', 'danger');
            return;
        }

        setLoading(true);
        $('btn-register-start').disabled = true;
        try {
            var res = await api('/auth/register', {
                method: 'POST',
                body: JSON.stringify({ username: username, password: pass, email: email }),
            });
            if (res.ok && res.data && res.data.registration_token) {
                regToken = res.data.registration_token;
                $('reg-email-display').textContent = email;
                $('register-step1').style.display = 'none';
                $('register-step2').style.display = 'block';
                // Start 90s countdown
                regSecondsLeft = res.data.expires_in || 90;
                $('reg-timer-value').textContent = regSecondsLeft;
                stopRegTimer();
                regTimer = setInterval(function() {
                    regSecondsLeft--;
                    $('reg-timer-value').textContent = regSecondsLeft;
                    if (regSecondsLeft <= 0) {
                        stopRegTimer();
                        // Auto-cancel on timeout
                        showAlert('register-error', 'Время действия кода истекло. Начните регистрацию заново.', 'danger');
                        $('register-step1').style.display = 'block';
                        $('register-step2').style.display = 'none';
                        regToken = null;
                    }
                }, 1000);
                // Focus code input
                setTimeout(function() { var ci = $('reg-code'); if (ci) ci.focus(); }, 200);
                showAlert('register-info', '📧 Код отправлен! Проверьте почту.', 'info');
            } else {
                var msg = res.data?.detail || 'Ошибка регистрации. Попробуйте позже.';
                showAlert('register-error', msg, 'danger');
            }
        } catch(e) {
            showAlert('register-error', 'Ошибка сети. Проверьте подключение.', 'danger');
        } finally {
            setLoading(false);
            $('btn-register-start').disabled = false;
        }
    }

    async function handleRegisterConfirm() {
        var code = $('reg-code').value.trim();
        if (!code || code.length !== 6 || !/^\d+$/.test(code)) {
            showAlert('register-error', 'Введите 6-значный код из письма', 'danger');
            return;
        }
        if (!regToken) {
            showAlert('register-error', 'Сессия регистрации истекла. Начните заново.', 'danger');
            return;
        }
        if (regSecondsLeft <= 0) {
            showAlert('register-error', 'Время действия кода истекло.', 'danger');
            return;
        }

        setLoading(true);
        $('btn-register-confirm').disabled = true;
        try {
            var res = await api('/auth/verify-registration', {
                method: 'POST',
                body: JSON.stringify({ registration_token: regToken, code: code }),
            });
            if (res.ok) {
                stopRegTimer();
                showAlert('register-info', '✅ Регистрация успешна! Теперь войдите.', 'success');
                hideAlert('register-error');
                // Switch back to login form with username pre-filled
                setTimeout(function() {
                    $('login-username').value = $('reg-username').value.trim();
                    $('login-password').value = '';
                    $('login-password').focus();
                    hideRegisterForm();
                    hideAlert('register-info');
                }, 1500);
            } else {
                var msg = res.data?.detail || 'Неверный код или сессия истекла';
                if (res.status === 410 || res.status === 404) {
                    stopRegTimer();
                    showAlert('register-error', 'Сессия истекла. Начните регистрацию заново.', 'danger');
                    $('register-step1').style.display = 'block';
                    $('register-step2').style.display = 'none';
                    regToken = null;
                } else {
                    showAlert('register-error', msg, 'danger');
                }
            }
        } catch(e) {
            showAlert('register-error', 'Ошибка сети. Проверьте подключение.', 'danger');
        } finally {
            setLoading(false);
            $('btn-register-confirm').disabled = false;
        }
    }

    // ── Forgot password flow ────────────────────────────────────────
    var forgotToken = null;
    var forgotTimer = null;
    var forgotSecondsLeft = 0;

    window.showForgotForm = function() {
        $('login-form').style.display = 'none';
        $('register-form').style.display = 'none';
        $('forgot-form').style.display = 'block';
        $('forgot-step1').style.display = 'block';
        $('forgot-step2').style.display = 'none';
        $('forgot-step3').style.display = 'none';
        hideAlert('login-error');
        hideAlert('forgot-error');
        hideAlert('forgot-info');
    };

    window.hideForgotForm = function() {
        $('login-form').style.display = 'block';
        $('forgot-form').style.display = 'none';
        stopForgotTimer();
    };

    window.cancelForgot = function() {
        stopForgotTimer();
        forgotToken = null;
        forgotSecondsLeft = 0;
        $('login-form').style.display = 'block';
        $('forgot-form').style.display = 'none';
        $('forgot-step1').style.display = 'block';
        $('forgot-step2').style.display = 'none';
        $('forgot-step3').style.display = 'none';
        hideAlert('forgot-error');
        hideAlert('forgot-info');
    };

    function stopForgotTimer() {
        if (forgotTimer) { clearInterval(forgotTimer); forgotTimer = null; }
    }

    async function handleForgotStart() {
        hideAlert('forgot-error');
        hideAlert('forgot-info');
        var email = $('forgot-email').value.trim();
        if (!email || email.indexOf('@') === -1) {
            showAlert('forgot-error', 'Введите корректный email', 'danger');
            return;
        }

        setLoading(true);
        $('btn-forgot-start').disabled = true;
        try {
            var res = await api('/auth/forgot-password', {
                method: 'POST',
                body: JSON.stringify({ email: email }),
            });
            if (res.ok && res.data) {
                forgotToken = res.data.registration_token || null;
                // ALWAYS move to step 2 for UX consistency (don't leak whether email exists)
                $('forgot-email-display').textContent = email;
                $('forgot-step1').style.display = 'none';
                $('forgot-step2').style.display = 'block';
                // Start timer
                forgotSecondsLeft = res.data.expires_in || 90;
                $('forgot-timer-value').textContent = forgotSecondsLeft;
                stopForgotTimer();
                forgotTimer = setInterval(function() {
                    forgotSecondsLeft--;
                    $('forgot-timer-value').textContent = forgotSecondsLeft;
                    if (forgotSecondsLeft <= 0) {
                        stopForgotTimer();
                        showAlert('forgot-error', 'Время действия кода истекло.', 'danger');
                        $('forgot-step1').style.display = 'block';
                        $('forgot-step2').style.display = 'none';
                        forgotToken = null;
                    }
                }, 1000);
                setTimeout(function() { var ci = $('forgot-code'); if (ci) ci.focus(); }, 200);
                showAlert('forgot-info', '📧 ' + (res.data.message || 'Код отправлен!'), 'info');
            } else {
                showAlert('forgot-error', res.data?.detail || 'Ошибка', 'danger');
            }
        } catch(e) {
            showAlert('forgot-error', 'Ошибка сети', 'danger');
        } finally {
            setLoading(false);
            $('btn-forgot-start').disabled = false;
        }
    }

    async function handleForgotVerify() {
        var code = $('forgot-code').value.trim();
        if (!code || code.length !== 6 || !/^\d+$/.test(code)) {
            showAlert('forgot-error', 'Введите 6-значный код', 'danger');
            return;
        }
        if (forgotSecondsLeft <= 0) {
            showAlert('forgot-error', 'Время кода истекло. Начните заново.', 'danger');
            return;
        }

        // Move to step 3 — actual verification happens on save via backend
        stopForgotTimer();
        hideAlert('forgot-error');
        $('forgot-step2').style.display = 'none';
        $('forgot-step3').style.display = 'block';
        setTimeout(function() { var pi = $('forgot-new-pass'); if (pi) pi.focus(); }, 200);
    }

    async function handleForgotSave() {
        var pass = $('forgot-new-pass').value;
        var pass2 = $('forgot-new-pass2').value;
        if (!pass || pass.length < 16) {
            showAlert('forgot-error', 'Пароль должен содержать не менее 16 символов, заглавные и строчные буквы, цифры и спецсимволы', 'danger');
            return;
        }
        if (pass !== pass2) {
            showAlert('forgot-error', 'Пароли не совпадают', 'danger');
            return;
        }
        var code = $('forgot-code').value.trim();

        setLoading(true);
        $('btn-forgot-save').disabled = true;
        try {
            var res = await api('/auth/reset-password', {
                method: 'POST',
                body: JSON.stringify({ registration_token: forgotToken, code: code, new_password: pass }),
            });
            if (res.ok) {
                showAlert('forgot-info', '✅ Пароль изменён! Теперь войдите.', 'success');
                hideAlert('forgot-error');
                setTimeout(function() {
                    cancelForgot();
                    hideAlert('forgot-info');
                }, 1500);
            } else {
                showAlert('forgot-error', res.data?.detail || 'Ошибка сброса пароля', 'danger');
            }
        } catch(e) {
            showAlert('forgot-error', 'Ошибка сети', 'danger');
        } finally {
            setLoading(false);
            $('btn-forgot-save').disabled = false;
        }
    }

    // ── Dashboard ──────────────────────────────────────────────
    async function loadDashboardInfo() {
        if (!currentUser) return;
        $('dash-username').textContent = currentUser.username || '—';
        const roleMap = { 'administrator': 'Администратор', 'admin': 'Администратор', 'operator': 'Оператор', 'user': 'Пользователь' };
        $('dash-role').textContent = roleMap[currentUser.role] || (currentUser.role || 'Пользователь');
        $('dash-zone').textContent = ZONE;
        if ($('dash-tier')) $('dash-tier').textContent = currentUser.tier || 'free';

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
                const modelDescriptions = {
                    'qwen3-32b': 'Qwen3-32B — AWQ 4-bit, контекст 64K',
                    'qwen3.8-27b': 'Qwen3.8-27B — FP8, контекст 64K',
                };
                for (const m of (Array.isArray(models) ? models : [])) {
                    const name = m.id || m.name;
                    const desc = modelDescriptions[name] || '(описание недоступно)';
                    html += '<p>✦ <strong>' + escHtml(name) + '</strong> — <span class="text-muted">' + escHtml(desc) + '</span></p>';
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
        if (model === 'qwen3-32b') {
            info.innerHTML = '<b>Qwen3-32B</b> — AWQ 4-bit<br>📏 Контекст (max-model-len): <b>64K токенов</b><br>🖥 Размещение: N8, TP=2';
            info.style.color = 'var(--text)';
        } else if (model === 'qwen3.8-27b') {
            info.innerHTML = '<b>Qwen3.8-27B</b> — FP8<br>📏 Контекст (max-model-len): <b>64K токенов</b><br>🖥 Размещение: N7, TP=2';
            info.style.color = 'var(--text)';
        } else {
            info.innerHTML = '';
        }
    }

    function addChatMessage(role, content, model) {
        const msgs = $('chat-messages');
        if (!msgs) return;
        let meta = '';
        if (role === 'assistant' && model) {
            meta = '<div class="msg-meta">🤖 ' + escHtml(model) + '</div>';
        }
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-msg ' + role;
        msgDiv.innerHTML = meta + formatMessage(content) +
            (role === 'assistant' ? '<div class="msg-actions"><button class="btn btn-sm btn-outline" onclick="var t=this.closest(\'.chat-msg\').textContent.replace(\'📋 Копировать\',\'\').trim();navigator.clipboard.writeText(t);this.textContent=\'✓ Скопировано\';setTimeout(()=>this.remove(),2000);">📋 Копировать</button></div>' : '');
        msgs.appendChild(msgDiv);
        renderMathInElement(msgDiv);
        msgs.scrollTop = msgs.scrollHeight;
    }

    function showChatError(code, detail) {
        const errors = {
            401: 'Ошибка авторизации. Войдите заново.',
            403: 'Доступ запрещён. Возможные причины: нет тарифа, нет прав на модель, нет организации.',
            404: 'Модель или endpoint не найден.',
            422: 'Некорректный запрос.',
            429: 'Превышен лимит запросов. Подождите минуту.',
            500: 'Внутренняя ошибка сервера.',
            502: 'Ошибка шлюза.',
            503: 'Сервис временно недоступен.',
            504: 'Таймаут — модель не успела ответить.',
            0: 'Ошибка сети — проверьте подключение.',
        };
        const msg = errors[code] || ('Ошибка HTTP ' + code + ': ' + (detail || 'неизвестная ошибка'));
        addChatMessage('error', msg);
    }

    const DEFAULT_MAX_TOKENS = 2048;
    const HARD_MAX_TOKENS = 4096;

    function reRenderSessionMessages(s) {
        var msgs = $('chat-messages');
        if (!msgs) return;
        msgs.innerHTML = '';
        var h = s.history || [];
        for (var i = 0; i < h.length; i++) {
            var msg = h[i];
            if (msg.role === 'user') addChatMessage('user', msg.content);
            else if (msg.role === 'assistant') addChatMessage('assistant', msg.content, msg.model || '');
            else if (msg.role === 'error') addChatMessage('error', msg.content);
        }
        var gen = ensureGeneration(s);
        if (gen.status === 'generating') {
            addChatMessage('assistant', '⏳ Генерация ответа...', gen.model || s.model || DEFAULT_MODEL_ID);
        } else if (gen.status === 'needs_continue') {
            addChatMessage('system', '⚠️ Ответ достиг установленного лимита.');
            addContinueButton(gen.model || s.model || DEFAULT_MODEL_ID);
        }
    }

    async function sendChatMessage() {
        if (!modelCatalogLoaded || !modelCatalog.length) {
            addChatMessage('error', 'Каталог моделей недоступен — отправка отключена. Обновите страницу.');
            return;
        }
        var input = $('chat-input');
        var model = resolveActiveModel($('chat-model-select')?.value);
        var content = input.value.trim();
        if (!content) return;
        if (authToken === null) { showChatError(401); return; }

        input.value = '';
        $('btn-send-message').disabled = true;

        var maxTokens = parseInt($('chat-max-tokens')?.value) || DEFAULT_MAX_TOKENS;
        if (maxTokens > HARD_MAX_TOKENS) { maxTokens = HARD_MAX_TOKENS; }
        var temperature = parseFloat($('chat-temperature')?.value) || 0.7;

        // Capture exact session + generation state
        var session = getCurrentSession();
        var sessionId = session.id;
        var gen = ensureGeneration(session);
        var requestId = uid();
        var answerId = 'a' + uid();
        gen.status = 'generating';
        gen.request_id = requestId;
        gen.answer_id = answerId;
        gen.model = model;
        gen.finish_reason = null;

        session.history.push({ role: 'user', content: content });
        session.model = model;
        if (session.title === 'Новый чат') {
            session.title = content.length > 50 ? content.substring(0, 47) + '...' : content;
        }
        saveChatSessions();
        renderChatList();
        if (currentSessionId === sessionId) {
            // Render user bubble + generation indicator from state (single source of truth)
            reRenderSessionMessages(session);
        }
        // Persist the user question to the server BEFORE long inference
        await enqueueServerPersist(session);

        var messages = session.history.slice(-20);
        try {
            const res = await api('/chat', {
                method: 'POST',
                body: JSON.stringify({ model: model, messages: messages, max_tokens: maxTokens, temperature: temperature }),
            });

            // Session-safe response handling (captured sessionId, not current)
            var s2 = findSession(sessionId);
            if (!s2) return; // session deleted while awaiting
            var g2 = ensureGeneration(s2);
            if (g2.request_id !== requestId) return; // stale response

            if (res.ok && res.data) {
                var reply = '';
                var finishReason = 'stop';
                if (res.data.choices && res.data.choices[0]) {
                    var choice = res.data.choices[0];
                    reply = choice.message?.content || choice.text || JSON.stringify(choice);
                    finishReason = choice.finish_reason || 'stop';
                } else if (res.data.content) {
                    reply = res.data.content;
                } else if (res.data.response) {
                    reply = res.data.response;
                }
                if (!reply || reply.trim() === '') {
                    reply = res.data.choices?.[0]?.text || 'Пустой ответ от модели.';
                }

                // Append to logical assistant answer (same answer_id)
                var ansItem = findAnswerItem(s2, answerId);
                if (ansItem) {
                    ansItem.content = ansItem.content + '\n' + reply;
                    ansItem.finish_reason = finishReason;
                } else {
                    s2.history.push({ role: 'assistant', content: reply, model: model, answer_id: answerId, finish_reason: finishReason });
                }
                g2.finish_reason = finishReason;
                g2.status = (finishReason === 'length') ? 'needs_continue' : 'idle';
                g2.request_id = null;
                g2.answer_id = (finishReason === 'length') ? answerId : null;

                if (res.data.usage) {
                    s2.tokens += (res.data.usage.total_tokens || 0);
                } else {
                    s2.tokens += Math.round(reply.length / 4);
                }
                s2.requests++;
                saveChatSessions();
                updateTokenCounters();
                renderChatList();
                enqueueServerPersist(s2);
                if (currentSessionId === sessionId) {
                    reRenderSessionMessages(s2);
                }
            } else {
                g2.status = 'idle';
                g2.request_id = null;
                saveChatSessions();
                if (currentSessionId === sessionId) {
                    showChatError(res.status, res.data?.detail || res.data?.error || '');
                }
            }
        } catch (e) {
            var s3 = findSession(sessionId);
            if (s3) {
                var g3 = ensureGeneration(s3);
                if (g3.request_id === requestId) {
                    g3.status = 'idle';
                    g3.request_id = null;
                    saveChatSessions();
                }
            }
            if (currentSessionId === sessionId) {
                if (s3) reRenderSessionMessages(s3);
                showChatError(0);
            }
        } finally {
            $('btn-send-message').disabled = false;
            input.focus();
        }
    }

    function addContinueButton(model) {
        const msgs = $('chat-messages');
        if (!msgs) return;
        const btn = document.createElement('button');
        btn.className = 'btn btn-sm btn-outline btn-continue';
        btn.textContent = 'Продолжить';
        btn.onclick = function () { continueAnswer(model, btn); };
        msgs.appendChild(btn);
        msgs.scrollTop = msgs.scrollHeight;
    }

    async function continueAnswer(model, btn) {
        var session = getCurrentSession();
        var sessionId = session.id;
        var gen = ensureGeneration(session);
        if (gen.status !== 'needs_continue') return;
        var answerId = gen.answer_id;
        var requestId = uid();
        gen.status = 'generating';
        gen.request_id = requestId;
        saveChatSessions();
        if (btn) btn.remove();
        if (currentSessionId === sessionId) {
            addChatMessage('assistant', '⏳ Генерация продолжения...', model);
        }
        var messages = session.history.slice(-20).concat([
            { role: 'user', content: 'Продолжи ответ с места остановки. Не повторяй уже написанное.' }
        ]);
        try {
            const res = await api('/chat', {
                method: 'POST',
                body: JSON.stringify({
                    model: model,
                    messages: messages,
                    max_tokens: DEFAULT_MAX_TOKENS,
                    temperature: 0.7,
                }),
            });

            var s2 = findSession(sessionId);
            if (!s2) return;
            var g2 = ensureGeneration(s2);
            if (g2.request_id !== requestId) return;

            if (res.ok && res.data) {
                var reply = '';
                var fr = 'stop';
                if (res.data.choices && res.data.choices[0]) {
                    var choice = res.data.choices[0];
                    reply = choice.message?.content || choice.text || '';
                    fr = choice.finish_reason || 'stop';
                }
                if (!reply || reply.trim() === '') {
                    reply = res.data.choices?.[0]?.text || 'Пустой ответ от модели.';
                }

                // Append to the SAME logical assistant answer
                var ansItem = findAnswerItem(s2, answerId);
                if (ansItem) {
                    ansItem.content = ansItem.content + '\n' + reply;
                    ansItem.finish_reason = fr;
                }
                g2.finish_reason = fr;
                g2.status = (fr === 'length') ? 'needs_continue' : 'idle';
                g2.request_id = null;
                g2.answer_id = (fr === 'length') ? answerId : null;

                if (res.data.usage) {
                    s2.tokens += (res.data.usage.total_tokens || 0);
                } else {
                    s2.tokens += Math.round(reply.length / 4);
                }
                s2.requests++;
                saveChatSessions();
                updateTokenCounters();
                renderChatList();
                enqueueServerPersist(s2);
                if (currentSessionId === sessionId) {
                    reRenderSessionMessages(s2);
                }
            } else {
                g2.status = 'needs_continue';
                g2.request_id = null;
                saveChatSessions();
                if (currentSessionId === sessionId) {
                    showChatError(res.status, res.data?.detail || res.data?.error || '');
                }
            }
        } catch (e) {
            var s3 = findSession(sessionId);
            if (s3) {
                var g3 = ensureGeneration(s3);
                if (g3.request_id === requestId) {
                    g3.status = 'needs_continue';
                    g3.request_id = null;
                    saveChatSessions();
                }
            }
            if (currentSessionId === sessionId) {
                if (s3) reRenderSessionMessages(s3);
                showChatError(0);
            }
        }
    }

    function clearChat() {
        var s = getCurrentSession();
        s.history = [];
        s.tokens = 0;
        s.requests = 0;
        s.title = 'Новый чат';
        s.generation = { status: 'idle', request_id: null, answer_id: null, model: null, finish_reason: null };
        updateTokenCounters();
        var msgs = $('chat-messages');
        if (msgs) { msgs.innerHTML = ''; }
        saveChatSessions();
        renderChatList();
    }

    // ── Multi-session chat ops ────────────────────────────────────
    window._switchChat = function(sessionId) {
        // Save current before switching
        saveChatSessions();
        currentSessionId = sessionId;
        localStorage.setItem('aither_current_chat', currentSessionId);
        var s = getCurrentSession();
        // Restore model only if still in the active catalog; otherwise migrate.
        if (s.model && isActiveModel(s.model)) {
            if ($('chat-model-select')) $('chat-model-select').value = s.model;
        } else {
            s.model = DEFAULT_MODEL_ID;
            if ($('chat-model-select')) $('chat-model-select').value = DEFAULT_MODEL_ID;
        }
        updateModelInfo();
        // Restore messages + generation state (generating / needs_continue)
        reRenderSessionMessages(s);
        updateTokenCounters();
        renderChatList();
    };

    window._deleteChat = function(sessionId) {
        var target = findSession(sessionId);
        var filtered = [];
        for (var i = 0; i < chatSessions.length; i++) {
            if (chatSessions[i].id !== sessionId) filtered.push(chatSessions[i]);
        }
        chatSessions = filtered;
        saveChatSessions();
        if (target) serverDeleteChat(target);
        if (sessionId === currentSessionId) {
            currentSessionId = chatSessions.length > 0 ? chatSessions[0].id : null;
            if (currentSessionId) {
                window._switchChat(currentSessionId);
            } else {
                // No sessions left, create new
                currentSessionId = uid();
                var ns = { id: currentSessionId, title: 'Новый чат', timestamp: new Date().toISOString(), model: DEFAULT_MODEL_ID, history: [], tokens: 0, requests: 0 };
                chatSessions = [ns];
                saveChatSessions();
                var msgs = $('chat-messages');
                if (msgs) msgs.innerHTML = '';
                updateTokenCounters();
            }
        }
        renderChatList();
    };

    window._newChat = function() {
        saveChatSessions();
        currentSessionId = uid();
        var ns = { id: currentSessionId, title: 'Новый чат', timestamp: new Date().toISOString(), model: resolveActiveModel($('chat-model-select')?.value), history: [], tokens: 0, requests: 0 };
        chatSessions.unshift(ns);
        // Reset UI
        var msgs = $('chat-messages');
        if (msgs) msgs.innerHTML = '';
        // Reset model select to the default active model
        if ($('chat-model-select')) $('chat-model-select').value = DEFAULT_MODEL_ID;
        updateModelInfo();
        updateTokenCounters();
        saveChatSessions();
        renderChatList();
    };

    // Legacy names for backward compat (used by checkSession and other parts)
    function saveChatState() { saveChatSessions(); }
    function loadChatState() {
        loadChatSessions();
        return getCurrentSession().history;
    }
    function restoreChatMessages() {
        var s = getCurrentSession();
        reRenderSessionMessages(s);
        updateTokenCounters();
        renderChatList();
    }

    // ── API Keys ───────────────────────────────────────────────
    async function loadApiKeys() {
        setLoading(true);
        try {
            const res = await api('/api-keys');
            const tokens = res.data?.tokens || (Array.isArray(res.data) ? res.data : []);
            if (res.ok) {
                if (tokens.length === 0) {
                    $('apikeys-content').innerHTML = '<p class="text-muted">Нет созданных ключей. Нажмите «Создать новый ключ».</p>';
                    return;
                }
                let html = '<table class="data-table"><tr><th>Название</th><th>Префикс</th><th>Назначение</th><th>Модели</th><th>Создан</th><th>Истекает</th><th>Последнее использование</th><th>Статус</th><th>Действия</th></tr>';
                for (const k of tokens) {
                    const revoked = k.revoked || k.revoked_at;
                    const prefix = (k.key_prefix || k.token_id || k.id || '—');
                    var sf = (k.scopes || []).map(function(s) { return s === 'model:qwen3:chat' ? 'Qwen3 (qwen3-32b, qwen3.8-27b)' : s; });
                    sf = Array.from(new Set(sf)).join(', ');
                    var sc = revoked ? 'badge-revoked' : (k.status === 'expired' ? 'badge-expired' : 'badge-enabled');
                    var st = revoked ? 'Отозван' : (k.status === 'expired' ? 'Истёк' : 'Активен');
                    html += '<tr><td>' + escHtml(k.name || '—') + '</td><td><code>' + escHtml(k.key_prefix || '—') + '</code></td><td>' + escHtml(k.purpose || 'api') + '</td><td>' + escHtml(sf) + '</td><td>' + ((k.created_at || '').substring(0, 10) || '—') + '</td><td>' + ((k.expires_at || '').substring(0, 10) || '—') + '</td><td>' + ((k.last_used_at || '').substring(0, 16) || '—') + '</td><td class="' + sc + '">' + st + '</td><td>' + (revoked ? '' : '<button class="btn btn-sm btn-danger" onclick="window._revokeToken(\'' + (k.id || k.key_prefix || k.token_id) + '\')">Отозвать</button>') + '</td></tr>';
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


    function showCreateTokenModal() {
        modal('\n            <h2>Создать API-ключ</h2>\n            <div class="form-group">\n                <label>Название</label>\n                <input type="text" id="modal-token-name" class="form-input" placeholder="Например: Hermes Home">\n            </div>\n            <div class="form-group">\n                <label>Назначение</label>\n                <select id="modal-token-purpose" class="form-input">\n                    <option value="agent">🤖 AI Agent</option>\n                    <option value="api">🔌 API / Разработка</option>\n                    <option value="other">📌 Другое</option>\n                </select>\n            </div>\n            <div class="form-group">\n                <label>Модели</label>\n                <div style="display:flex;flex-direction:column;gap:6px;margin-top:6px;">\n                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">\n                        <input type="checkbox" id="modal-model-qwen3-32b" value="qwen3-32b" checked>\n                        <span>Qwen3-32B</span>\n                    </label>\n                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">\n                        <input type="checkbox" id="modal-model-qwen38-27b" value="qwen3.8-27b" checked>\n                        <span>Qwen3.8-27B</span><br><span style="font-size:11px;color:var(--text-muted);">Обе модели используют scope model:qwen3:chat</span>\n                    </label>\n                </div>\n            </div>\n            <div class="form-group">\n                <label>Срок действия</label>\n                <select id="modal-token-expiry" class="form-input">\n                    <option value="30">30 дней</option>\n                    <option value="90" selected>90 дней</option>\n                    <option value="180">180 дней</option>\n                    <option value="365">365 дней</option>\n                </select>\n            </div>\n            <div id="modal-token-result" style="display:none;">\n                <div class="alert alert-success" style="margin-top:12px;">\n                    ✅ API-ключ создан. <strong>Показан только один раз.</strong>\n                </div>\n                <div class="copy-field">\n                    <input type="text" id="modal-token-full" readonly>\n                    <button class="btn btn-sm btn-primary" onclick="var i=document.getElementById(\'modal-token-full\');i.select();navigator.clipboard?.writeText(i.value);this.textContent=\'✓ Скопировано\';setTimeout(()=>this.textContent=\'Копировать\',2000);">Копировать</button>\n                </div>\n                <p class="text-muted" style="margin-top:4px;">Формат: aither_... (Bearer-токен)</p>\n            </div>\n            <div style="display:flex;gap:8px;margin-top:16px;">\n                <button class="btn btn-primary" id="modal-token-create-btn" onclick="window._createToken()">Создать API-ключ</button>\n                <button class="btn btn-outline" onclick="closeModal()">Закрыть</button>\n            </div>\n        ');
    }

    window._createToken = async function() {
            const name = document.getElementById('modal-token-name')?.value?.trim() || 'API Key';
            const purpose = document.getElementById('modal-token-purpose')?.value || 'agent';
            // Both active Qwen3 models share the single model:qwen3:chat scope.
            const want32b = document.getElementById('modal-model-qwen3-32b')?.checked;
            const want38b = document.getElementById('modal-model-qwen38-27b')?.checked;
            const scopes = (want32b || want38b) ? ['model:qwen3:chat'] : [];
            if (scopes.length === 0) { alert('Выберите хотя бы одну модель.'); return; }
            const expiresInDays = Number(document.getElementById('modal-token-expiry')?.value || 90);
            document.getElementById('modal-token-create-btn').disabled = true;
            try {
                const resp = await api('/api-keys', {
                    method: 'POST',
                    body: JSON.stringify({ name, purpose, scopes, expires_in_days: expiresInDays })
                });
                if (resp.ok && resp.data && resp.data.key) {
                    document.getElementById('modal-token-result').style.display = 'block';
                    document.getElementById('modal-token-full').value = resp.data.key;
                    await loadApiKeys();
                } else {
                    alert('Ошибка: ' + (resp.data?.detail || 'не удалось создать ключ'));
                }
            } catch(e) { alert('Ошибка сети'); }
            document.getElementById('modal-token-create-btn').disabled = false;
        }


    // ── Status ─────────────────────────────────────────────────
    async function loadStatusPage() {
        setLoading(true);
        try {
            const h = await fetch('/health').then(r => r.json());
            let html = '<div class="info-row"><span class="info-label">Статус</span><span class="info-value" style="color:var(--success)">✓ Работает</span></div>';
            html += '<div class="info-row"><span class="info-label">Версия</span><span class="info-value">' + (h.version || '—') + '</span></div>';
            html += '<div class="info-row"><span class="info-label">Redis</span><span class="info-value" style="color:' + (h.redis==='connected'?'var(--success)':'var(--danger)') + '">' + (h.redis || '—') + '</span></div>';
            html += '<div class="info-row"><span class="info-label">Rate Limit</span><span class="info-value">' + (h.rate_limit || '—') + '</span></div>';
            html += '<div class="info-row"><span class="info-label">Auth</span><span class="info-value">' + (h.auth || '—') + '</span></div>';
            html += '<div class="info-row"><span class="info-label">Зона</span><span class="info-value">' + ZONE + '</span></div>';
            $('status-content').innerHTML = html;
        } catch {
            $('status-content').innerHTML = '<p class="text-muted">Не удалось получить статус</p>';
        }
        try {
            const v = await fetch('/version').then(r => r.json());
            $('version-content').innerHTML = '<div class="info-row"><span class="info-label">Сервис</span><span class="info-value">' + (v.service||'—') + '</span></div><div class="info-row"><span class="info-label">Версия</span><span class="info-value">' + (v.version||'—') + '</span></div><div class="info-row"><span class="info-label">Сборка</span><span class="info-value">' + (v.build||'—') + '</span></div>';
        } catch { $('version-content').innerHTML = '<p class="text-muted">—</p>'; }
        setLoading(false);
    }

    // ── Profile ────────────────────────────────────────────────
    async function loadProfile() {
        if (!currentUser) return;
        // Refresh user from /auth/me
        try {
            const res = await api('/auth/me');
            if (res.ok && res.data) currentUser = { ...currentUser, ...res.data };
        } catch {}
        $('profile-id').textContent = currentUser.id || '—';
        $('profile-username').textContent = currentUser.username || '—';
        const roleMap = { 'administrator': 'Администратор', 'admin': 'Администратор', 'operator': 'Оператор', 'user': 'Пользователь' };
        $('profile-role').textContent = roleMap[currentUser.role] || (currentUser.role || '—');
        $('profile-tier').textContent = currentUser.tier || 'free';
        $('profile-zone').textContent = ZONE;
    }

    // ── Session check ──────────────────────────────────────────
    async function checkSession() {
        if (!authToken) return false;
        try {
            const res = await fetch(API_URL + '/auth/me', {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + authToken
                },
                credentials: 'same-origin'
            });
            if (res.ok) {
                currentUser = await res.json();
                updateNav();
                loadModelCatalog();
                // Restore saved page, default to dashboard
                var savedPage = 'dashboard';
                try { savedPage = localStorage.getItem('aither_page') || 'dashboard'; } catch(e) {}
                showPage(savedPage);
                if (savedPage === 'dashboard') loadDashboardInfo();
                if (savedPage === 'chat') { updateModelInfo(); restoreChatMessages(); }
                if (savedPage === 'api-keys') loadApiKeys();
                return true;
            }
        } catch {}
        authToken = null; currentUser = null;
        localStorage.removeItem('aither_token');
        updateNav(); showPage('login');
        return false;
    }

    // ── Documentation viewer ────────────────────────────────────
    window.showDoc = function(path) {
        setLoading(true);
        fetch(path)
            .then(function(r) {
                if (r.ok) return r.text();
                throw new Error('HTTP ' + r.status);
            })
            .then(function(text) {
                setLoading(false);
                var title = path.split('/').pop().replace(/\.md$/, '').replace(/_/g, ' ');
                var mdHtml = renderMarkdown(text);
                modal('<div style="max-width:900px;">' +
                    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">' +
                    '<h2 style="margin:0;font-size:18px;color:var(--primary);">' + escHtml(title) + '</h2>' +
                    '<button class="btn btn-sm btn-outline" onclick="closeModal()">✕ Закрыть</button>' +
                    '</div>' +
                    '<div class="wiki-doc-body" style="max-height:65vh;">' + mdHtml + '</div>' +
                    '<div style="margin-top:12px;display:flex;gap:8px;">' +
                    '<button class="btn btn-sm btn-outline" onclick="window.open(\'' + path + '\',\'_blank\')">Открыть в новом окне</button></div>' +
                    '</div>');
                var db = document.querySelector('.wiki-doc-body');
                if (db) renderMathInElement(db);
            })
            .catch(function() {
                setLoading(false);
                window.open(path, '_blank');
            });
    };

    // ── Tariffs ─────────────────────────────────────────────────
    async function loadTariffsPage() {
        setLoading(true);
        try {
            // Show current tier
            if (currentUser && currentUser.tier) {
                const tierEl = $('current-tier-display');
                if (tierEl) tierEl.textContent = currentUser.tier;
                const activeEl = $('tariff-active');
                if (activeEl) activeEl.style.display = 'block';
            }
            // Highlight current tier with CSS class
            document.querySelectorAll('.tier-card').forEach(function(card) {
                card.classList.remove('active');
            });
            if (currentUser && currentUser.tier) {
                var currentCard = $('tier-' + currentUser.tier);
                if (currentCard) currentCard.classList.add('active');
            }
        } catch(e) {}
        setLoading(false);
    }

    window._selectTier = async function(tier) {
        setLoading(true);
        const tierNames = { free: 'Free', starter: 'Starter', pro: 'Pro', enterprise: 'Enterprise' };
        try {
            const res = await api('/billing/tier', {
                method: 'POST',
                body: JSON.stringify({ tier: tier }),
            });
            if (res.ok) {
                if ($('tariff-selected')) $('tariff-selected').style.display = 'block';
                if ($('tariff-name')) $('tariff-name').textContent = tierNames[tier] || tier;
                if ($('current-tier-display')) $('current-tier-display').textContent = tier;
                if ($('tariff-active')) $('tariff-active').style.display = 'block';
                if (currentUser) currentUser.tier = tier;
                loadTariffsPage();
            } else {
                // Backend may not support tier change — show informational message
                if ($('tariff-selected')) $('tariff-selected').style.display = 'block';
                if ($('tariff-name')) $('tariff-name').textContent = tierNames[tier] || tier + ' (для изменения обратитесь к администратору)';
            }
        } catch(e) {
            if ($('tariff-selected')) $('tariff-selected').style.display = 'block';
            if ($('tariff-name')) $('tariff-name').textContent = tierNames[tier] || tier + ' (для изменения обратитесь к администратору)';
        }
        setLoading(false);
    };

    // ── Init ──────────────────────────────────────────────────
    function init() {
        // Load sessions early
        loadChatSessions();
        updateNav();
        $('login-form')?.addEventListener('submit', handleLogin);
        $('btn-logout')?.addEventListener('click', handleLogout);
        $('btn-create-apikey')?.addEventListener('click', showCreateTokenModal);
        $('btn-send-message')?.addEventListener('click', sendChatMessage);
        $('btn-clear-chat')?.addEventListener('click', clearChat);
        $('btn-new-chat')?.addEventListener('click', window._newChat);
        $('btn-register-start')?.addEventListener('click', handleRegisterStart);
        $('btn-register-confirm')?.addEventListener('click', handleRegisterConfirm);
        $('btn-forgot-start')?.addEventListener('click', handleForgotStart);
        $('btn-forgot-verify')?.addEventListener('click', handleForgotVerify);
        $('btn-forgot-save')?.addEventListener('click', handleForgotSave);
        // Allow Enter in forgot code input
        $('forgot-code')?.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') { e.preventDefault(); handleForgotVerify(); }
        });
        // Allow Enter in code input to confirm
        $('reg-code')?.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') { e.preventDefault(); handleRegisterConfirm(); }
        });
        $('btn-submit-feedback')?.addEventListener('click', async function() {
            const topic = $('feedback-topic')?.value || 'other';
            const message = $('feedback-message')?.value?.trim();
            if (!message) {
                showAlert('feedback-success', 'Пожалуйста, введите сообщение.', 'danger');
                return;
            }
            try {
                const formData = new FormData();
                formData.append('topic', topic);
                formData.append('message', message);
                const fileInput = $('feedback-file');
                if (fileInput && fileInput.files.length > 0) {
                    formData.append('file', fileInput.files[0]);
                }
                const headers = {};
                const token = localStorage.getItem('aither_token');
                if (token) headers['Authorization'] = 'Bearer ' + token;
                const resp = await fetch('/api/v1/feedback', {
                    method: 'POST',
                    headers: headers,
                    body: formData
                });
                if (resp.ok) {
                    showAlert('feedback-success', '✅ Спасибо! Ваш отзыв отправлен.', 'success');
                    $('feedback-message').value = '';
                    if (fileInput) fileInput.value = '';
                } else {
                    const err = await resp.json().catch(() => ({}));
                    showAlert('feedback-success', '❌ Ошибка: ' + (err.detail || 'не удалось отправить'), 'danger');
                }
            } catch (e) {
                showAlert('feedback-success', '❌ Ошибка сети: ' + e.message, 'danger');
            }
        });
        $('chat-model-select')?.addEventListener('change', updateModelInfo);
        $('chat-temperature')?.addEventListener('input', function() {
            if ($('chat-temp-val')) $('chat-temp-val').textContent = this.value;
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
                if (page === 'admin') loadAdminPage();
                if (page === 'tariffs') loadTariffsPage();
                if (page === 'billing') loadBillingPage();
                if (page === 'usage') loadUsagePage();
                if (page === 'wiki') loadWikiPage();
                if (page === 'rag') loadRagPage();
                if (page === 'monitoring') loadMonitoringPage();
            });
        });

        updateModelInfo();

        // OAuth callback: extract token from URL and store it
        var params = new URLSearchParams(window.location.search);
        var oauthToken = params.get('aither_token');
        if (oauthToken && oauthToken.length > 10) {
            authToken = oauthToken;
            localStorage.setItem('aither_token', authToken);
            window.history.replaceState({}, document.title, window.location.pathname);
        }

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
                checkSession();
            } else {
                showAlert('login-error', result.data.detail || 'LDAP authentication failed', 'danger');
            }
        })
        .catch(function(e) {
            setLoading(false);
            showAlert('login-error', 'LDAP service unavailable: ' + e.message, 'danger');
        });
    };

    // ── Admin Dashboard ──────────────────────────────────────────
    async function loadAdminPage() {
        setLoading(true);
        try {
            const h = await api('/admin/gateway/health');
            if (h.ok) {
                const deps = h.data.dependencies || {};
                $('admin-gateway').innerHTML = Object.entries(deps).map(([k,v]) =>
                    '<div>' + escHtml(k) + ': ' + (typeof v==='object'?JSON.stringify(v):v) + '</div>').join('');
            }
            const m = await api('/admin/gateway/models');
            if (m.ok) {
                const models = m.data.models || [];
                $('admin-models').innerHTML = models.map(m =>
                    '<div>' + escHtml(m.id) + ': ' + (m.display_name||'') + ' (' + (m.status||'?') + ')</div>').join('') || 'Нет данных';
            }
            const u = await api('/admin/users');
            if (u.ok) {
                const users = Array.isArray(u.data) ? u.data : (u.data.users||[]);
                $('admin-users').innerHTML = users.slice(0,10).map(u =>
                    '<div>' + escHtml(u.username) + ' (' + (u.role||'?') + ') ' + (u.disabled?'⛔':'') + '</div>').join('') || 'Нет пользователей';
            }
        } catch(e) {}
        setLoading(false);
    }

    window._adminAction = async function(action, model) {
        setLoading(true);
        const res = await api('/admin/gateway/models/' + model + '/' + action, {method:'POST'});
        alert((res.ok?'✅ ':'❌ ') + (res.data?.status || res.data?.detail || 'OK'));
        setLoading(false);
        if (res.ok) loadAdminPage();
    };

    async function loadBillingPage() {
        setLoading(true);
        try {
            const b = await api('/billing/me');
            if (b.ok && b.data) {
                $('billing-balance').innerHTML = '\n                    <div>Баланс: <b>' + (b.data.balance||0) + '</b></div>\n                    <div>Зарезервировано: ' + (b.data.reserved||0) + '</div>\n                    <div>Доступно: ' + (b.data.available||0) + '</div>';
                $('billing-tier').innerHTML = '\n                    <div>Тариф: <b style="color:var(--primary)">' + (b.data.tier||'free') + '</b></div>\n                    <div>Лимит: ' + (b.data.quota_daily||'—') + ' запросов/день</div>';
                $('billing-stats').innerHTML = '\n                    <div>Запросов сегодня: <b>' + (b.data.requests_today||0) + '</b></div>\n                    <div>Токенов: ' + (b.data.tokens_today||0) + '</div>';
            } else {
                // Fallback: show user's tier and current counters
                $('billing-balance').innerHTML = '<div>Баланс: <b>0</b></div><div class="text-muted">Биллинг-сервис недоступен</div>';
                $('billing-tier').innerHTML = '<div>Тариф: <b style="color:var(--primary)">' + (currentUser?.tier || 'free') + '</b></div><div class="text-muted">Для изменения перейдите на вкладку 💳 Тарифы</div>';
                $('billing-stats').innerHTML = '<div>Запросов (сессия): <b>' + getCurrentSession().requests + '</b></div><div>Токенов (сессия): <b>' + getCurrentSession().tokens + '</b></div>';
            }
            // Ledger
            try {
                const l = await api('/billing/me/ledger');
                if (l.ok && l.data && l.data.ledger && l.data.ledger.length > 0) {
                    const ledger = l.data.ledger;
                    $('billing-ledger').innerHTML = '<table class="data-table"><tr><th>Сумма</th><th>Тип</th><th>Баланс</th><th>Время</th></tr>' +
                        ledger.slice(0,15).map(r => '<tr>\n                        <td>' + r.amount + '</td><td>' + r.operation + '</td>\n                        <td>' + r.balance_after + '</td><td>' + ((r.created_at||'').substring(0,16)) + '</td>\n                    </tr>').join('') + '</table>';
                } else {
                    $('billing-ledger').innerHTML = '<p class="text-muted">История операций недоступна</p>';
                }
            } catch(e) {
                $('billing-ledger').innerHTML = '<p class="text-muted">История операций недоступна</p>';
            }
        } catch(e) {
            $('billing-balance').innerHTML = '<p class="text-muted">Биллинг недоступен</p>';
        }
        setLoading(false);
    }

    async function loadUsagePage() {
        setLoading(true);
        try {
            const u = await api('/usage/me');
            if (u.ok && u.data) {
                $('usage-today').innerHTML = '\n                    <div>Запросов сегодня: <b>' + (u.data.requests_today||0) + '</b></div>\n                    <div>Всего запросов: ' + (u.data.total_requests||0) + '</div>';
                $('usage-tokens').innerHTML = '\n                    <div>Входных токенов: <b>' + (u.data.input_tokens||u.data.tokens_today||0) + '</b></div>\n                    <div>Выходных токенов: <b>' + (u.data.output_tokens||0) + '</b></div>\n                    <div>Всего токенов: ' + (u.data.total_tokens||0) + '</div>';
            } else {
                $('usage-today').innerHTML = '<div>Запросов (сессия): <b>' + getCurrentSession().requests + '</b></div><p class="text-muted">Данные сервера недоступны</p>';
                $('usage-tokens').innerHTML = '<div>Токенов (сессия): <b>' + getCurrentSession().tokens + '</b></div><p class="text-muted">Данные сервера недоступны</p>';
            }
            var curSession = getCurrentSession();
            var usageModel = (curSession && curSession.model) ? (MODEL_LABELS[curSession.model] || curSession.model) : '—';
            $('usage-models').innerHTML = '<div class="text-muted">📊 Модель текущей сессии:</div>\n                <div>' + escHtml(usageModel) + ' ' + (getCurrentSession().requests > 0 ? '✓' : '—') + '</div>';
        } catch(e) {
            $('usage-today').innerHTML = '<p class="text-muted">Ошибка загрузки</p>';
        }
        setLoading(false);
    }

    // ── RAG Page ─────────────────────────────────────────────────
    async function loadRagPage() {
        setLoading(true);
        try {
            const s = await api('/rag/status');
            if (s.ok && s.data) {
                var d = s.data;
                $('rag-status').innerHTML =
                    '<div style="font-size:16px;font-weight:700;color:var(--success);margin-bottom:8px;">✓ Доступен</div>' +
                    '<div class="info-row"><span class="info-label">Документов</span><span class="info-value">' + (d.documents||0) + '</span></div>' +
                    '<div class="info-row"><span class="info-label">Движок</span><span class="info-value" style="font-size:11px;">' + escHtml(d.engine||'—') + '</span></div>' +
                    '<div class="info-row"><span class="info-label">Поиск</span><span class="info-value" style="color:var(--success);">Token-overlap + boost</span></div>';
            } else {
                $('rag-status').innerHTML = '<div style="color:var(--warning);font-weight:600;">⚠ Требуется scope rag:query</div><p class="text-muted" style="font-size:11px;">Для использования RAG необходим тариф Free+ и scope rag:query.</p>';
            }
        } catch(e) {
            $('rag-status').innerHTML = '<p class="text-muted">RAG сервис недоступен</p>';
        }
        setLoading(false);
    }

    window._ragQuery = async function() {
        var q = ($('rag-query-input') && $('rag-query-input').value) || '';
        if (!q) return;
        setLoading(true);
        $('rag-query-result').innerHTML = '<p class="text-muted">⏳ Ищу в базе знаний и генерирую ответ...</p>';
        try {
            var r = await api('/rag/query', {method:'POST',body:JSON.stringify({query:q,top_k:5})});
            var html = '';
            if (r.ok && r.data) {
                // Answer from LLM
                var answer = r.data.answer || 'Нет ответа';
                html += '<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:12px;">' +
                    '<div style="font-size:10px;color:var(--primary);margin-bottom:6px;">🤖 Ответ модели (' + (r.data.model||'RAG') + ')</div>' +
                    '<div style="font-size:13px;line-height:1.6;white-space:pre-wrap;">' + formatMessage(answer) + '</div>' +
                    '</div>';
                // Sources
                var sources = r.data.sources || [];
                if (sources.length > 0) {
                    html += '<div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">📚 Источники (' + sources.length + '):</div>';
                    sources.forEach(function(s, i) {
                        html += '<div style="font-size:11px;padding:4px 8px;margin:2px 0;background:var(--bg-input);border-radius:4px;">' +
                            (i+1) + '. <b>' + escHtml(s.title||s.source) + '</b> ' +
                            '<span style="color:var(--primary);">(' + (s.score||0).toFixed(2) + ')</span> ' +
                            '<span style="color:var(--text-muted);">— ' + escHtml(s.source) + '</span>' +
                            '</div>';
                    });
                }
            } else {
                html = '<div style="color:var(--danger);">Ошибка: ' + (r.data?.detail||r.status) + '</div>';
            }
            $('rag-query-result').innerHTML = html;
        } catch(e) {
            $('rag-query-result').innerHTML = '<div style="color:var(--danger);">Ошибка сети</div>';
        }
        setLoading(false);
    };

    window._chatRagSearch = async function() {
        var q = ($('chat-rag-input') && $('chat-rag-input').value) || '';
        if (!q) return;
        setLoading(true);
        try {
            var r = await api('/rag/query', {method:'POST',body:JSON.stringify({query:q,top_k:3})});
            if (r.ok && r.data) {
                var answer = r.data.answer || 'Не удалось получить ответ.';
                var sources = r.data.sources || [];
                var srcInfo = '';
                if (sources.length > 0) {
                    srcInfo = '\n\n📚 Источники: ' + sources.map(function(s) {
                        return s.title || s.source;
                    }).join('; ');
                }
                var ragModel = (r.data && r.data.model) ? r.data.model : 'RAG';
                addChatMessage('assistant', '🔍 RAG-ответ:\n\n' + answer + srcInfo, ragModel);
                var session = getCurrentSession();
                session.history.push({ role: 'assistant', content: '🔍 RAG-ответ:\n\n' + answer + srcInfo, model: ragModel });
                saveChatSessions();
                renderChatList();
            } else {
                addChatMessage('error', '❌ RAG: ' + (r.data?.detail || 'Ошибка'));
            }
            $('chat-rag-input').value = '';
            // Hide inline result div
            var resultDiv = $('chat-rag-result');
            if (resultDiv) resultDiv.style.display = 'none';
        } catch(e) {
            addChatMessage('error', '❌ RAG: ошибка сети');
        }
        setLoading(false);
    };

    window._wikiSearch = async function() {
        var q = ($('wiki-search-input') && $('wiki-search-input').value) || '';
        if (!q) return;
        setLoading(true);
        try {
            var r = await api('/rag/hybrid-query', {method:'POST',body:JSON.stringify({query:q,top_k:10})});
            if (r.ok && r.data && r.data.results) {
                var results = r.data.results;
                if (results.length === 0) {
                    $('wiki-search-result').innerHTML = '<p class="text-muted">Ничего не найдено по запросу «' + escHtml(q) + '»</p>';
                } else {
                    var html = '<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Найдено статей: <b>' + results.length + '</b></div>';
                    results.forEach(function(d, i) {
                        var idx = i;
                        html += '<div class="wiki-article-link" onclick="window._showWikiContent(\'' +
                            escHtml((d.text||'').replace(/'/g, "\\'")) + '\', \'' +
                            escHtml((d.title||d.source).replace(/'/g, "\\'")) + '\', \'' +
                            escHtml((d.source||'').replace(/'/g, "\\'")) + '\')" style="cursor:pointer;padding:6px 8px;margin:2px 0;border-radius:4px;font-size:12px;transition:background 0.15s;" onmouseover="this.style.background=\'var(--bg-card-hover)\'" onmouseout="this.style.background=\'transparent\'">' +
                            '<span style="color:var(--primary);font-weight:500;">' + (i+1) + '.</span> ' +
                            escHtml((d.title||d.source).substring(0,80)) +
                            ' <span style="color:var(--text-muted);font-size:10px;">(' + (d.score||0).toFixed(2) + ')</span>' +
                            '</div>';
                    });
                    $('wiki-search-result').innerHTML = html;
                }
            } else {
                $('wiki-search-result').innerHTML = '<p class="text-muted">Поиск недоступен</p>';
            }
        } catch(e) { $('wiki-search-result').innerHTML = '<p class="text-muted">Ошибка</p>'; }
        setLoading(false);
    };

    window._showWikiContent = async function(text, title, source) {
        var el = $('wiki-content');
        if (!el) return;
        el.innerHTML = '<p class="text-muted">⏳ Загрузка полного документа...</p>';
        try {
            var docRes = await api('/rag/doc?source=' + encodeURIComponent(source));
            if (docRes.ok && docRes.data && docRes.data.content) {
                var fullText = docRes.data.content;
                var mdHtml = renderMarkdown(fullText);
                el.innerHTML =
                    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
                    '<div style="font-weight:600;font-size:14px;color:var(--primary);">' + escHtml(docRes.data.title||title) + '</div>' +
                    '<button class="btn btn-sm btn-outline" onclick="window._closeWikiDoc()" style="font-size:10px;">✕ Закрыть</button>' +
                    '</div>' +
                    '<div style="font-size:10px;color:var(--text-muted);margin-bottom:8px;">📄 ' + escHtml(docRes.data.source||source) + ' | ' + (docRes.data.size||0) + ' симв.</div>' +
                    '<div class="wiki-doc-body">' + mdHtml + '</div>';
                renderMathInElement(el.querySelector('.wiki-doc-body'));
                el.scrollTop = 0;
            } else {
                el.innerHTML = '<p class="text-muted">Не удалось загрузить документ</p>';
            }
        } catch(e) {
            el.innerHTML = '<p class="text-muted">Ошибка загрузки</p>';
        }
    };

    window._closeWikiDoc = function() {
        var el = $('wiki-content');
        if (el) el.innerHTML = '<p class="text-muted">Нажмите на статью в результатах поиска, чтобы увидеть её содержание.</p>';
    };

    async function loadWikiPage() {
        setLoading(true);
        try {
            const s = await api('/rag/status');
            if (s.ok && s.data) {
                $('wiki-graph-status').innerHTML = '<div style="color:var(--success)">✓ Wiki-Graph доступен</div>' +
                    '<div style="font-size:11px;color:var(--text-muted);">Документов: ' + (s.data.documents||0) + ' | Движок: ' + (s.data.engine||'—') + '</div>';
            } else {
                $('wiki-graph-status').innerHTML = '<div class="text-muted">Wiki-Graph недоступен</div>';
            }
            $('wiki-pages').innerHTML = '<p class="text-muted">Wiki-Graph RAG — поиск по учебному пособию Aither (5 томов) и документации платформы.</p><p>Введите запрос в поле выше для гибридного поиска по всем разделам.</p>';
        } catch(e) {
            $('wiki-pages').innerHTML = '<p class="text-muted">Wiki-Graph временно недоступен</p>';
        }
        setLoading(false);
    }

    // ── Monitoring Page ──────────────────────────────────────────
    async function loadMonitoringPage() {
        setLoading(true);
        try {
            const s = await api('/monitoring/summary');
            if (s.ok && s.data) {
                $('mon-gateway').innerHTML = '<div>Gateway: ' + (s.data.gateway||'?') + '</div>\n                    <div>' + JSON.stringify(s.data.dependencies||{}) + '</div>';
            } else {
                $('mon-gateway').innerHTML = '<p class="text-muted">Недоступно (требуется роль operator/administrator)</p>';
            }
            const m = await api('/monitoring/models');
            if (m.ok && m.data) {
                const models = m.data.models || m.data || [];
                $('mon-models').innerHTML = Array.isArray(models) ? models.map(function(m) {
                    return '<div>' + escHtml(m.id||m) + ': ' + (m.status||'?') + '</div>';
                }).join('') || 'Нет данных' : JSON.stringify(models);
            } else {
                $('mon-models').innerHTML = '<p class="text-muted">Недоступно</p>';
            }
            $('mon-security').innerHTML = '<p class="text-muted">Журнал безопасности — ожидает реализации</p>';
            $('mon-billing').innerHTML = '<p class="text-muted">Статистика биллинга — ожидает реализации</p>';
        } catch(e) {
            $('mon-gateway').innerHTML = '<p class="text-muted">Ошибка загрузки</p>';
        }
        setLoading(false);
    };
})();