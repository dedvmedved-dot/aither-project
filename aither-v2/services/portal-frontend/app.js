/* Aither Portal — Stage 15 Application Logic */
(function () {
    'use strict';

    const API_URL = window._API_URL || '/api/v1';
    let authToken = localStorage.getItem('aither_token') || null;
    let currentUser = null;

    // DOM refs
    const $ = (id) => document.getElementById(id);
    const pages = ['login', 'dashboard', 'profile', 'status'];

    // ── Helpers ────────────────────────────────────────────────

    async function api(path, opts = {}) {
        const headers = { 'Content-Type': 'application/json', ...opts.headers };
        if (authToken) headers['Authorization'] = 'Bearer ' + authToken;
        const res = await fetch(API_URL + path, { ...opts, headers });
        let data;
        try { data = await res.json(); } catch { data = null; }
        return { status: res.status, ok: res.ok, data };
    }

    function showPage(id) {
        pages.forEach(p => {
            const el = $(`page-${p}`);
            if (el) el.classList.remove('active');
        });
        const target = $(`page-${id}`);
        if (target) target.classList.add('active');

        // Update nav
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.page === id);
        });
    }

    function showError(id, msg) {
        const el = $(id);
        if (!el) return;
        el.textContent = msg;
        el.style.display = 'block';
    }

    function hideError(id) {
        const el = $(id);
        if (el) el.style.display = 'none';
    }

    function setLoading(show) {
        const overlay = $('loading-overlay');
        if (overlay) overlay.style.display = show ? 'flex' : 'none';
    }

    function updateNav() {
        const nav = $('main-nav');
        const loginPage = $('page-login');
        if (authToken && currentUser) {
            nav.style.display = 'flex';
            loginPage.classList.remove('active');
            $('nav-username').textContent = currentUser.username;
            $('nav-role-badge').textContent = currentUser.role === 'administrator' ? 'Admin' : 'User';
        } else {
            nav.style.display = 'none';
        }
    }

    function updateDashboard() {
        if (!currentUser) return;
        $('dash-username').textContent = currentUser.username;
        $('dash-role').textContent = currentUser.role === 'administrator' ? 'Administrator' : 'User';
        $('dash-role').className = 'role-badge';
    }

    function updateProfile() {
        if (!currentUser) return;
        $('profile-id').textContent = currentUser.id;
        $('profile-username').textContent = currentUser.username;
        $('profile-role').textContent = currentUser.role === 'administrator' ? 'Administrator' : 'User';
    }

    // ── Login ─────────────────────────────────────────────────

    async function handleLogin(e) {
        e.preventDefault();
        hideError('login-error');

        const username = $('login-username').value.trim();
        const password = $('login-password').value;

        if (!username || !password) {
            showError('login-error', 'Please enter username and password');
            return;
        }

        setLoading(true);
        const btn = $('login-submit');
        btn.disabled = true;

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
                updateDashboard();
                $('login-username').value = '';
                $('login-password').value = '';
                await loadSystemInfo();
            } else {
                const msg = res.data?.detail || 'Login failed';
                showError('login-error', msg);
            }
        } catch (err) {
            showError('login-error', 'Network error — please try again');
        } finally {
            setLoading(false);
            btn.disabled = false;
        }
    }

    // ── Logout ────────────────────────────────────────────────

    async function handleLogout() {
        setLoading(true);
        try {
            await api('/auth/logout', { method: 'POST' });
        } catch { /* ignore */ }
        authToken = null;
        currentUser = null;
        localStorage.removeItem('aither_token');
        updateNav();
        showPage('login');
        setLoading(false);
    }

    // ── Profile ───────────────────────────────────────────────

    async function loadProfile() {
        if (!authToken || !currentUser) return;
        updateProfile();

        // Refresh from server
        const res = await api('/auth/me');
        if (res.ok && res.data) {
            currentUser = res.data;
            updateProfile();
            updateDashboard();
            updateNav();
        }
    }

    // ── System Info ────────────────────────────────────────────

    async function loadSystemInfo() {
        // Version
        try {
            const v = await fetch('/version').then(r => r.json());
            $('dash-version').textContent = v.version || v.service || '—';
        } catch { $('dash-version').textContent = 'unreachable'; }

        // Health
        try {
            const h = await fetch('/health').then(r => r.json());
            $('dash-status').textContent = h.status === 'ok' ? 'Healthy' : 'Degraded';
            $('dash-status').className = 'status-indicator ' + (h.status === 'ok' ? 'ok' : 'warning');
        } catch { $('dash-status').textContent = 'Unreachable'; }
    }

    async function loadStatusPage() {
        setLoading(true);
        try {
            // Services
            let html = '';
            try {
                const res = await api('/status');
                if (res.ok && res.data && res.data.services) {
                    for (const [name, status] of Object.entries(res.data.services)) {
                        const healthy = typeof status === 'object' || status === 'healthy';
                        html += `<div class="service-row">
                            <span class="service-name">${name}</span>
                            <span class="service-status ${healthy ? 'ok' : 'error'}">${healthy ? 'Healthy' : 'Unreachable'}</span>
                        </div>`;
                    }
                } else {
                    html = '<p class="text-muted">Status unavailable</p>';
                }
            } catch {
                html = '<p class="text-muted">Status service unreachable</p>';
            }
            $('status-content').innerHTML = html;

            // Version
            try {
                const v = await fetch('/version').then(r => r.json());
                $('version-content').innerHTML = `
                    <div class="info-row"><span class="info-label">Service</span><span class="info-value">${v.service || '—'}</span></div>
                    <div class="info-row"><span class="info-label">Version</span><span class="info-value">${v.version || '—'}</span></div>
                    <div class="info-row"><span class="info-label">Build</span><span class="info-value">${v.build || '—'}</span></div>
                `;
            } catch {
                $('version-content').innerHTML = '<p class="text-muted">Version info unavailable</p>';
            }
        } finally {
            setLoading(false);
        }
    }

    // ── Session Check ─────────────────────────────────────────

    async function checkSession() {
        if (!authToken) return false;
        const res = await api('/auth/me');
        if (res.ok && res.data) {
            currentUser = res.data;
            updateNav();
            updateDashboard();
            await loadSystemInfo();
            showPage('dashboard');
            return true;
        }
        // Token expired or invalid
        authToken = null;
        currentUser = null;
        localStorage.removeItem('aither_token');
        updateNav();
        showPage('login');
        return false;
    }

    // ── Init ──────────────────────────────────────────────────

    function init() {
        // Login form
        $('login-form').addEventListener('submit', handleLogin);

        // Logout button
        $('btn-logout').addEventListener('click', handleLogout);

        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                showPage(page);
                if (page === 'profile') loadProfile();
                if (page === 'status') loadStatusPage();
            });
        });

        // Auto-login check
        if (authToken) {
            checkSession();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
