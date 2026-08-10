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
            var s = { id: currentSessionId, title: 'Новый чат', timestamp: new Date().toISOString(), model: 'qwen2.5-32b-instruct', history: [], tokens: 0, requests: 0 };
            chatSessions.unshift(s);
            saveChatSessions();
            return s;
        }
        var found = null;
        for (var i = 0; i < chatSessions.length; i++) {
            if (chatSessions[i].id === currentSessionId) { found = chatSessions[i]; break; }
        }
        if (!found) {
            found = { id: currentSessionId, title: 'Новый чат', timestamp: new Date().toISOString(), model: 'qwen2.5-32b-instruct', history: [], tokens: 0, requests: 0 };
            chatSessions.unshift(found);
            saveChatSessions();
        }
        return found;
    }

    function getChatHistory() { return getCurrentSession().history; }
    function getChatTokens() { return getCurrentSession().tokens; }
    function getChatRequests() { return getCurrentSession().requests; }

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
                            timestamp: new Date().toISOString(), model: 'qwen2.5-32b-instruct',
                            history: old.history, tokens: old.tokens || 0, requests: old.requests || 0
                        }];
                        localStorage.removeItem('aither_chat');
                    }
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

        // Headers
        html = html.replace(/^#### (.+)$/gm, '<h5>$1</h5>');
        html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
        html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

        // Bold, italic
        html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<b><i>$1</i></b>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
        html = html.replace(/\*(.+?)\*/g, '<i>$1</i>');
        html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

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


    function formatMessage(text) {
        // Process ```code``` blocks with syntax highlighting + copy button
        var result = '';
        var parts = text.split(/(```(\w*)\n?([\s\S]*?)```)/g);
        var i = 0;
        var blockIdx = 0;
        while (i < parts.length) {
            if (parts[i] && parts[i].startsWith('```')) {
                var lang = (parts[i+1] || '').trim() || 'text';
                var rawCode = (parts[i+2] || '').replace(/\n$/, '');
                var highlighted = highlightCode(rawCode, lang);
                var blockId = 'cb' + (blockIdx++);
                // Encode code for safe data attribute
                var encodedCode = rawCode.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                result +=
                    '<div class="code-block">' +
                    '<div class="code-header">' +
                    '<span class="code-lang">' + escHtml(lang) + '</span>' +
                    '<button class="btn btn-sm btn-copy-code" onclick="var el=document.getElementById(\'' + blockId + '\');var txt=el.textContent;navigator.clipboard.writeText(txt).then(function(){var b=document.getElementById(\'' + blockId + '-btn\');b.textContent=\'✓ Скопировано\';setTimeout(function(){b.textContent=\'📋 Копировать\';},2000);});" id="' + blockId + '-btn">📋 Копировать</button>' +
                    '</div>' +
                    '<pre><code id="' + blockId + '">' + highlighted + '</code></pre>' +
                    '</div>';
                i += 3;
            } else {
                result += formatMarkdown(escHtml(parts[i] || ''));
                i++;
            }
        }
        if (!result) result = escHtml(text);
        return result;
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
                    'qwen2.5-32b-instruct': 'Qwen2.5-32B (32K)',
                    'qwen3-32b': 'Qwen3-32B (64K)',
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
        if (model === 'qwen2.5-32b-instruct') {
            info.innerHTML = '<b>Qwen2.5-32B-Instruct-AWQ</b> — 32 млрд параметров, AWQ 4-bit<br>📏 Контекст: <b>32K токенов</b> (родной)<br>🎯 Режимы: чат, инструкции, tool calling<br>🖥 Размещение: N7, 2×RTX 6000 (TP=2)';
            info.style.color = 'var(--text)';
        } else {
            info.innerHTML = '<b>Qwen3-32B-AWQ</b> — 32 млрд параметров, AWQ 4-bit<br>📏 Контекст: <b>32K родной + YaRN до 64K</b><br>⚠️ На 64K возможна деградация внимания<br>🎯 Режимы: чат, инструкции, tool calling<br>🖥 Размещение: N8, 2×RTX 6000 (TP=2)';
            info.style.color = 'var(--text)';
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

    async function sendChatMessage() {
        var input = $('chat-input');
        var model = $('chat-model-select')?.value || 'qwen2.5-32b-instruct';
        var content = input.value.trim();
        if (!content) return;

        if (authToken === null) {
            showChatError(401);
            return;
        }

        input.value = '';
        addChatMessage('user', content);
        addChatMessage('assistant', '⏳ Генерация ответа...', model);
        $('btn-send-message').disabled = true;

        var maxTokens = parseInt($('chat-max-tokens')?.value) || 512;
        var temperature = parseFloat($('chat-temperature')?.value) || 0.7;
        // Update session history
        var session = getCurrentSession();
        session.history.push({ role: 'user', content: content });
        session.model = model;
        // Auto-title from first user message
        if (session.title === 'Новый чат') {
            session.title = content.length > 50 ? content.substring(0, 47) + '...' : content;
        }
        saveChatSessions();
        renderChatList();

        try {
            const res = await api('/chat', {
                method: 'POST',
                body: JSON.stringify({
                    model: model,
                    messages: session.history.slice(-20),
                    max_tokens: maxTokens,
                    temperature: temperature,
                }),
            });

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
                    reply = res.data.choices?.[0]?.text || 'Пустой ответ от модели.';
                }

                session.history.push({ role: 'assistant', content: reply, model: model });
                addChatMessage('assistant', reply, model);
                if (res.data.usage) {
                    session.tokens += (res.data.usage.total_tokens || 0);
                } else {
                    session.tokens += Math.round(reply.length / 4);
                }
                session.requests++;
                updateTokenCounters();
                saveChatSessions();
                renderChatList();
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
        var s = getCurrentSession();
        s.history = [];
        s.tokens = 0;
        s.requests = 0;
        s.title = 'Новый чат';
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
        // Restore model
        if (s.model && $('chat-model-select')) {
            $('chat-model-select').value = s.model;
        }
        updateModelInfo();
        // Restore messages
        var msgs = $('chat-messages');
        if (!msgs) return;
        msgs.innerHTML = '';
        var h = s.history || [];
        for (var i = 0; i < h.length; i++) {
            var msg = h[i];
            if (msg.role === 'user') {
                addChatMessage('user', msg.content);
            } else if (msg.role === 'assistant') {
                addChatMessage('assistant', msg.content, msg.model || '');
            } else if (msg.role === 'error') {
                addChatMessage('error', msg.content);
            }
        }
        updateTokenCounters();
        renderChatList();
    };

    window._deleteChat = function(sessionId) {
        var filtered = [];
        for (var i = 0; i < chatSessions.length; i++) {
            if (chatSessions[i].id !== sessionId) filtered.push(chatSessions[i]);
        }
        chatSessions = filtered;
        saveChatSessions();
        if (sessionId === currentSessionId) {
            currentSessionId = chatSessions.length > 0 ? chatSessions[0].id : null;
            if (currentSessionId) {
                window._switchChat(currentSessionId);
            } else {
                // No sessions left, create new
                currentSessionId = uid();
                var ns = { id: currentSessionId, title: 'Новый чат', timestamp: new Date().toISOString(), model: 'qwen2.5-32b-instruct', history: [], tokens: 0, requests: 0 };
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
        var ns = { id: currentSessionId, title: 'Новый чат', timestamp: new Date().toISOString(), model: $('chat-model-select')?.value || 'qwen2.5-32b-instruct', history: [], tokens: 0, requests: 0 };
        chatSessions.unshift(ns);
        // Reset UI
        var msgs = $('chat-messages');
        if (msgs) msgs.innerHTML = '';
        // Reset model select to default if needed
        if ($('chat-model-select')) $('chat-model-select').value = 'qwen2.5-32b-instruct';
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
        var msgs = $('chat-messages');
        if (!msgs) return;
        msgs.innerHTML = '';
        var h = s.history || [];
        for (var i = 0; i < h.length; i++) {
            var msg = h[i];
            if (msg.role === 'user') {
                addChatMessage('user', msg.content);
            } else if (msg.role === 'assistant') {
                addChatMessage('assistant', msg.content, msg.model || '');
            } else if (msg.role === 'error') {
                addChatMessage('error', msg.content);
            }
        }
        updateTokenCounters();
        renderChatList();
    }

    // ── API Keys ───────────────────────────────────────────────
    async function loadApiKeys() {
        setLoading(true);
        try {
            const res = await api('/tokens');
            const tokens = res.data?.tokens || (Array.isArray(res.data) ? res.data : []);
            if (res.ok) {
                if (tokens.length === 0) {
                    $('apikeys-content').innerHTML = '<p class="text-muted">Нет созданных ключей. Нажмите «Создать новый ключ».</p>';
                    return;
                }
                let html = '<table class="data-table"><tr><th>Название</th><th>Префикс</th><th>Создан</th><th>Статус</th><th>Действия</th></tr>';
                for (const k of tokens) {
                    const revoked = k.revoked || k.revoked_at;
                    const prefix = (k.key_prefix || k.token_id || k.id || '—');
                    var scopesDisplay = (k.scopes || []).map(function(s) { return s === 'model:32b:chat' ? 'Qwen2.5' : s === 'model:qwen3:chat' ? 'Qwen3' : s; }).join(', ');
                    var statusClass = revoked ? 'badge-revoked' : (k.status === 'expired' ? 'badge-expired' : 'badge-enabled');
                    var statusText = revoked ? 'Отозван' : (k.status === 'expired' ? 'Истёк' : 'Активен');
                    html += '<tr>                        <td>' + escHtml(k.name || 'Без названия') + '</td>                        <td><code>' + escHtml(k.key_prefix || '—') + '</code></td>                        <td>' + escHtml(k.purpose || 'api') + '</td>                        <td>' + escHtml(scopesDisplay) + '</td>                        <td>' + ((k.created_at || '').substring(0, 10) || '—') + '</td>                        <td>' + ((k.expires_at || '').substring(0, 10) || '—') + '</td>                        <td>' + ((k.last_used_at || '').substring(0, 16) || '—') + '</td>                        <td class="' + statusClass + '">' + statusText + '</td>                        <td>' + (revoked ? '' : '<button class="btn btn-sm btn-danger" onclick="window._revokeToken(\'' + (k.id || k.key_prefix || k.token_id) + '\')">Отозвать</button>') + '</td>                    </tr>';
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
            const res = await api('/tokens');
            const tokens = res.data?.tokens || [];
            const token = tokens.find(t => (t.token_id || t.id) === id);
            if (!token || !token.token) {
                alert('Не удалось найти ключ для тестирования.');
                setLoading(false);
                return;
            }
            const testRes = await fetch('/api/v1/models', {
                headers: { 'Authorization': 'Bearer ' + token.token, 'Content-Type': 'application/json' }
            });
            let resultHtml = '';
            if (testRes.ok) {
                const data = await testRes.json();
                const models = data.data || [];
                resultHtml = '<div class="alert alert-success">✅ Ключ работает. Модели: ' + models.map(m => m.id).join(', ') + '</div>';
            } else {
                resultHtml = '<div class="alert alert-danger">❌ Ошибка HTTP ' + testRes.status + '</div>';
            }
            const c = $('apikeys-content');
            if (c) { c.insertAdjacentHTML('afterbegin', resultHtml); }
        } catch (e) {
            alert('Ошибка при тестировании ключа.');
        } finally { setLoading(false); }
    };
})();
