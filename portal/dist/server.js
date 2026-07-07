"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fastify_1 = __importDefault(require("fastify"));
const cors_1 = __importDefault(require("@fastify/cors"));
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
const pg_1 = require("pg");
const crypto_1 = require("crypto");
const PORT = 3000;
const JWT_SECRET = process.env.JWT_SECRET || "dev-jwt-secret-change-me";
const CORE_API = process.env.CORE_API || "http://10.129.13.78:32293";
const pool = new pg_1.Pool({
    host: process.env.PG_HOST || "127.0.0.1",
    port: Number(process.env.PG_PORT) || 5432,
    user: process.env.PG_USER || "portal",
    database: process.env.PG_DB || "portal",
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
async function main() {
    const app = (0, fastify_1.default)({ logger: false });
    await app.register(cors_1.default, { origin: "*" });
    // DDL
    await pool.query(`
    CREATE TABLE IF NOT EXISTS portal_users (
      user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      oauth_provider text NOT NULL DEFAULT 'github',
      oauth_id text NOT NULL,
      email text,
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
  `);
    // ==================== AUTH ====================
    // GitHub OAuth
    const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || "";
    const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET || "";
    app.get("/auth/github", async (_req, reply) => {
        if (!GITHUB_CLIENT_ID)
            return reply.status(500).send({ error: "GitHub OAuth not configured" });
        const state = (0, crypto_1.randomBytes)(16).toString("hex");
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
            return reply.status(502).send({ error: "GitHub OAuth error: " + e.message });
        }
    });
    app.post("/auth/dev/login", async (req) => {
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
        }
        else {
            userId = user.rows[0].user_id;
            await pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [userId]);
        }
        const tok = signToken(userId);
        return { access_token: tok, user: { user_id: userId, login: name, email } };
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
    app.get("/api/v1/core/status", async (_r, reply) => {
        try {
            const r = await fetch(CORE_API + "/health");
            return reply.send(await r.json());
        }
        catch (e) {
            return reply.status(502).send({ error: "core_unreachable", detail: e.message });
        }
    });
    app.get("/api/v1/users", async () => {
        const r = await pool.query("SELECT user_id, display_name, email, oauth_provider, created_at FROM portal_users ORDER BY created_at DESC");
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
            return reply.status(500).send({ error: e.message });
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
        const r = await pool.query(`SELECT chat_id, title, model, share_token, created_at, updated_at
       FROM chats WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 50`, [p.user_id]);
        return { chats: r.rows };
    });
    // Create chat
    app.post("/api/v1/chats", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
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
            // Call Gateway with streaming
            const vllmRes = await fetch(CORE_API + "/v1/chat/completions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    model: chat.model,
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
                return reply.status(502).send({ error: "stream error: " + e.message });
            }
            reply.raw.end();
        }
    });
    // ==================== BALANCE proxy ====================
    app.get("/api/v1/billing", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const orgId = req.query.org_id;
        if (!orgId)
            return reply.status(400).send({ error: "org_id required" });
        const dToken = await getDelegationToken(orgId, p.user_id);
        if (!dToken)
            return reply.status(400).send({ error: "no active API key" });
        try {
            const r = await fetch(CORE_API + "/v1/billing/", { headers: { Authorization: "Bearer " + dToken } });
            return reply.send(await r.json());
        }
        catch (e) {
            return reply.status(502).send({ error: "gateway unreachable" });
        }
    });
    app.get("/api/v1/usage", async (req, reply) => {
        const p = auth(req, reply);
        if (!p)
            return;
        const orgId = req.query.org_id;
        if (!orgId)
            return reply.status(400).send({ error: "org_id required" });
        const dToken = await getDelegationToken(orgId, p.user_id);
        if (!dToken)
            return reply.status(400).send({ error: "no active API key" });
        try {
            const r = await fetch(CORE_API + "/v1/usage/", { headers: { Authorization: "Bearer " + dToken } });
            return reply.send(await r.json());
        }
        catch (e) {
            return reply.status(502).send({ error: "gateway unreachable" });
        }
    });
    await app.listen({ port: PORT, host: "0.0.0.0" });
    console.log("Portal BFF v0.5.0 (with chat) on :" + PORT);
}
main().catch((e) => { console.error(e); process.exit(1); });
