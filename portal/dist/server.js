"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fastify_1 = __importDefault(require("fastify"));
const cors_1 = __importDefault(require("@fastify/cors"));
const rate_limit_1 = __importDefault(require("@fastify/rate-limit"));
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
const pg_1 = require("pg");
const crypto_1 = require("crypto");
const ldap_1 = require("./ldap");
const policies_1 = require("./policies");
const PORT = 3000;
const JWT_SECRET = process.env.JWT_SECRET || (() => { throw new Error("JWT_SECRET env required"); })();
const CORE_API = process.env.CORE_API || "http://gateway:8080";
const IS_PRODUCTION = process.env.NODE_ENV === "production";
const PUBLIC_HOST = process.env.PUBLIC_HOST || "localhost";
const CORS_ORIGIN = process.env.CORS_ORIGIN || (IS_PRODUCTION ? `https://${PUBLIC_HOST}` : `http://${PUBLIC_HOST}`);
const pool = new pg_1.Pool({
    host: process.env.PG_HOST || "10.129.13.78",
    port: Number(process.env.PG_PORT) || 31113,
    user: process.env.PG_USER || "aither",
    password: process.env.PGPASSWORD || "",
    database: process.env.PG_DB || "aither",
});
function signToken(userId) {
    return jsonwebtoken_1.default.sign({ user_id: userId }, JWT_SECRET, { expiresIn: "24h" });
}
function verifyToken(tok) {
    try {
        return jsonwebtoken_1.default.verify(tok, JWT_SECRET);
    }
    catch {
        return null;
    }
}
function auth(req, reply) {
    const ah = req.headers.authorization || "";
    if (!ah.startsWith("Bearer ")) {
        reply.status(401).send({ error: "unauthorized" });
        return null;
    }
    const p = verifyToken(ah.slice(7));
    if (!p) {
        reply.status(401).send({ error: "invalid_token" });
        return null;
    }
    return p;
}
async function checkOrgOwner(orgId, userId) {
    const r = await pool.query("SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND role='owner'", [orgId, userId]);
    return r.rows.length > 0;
}
const STARTER_TOKENS = 100_000; // 100K токенов новому пользователю
const REFILL_TOKENS = 100_000; // авто-пополнение при обнулении
const REFILL_LIMIT = 10; // максимум авто-пополнений (защита от бесконечного цикла)
/** Создаёт личный org для нового пользователя и начисляет стартовые токены */
async function ensurePersonalOrg(userId) {
    const exist = await pool.query(`SELECT o.org_id FROM portal_organizations o
     JOIN portal_org_members m ON o.org_id=m.org_id
     WHERE m.user_id=$1 AND o.name='Личный'`, [userId]);
    if (exist.rows.length > 0)
        return exist.rows[0].org_id;
    const org = await pool.query("INSERT INTO portal_organizations (name) VALUES ('Личный') RETURNING org_id");
    const orgId = org.rows[0].org_id;
    await pool.query("INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1,$2,'owner')", [orgId, userId]);
    await pool.query(`INSERT INTO billing_accounts (org_id, reserved, total_tokens, meta)
     VALUES ($1,0,$2,'{}'::jsonb)
     ON CONFLICT (org_id) DO NOTHING`, [orgId, STARTER_TOKENS]);
    console.log(`[auto-balance] new user ${userId}: personal org ${orgId} + ${STARTER_TOKENS} tokens`);
    return orgId;
}
function hashPassword(password) {
    // scrypt: 64-bit salt + 64-byte hash, base64-encoded
    const salt = (0, crypto_1.randomBytes)(16).toString("hex");
    const hash = (0, crypto_1.scryptSync)(password, salt, 64).toString("hex");
    return `${salt}:${hash}`;
}
function verifyPassword(password, stored) {
    const [salt, hash] = stored.split(":");
    if (!salt || !hash)
        return false;
    const derived = (0, crypto_1.scryptSync)(password, salt, 64).toString("hex");
    return (0, crypto_1.timingSafeEqual)(Buffer.from(hash), Buffer.from(derived));
}
function safeError(e) {
    return IS_PRODUCTION ? "internal_error" : e.message || String(e);
}
/** Store OAuth state in cookie, return state value */
function setOAuthState(reply, prefix) {
    const state = (0, crypto_1.randomBytes)(16).toString("hex");
    reply.header("Set-Cookie", `oauth_state=${prefix}:${state}; Path=/; HttpOnly; SameSite=Lax; Max-Age=600` +
        (IS_PRODUCTION ? "; Secure" : ""));
    return state;
}
/** Validate OAuth state from cookie. Clears cookie. Returns true if valid. */
function validateOAuthState(req, reply, prefix) {
    const cookieState = (req.headers.cookie || "")
        .split(";").map((c) => c.trim())
        .find((c) => c.startsWith("oauth_state="))
        ?.split("=")[1];
    const queryState = req.query?.state || "";
    // Clear cookie
    reply.header("Set-Cookie", "oauth_state=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0" +
        (IS_PRODUCTION ? "; Secure" : ""));
    if (!cookieState || !queryState)
        return false;
    return cookieState === `${prefix}:${queryState}`;
}
async function main() {
    const app = (0, fastify_1.default)({ logger: false });
    await app.register(cors_1.default, { origin: CORS_ORIGIN, credentials: true });
    // Rate limiting: 100 req/min per IP
    await app.register(rate_limit_1.default, { max: 100, timeWindow: "1 minute" });
    // DDL
    await pool.query(`
    CREATE TABLE IF NOT EXISTS portal_users (
      user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      oauth_provider text NOT NULL DEFAULT 'github',
      oauth_id text NOT NULL,
      email text,
      password_hash text,
      display_name text,
      avatar_url text,
      created_at timestamptz NOT NULL DEFAULT now(),
      last_login_at timestamptz,
      UNIQUE(oauth_provider, oauth_id)
    );
    CREATE TABLE IF NOT EXISTS portal_organizations (
      org_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      name text NOT NULL,
      aither_org_id uuid,
      status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','deleted')),
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS portal_org_members (
      membership_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id uuid NOT NULL REFERENCES portal_organizations(org_id),
      user_id uuid NOT NULL REFERENCES portal_users(user_id),
      role text NOT NULL DEFAULT 'developer' CHECK (role IN ('owner','billing_admin','developer','viewer')),
      status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
      created_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(org_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS portal_api_keys (
      key_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id uuid REFERENCES portal_organizations(org_id),
      api_key text NOT NULL UNIQUE,
      api_key_prefix text NOT NULL,
      name text NOT NULL DEFAULT 'default',
      status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
      created_at timestamptz NOT NULL DEFAULT now(),
      expires_at timestamptz,
      last_used_at timestamptz
    );
    CREATE TABLE IF NOT EXISTS chats (
      chat_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid NOT NULL REFERENCES portal_users(user_id),
      title text NOT NULL DEFAULT 'Новый чат',
      model text NOT NULL DEFAULT 'qwen2.5-14b',
      share_token text UNIQUE,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS chat_messages (
      message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      chat_id uuid NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
      role text NOT NULL CHECK (role IN ('user','assistant','system')),
      content text NOT NULL DEFAULT '',
      tokens_used int NOT NULL DEFAULT 0,
      created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS payment_transactions (
      txn_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id uuid REFERENCES portal_organizations(org_id),
      user_id uuid REFERENCES portal_users(user_id),
      provider text NOT NULL DEFAULT 'yookassa',
      provider_payment_id text,
      amount_rub numeric(12,2) NOT NULL,
      tokens int NOT NULL DEFAULT 0,
      status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','succeeded','canceled')),
      meta jsonb DEFAULT '{}',
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS billing_accounts (
      org_id uuid PRIMARY KEY REFERENCES portal_organizations(org_id),
      reserved bigint NOT NULL DEFAULT 0,
      total_tokens bigint NOT NULL DEFAULT 0
    );
  `);
    await pool.query(policies_1.POLICIES_DDL);
    // ==================== AUTH ====================
    // GitHub OAuth
    const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || "";
    const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET || "";
    app.get("/auth/github", async (_req, reply) => {
        if (!GITHUB_CLIENT_ID)
            return reply.status(500).send({ error: "GitHub OAuth not configured" });
        const state = setOAuthState(reply, "github");
        const params = new URLSearchParams({
            client_id: GITHUB_CLIENT_ID,
            redirect_uri: process.env.GITHUB_REDIRECT_URI || `http://${process.env.PUBLIC_HOST || "localhost"}/auth/github/callback`,
            scope: "read:user user:email",
            state,
        });
        return reply.redirect(`https://github.com/login/oauth/authorize?${params}`);
    });
    app.get("/auth/github/callback", async (req, reply) => {
        if (!GITHUB_CLIENT_ID || !GITHUB_CLIENT_SECRET)
            return reply.status(500).send({ error: "GitHub OAuth not configured" });
        const { code, state } = req.query;
        if (!code)
            return reply.status(400).send({ error: "missing code" });
        if (!validateOAuthState(req, reply, "github"))
            return reply.status(403).send({ error: "invalid_state" });
        try {
            // Exchange code for access token
            const tokenRes = await fetch("https://github.com/login/oauth/access_token", {
                method: "POST",
                headers: { "Accept": "application/json", "Content-Type": "application/json" },
                body: JSON.stringify({
                    client_id: GITHUB_CLIENT_ID,
                    client_secret: GITHUB_CLIENT_SECRET,
                    code,
                    redirect_uri: process.env.GITHUB_REDIRECT_URI || `http://${process.env.PUBLIC_HOST || "localhost"}/auth/github/callback`,
                }),
            });
            const tokenData = await tokenRes.json();
            if (tokenData.error)
                return reply.status(403).send({ error: tokenData.error_description || tokenData.error });
            const accessToken = tokenData.access_token;
            // Get user info
            const [userRes, emailsRes] = await Promise.all([
                fetch("https://api.github.com/user", { headers: { Authorization: `Bearer ${accessToken}`, "User-Agent": "aither-portal" } }),
                fetch("https://api.github.com/user/emails", { headers: { Authorization: `Bearer ${accessToken}`, "User-Agent": "aither-portal" } }),
            ]);
            const ghUser = await userRes.json();
            const emails = await emailsRes.json();
            const primaryEmail = emails.find((e) => e.primary)?.email || emails[0]?.email || "";
            const oauthId = String(ghUser.id);
            const displayName = ghUser.name || ghUser.login;
            const avatarUrl = ghUser.avatar_url || "";
            // Upsert user
            let user = await pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["github", oauthId]);
            let userId;
            if (user.rows.length === 0) {
                const ins = await pool.query(`INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, avatar_url, last_login_at)
           VALUES ($1,$2,$3,$4,$5,now()) RETURNING user_id`, ["github", oauthId, primaryEmail, displayName, avatarUrl]);
                userId = ins.rows[0].user_id;
                await ensurePersonalOrg(userId);
            }
            else {
                userId = user.rows[0].user_id;
                await pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4", [primaryEmail, displayName, avatarUrl, userId]);
            }
            const tok = signToken(userId);
            const redirectHost = process.env.PUBLIC_HOST || "localhost";
            return reply.redirect(`http://${redirectHost}/?aither_token=${tok}&user_id=${userId}&name=${encodeURIComponent(displayName)}`);
        }
        catch (e) {
            return reply.status(502).send({ error: "GitHub OAuth error: " + safeError(e) });
        }
    });
    // Google OAuth
    const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || "";
    const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET || "";
    app.get("/auth/google", async (_req, reply) => {
        if (!GOOGLE_CLIENT_ID)
            return reply.status(500).send({ error: "Google OAuth not configured" });
        const state = setOAuthState(reply, "google");
        const redirectUri = process.env.GOOGLE_REDIRECT_URI || `http://${process.env.PUBLIC_HOST || "localhost"}/auth/google/callback`;
        const params = new URLSearchParams({
            client_id: GOOGLE_CLIENT_ID,
            redirect_uri: redirectUri,
            response_type: "code",
            scope: "openid profile email",
            state,
        });
        return reply.redirect(`https://accounts.google.com/o/oauth2/v2/auth?${params}`);
    });
    app.get("/auth/google/callback", async (req, reply) => {
        if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET)
            return reply.status(500).send({ error: "Google OAuth not configured" });
        const { code } = req.query;
        if (!code)
            return reply.status(400).send({ error: "missing code" });
        if (!validateOAuthState(req, reply, "google"))
            return reply.status(403).send({ error: "invalid_state" });
        try {
            const redirectUri = process.env.GOOGLE_REDIRECT_URI || `http://${process.env.PUBLIC_HOST || "localhost"}/auth/google/callback`;
            const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: new URLSearchParams({
                    client_id: GOOGLE_CLIENT_ID,
                    client_secret: GOOGLE_CLIENT_SECRET,
                    code,
                    redirect_uri: redirectUri,
                    grant_type: "authorization_code",
                }),
            });
            const tokenData = await tokenRes.json();
            if (tokenData.error)
                return reply.status(403).send({ error: tokenData.error_description || tokenData.error });
            // Get userinfo via OpenID Connect
            const userRes = await fetch("https://openidconnect.googleapis.com/v1/userinfo", {
                headers: { Authorization: `Bearer ${tokenData.access_token}` },
            });
            const gu = await userRes.json();
            const oauthId = gu.sub;
            const displayName = gu.name || gu.email?.split("@")[0] || "";
            const email = gu.email || "";
            const avatarUrl = gu.picture || "";
            let user = await pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["google", oauthId]);
            let userId;
            if (user.rows.length === 0) {
                const ins = await pool.query(`INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, avatar_url, last_login_at)
           VALUES ($1,$2,$3,$4,$5,now()) RETURNING user_id`, ["google", oauthId, email, displayName, avatarUrl]);
                userId = ins.rows[0].user_id;
                await ensurePersonalOrg(userId);
            }
            else {
                userId = user.rows[0].user_id;
                await pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4", [email, displayName, avatarUrl, userId]);
            }
            const tok = signToken(userId);
            const redirectHost = process.env.PUBLIC_HOST || "localhost";
            return reply.redirect(`http://${redirectHost}/?aither_token=${tok}&user_id=${userId}&name=${encodeURIComponent(displayName)}`);
        }
        catch (e) {
            return reply.status(502).send({ error: "Google OAuth error: " + safeError(e) });
        }
    });
    // Yandex OAuth
    const YANDEX_CLIENT_ID = process.env.YANDEX_CLIENT_ID || "";
    const YANDEX_CLIENT_SECRET = process.env.YANDEX_CLIENT_SECRET || "";
    app.get("/auth/yandex", async (_req, reply) => {
        if (!YANDEX_CLIENT_ID)
            return reply.status(500).send({ error: "Yandex OAuth not configured" });
        const state = setOAuthState(reply, "yandex");
        const params = new URLSearchParams({
            client_id: YANDEX_CLIENT_ID,
            redirect_uri: process.env.YANDEX_REDIRECT_URI || `http://${process.env.PUBLIC_HOST || "localhost"}/auth/yandex/callback`,
            response_type: "code",
            scope: "login:email login:info",
            state,
        });
        return reply.redirect(`https://oauth.yandex.ru/authorize?${params}`);
    });
    app.get("/auth/yandex/callback", async (req, reply) => {
        if (!YANDEX_CLIENT_ID || !YANDEX_CLIENT_SECRET)
            return reply.status(500).send({ error: "Yandex OAuth not configured" });
        const { code } = req.query;
        if (!code)
            return reply.status(400).send({ error: "missing code" });
        if (!validateOAuthState(req, reply, "yandex"))
            return reply.status(403).send({ error: "invalid_state" });
        try {
            const tokenRes = await fetch("https://oauth.yandex.ru/token", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: new URLSearchParams({
                    grant_type: "authorization_code",
                    code,
                    client_id: YANDEX_CLIENT_ID,
                    client_secret: YANDEX_CLIENT_SECRET,
                }),
            });
            const tokenData = await tokenRes.json();
            if (tokenData.error)
                return reply.status(403).send({ error: tokenData.error_description || tokenData.error });
            const userRes = await fetch("https://login.yandex.ru/info?format=json", {
                headers: { Authorization: `OAuth ${tokenData.access_token}` },
            });
            const yu = await userRes.json();
            const oauthId = yu.id;
            const displayName = yu.real_name || yu.login || yu.default_email?.split("@")[0] || "";
            const email = yu.default_email || "";
            const avatarUrl = yu.default_avatar_id
                ? `https://avatars.yandex.net/get-yapic/${yu.default_avatar_id}/islands-200`
                : "";
            let user = await pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["yandex", oauthId]);
            let userId;
            if (user.rows.length === 0) {
                const ins = await pool.query(`INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, avatar_url, last_login_at)
           VALUES ($1,$2,$3,$4,$5,now()) RETURNING user_id`, ["yandex", oauthId, email, displayName, avatarUrl]);
                userId = ins.rows[0].user_id;
                await ensurePersonalOrg(userId);
            }
            else {
                userId = user.rows[0].user_id;
                await pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4", [email, displayName, avatarUrl, userId]);
            }
            const tok = signToken(userId);
            const redirectHost = process.env.PUBLIC_HOST || "localhost";
            return reply.redirect(`http://${redirectHost}/?aither_token=${tok}&user_id=${userId}&name=${encodeURIComponent(displayName)}`);
        }
        catch (e) {
            return reply.status(502).send({ error: "Yandex OAuth error: " + safeError(e) });
        }
    });
    // === LDAP Authentication (FreeIPA / ALD Pro / OpenLDAP) ===
    app.post("/auth/ldap", async (req, reply) => {
        if (!(0, ldap_1.isLDAPEnabled)())
            return reply.status(501).send({ error: "LDAP not configured" });
        const { username, password } = req.body || {};
        if (!username || !password)
            return reply.status(400).send({ error: "username and password required" });
        try {
            const ldapUser = await (0, ldap_1.authenticateViaLDAP)(username, password);
            if (!ldapUser)
                return reply.status(401).send({ error: "invalid ldap credentials" });
            // Upsert portal user
            const oauthId = `ldap:${ldapUser.uid}`;
            const provider = "ldap";
            let user = await pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", [provider, oauthId]);
            let userId;
            if (user.rows.length === 0) {
                const ins = await pool.query(`INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, last_login_at)
           VALUES ($1,$2,$3,$4,now()) RETURNING user_id`, [provider, oauthId, ldapUser.email, ldapUser.displayName]);
                userId = ins.rows[0].user_id;
                await ensurePersonalOrg(userId);
            }
            else {
                userId = user.rows[0].user_id;
                await pool.query("UPDATE portal_users SET email=$1, display_name=$2, last_login_at=now() WHERE user_id=$3", [ldapUser.email, ldapUser.displayName, userId]);
            }
            const tok = signToken(userId);
            return {
                access_token: tok,
                user: { user_id: userId, login: ldapUser.uid, email: ldapUser.email },
                ldap_groups: ldapUser.groups,
                ldap_role: ldapUser.role,
            };
        }
        catch (e) {
            return reply.status(502).send({ error: "LDAP error: " + safeError(e) });
        }
    });
    app.post("/auth/dev/login", async (req, reply) => {
        // Dev-провайдер отключён в продакшене (404 — endpoint не существует)
        if (IS_PRODUCTION)
            return reply.status(404).send({ error: "not_found" });
        const { name } = req.body;
        if (!name)
            return { error: "name required" };
        const oid = name.toLowerCase().replace(/[^a-z0-9]/g, "-");
        const email = name.includes("@") ? name : name + "@dev.local";
        let user = await pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["dev", oid]);
        let userId;
        if (user.rows.length === 0) {
            const ins = await pool.query("INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, last_login_at) VALUES ($1,$2,$3,$4,now()) RETURNING user_id", ["dev", oid, email, name]);
            userId = ins.rows[0].user_id;
            await ensurePersonalOrg(userId);
        }
        else {
            userId = user.rows[0].user_id;
            await pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [userId]);
        }
        const tok = signToken(userId);
        return { access_token: tok, user: { user_id: userId, login: name, email } };
    });
    // === SaaS Signup ===
    app.post("/auth/signup", async (req, reply) => {
        const { email, password, org_name, invite_code } = req.body || {};
        if (!email || !password)
            return reply.status(400).send({ error: "email and password required" });
        if (password.length < 6)
            return reply.status(400).send({ error: "password must be at least 6 characters" });
        // Invitation-only: if INVITE_CODE set in env, must match
        const requiredCode = process.env.INVITE_CODE || "";
        if (requiredCode && invite_code !== requiredCode)
            return reply.status(403).send({ error: "registration requires valid invitation code" });
        const existing = await pool.query("SELECT user_id FROM portal_users WHERE email=$1 AND oauth_provider='email'", [email]);
        if (existing.rows.length > 0)
            return reply.status(409).send({ error: "email already registered" });
        const hash = hashPassword(password);
        const ins = await pool.query("INSERT INTO portal_users (oauth_provider, oauth_id, email, password_hash, display_name, last_login_at) VALUES ('email',$1,$2,$3,$4,now()) RETURNING user_id", [email, email, hash, email.split("@")[0]]);
        const userId = ins.rows[0].user_id;
        const orgId = await ensurePersonalOrg(userId);
        // Create named org
        const orgName = org_name || "Моя организация";
        const newOrg = await pool.query("INSERT INTO portal_organizations (name) VALUES ($1) RETURNING org_id", [orgName]);
        const newOrgId = newOrg.rows[0].org_id;
        await pool.query("INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1,$2,'owner')", [newOrgId, userId]);
        // Create billing account for the org
        try {
            await pool.query("INSERT INTO billing_accounts (org_id, reserved, total_tokens, meta) VALUES ($1,0,$2,'{}'::jsonb) ON CONFLICT (org_id) DO NOTHING", [newOrgId, STARTER_TOKENS]);
        }
        catch (e) { /* table may not exist yet */ }
        // Auto-create API key
        const key = "ak-" + (0, crypto_1.randomBytes)(24).toString("hex");
        await pool.query("INSERT INTO portal_api_keys (org_id, user_id, name, key_hash, api_key, api_key_prefix, status) VALUES ($1,$2,$3,$4,$5,$6,'active')", [newOrgId, userId, "default", key, key, "ak-"]);
        const tok = signToken(userId);
        return {
            access_token: tok,
            user: { user_id: userId, email, display_name: email.split("@")[0] },
            org: { org_id: newOrgId, name: orgName },
            api_key: key,
        };
    });
    // === SaaS Login ===
    app.post("/auth/login", async (req, reply) => {
        const { email, password } = req.body || {};
        if (!email || !password)
            return reply.status(400).send({ error: "email and password required" });
        const r = await pool.query("SELECT user_id, password_hash, display_name FROM portal_users WHERE email=$1 AND oauth_provider='email'", [email]);
        if (r.rows.length === 0)
            return reply.status(401).send({ error: "invalid credentials" });
        if (!verifyPassword(password, r.rows[0].password_hash))
            return reply.status(401).send({ error: "invalid credentials" });
        await pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [r.rows[0].user_id]);
        const tok = signToken(r.rows[0].user_id);
        return {
            access_token: tok,
            user: { user_id: r.rows[0].user_id, email, display_name: r.rows[0].display_name },
        };
    });
    app.get("/api/v1/me", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const r = await pool.query("SELECT user_id, display_name, email, avatar_url, oauth_provider, created_at FROM portal_users WHERE user_id=$1", [p.user_id]);
        if (r.rows.length === 0)
            return reply.status(404).send({ error: "user not found" });
        return { user: r.rows[0] };
    });
    app.get("/api/v1/status", async () => {
        const o = await pool.query("SELECT count(*) FROM portal_organizations");
        const u = await pool.query("SELECT count(*) FROM portal_users");
        const k = await pool.query("SELECT count(*) FROM portal_api_keys WHERE status='active'");
        return { version: "0.5.0", orgs: Number(o.rows[0].count), users: Number(u.rows[0].count), active_keys: Number(k.rows[0].count) };
    });
    // Model catalog — maps short names to vLLM paths
    const MODEL_MAP = {
        "qwen2.5-14b": {
            display_name: "Qwen 2.5 14B",
            vllm_path: "/models/Qwen2.5-14B-Instruct",
            description: "Быстрая универсальная модель",
        },
        "qwen2.5-32b": {
            display_name: "Qwen 2.5 32B",
            vllm_path: "/models/Qwen2.5-32B-Instruct-GPTQ",
            description: "Мощная модель для сложных задач",
        },
    };
    app.get("/api/v1/models", async (_r, reply) => {
        return reply.send({
            object: "list",
            data: Object.entries(MODEL_MAP).map(([id, m]) => ({
                id,
                object: "model",
                display_name: m.display_name,
                description: m.description,
                max_tokens: id.endsWith("32b") ? 8192 : 4096,
                tags: id.endsWith("32b") ? ["code", "analysis"] : ["chat", "code", "fast"],
            })),
        });
    });
    app.get("/api/v1/core/status", async (_r, reply) => {
        try {
            const r = await fetch(CORE_API + "/health");
            const text = await r.text();
            if (!text)
                return reply.send({ status: "ok", model: "vLLM", note: "health returned empty (vLLM direct)" });
            try {
                return reply.send(JSON.parse(text));
            }
            catch {
                return reply.send({ status: "ok", raw: text.slice(0, 200) });
            }
        }
        catch (e) {
            return reply.send({ status: "unreachable", error: safeError(e) });
        }
    });
    app.get("/api/v1/users", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        // Only show users who share an organization with the requester
        const r = await pool.query(`SELECT DISTINCT u.user_id, u.display_name, u.email, u.oauth_provider, u.created_at
       FROM portal_users u
       JOIN portal_org_members m ON u.user_id = m.user_id
       WHERE m.org_id IN (
         SELECT org_id FROM portal_org_members WHERE user_id = $1
       )
       ORDER BY u.created_at DESC`, [p.user_id]);
        return { users: r.rows };
    });
    // ==================== ORGS ====================
    app.get("/api/v1/orgs", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const r = await pool.query(`SELECT o.org_id, o.name, o.status, o.created_at, m.role
       FROM portal_organizations o
       JOIN portal_org_members m ON o.org_id = m.org_id
       WHERE m.user_id = $1 AND m.status = 'active'
       ORDER BY o.created_at DESC`, [p.user_id]);
        return { orgs: r.rows };
    });
    app.post("/api/v1/orgs", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { name } = req.body;
        if (!name || typeof name !== "string" || name.trim().length === 0)
            return reply.status(400).send({ error: "name is required" });
        const client = await pool.connect();
        try {
            await client.query("BEGIN");
            const org = await client.query("INSERT INTO portal_organizations (name) VALUES ($1) RETURNING org_id, name, status, created_at", [name.trim()]);
            const o = org.rows[0];
            await client.query("INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1, $2, 'owner')", [o.org_id, p.user_id]);
            await client.query("COMMIT");
            return { org: { ...o, role: "owner" } };
        }
        catch (e) {
            await client.query("ROLLBACK");
            return reply.status(500).send({ error: safeError(e) });
        }
        finally {
            client.release();
        }
    });
    app.get("/api/v1/orgs/:orgId", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { orgId } = req.params;
        const r = await pool.query(`SELECT o.org_id, o.name, o.status, o.created_at, m.role
       FROM portal_organizations o JOIN portal_org_members m ON o.org_id = m.org_id
       WHERE o.org_id = $1 AND m.user_id = $2`, [orgId, p.user_id]);
        if (r.rows.length === 0)
            return reply.status(404).send({ error: "org not found" });
        return { org: r.rows[0] };
    });
    // ==================== ORG SECURITY POLICIES ====================
    app.get("/api/v1/orgs/:orgId/policy", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { orgId } = req.params;
        const m = await pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id]);
        if (m.rows.length === 0)
            return reply.status(403).send({ error: "not a member" });
        try {
            const policy = await (0, policies_1.loadPolicy)(pool, orgId);
            return { org_id: orgId, policy };
        }
        catch (e) {
            return reply.status(500).send({ error: safeError(e) });
        }
    });
    app.put("/api/v1/orgs/:orgId/policy", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { orgId } = req.params;
        if (!await checkOrgOwner(orgId, p.user_id))
            return reply.status(403).send({ error: "owner only" });
        const body = req.body || {};
        const allowedKeys = [
            "dlp_enabled", "jailbreak_detection", "sensitive_data_patterns",
            "allowed_ip_cidrs", "mfa_required", "session_timeout_min",
            "api_key_max_age_days", "api_key_rotation_required",
            "custom_rpm", "custom_tpm", "max_concurrent_requests",
            "allowed_models", "max_tokens_per_request",
            "chat_retention_days", "audit_log_retention_days",
            "chat_enabled",
        ];
        const updates = {};
        for (const key of allowedKeys) {
            if (key in body)
                updates[key] = body[key];
        }
        if (Object.keys(updates).length === 0)
            return reply.status(400).send({ error: "no valid policy fields provided" });
        const err = (0, policies_1.validatePolicy)(updates);
        if (err)
            return reply.status(400).send({ error: err });
        try {
            const policy = await (0, policies_1.savePolicy)(pool, orgId, updates);
            return { org_id: orgId, policy };
        }
        catch (e) {
            return reply.status(500).send({ error: safeError(e) });
        }
    });
    // ==================== API KEYS ====================
    app.get("/api/v1/orgs/:orgId/api-keys", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { orgId } = req.params;
        const m = await pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id]);
        if (m.rows.length === 0)
            return reply.status(403).send({ error: "not a member" });
        const r = await pool.query(`SELECT key_id, api_key_prefix, name, status, created_at, expires_at, last_used_at
       FROM portal_api_keys WHERE org_id=$1 AND status!='revoked' ORDER BY created_at DESC`, [orgId]);
        return { keys: r.rows };
    });
    app.post("/api/v1/orgs/:orgId/api-keys", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { orgId } = req.params;
        if (!await checkOrgOwner(orgId, p.user_id))
            return reply.status(403).send({ error: "owner only" });
        const apiKey = "ak-" + (0, crypto_1.randomBytes)(24).toString("hex");
        const apiKeyPrefix = apiKey.slice(0, 11);
        const name = req.body?.name || "default";
        const r = await pool.query(`INSERT INTO portal_api_keys (org_id, api_key, api_key_prefix, name)
       VALUES ($1,$2,$3,$4) RETURNING key_id, api_key_prefix, name, status, created_at`, [orgId, apiKey, apiKeyPrefix, name]);
        return { key: { ...r.rows[0], api_key: apiKey } };
    });
    app.delete("/api/v1/orgs/:orgId/api-keys/:keyId", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { orgId, keyId } = req.params;
        if (!await checkOrgOwner(orgId, p.user_id))
            return reply.status(403).send({ error: "owner only" });
        const r = await pool.query("UPDATE portal_api_keys SET status='revoked' WHERE key_id=$1 AND org_id=$2 RETURNING key_id, status", [keyId, orgId]);
        if (r.rows.length === 0)
            return reply.status(404).send({ error: "key not found" });
        return { key: r.rows[0] };
    });
    // ==================== DELEGATION ====================
    const fs = require("fs");
    const DELEGATION_PRIVATE_KEY = (() => {
        try {
            return fs.readFileSync("/app/delegation/private.pem", "utf8");
        }
        catch { }
        try {
            return fs.readFileSync("./delegation/private.pem", "utf8");
        }
        catch { }
        return process.env.DELEGATION_PRIVATE_KEY || "";
    })();
    app.post("/api/v1/orgs/:orgId/delegate", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { orgId } = req.params;
        const { api_key } = req.body;
        if (!api_key)
            return reply.status(400).send({ error: "api_key required" });
        const k = await pool.query("SELECT key_id FROM portal_api_keys WHERE org_id=$1 AND api_key=$2 AND status='active'", [orgId, api_key]);
        if (k.rows.length === 0)
            return reply.status(403).send({ error: "invalid or revoked" });
        const m = await pool.query("SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id]);
        if (m.rows.length === 0)
            return reply.status(403).send({ error: "not a member" });
        await pool.query("UPDATE portal_api_keys SET last_used_at=now() WHERE key_id=$1", [k.rows[0].key_id]);
        const delegationToken = jsonwebtoken_1.default.sign({ org_id: orgId, key_id: k.rows[0].key_id, user_id: p.user_id }, DELEGATION_PRIVATE_KEY, { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" });
        return { delegation_token: delegationToken, expires_in: 300 };
    });
    // ==================== CHATS ====================
    /** Check if chat is enabled for any org the user belongs to. Returns true if enabled. */
    async function checkChatEnabled(userId, reply) {
        const orgs = await pool.query(`SELECT o.org_id FROM portal_organizations o
       JOIN portal_org_members m ON o.org_id = m.org_id
       WHERE m.user_id = $1 AND m.status = 'active'
       LIMIT 1`, [userId]);
        if (orgs.rows.length === 0) {
            reply.status(403).send({ error: "chat_disabled", detail: "no active organization" });
            return false;
        }
        const policy = await (0, policies_1.loadPolicy)(pool, orgs.rows[0].org_id);
        if (!policy.chat_enabled) {
            reply.status(403).send({ error: "chat_disabled", detail: "чат отключён в настройках безопасности организации" });
            return false;
        }
        return true;
    }
    // Get org's active API key (for delegation in chat)
    async function getOrgApiKey(orgId) {
        const r = await pool.query("SELECT api_key FROM portal_api_keys WHERE org_id=$1 AND status='active' ORDER BY created_at ASC LIMIT 1", [orgId]);
        return r.rows.length > 0 ? r.rows[0].api_key : null;
    }
    // Get delegation token for org (auto-creates API key if needed)
    async function getDelegationToken(orgId, userId) {
        let apiKey = await getOrgApiKey(orgId);
        if (!apiKey) {
            // Auto-create first API key for org
            apiKey = "ak-" + (0, crypto_1.randomBytes)(24).toString("hex");
            const apiKeyPrefix = apiKey.slice(0, 11);
            await pool.query("INSERT INTO portal_api_keys (org_id, api_key, api_key_prefix, name) VALUES ($1,$2,$3,'auto')", [orgId, apiKey, apiKeyPrefix]);
        }
        return jsonwebtoken_1.default.sign({ org_id: orgId, key_id: "chat", user_id: userId }, DELEGATION_PRIVATE_KEY, { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" });
    }
    // List chats
    app.get("/api/v1/chats", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        if (!await checkChatEnabled(p.user_id, reply))
            return;
        const r = await pool.query(`SELECT chat_id, title, model, share_token, created_at, updated_at
       FROM chats WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 50`, [p.user_id]);
        return { chats: r.rows };
    });
    // Create chat
    app.post("/api/v1/chats", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        if (!await checkChatEnabled(p.user_id, reply))
            return;
        const { title, model } = req.body || {};
        const r = await pool.query(`INSERT INTO chats (user_id, title, model) VALUES ($1,$2,$3)
       RETURNING chat_id, title, model, created_at`, [p.user_id, title || "Новый чат", model || "qwen2.5-14b"]);
        return { chat: r.rows[0] };
    });
    // Get chat with messages
    app.get("/api/v1/chats/:chatId", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        if (!await checkChatEnabled(p.user_id, reply))
            return;
        const { chatId } = req.params;
        const c = await pool.query("SELECT * FROM chats WHERE chat_id=$1 AND user_id=$2", [chatId, p.user_id]);
        if (c.rows.length === 0)
            return reply.status(404).send({ error: "chat not found" });
        const msgs = await pool.query("SELECT message_id, role, content, tokens_used, created_at FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC", [chatId]);
        return { chat: c.rows[0], messages: msgs.rows };
    });
    // Delete chat
    app.delete("/api/v1/chats/:chatId", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        if (!await checkChatEnabled(p.user_id, reply))
            return;
        const { chatId } = req.params;
        const r = await pool.query("DELETE FROM chats WHERE chat_id=$1 AND user_id=$2 RETURNING chat_id", [chatId, p.user_id]);
        if (r.rows.length === 0)
            return reply.status(404).send({ error: "chat not found" });
        return { deleted: true };
    });
    // Share chat (generate token)
    app.post("/api/v1/chats/:chatId/share", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        if (!await checkChatEnabled(p.user_id, reply))
            return;
        const { chatId } = req.params;
        const shareToken = (0, crypto_1.randomBytes)(16).toString("hex");
        const r = await pool.query("UPDATE chats SET share_token=$1 WHERE chat_id=$2 AND user_id=$3 RETURNING chat_id, share_token", [shareToken, chatId, p.user_id]);
        if (r.rows.length === 0)
            return reply.status(404).send({ error: "chat not found" });
        return { share_token: shareToken, url: `/shared/${shareToken}` };
    });
    // View shared chat (no auth)
    app.get("/api/v1/shared/:shareToken", async (req, reply) => {
        const { shareToken } = req.params;
        const c = await pool.query("SELECT chat_id, title, model, created_at FROM chats WHERE share_token=$1", [shareToken]);
        if (c.rows.length === 0)
            return reply.status(404).send({ error: "not found" });
        const msgs = await pool.query("SELECT role, content, created_at FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC", [c.rows[0].chat_id]);
        return { chat: c.rows[0], messages: msgs.rows };
    });
    // Send message + stream AI response
    app.post("/api/v1/chats/:chatId/messages", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        if (!await checkChatEnabled(p.user_id, reply))
            return;
        const { chatId } = req.params;
        const { content, org_id } = req.body || {};
        if (!content)
            return reply.status(400).send({ error: "content required" });
        // Get chat
        const c = await pool.query("SELECT * FROM chats WHERE chat_id=$1 AND user_id=$2", [chatId, p.user_id]);
        if (c.rows.length === 0)
            return reply.status(404).send({ error: "chat not found" });
        const chat = c.rows[0];
        // Save user message
        const userMsg = await pool.query("INSERT INTO chat_messages (chat_id, role, content) VALUES ($1,'user',$2) RETURNING message_id, created_at", [chatId, content]);
        // Skip delegation token — direct to vLLM
        // Build message history
        const history = await pool.query("SELECT role, content FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC", [chatId]);
        const messages = history.rows.map((m) => ({ role: m.role, content: m.content }));
        // Auto-title: use first 50 chars of first user message
        if (chat.title === "Новый чат" && history.rows.filter((m) => m.role === "user").length === 1) {
            const title = content.slice(0, 50).replace(/\n/g, " ");
            await pool.query("UPDATE chats SET title=$1 WHERE chat_id=$2", [title, chatId]);
        }
        try {
            // Translate model short name → vLLM path
            const modelInfo = MODEL_MAP[chat.model] || MODEL_MAP["qwen2.5-14b"];
            const vllmModel = modelInfo.vllm_path;
            const vllmEndpoint = CORE_API;
            // Call vLLM with streaming
            const vllmRes = await fetch(vllmEndpoint + "/v1/chat/completions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    model: vllmModel,
                    messages: [...messages, { role: "user", content }],
                    max_tokens: 2048,
                    temperature: 0.7,
                    stream: true,
                }),
            });
            if (!vllmRes.ok || !vllmRes.body) {
                // Delete user message on error
                await pool.query("DELETE FROM chat_messages WHERE message_id=$1", [userMsg.rows[0].message_id]);
                return reply.status(502).send({ error: "vLLM error: " + vllmRes.status });
            }
            // Stream SSE to client
            reply.raw.writeHead(200, {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            });
            let fullContent = "";
            const reader = vllmRes.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done)
                        break;
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split("\n");
                    buffer = lines.pop() || "";
                    for (const line of lines) {
                        if (line.startsWith("data: ")) {
                            const data = line.slice(6);
                            if (data === "[DONE]")
                                continue;
                            try {
                                const parsed = JSON.parse(data);
                                const delta = parsed.choices?.[0]?.delta?.content || "";
                                fullContent += delta;
                                // Forward to client
                                reply.raw.write(`data: ${JSON.stringify({ delta })}\n\n`);
                            }
                            catch { }
                        }
                    }
                }
            }
            finally {
                reader.releaseLock();
            }
            // Save assistant message
            const tokensUsed = Math.ceil(fullContent.length / 4); // rough estimate
            await pool.query("INSERT INTO chat_messages (chat_id, role, content, tokens_used) VALUES ($1,'assistant',$2,$3)", [chatId, fullContent, tokensUsed]);
            await pool.query("UPDATE chats SET updated_at=now() WHERE chat_id=$1", [chatId]);
            reply.raw.write(`data: ${JSON.stringify({ delta: "", done: true, tokens_used: tokensUsed })}\n\n`);
            reply.raw.end();
        }
        catch (e) {
            // Delete user message on error
            await pool.query("DELETE FROM chat_messages WHERE message_id=$1", [userMsg.rows[0].message_id]);
            if (!reply.raw.headersSent) {
                return reply.status(502).send({ error: "stream error: " + safeError(e) });
            }
            reply.raw.end();
        }
    });
    // ==================== BALANCE (local) ====================
    app.get("/api/v1/billing", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const orgId = req.query.org_id;
        if (!orgId)
            return reply.status(400).send({ error: "org_id required" });
        try {
            const r = await pool.query("SELECT total_tokens, reserved, meta FROM billing_accounts WHERE org_id=$1", [orgId]);
            if (r.rows.length === 0)
                return reply.send({ org_id: orgId, total_tokens: 0, reserved: 0 });
            let total = Number(r.rows[0].total_tokens);
            const meta = r.rows[0].meta || {};
            const refillCount = meta.refill_count || 0;
            // Auto-refill when balance hits 0 (until limit)
            if (total <= 0 && refillCount < REFILL_LIMIT) {
                await pool.query(`UPDATE billing_accounts SET total_tokens = total_tokens + $1,
           meta = jsonb_set(COALESCE(meta,'{}'::jsonb),'{refill_count}',$2::jsonb),
           updated_at = now() WHERE org_id=$3`, [REFILL_TOKENS, JSON.stringify(refillCount + 1), orgId]);
                total += REFILL_TOKENS;
                console.log(`[auto-refill] org ${orgId}: +${REFILL_TOKENS} tokens (refill #${refillCount + 1}/${REFILL_LIMIT})`);
            }
            return reply.send({ org_id: orgId, total_tokens: total, reserved: Number(r.rows[0].reserved) });
        }
        catch (e) {
            return reply.send({ org_id: orgId, total_tokens: 0, reserved: 0, note: "billing_accounts table missing" });
        }
    });
    app.get("/api/v1/usage", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const orgId = req.query.org_id;
        if (!orgId)
            return reply.status(400).send({ error: "org_id required" });
        try {
            const r = await pool.query("SELECT count(*), coalesce(sum(tokens),0) FROM payment_transactions WHERE org_id=$1 AND status='succeeded'", [orgId]);
            return reply.send({ org_id: orgId, payments: Number(r.rows[0].count), total_tokens: Number(r.rows[0].sum) });
        }
        catch (e) {
            return reply.send({ org_id: orgId, payments: 0, total_tokens: 0 });
        }
    });
    // === Dashboard: aggregated usage for charts ===
    app.get("/api/v1/billing/dashboard", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const orgId = req.query.org_id;
        if (!orgId)
            return reply.status(400).send({ error: "org_id required" });
        try {
            // Daily usage (last 30 days)
            const daily = await pool.query(`SELECT date(created_at) as day, coalesce(sum(tokens),0) as tokens, count(*) as requests
         FROM payment_transactions
         WHERE org_id=$1 AND status='succeeded' AND created_at > now() - interval '30 days'
         GROUP BY day ORDER BY day`, [orgId]);
            // Current month total
            const month = await pool.query(`SELECT coalesce(sum(tokens),0) as total, count(*) as count
         FROM payment_transactions
         WHERE org_id=$1 AND status='succeeded'
           AND date_trunc('month', created_at) = date_trunc('month', now())`, [orgId]);
            // Top models (from meta jsonb)
            const byModel = await pool.query(`SELECT COALESCE(meta->>'model','unknown') as model, coalesce(sum(tokens),0) as tokens, count(*) as requests
         FROM payment_transactions
         WHERE org_id=$1 AND status='succeeded' AND created_at > now() - interval '30 days'
         GROUP BY meta->>'model' ORDER BY tokens DESC LIMIT 10`, [orgId]);
            // Billing balance
            const bal = await pool.query("SELECT total_tokens, reserved FROM billing_accounts WHERE org_id=$1", [orgId]);
            const balance = bal.rows.length > 0 ? { total_tokens: Number(bal.rows[0].total_tokens), reserved: Number(bal.rows[0].reserved) } : { total_tokens: 0, reserved: 0 };
            return reply.send({
                org_id: orgId,
                balance,
                daily: daily.rows,
                month: month.rows[0] ? { total: Number(month.rows[0].total), count: Number(month.rows[0].count) } : { total: 0, count: 0 },
                by_model: byModel.rows,
            });
        }
        catch (e) {
            return reply.status(500).send({ error: safeError(e) });
        }
    });
    // ==================== PAYMENTS (YooKassa) ====================
    const YOOKASSA_SHOP_ID = process.env.YOOKASSA_SHOP_ID || "";
    const YOOKASSA_SECRET = process.env.YOOKASSA_SECRET || "";
    const TOKENS_PER_RUBLE = 1000; // 1 ₽ = 1000 токенов (для теста; в продакшене ~100)
    // Create payment → redirect to YooKassa
    app.post("/api/v1/billing/topup", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { org_id, amount_rub } = req.body;
        if (!org_id || !amount_rub || amount_rub < 1)
            return reply.status(400).send({ error: "org_id and amount_rub (>=1) required" });
        // Check org membership
        const m = await pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [org_id, p.user_id]);
        if (m.rows.length === 0)
            return reply.status(403).send({ error: "not a member" });
        const tokens = Math.floor(amount_rub * TOKENS_PER_RUBLE);
        // Create transaction record
        const txn = await pool.query(`INSERT INTO payment_transactions (org_id, user_id, provider, amount_rub, tokens, status, meta)
       VALUES ($1,$2,'yookassa',$3,$4,'pending','{}'::jsonb) RETURNING txn_id`, [org_id, p.user_id, amount_rub, tokens]);
        const txnId = txn.rows[0].txn_id;
        // If YooKassa is not configured, auto-succeed for dev mode
        if (!YOOKASSA_SHOP_ID || !YOOKASSA_SECRET) {
            await pool.query("UPDATE payment_transactions SET status='succeeded', updated_at=now(), meta=$1 WHERE txn_id=$2", [JSON.stringify({ dev_mode: true }), txnId]);
            // Credit tokens directly (simulate YooKassa callback)
            await pool.query(`INSERT INTO billing_accounts (org_id, reserved, total_tokens)
         VALUES ($1, 0, $2)
         ON CONFLICT (org_id) DO UPDATE SET total_tokens = billing_accounts.total_tokens + $2`, [org_id, tokens]);
            return reply.send({
                ok: true,
                txn_id: txnId,
                status: "succeeded",
                tokens: tokens,
                dev_mode: true,
            });
        }
        // Create YooKassa payment
        try {
            const idempotenceKey = txnId;
            const ykRes = await fetch("https://api.yookassa.ru/v3/payments", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Basic " + Buffer.from(YOOKASSA_SHOP_ID + ":" + YOOKASSA_SECRET).toString("base64"),
                    "Idempotence-Key": idempotenceKey,
                },
                body: JSON.stringify({
                    amount: { value: amount_rub.toFixed(2), currency: "RUB" },
                    confirmation: { type: "redirect", return_url: `http://${process.env.PUBLIC_HOST || "localhost"}/` },
                    description: `Пополнение Aither: ${tokens.toLocaleString()} токенов`,
                    metadata: { txn_id: txnId, org_id },
                }),
            });
            const ykData = await ykRes.json();
            if (ykRes.ok && ykData.confirmation?.confirmation_url) {
                await pool.query("UPDATE payment_transactions SET provider_payment_id=$1, meta=$2 WHERE txn_id=$3", [ykData.id, JSON.stringify(ykData), txnId]);
                return reply.send({
                    ok: true,
                    txn_id: txnId,
                    confirmation_url: ykData.confirmation.confirmation_url,
                    status: "pending",
                });
            }
            return reply.status(502).send({ error: "yookassa error", detail: ykData });
        }
        catch (e) {
            return reply.status(502).send({ error: "yookassa error: " + safeError(e) });
        }
    });
    // YooKassa webhook — called by YooKassa when payment status changes
    app.post("/api/v1/billing/webhook", async (req, reply) => {
        try {
            const body = req.body;
            const event = body?.event;
            const payment = body?.object;
            if (event === "payment.succeeded" && payment?.status === "succeeded") {
                const txnId = payment.metadata?.txn_id;
                if (!txnId)
                    return reply.send({ ok: false, error: "no txn_id in metadata" });
                const txn = await pool.query("SELECT txn_id, org_id, tokens, status FROM payment_transactions WHERE txn_id=$1", [txnId]);
                if (txn.rows.length === 0)
                    return reply.send({ ok: false, error: "txn not found" });
                if (txn.rows[0].status === "succeeded")
                    return reply.send({ ok: true, status: "already_processed" });
                // Mark succeeded + credit tokens
                await pool.query("BEGIN");
                await pool.query("UPDATE payment_transactions SET status='succeeded', updated_at=now(), meta=$1 WHERE txn_id=$2", [JSON.stringify(payment), txnId]);
                await pool.query(`INSERT INTO billing_accounts (org_id, reserved, total_tokens)
           VALUES ($1, 0, $2)
           ON CONFLICT (org_id) DO UPDATE SET total_tokens = billing_accounts.total_tokens + $2`, [txn.rows[0].org_id, txn.rows[0].tokens]);
                await pool.query("COMMIT");
                return reply.send({ ok: true, status: "credited" });
            }
            return reply.send({ ok: true, status: "ignored", event });
        }
        catch (e) {
            return reply.status(500).send({ ok: false, error: safeError(e) });
        }
    });
    // List payment transactions for org
    app.get("/api/v1/billing/payments", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const orgId = req.query.org_id;
        if (!orgId)
            return reply.status(400).send({ error: "org_id required" });
        const m = await pool.query("SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id]);
        if (m.rows.length === 0)
            return reply.status(403).send({ error: "not a member" });
        const r = await pool.query(`SELECT txn_id, provider, amount_rub, tokens, status, created_at
       FROM payment_transactions WHERE org_id=$1 ORDER BY created_at DESC LIMIT 50`, [orgId]);
        return reply.send({ payments: r.rows });
    });
    // === Tariff plans ===
    app.get("/api/v1/tiers", async (_req, reply) => {
        try {
            const r = await pool.query("SELECT tier_id, name, description, rpm_limit, tpm_limit, daily_request_limit, models, rag_enabled, priority, price_rub_month, features FROM subscription_tiers ORDER BY priority");
            return reply.send({ tiers: r.rows });
        }
        catch (e) {
            return reply.status(500).send({ error: safeError(e) });
        }
    });
    app.get("/api/v1/org/tier", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const orgId = req.query.org_id;
        if (!orgId)
            return reply.status(400).send({ error: "org_id required" });
        try {
            const r = await pool.query(`SELECT b.tier, t.name, t.rpm_limit, t.tpm_limit, t.daily_request_limit, t.models, t.rag_enabled, t.priority, t.price_rub_month, t.features
         FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier = t.tier_id WHERE b.org_id=$1`, [orgId]);
            if (r.rows.length === 0)
                return reply.send({ org_id: orgId, tier: "free", name: "Free" });
            return reply.send(r.rows[0]);
        }
        catch (e) {
            return reply.status(500).send({ error: safeError(e) });
        }
    });
    // === Tier upgrade ===
    app.post("/api/v1/orgs/:orgId/upgrade", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const { orgId } = req.params;
        const { tier } = req.body;
        if (!tier)
            return reply.status(400).send({ error: "tier required (free|standard|vip|enterprise)" });
        // Check org membership
        const m = await pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id]);
        if (m.rows.length === 0)
            return reply.status(403).send({ error: "not a member" });
        // Validate tier exists
        const t = await pool.query("SELECT tier_id FROM subscription_tiers WHERE tier_id=$1", [tier]);
        if (t.rows.length === 0)
            return reply.status(400).send({ error: "invalid tier" });
        await pool.query("UPDATE billing_accounts SET tier=$1, updated_at=now() WHERE org_id=$2", [tier, orgId]);
        // Return updated tier info
        const r = await pool.query(`SELECT b.tier, t.name, t.rpm_limit, t.tpm_limit, t.daily_request_limit, t.models, t.rag_enabled, t.priority
       FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier = t.tier_id WHERE b.org_id=$1`, [orgId]);
        return reply.send({ ok: true, tier: r.rows[0] });
    });
    // ==================== ADMIN PROXY ====================
    const ADMIN_KEY = process.env.ADMIN_KEY || "";
    // Proxy /api/v1/admin/* → Gateway /admin/*
    app.all("/api/v1/admin/*", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        // Check if user is org owner for any org (admin gate)
        const orgs = await pool.query("SELECT role FROM portal_org_members WHERE user_id=$1 AND role='owner' AND status='active' LIMIT 1", [p.user_id]);
        if (orgs.rows.length === 0 && ADMIN_KEY) {
            // If ADMIN_KEY is set and user provides it, allow global admin
            const adminHeader = req.headers["x-admin-key"] || "";
            if (adminHeader !== ADMIN_KEY)
                return reply.status(403).send({ error: "admin access required" });
        }
        const path = req.params["*"];
        const gwUrl = `${CORE_API}/admin/${path}`;
        try {
            const method = req.method;
            const headers = { "Content-Type": "application/json" };
            if (ADMIN_KEY)
                headers["Authorization"] = `Bearer ${ADMIN_KEY}`;
            let body;
            if (method === "POST" || method === "PUT") {
                body = JSON.stringify(req.body);
                headers["Content-Length"] = String(body.length);
            }
            const resp = await fetch(gwUrl, { method, headers, body });
            const data = await resp.json();
            return reply.status(resp.status).send(data);
        }
        catch (e) {
            return reply.status(502).send({ error: "gateway unreachable", detail: safeError(e) });
        }
    });
    // При production: слушаем только localhost (nginx проксирует)
    const listenHost = IS_PRODUCTION ? "127.0.0.1" : "0.0.0.0";
    await app.listen({ port: PORT, host: listenHost });
    console.log(`Portal BFF v0.6.0 (security-hardened) on ${listenHost}:${PORT}`);
}
main().catch((e) => { console.error(e); process.exit(1); });
