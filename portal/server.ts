import Fastify from "fastify";
import cors from "@fastify/cors";
import jwt from "jsonwebtoken";
import { Pool } from "pg";
import { randomBytes } from "crypto";
import { checkSecurity } from "./security";

const PORT = 3000;
const JWT_SECRET = process.env.JWT_SECRET || "dev-jwt-secret-change-me";
const CORE_API = process.env.CORE_API || "http://10.129.13.78:30900";
const CORE_API_32B = process.env.CORE_API_32B || "http://10.129.13.78:30900";  // Gateway handles model routing

const pool = new Pool({
  host: process.env.PG_HOST || "127.0.0.1",
  port: Number(process.env.PG_PORT) || 5432,
  user: process.env.PG_USER || "portal",
  database: process.env.PG_DB || "portal",
});

function signToken(userId: string): string {
  return jwt.sign({ user_id: userId }, JWT_SECRET, { expiresIn: "24h" });
}
function verifyToken(tok: string): { user_id: string } | null {
  try { return jwt.verify(tok, JWT_SECRET) as { user_id: string }; }
  catch { return null; }
}
function auth(req: any, reply: any): { user_id: string } | null {
  const ah = req.headers.authorization || "";
  if (!ah.startsWith("Bearer ")) { reply.status(401).send({ error: "unauthorized" }); return null; }
  const p = verifyToken(ah.slice(7));
  if (!p) { reply.status(401).send({ error: "invalid_token" }); return null; }
  return p;
}
async function checkOrgOwner(orgId: string, userId: string): Promise<boolean> {
  const r = await pool.query("SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND role='owner'", [orgId, userId]);
  return r.rows.length > 0;
}

const STARTER_TOKENS = 100_000;    // 100K токенов новому пользователю
const REFILL_TOKENS  = 100_000;    // авто-пополнение при обнулении
const REFILL_LIMIT   = 10;         // максимум авто-пополнений (защита от бесконечного цикла)

/** Создаёт личный org для нового пользователя и начисляет стартовые токены */
async function ensurePersonalOrg(userId: string): Promise<string> {
  const exist = await pool.query(
    `SELECT o.org_id FROM portal_organizations o
     JOIN portal_org_members m ON o.org_id=m.org_id
     WHERE m.user_id=$1 AND o.name='Личный'`, [userId]);
  if (exist.rows.length > 0) return exist.rows[0].org_id;

  const org = await pool.query(
    "INSERT INTO portal_organizations (name) VALUES ('Личный') RETURNING org_id");
  const orgId = org.rows[0].org_id;
  await pool.query(
    "INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1,$2,'owner')",
    [orgId, userId]);
  await pool.query(
    `INSERT INTO billing_accounts (org_id, reserved, total_tokens, meta)
     VALUES ($1,0,$2,'{}'::jsonb)
     ON CONFLICT (org_id) DO NOTHING`, [orgId, STARTER_TOKENS]);
  console.log(`[auto-balance] new user ${userId}: personal org ${orgId} + ${STARTER_TOKENS} tokens`);
  return orgId;
}

async function main() {
  const app = Fastify({ logger: false });
  await app.register(cors, { origin: "*" });

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
    CREATE TABLE IF NOT EXISTS security_audit (
      event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid,
      org_id uuid,
      chat_id uuid,
      category text NOT NULL,
      reason text NOT NULL,
      content_snippet text,
      model text,
      ip_address text,
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

  // ==================== AUTH ====================

  // GitHub OAuth
  const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || "";
  const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET || "";

  app.get("/auth/github", async (_req, reply) => {
    if (!GITHUB_CLIENT_ID) return reply.status(500).send({ error: "GitHub OAuth not configured" });
    const state = randomBytes(16).toString("hex");
    const params = new URLSearchParams({
      client_id: GITHUB_CLIENT_ID,
      redirect_uri: process.env.GITHUB_REDIRECT_URI || `http://${process.env.PUBLIC_HOST || "localhost"}/auth/github/callback`,
      scope: "read:user user:email",
      state,
    });
    return reply.redirect(`https://github.com/login/oauth/authorize?${params}`);
  });

  app.get("/auth/github/callback", async (req: any, reply) => {
    if (!GITHUB_CLIENT_ID || !GITHUB_CLIENT_SECRET)
      return reply.status(500).send({ error: "GitHub OAuth not configured" });

    const { code, state } = req.query;
    if (!code) return reply.status(400).send({ error: "missing code" });

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
      const tokenData: any = await tokenRes.json();
      if (tokenData.error) return reply.status(403).send({ error: tokenData.error_description || tokenData.error });

      const accessToken = tokenData.access_token;

      // Get user info
      const [userRes, emailsRes] = await Promise.all([
        fetch("https://api.github.com/user", { headers: { Authorization: `Bearer ${accessToken}`, "User-Agent": "aither-portal" } }),
        fetch("https://api.github.com/user/emails", { headers: { Authorization: `Bearer ${accessToken}`, "User-Agent": "aither-portal" } }),
      ]);
      const ghUser: any = await userRes.json();
      const emails: any = await emailsRes.json();
      const primaryEmail = emails.find((e: any) => e.primary)?.email || emails[0]?.email || "";

      const oauthId = String(ghUser.id);
      const displayName = ghUser.name || ghUser.login;
      const avatarUrl = ghUser.avatar_url || "";

      // Upsert user
      let user = await pool.query(
        "SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2",
        ["github", oauthId]
      );
      let userId: string;
      if (user.rows.length === 0) {
        const ins = await pool.query(
          `INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, avatar_url, last_login_at)
           VALUES ($1,$2,$3,$4,$5,now()) RETURNING user_id`,
          ["github", oauthId, primaryEmail, displayName, avatarUrl]
        );
        userId = ins.rows[0].user_id;
        await ensurePersonalOrg(userId);
      } else {
        userId = user.rows[0].user_id;
        await pool.query(
          "UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4",
          [primaryEmail, displayName, avatarUrl, userId]
        );
      }

      const tok = signToken(userId);
      const redirectHost = process.env.PUBLIC_HOST || "localhost";
      return reply.redirect(`http://${redirectHost}/?aither_token=${tok}&user_id=${userId}&name=${encodeURIComponent(displayName)}`);
    } catch (e: any) {
      return reply.status(502).send({ error: "GitHub OAuth error: " + e.message });
    }
  });

  // Google OAuth
  const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || "";
  const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET || "";

  app.get("/auth/google", async (_req, reply) => {
    if (!GOOGLE_CLIENT_ID) return reply.status(500).send({ error: "Google OAuth not configured" });
    const state = randomBytes(16).toString("hex");
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

  app.get("/auth/google/callback", async (req: any, reply) => {
    if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET)
      return reply.status(500).send({ error: "Google OAuth not configured" });

    const { code } = req.query;
    if (!code) return reply.status(400).send({ error: "missing code" });

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
      const tokenData: any = await tokenRes.json();
      if (tokenData.error) return reply.status(403).send({ error: tokenData.error_description || tokenData.error });

      // Get userinfo via OpenID Connect
      const userRes = await fetch("https://openidconnect.googleapis.com/v1/userinfo", {
        headers: { Authorization: `Bearer ${tokenData.access_token}` },
      });
      const gu: any = await userRes.json();

      const oauthId = gu.sub;
      const displayName = gu.name || gu.email?.split("@")[0] || "";
      const email = gu.email || "";
      const avatarUrl = gu.picture || "";

      let user = await pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["google", oauthId]);
      let userId: string;
      if (user.rows.length === 0) {
        const ins = await pool.query(
          `INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, avatar_url, last_login_at)
           VALUES ($1,$2,$3,$4,$5,now()) RETURNING user_id`,
          ["google", oauthId, email, displayName, avatarUrl]
        );
        userId = ins.rows[0].user_id;
        await ensurePersonalOrg(userId);
      } else {
        userId = user.rows[0].user_id;
        await pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4",
          [email, displayName, avatarUrl, userId]);
      }

      const tok = signToken(userId);
      const redirectHost = process.env.PUBLIC_HOST || "localhost";
      return reply.redirect(`http://${redirectHost}/?aither_token=${tok}&user_id=${userId}&name=${encodeURIComponent(displayName)}`);
    } catch (e: any) {
      return reply.status(502).send({ error: "Google OAuth error: " + e.message });
    }
  });

  // Yandex OAuth
  const YANDEX_CLIENT_ID = process.env.YANDEX_CLIENT_ID || "";
  const YANDEX_CLIENT_SECRET = process.env.YANDEX_CLIENT_SECRET || "";

  app.get("/auth/yandex", async (_req, reply) => {
    if (!YANDEX_CLIENT_ID) return reply.status(500).send({ error: "Yandex OAuth not configured" });
    const state = randomBytes(16).toString("hex");
    const params = new URLSearchParams({
      client_id: YANDEX_CLIENT_ID,
      redirect_uri: process.env.YANDEX_REDIRECT_URI || `http://${process.env.PUBLIC_HOST || "localhost"}/auth/yandex/callback`,
      response_type: "code",
      scope: "login:email login:info",
      state,
    });
    return reply.redirect(`https://oauth.yandex.ru/authorize?${params}`);
  });

  app.get("/auth/yandex/callback", async (req: any, reply) => {
    if (!YANDEX_CLIENT_ID || !YANDEX_CLIENT_SECRET)
      return reply.status(500).send({ error: "Yandex OAuth not configured" });

    const { code } = req.query;
    if (!code) return reply.status(400).send({ error: "missing code" });

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
      const tokenData: any = await tokenRes.json();
      if (tokenData.error) return reply.status(403).send({ error: tokenData.error_description || tokenData.error });

      const userRes = await fetch("https://login.yandex.ru/info?format=json", {
        headers: { Authorization: `OAuth ${tokenData.access_token}` },
      });
      const yu: any = await userRes.json();

      const oauthId = yu.id;
      const displayName = yu.real_name || yu.login || yu.default_email?.split("@")[0] || "";
      const email = yu.default_email || "";
      const avatarUrl = yu.default_avatar_id
        ? `https://avatars.yandex.net/get-yapic/${yu.default_avatar_id}/islands-200`
        : "";

      let user = await pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["yandex", oauthId]);
      let userId: string;
      if (user.rows.length === 0) {
        const ins = await pool.query(
          `INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, avatar_url, last_login_at)
           VALUES ($1,$2,$3,$4,$5,now()) RETURNING user_id`,
          ["yandex", oauthId, email, displayName, avatarUrl]
        );
        userId = ins.rows[0].user_id;
        await ensurePersonalOrg(userId);
      } else {
        userId = user.rows[0].user_id;
        await pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4",
          [email, displayName, avatarUrl, userId]);
      }

      const tok = signToken(userId);
      const redirectHost = process.env.PUBLIC_HOST || "localhost";
      return reply.redirect(`http://${redirectHost}/?aither_token=${tok}&user_id=${userId}&name=${encodeURIComponent(displayName)}`);
    } catch (e: any) {
      return reply.status(502).send({ error: "Yandex OAuth error: " + e.message });
    }
  });

  app.post("/auth/dev/login", async (req) => {
    const { name }: any = req.body;
    if (!name) return { error: "name required" };
    const oid = name.toLowerCase().replace(/[^a-z0-9]/g, "-");
    const email = name.includes("@") ? name : name + "@dev.local";
    let user = await pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["dev", oid]);
    let userId: string;
    if (user.rows.length === 0) {
      const ins = await pool.query(
        "INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, last_login_at) VALUES ($1,$2,$3,$4,now()) RETURNING user_id",
        ["dev", oid, email, name]
      );
      userId = ins.rows[0].user_id;
      await ensurePersonalOrg(userId);
    } else {
      userId = user.rows[0].user_id;
      await pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [userId]);
    }
    const tok = signToken(userId);
    return { access_token: tok, user: { user_id: userId, login: name, email } };
  });

  app.get("/api/v1/me", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const r = await pool.query("SELECT user_id, display_name, email, avatar_url, oauth_provider, created_at FROM portal_users WHERE user_id=$1", [p.user_id]);
    if (r.rows.length === 0) return reply.status(404).send({ error: "user not found" });
    return { user: r.rows[0] };
  });

  app.get("/api/v1/status", async () => {
    const o = await pool.query("SELECT count(*) FROM portal_organizations");
    const u = await pool.query("SELECT count(*) FROM portal_users");
    const k = await pool.query("SELECT count(*) FROM portal_api_keys WHERE status='active'");
    return { version: "0.5.0", orgs: Number(o.rows[0].count), users: Number(u.rows[0].count), active_keys: Number(k.rows[0].count) };
  });

  // Model catalog — maps short names to vLLM paths
  const MODEL_MAP: Record<string, { display_name: string; vllm_path: string; description: string }> = {
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
      if (!text) return reply.send({ status: "ok", model: "vLLM", note: "health returned empty (vLLM direct)" });
      try { return reply.send(JSON.parse(text)); }
      catch { return reply.send({ status: "ok", raw: text.slice(0, 200) }); }
    } catch (e: any) {
      return reply.send({ status: "unreachable", error: e.message });
    }
  });

  app.get("/api/v1/users", async () => {
    const r = await pool.query("SELECT user_id, display_name, email, oauth_provider, created_at FROM portal_users ORDER BY created_at DESC");
    return { users: r.rows };
  });

  // ==================== ORGS ====================

  app.get("/api/v1/orgs", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const r = await pool.query(
      `SELECT o.org_id, o.name, o.status, o.created_at, m.role
       FROM portal_organizations o
       JOIN portal_org_members m ON o.org_id = m.org_id
       WHERE m.user_id = $1 AND m.status = 'active'
       ORDER BY o.created_at DESC`, [p.user_id]);
    return { orgs: r.rows };
  });

  app.post("/api/v1/orgs", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { name }: any = req.body;
    if (!name || typeof name !== "string" || name.trim().length === 0)
      return reply.status(400).send({ error: "name is required" });
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const org = await client.query(
        "INSERT INTO portal_organizations (name) VALUES ($1) RETURNING org_id, name, status, created_at",
        [name.trim()]);
      const o = org.rows[0];
      await client.query(
        "INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1, $2, 'owner')",
        [o.org_id, p.user_id]);
      await client.query("COMMIT");
      return { org: { ...o, role: "owner" } };
    } catch (e: any) { await client.query("ROLLBACK"); return reply.status(500).send({ error: e.message }); }
    finally { client.release(); }
  });

  app.get("/api/v1/orgs/:orgId", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { orgId } = req.params;
    const r = await pool.query(
      `SELECT o.org_id, o.name, o.status, o.created_at, m.role
       FROM portal_organizations o JOIN portal_org_members m ON o.org_id = m.org_id
       WHERE o.org_id = $1 AND m.user_id = $2`, [orgId, p.user_id]);
    if (r.rows.length === 0) return reply.status(404).send({ error: "org not found" });
    return { org: r.rows[0] };
  });

  // ==================== API KEYS ====================

  app.get("/api/v1/orgs/:orgId/api-keys", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { orgId } = req.params;
    const m = await pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id]);
    if (m.rows.length === 0) return reply.status(403).send({ error: "not a member" });
    const r = await pool.query(
      `SELECT key_id, api_key_prefix, name, status, created_at, expires_at, last_used_at
       FROM portal_api_keys WHERE org_id=$1 AND status!='revoked' ORDER BY created_at DESC`, [orgId]);
    return { keys: r.rows };
  });

  app.post("/api/v1/orgs/:orgId/api-keys", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { orgId } = req.params;
    if (!await checkOrgOwner(orgId, p.user_id)) return reply.status(403).send({ error: "owner only" });
    const apiKey = "ak-" + randomBytes(24).toString("hex");
    const apiKeyPrefix = apiKey.slice(0, 11);
    const name: string = (req.body as any)?.name || "default";
    const r = await pool.query(
      `INSERT INTO portal_api_keys (org_id, api_key, api_key_prefix, name)
       VALUES ($1,$2,$3,$4) RETURNING key_id, api_key_prefix, name, status, created_at`,
      [orgId, apiKey, apiKeyPrefix, name]);
    return { key: { ...r.rows[0], api_key: apiKey } };
  });

  app.delete("/api/v1/orgs/:orgId/api-keys/:keyId", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { orgId, keyId } = req.params;
    if (!await checkOrgOwner(orgId, p.user_id)) return reply.status(403).send({ error: "owner only" });
    const r = await pool.query(
      "UPDATE portal_api_keys SET status='revoked' WHERE key_id=$1 AND org_id=$2 RETURNING key_id, status",
      [keyId, orgId]);
    if (r.rows.length === 0) return reply.status(404).send({ error: "key not found" });
    return { key: r.rows[0] };
  });

  // ==================== DELEGATION ====================

  const fs = require("fs");
  const DELEGATION_PRIVATE_KEY = (() => {
    try { return fs.readFileSync("/app/delegation/private.pem", "utf8"); } catch {}
    try { return fs.readFileSync("./delegation/private.pem", "utf8"); } catch {}
    return process.env.DELEGATION_PRIVATE_KEY || "";
  })();

  app.post("/api/v1/orgs/:orgId/delegate", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { orgId } = req.params;
    const { api_key }: any = req.body;
    if (!api_key) return reply.status(400).send({ error: "api_key required" });
    const k = await pool.query(
      "SELECT key_id FROM portal_api_keys WHERE org_id=$1 AND api_key=$2 AND status='active'", [orgId, api_key]);
    if (k.rows.length === 0) return reply.status(403).send({ error: "invalid or revoked" });
    const m = await pool.query(
      "SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id]);
    if (m.rows.length === 0) return reply.status(403).send({ error: "not a member" });
    await pool.query("UPDATE portal_api_keys SET last_used_at=now() WHERE key_id=$1", [k.rows[0].key_id]);
    const delegationToken = jwt.sign(
      { org_id: orgId, key_id: k.rows[0].key_id, user_id: p.user_id },
      DELEGATION_PRIVATE_KEY, { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" });
    return { delegation_token: delegationToken, expires_in: 300 };
  });

  // ==================== CHATS ====================

  // Get org's active API key (for delegation in chat)
  async function getOrgApiKey(orgId: string): Promise<string | null> {
    const r = await pool.query(
      "SELECT api_key FROM portal_api_keys WHERE org_id=$1 AND status='active' ORDER BY created_at ASC LIMIT 1",
      [orgId]);
    return r.rows.length > 0 ? r.rows[0].api_key : null;
  }

  // Get delegation token for org (auto-creates API key if needed)
  async function getDelegationToken(orgId: string, userId: string): Promise<string | null> {
    let apiKey = await getOrgApiKey(orgId);
    if (!apiKey) {
      // Auto-create first API key for org
      apiKey = "ak-" + randomBytes(24).toString("hex");
      const apiKeyPrefix = apiKey.slice(0, 11);
      await pool.query(
        "INSERT INTO portal_api_keys (org_id, api_key, api_key_prefix, name) VALUES ($1,$2,$3,'auto')",
        [orgId, apiKey, apiKeyPrefix]);
    }
    return jwt.sign(
      { org_id: orgId, key_id: "chat", user_id: userId },
      DELEGATION_PRIVATE_KEY, { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" });
  }

  // List chats
  app.get("/api/v1/chats", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const r = await pool.query(
      `SELECT chat_id, title, model, share_token, created_at, updated_at
       FROM chats WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 50`,
      [p.user_id]);
    return { chats: r.rows };
  });

  // Create chat
  app.post("/api/v1/chats", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { title, model }: any = req.body || {};
    const r = await pool.query(
      `INSERT INTO chats (user_id, title, model) VALUES ($1,$2,$3)
       RETURNING chat_id, title, model, created_at`,
      [p.user_id, title || "Новый чат", model || "qwen2.5-14b"]);
    return { chat: r.rows[0] };
  });

  // Get chat with messages
  app.get("/api/v1/chats/:chatId", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { chatId } = req.params;
    const c = await pool.query("SELECT * FROM chats WHERE chat_id=$1 AND user_id=$2", [chatId, p.user_id]);
    if (c.rows.length === 0) return reply.status(404).send({ error: "chat not found" });
    const msgs = await pool.query(
      "SELECT message_id, role, content, tokens_used, created_at FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC",
      [chatId]);
    return { chat: c.rows[0], messages: msgs.rows };
  });

  // Delete chat
  app.delete("/api/v1/chats/:chatId", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { chatId } = req.params;
    const r = await pool.query("DELETE FROM chats WHERE chat_id=$1 AND user_id=$2 RETURNING chat_id", [chatId, p.user_id]);
    if (r.rows.length === 0) return reply.status(404).send({ error: "chat not found" });
    return { deleted: true };
  });

  // Share chat (generate token)
  app.post("/api/v1/chats/:chatId/share", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { chatId } = req.params;
    const shareToken = randomBytes(16).toString("hex");
    const r = await pool.query(
      "UPDATE chats SET share_token=$1 WHERE chat_id=$2 AND user_id=$3 RETURNING chat_id, share_token",
      [shareToken, chatId, p.user_id]);
    if (r.rows.length === 0) return reply.status(404).send({ error: "chat not found" });
    return { share_token: shareToken, url: `/shared/${shareToken}` };
  });

  // View shared chat (no auth)
  app.get("/api/v1/shared/:shareToken", async (req: any, reply) => {
    const { shareToken } = req.params;
    const c = await pool.query("SELECT chat_id, title, model, created_at FROM chats WHERE share_token=$1", [shareToken]);
    if (c.rows.length === 0) return reply.status(404).send({ error: "not found" });
    const msgs = await pool.query(
      "SELECT role, content, created_at FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC",
      [c.rows[0].chat_id]);
    return { chat: c.rows[0], messages: msgs.rows };
  });

  // Send message + stream AI response
  app.post("/api/v1/chats/:chatId/messages", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { chatId } = req.params;
    const { content, org_id }: any = req.body || {};
    if (!content) return reply.status(400).send({ error: "content required" });

    // ── Security check: prompt injection + DLP ──
    const secResult = checkSecurity([{ role: "user", content }]);
    if (!secResult.ok) {
      const ip = (req.headers["x-forwarded-for"] || req.headers["x-real-ip"] || req.ip || "").toString();
      await pool.query(
        `INSERT INTO security_audit (user_id, org_id, chat_id, category, reason, content_snippet, model, ip_address)
         VALUES ($1,$2,$3,$4,$5,$6,NULL,$7)`,
        [p.user_id, org_id || null, chatId, secResult.category, secResult.reason,
         content.slice(0, 200), ip]
      );
      console.log(`[security] BLOCKED ${secResult.category}: ${secResult.reason} (user=${p.user_id}, ip=${ip})`);
      return reply.status(403).send({ error: "security_violation", reason: secResult.reason });
    }

    // Get chat
    const c = await pool.query("SELECT * FROM chats WHERE chat_id=$1 AND user_id=$2", [chatId, p.user_id]);
    if (c.rows.length === 0) return reply.status(404).send({ error: "chat not found" });
    const chat = c.rows[0];

    // Save user message
    const userMsg = await pool.query(
      "INSERT INTO chat_messages (chat_id, role, content) VALUES ($1,'user',$2) RETURNING message_id, created_at",
      [chatId, content]);

    // Generate delegation token for Gateway
    const delegationToken = jwt.sign(
      { org_id: chat.org_id, key_id: "chat", user_id: (req as any).user.user_id },
      DELEGATION_PRIVATE_KEY, { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" });

    // Build message history
    const history = await pool.query(
      "SELECT role, content FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC", [chatId]);
    const messages = history.rows.map((m: any) => ({ role: m.role, content: m.content }));

    // Auto-title: use first 50 chars of first user message
    if (chat.title === "Новый чат" && history.rows.filter((m: any) => m.role === "user").length === 1) {
      const title = content.slice(0, 50).replace(/\n/g, " ");
      await pool.query("UPDATE chats SET title=$1 WHERE chat_id=$2", [title, chatId]);
    }

    try {
      // Translate model short name → vLLM path
      const modelInfo = MODEL_MAP[chat.model] || MODEL_MAP["qwen2.5-14b"];
      const vllmModel = modelInfo.vllm_path;
      const vllmEndpoint = chat.model === "qwen2.5-32b" ? CORE_API_32B : CORE_API;

      // Call Gateway (handles security, billing, routing, vLLM)
      const vllmRes = await fetch(vllmEndpoint + "/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + delegationToken,
        },
        body: JSON.stringify({
          model: chat.model,  // Gateway handles model routing
          messages: [...messages, { role: "user", content }],
          max_tokens: 2048,
          temperature: 0.7,
        }),
      });

      if (!vllmRes.ok) {
        const errText = await vllmRes.text();
        await pool.query("DELETE FROM chat_messages WHERE message_id=$1", [userMsg.rows[0].message_id]);
        return reply.status(vllmRes.status).send({ error: "Gateway error: " + errText.slice(0, 200) });
      }

      // Gateway returns full JSON (non-streaming)
      const vllmJson: any = await vllmRes.json();
      const fullContent = vllmJson.choices?.[0]?.message?.content || "";
      const usage = vllmJson.usage || {};
      const tokensUsed = usage.total_tokens || Math.ceil(fullContent.length / 4);

      // Stream SSE to client (backward compatible)
      reply.raw.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      });

      // Send content as single delta
      reply.raw.write(`data: ${JSON.stringify({ delta: fullContent })}\n\n`);

      // Save assistant message
      await pool.query(
        "INSERT INTO chat_messages (chat_id, role, content, tokens_used) VALUES ($1,'assistant',$2,$3)",
        [chatId, fullContent, tokensUsed]);
      await pool.query("UPDATE chats SET updated_at=now() WHERE chat_id=$1", [chatId]);

      reply.raw.write(`data: ${JSON.stringify({ delta: "", done: true, tokens_used: tokensUsed })}\n\n`);
      reply.raw.end();
    } catch (e: any) {
      // Delete user message on error
      await pool.query("DELETE FROM chat_messages WHERE message_id=$1", [userMsg.rows[0].message_id]);
      if (!reply.raw.headersSent) {
        return reply.status(502).send({ error: "stream error: " + e.message });
      }
      reply.raw.end();
    }
  });

  // ==================== BALANCE (local) ====================

  app.get("/api/v1/billing", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const orgId = (req.query as any).org_id;
    if (!orgId) return reply.status(400).send({ error: "org_id required" });
    try {
      const r = await pool.query("SELECT total_tokens, reserved, meta FROM billing_accounts WHERE org_id=$1", [orgId]);
      if (r.rows.length === 0) return reply.send({ org_id: orgId, total_tokens: 0, reserved: 0 });
      let total = Number(r.rows[0].total_tokens);
      const meta = r.rows[0].meta || {};
      const refillCount = meta.refill_count || 0;

      // Auto-refill when balance hits 0 (until limit)
      if (total <= 0 && refillCount < REFILL_LIMIT) {
        await pool.query(
          `UPDATE billing_accounts SET total_tokens = total_tokens + $1,
           meta = jsonb_set(COALESCE(meta,'{}'::jsonb),'{refill_count}',$2::jsonb),
           updated_at = now() WHERE org_id=$3`,
          [REFILL_TOKENS, JSON.stringify(refillCount + 1), orgId]);
        total += REFILL_TOKENS;
        console.log(`[auto-refill] org ${orgId}: +${REFILL_TOKENS} tokens (refill #${refillCount + 1}/${REFILL_LIMIT})`);
      }

      return reply.send({ org_id: orgId, total_tokens: total, reserved: Number(r.rows[0].reserved) });
    } catch (e: any) {
      return reply.send({ org_id: orgId, total_tokens: 0, reserved: 0, note: "billing_accounts table missing" });
    }
  });

  app.get("/api/v1/usage", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const orgId = (req.query as any).org_id;
    if (!orgId) return reply.status(400).send({ error: "org_id required" });
    try {
      const r = await pool.query(
        "SELECT count(*), coalesce(sum(tokens),0) FROM payment_transactions WHERE org_id=$1 AND status='succeeded'",
        [orgId]);
      return reply.send({ org_id: orgId, payments: Number(r.rows[0].count), total_tokens: Number(r.rows[0].sum) });
    } catch (e: any) {
      return reply.send({ org_id: orgId, payments: 0, total_tokens: 0 });
    }
  });

  // ==================== PAYMENTS (YooKassa) ====================

  const YOOKASSA_SHOP_ID = process.env.YOOKASSA_SHOP_ID || "";
  const YOOKASSA_SECRET = process.env.YOOKASSA_SECRET || "";
  const TOKENS_PER_RUBLE = 1000; // 1 ₽ = 1000 токенов (для теста; в продакшене ~100)

  // Create payment → redirect to YooKassa
  app.post("/api/v1/billing/topup", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { org_id, amount_rub }: any = req.body;
    if (!org_id || !amount_rub || amount_rub < 1)
      return reply.status(400).send({ error: "org_id and amount_rub (>=1) required" });

    // Check org membership
    const m = await pool.query(
      "SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'",
      [org_id, p.user_id]);
    if (m.rows.length === 0) return reply.status(403).send({ error: "not a member" });

    const tokens = Math.floor(amount_rub * TOKENS_PER_RUBLE);

    // Create transaction record
    const txn = await pool.query(
      `INSERT INTO payment_transactions (org_id, user_id, provider, amount_rub, tokens, status, meta)
       VALUES ($1,$2,'yookassa',$3,$4,'pending','{}'::jsonb) RETURNING txn_id`,
      [org_id, p.user_id, amount_rub, tokens]);

    const txnId: string = txn.rows[0].txn_id;

    // If YooKassa is not configured, auto-succeed for dev mode
    if (!YOOKASSA_SHOP_ID || !YOOKASSA_SECRET) {
      await pool.query(
        "UPDATE payment_transactions SET status='succeeded', updated_at=now(), meta=$1 WHERE txn_id=$2",
        [JSON.stringify({ dev_mode: true }), txnId]);

      // Credit tokens directly (simulate YooKassa callback)
      await pool.query(
        `INSERT INTO billing_accounts (org_id, reserved, total_tokens)
         VALUES ($1, 0, $2)
         ON CONFLICT (org_id) DO UPDATE SET total_tokens = billing_accounts.total_tokens + $2`,
        [org_id, tokens]);

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
      const ykData: any = await ykRes.json();

      if (ykRes.ok && ykData.confirmation?.confirmation_url) {
        await pool.query(
          "UPDATE payment_transactions SET provider_payment_id=$1, meta=$2 WHERE txn_id=$3",
          [ykData.id, JSON.stringify(ykData), txnId]);
        return reply.send({
          ok: true,
          txn_id: txnId,
          confirmation_url: ykData.confirmation.confirmation_url,
          status: "pending",
        });
      }

      return reply.status(502).send({ error: "yookassa error", detail: ykData });
    } catch (e: any) {
      return reply.status(502).send({ error: "yookassa error: " + e.message });
    }
  });

  // YooKassa webhook — called by YooKassa when payment status changes
  app.post("/api/v1/billing/webhook", async (req: any, reply) => {
    try {
      const body: any = req.body;
      const event = body?.event;
      const payment = body?.object;

      if (event === "payment.succeeded" && payment?.status === "succeeded") {
        const txnId = payment.metadata?.txn_id;
        if (!txnId) return reply.send({ ok: false, error: "no txn_id in metadata" });

        const txn = await pool.query(
          "SELECT txn_id, org_id, tokens, status FROM payment_transactions WHERE txn_id=$1",
          [txnId]);
        if (txn.rows.length === 0) return reply.send({ ok: false, error: "txn not found" });
        if (txn.rows[0].status === "succeeded") return reply.send({ ok: true, status: "already_processed" });

        // Mark succeeded + credit tokens
        await pool.query("BEGIN");
        await pool.query(
          "UPDATE payment_transactions SET status='succeeded', updated_at=now(), meta=$1 WHERE txn_id=$2",
          [JSON.stringify(payment), txnId]);

        await pool.query(
          `INSERT INTO billing_accounts (org_id, reserved, total_tokens)
           VALUES ($1, 0, $2)
           ON CONFLICT (org_id) DO UPDATE SET total_tokens = billing_accounts.total_tokens + $2`,
          [txn.rows[0].org_id, txn.rows[0].tokens]);

        await pool.query("COMMIT");
        return reply.send({ ok: true, status: "credited" });
      }

      return reply.send({ ok: true, status: "ignored", event });
    } catch (e: any) {
      return reply.status(500).send({ ok: false, error: e.message });
    }
  });

  // List payment transactions for org
  app.get("/api/v1/billing/payments", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const orgId = (req.query as any).org_id;
    if (!orgId) return reply.status(400).send({ error: "org_id required" });

    const m = await pool.query(
      "SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'",
      [orgId, p.user_id]);
    if (m.rows.length === 0) return reply.status(403).send({ error: "not a member" });

    const r = await pool.query(
      `SELECT txn_id, provider, amount_rub, tokens, status, created_at
       FROM payment_transactions WHERE org_id=$1 ORDER BY created_at DESC LIMIT 50`,
      [orgId]);
    return reply.send({ payments: r.rows });
  });

  await app.listen({ port: PORT, host: "0.0.0.0" });
  console.log("Portal BFF v0.5.0 (with chat) on :" + PORT);
}
main().catch((e) => { console.error(e); process.exit(1); });
