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
    const pages = ['login','dashboard','chat','api-keys','docs','feedback','status','profile','admin','tariffs','billing','usage','wiki','rag','monitoring'];

    // Token counter state
    let chatTokensUsed = 0;
    let chatRequestsMade = 0;

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
        escaped = escaped.replace(/(["][^"]*["]|['][^']*['])/g, '<span class="syn-string">$1</span>');
        escaped = escaped.replace(/\b(\d+\.?\d*)\b/g, '<span class="syn-number">$1</span>');
        return escaped;
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
                result += escHtml(parts[i] || '');
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
        authToken = null; currentUser = null; chatHistory = [];
        localStorage.removeItem('aither_token');
        localStorage.removeItem('aither_chat');
        localStorage.removeItem('aither_page');
        updateNav(); showPage('login');
        setLoading(false);
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
                    'qwen-14b': 'Чат-модель (14B) — оптимизирована для диалогов',
                    'qwen-32b-base': 'Базовая модель (32B) — продолжение текста',
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
        saveChatState();

        try {
            const res = await api('/chat', {
                method: 'POST',
                body: JSON.stringify({
                    model: model,
                    messages: chatHistory.slice(-20),
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

                chatHistory.push({ role: 'assistant', content: reply, model: model });
                addChatMessage('assistant', reply, model);
                if (res.data.usage) {
                    chatTokensUsed += (res.data.usage.total_tokens || 0);
                } else {
                    chatTokensUsed += Math.round(reply.length / 4);
                }
                chatRequestsMade++;
                updateTokenCounters();
                saveChatState();
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
        chatTokensUsed = 0;
        chatRequestsMade = 0;
        updateTokenCounters();
        var msgs = $('chat-messages');
        if (msgs) { msgs.innerHTML = ''; }
        saveChatState();
    }

    // ── Chat persistence ────────────────────────────────────────
    function saveChatState() {
        try {
            var state = {
                history: chatHistory.slice(-50),  // last 50 messages
                tokens: chatTokensUsed,
                requests: chatRequestsMade,
            };
            localStorage.setItem('aither_chat', JSON.stringify(state));
        } catch(e) {}
    }

    function loadChatState() {
        try {
            var raw = localStorage.getItem('aither_chat');
            if (!raw) return null;
            var state = JSON.parse(raw);
            if (state.history && Array.isArray(state.history)) {
                chatHistory = state.history;
                chatTokensUsed = state.tokens || 0;
                chatRequestsMade = state.requests || 0;
                updateTokenCounters();
                return chatHistory;
            }
        } catch(e) {}
        return null;
    }

    function restoreChatMessages() {
        var history = loadChatState();
        if (!history || history.length === 0) return;
        var msgs = $('chat-messages');
        if (!msgs) return;
        msgs.innerHTML = '';
        for (var i = 0; i < history.length; i++) {
            var msg = history[i];
            if (msg.role === 'user') {
                addChatMessage('user', msg.content);
            } else if (msg.role === 'assistant') {
                addChatMessage('assistant', msg.content, msg.model || '');
            } else if (msg.role === 'error') {
                addChatMessage('error', msg.content);
            }
        }
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
                let html = '<table class="data-table"><tr><th>Название</th><th>Префикс</th><th>Модели</th><th>Создан</th><th>Статус</th><th>Действия</th></tr>';
                for (const k of tokens) {
                    const revoked = k.revoked;
                    const prefix = (k.token_id || k.id || '—');
                    const scopes = (k.scopes || []).map(s => s.replace('model:', '').replace(':chat-adapter',':chat').replace(':chat','')).join(', ') || 'все';
                    html += '<tr>\n                        <td>' + escHtml(k.name || 'Без названия') + '</td>\n                        <td><code>' + escHtml(prefix) + '...</code></td>\n                        <td><span style="font-size:11px;">' + escHtml(scopes) + '</span></td>\n                        <td>' + ((k.created_at || '').substring(0, 16) || '—') + '</td>\n                        <td class="' + (revoked ? 'badge-revoked' : 'badge-enabled') + '">' + (revoked ? 'Отозван' : 'Активен') + '</td>\n                        <td>' + (revoked ? '' : '<button class="btn btn-sm btn-danger" onclick="window._revokeToken(\'' + (k.token_id || k.id) + '\')">Отозвать</button>\n                            <button class="btn btn-sm btn-outline" onclick="window._testToken(\'' + (k.token_id || k.id) + '\')" style="margin-left:4px;">Тест</button>') + '</td>\n                    </tr>';
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

    function showCreateTokenModal() {
        modal('\n            <h2>Создать API-ключ</h2>\n            <div class="form-group">\n                <label>Название ключа</label>\n                <input type="text" id="modal-token-name" class="form-input" placeholder="Например: Разработка">\n            </div>\n            <div class="form-group">\n                <label>Назначение</label>\n                <select id="modal-token-purpose" class="form-input">\n                    <option value="api">API / Web тестирование</option>\n                    <option value="agent">AI Agent</option>\n                    <option value="other">Другое</option>\n                </select>\n            </div>\n            <div class="form-group">\n                <label>Модели</label>\n                <select id="modal-token-models" class="form-input">\n                    <option value="both">Обе модели (14B + 32B)</option>\n                    <option value="qwen-14b">Только qwen-14b (Чат)</option>\n                    <option value="qwen-32b-base">Только qwen-32b-base (Базовая)</option>\n                </select>\n            </div>\n            <div id="modal-token-result" style="display:none;">\n                <div class="alert alert-info" style="margin-top:12px;">\n                    ⚠️ <strong>Сохраните ключ сейчас — он больше не будет показан!</strong>\n                </div>\n                <div class="copy-field">\n                    <input type="text" id="modal-token-full" readonly>\n                    <button class="btn btn-sm btn-primary" onclick="var i=document.getElementById(\'modal-token-full\');i.select();navigator.clipboard?.writeText(i.value);this.textContent=\'✓ Скопировано\';setTimeout(()=>this.textContent=\'Копировать\',2000);">Копировать</button>\n                </div>\n                <p class="text-muted" style="margin-top:4px;">Формат: athr_... (Bearer-токен для Authorization заголовка)</p>\n            </div>\n            <div style="display:flex;gap:8px;margin-top:16px;">\n                <button class="btn btn-primary" id="modal-token-create-btn" onclick="window._createToken()">Создать</button>\n                <button class="btn btn-outline" onclick="closeModal()">Закрыть</button>\n            </div>\n        ');
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
                // Restore saved page, default to dashboard
                var savedPage = 'dashboard';
                try { savedPage = localStorage.getItem('aither_page') || 'dashboard'; } catch(e) {}
                showPage(savedPage);
                if (savedPage === 'dashboard') loadDashboardInfo();
                if (savedPage === 'chat') { updateModelInfo(); restoreChatMessages(); }
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
        // Open doc in same window via fetch and modal
        setLoading(true);
        fetch(path)
            .then(function(r) {
                if (r.ok) return r.text();
                throw new Error('HTTP ' + r.status);
            })
            .then(function(text) {
                setLoading(false);
                modal('<div style="max-height:70vh;overflow-y:auto;font-size:13px;line-height:1.7;white-space:pre-wrap;font-family:inherit;">' +
                    escHtml(text).replace(/\n/g, '<br>') + '</div>' +
                    '<div style="margin-top:12px;display:flex;gap:8px;">' +
                    '<button class="btn btn-sm btn-outline" onclick="window.open(\'' + path + '\',\'_blank\')">Открыть в новом окне</button>' +
                    '<button class="btn btn-sm btn-outline" onclick="closeModal()">Закрыть</button></div>');
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
            // Highlight current tier
            document.querySelectorAll('.tier-card').forEach(function(card) {
                card.style.borderColor = 'var(--border)';
                card.style.boxShadow = '';
            });
            if (currentUser && currentUser.tier) {
                const currentCard = $('tier-' + currentUser.tier);
                if (currentCard) {
                    currentCard.style.borderColor = 'var(--primary)';
                    currentCard.style.boxShadow = '0 0 12px rgba(99,102,241,0.3)';
                }
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
                $('billing-stats').innerHTML = '<div>Запросов (сессия): <b>' + chatRequestsMade + '</b></div><div>Токенов (сессия): <b>' + chatTokensUsed + '</b></div>';
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
                $('usage-today').innerHTML = '<div>Запросов (сессия): <b>' + chatRequestsMade + '</b></div><p class="text-muted">Данные сервера недоступны</p>';
                $('usage-tokens').innerHTML = '<div>Токенов (сессия): <b>' + chatTokensUsed + '</b></div><p class="text-muted">Данные сервера недоступны</p>';
            }
            $('usage-models').innerHTML = '<div class="text-muted">📊 По моделям — статистика сессии:</div>\n                <div>qwen-14b: используется ' + (chatRequestsMade > 0 ? '✓' : '—') + '</div>\n                <div>qwen-32b-base: используется ' + (chatRequestsMade > 0 ? '✓' : '—') + '</div>';
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

    function updateTokenCounters() {
        if ($('chat-token-count')) $('chat-token-count').textContent = chatTokensUsed.toLocaleString();
        if ($('chat-request-count')) $('chat-request-count').textContent = chatRequestsMade;
    }

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
                addChatMessage('assistant', '🔍 RAG-ответ:\n\n' + answer + srcInfo, 'qwen-14b (RAG)');
                chatHistory.push({ role: 'assistant', content: '🔍 RAG-ответ:\n\n' + answer + srcInfo, model: 'qwen-14b (RAG)' });
                saveChatState();
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
                // Simple markdown to HTML conversion
                var html = fullText
                    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                    .replace(/^### (.+)$/gm, '<h4 style="margin:12px 0 4px;color:var(--text);">$1</h4>')
                    .replace(/^## (.+)$/gm, '<h3 style="margin:14px 0 6px;color:var(--primary);">$1</h3>')
                    .replace(/^# (.+)$/gm, '<h2 style="margin:16px 0 8px;color:var(--primary);font-size:16px;">$1</h2>')
                    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
                    .replace(/\*(.+?)\*/g, '<i>$1</i>')
                    .replace(/`(.+?)`/g, '<code>$1</code>')
                    .replace(/\n/g, '<br>');
                el.innerHTML =
                    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
                    '<div style="font-weight:600;font-size:14px;color:var(--primary);">' + escHtml(docRes.data.title||title) + '</div>' +
                    '<button class="btn btn-sm btn-outline" onclick="window._closeWikiDoc()" style="font-size:10px;">✕ Закрыть</button>' +
                    '</div>' +
                    '<div style="font-size:10px;color:var(--text-muted);margin-bottom:8px;">📄 ' + escHtml(docRes.data.source||source) + ' | ' + (docRes.data.size||0) + ' симв.</div>' +
                    '<div style="font-size:12px;line-height:1.7;max-height:55vh;overflow-y:auto;">' + html + '</div>';
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