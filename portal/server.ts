import "dotenv/config";
import Fastify from "fastify";
import cors from "@fastify/cors";
import rateLimit from "@fastify/rate-limit";
import jwt from "jsonwebtoken";
import { Pool } from "pg";
import { randomBytes, createHash, scryptSync, timingSafeEqual } from "crypto";
import { authenticateViaLDAP, isLDAPEnabled } from "./ldap";
import { POLICIES_DDL, loadPolicy, savePolicy, validatePolicy } from "./policies";
import { registerApiGateway } from "./api-gateway";
import fs from "fs";
import https from "https";

const PORT = 3000;
const JWT_SECRET = process.env.JWT_SECRET || (() => { throw new Error("JWT_SECRET env required"); })();
const CORE_API = process.env.CORE_API || "http://gateway:8080";
const CORE_API_MTLS = process.env.CORE_API_MTLS || "https://gateway:8443";

// mTLS agent for Gateway communication
const mtlsAgent = (() => {
  try {
    return new https.Agent({
      ca: fs.readFileSync(process.env.MTLS_CA || "/etc/aither/mtls/ca.crt"),
      cert: fs.readFileSync(process.env.MTLS_CERT || "/etc/aither/mtls/bff.crt"),
      key: fs.readFileSync(process.env.MTLS_KEY || "/etc/aither/mtls/bff.key"),
      rejectUnauthorized: true,
    });
  } catch (e) {
    console.warn("[mtls] Agent creation failed, falling back to plain HTTP:", e);
    return null;
  }
})();

// Helper: fetch from Gateway with mTLS if available
export async function gatewayFetch(path: string, opts: RequestInit = {}): Promise<Response> {
  const url = (mtlsAgent ? CORE_API_MTLS : CORE_API) + path;
  const fetchOpts: any = { ...opts };
  if (mtlsAgent) {
    // @ts-ignore — Node.js fetch supports agent via dispatcher
    fetchOpts.dispatcher = mtlsAgent;
  }
  return fetch(url, fetchOpts);
}
const IS_PRODUCTION = process.env.NODE_ENV === "production";
const PUBLIC_HOST = process.env.PUBLIC_HOST || "localhost";
const CORS_ORIGIN = process.env.CORS_ORIGIN || (IS_PRODUCTION ? `https://${PUBLIC_HOST}` : `http://${PUBLIC_HOST}`);

const pool = new Pool({
  host: process.env.PG_HOST || "10.129.13.78",
  port: Number(process.env.PG_PORT) || 31113,
  user: process.env.PG_USER || "aither",
  password: process.env.PGPASSWORD || "",
  database: process.env.PG_DB || "aither",
});

function signToken(userId: string): string {
  return jwt.sign({ user_id: userId }, JWT_SECRET, { expiresIn: "24h" });
}
function setTokenCookie(reply: any, token: string) {
  reply.header("Set-Cookie",
    `aither_token=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400`);
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
async function isSuperAdmin(userId: string): Promise<boolean> {
  const r = await pool.query("SELECT 1 FROM portal_users WHERE user_id=$1 AND role='super_admin'", [userId]);
  return r.rows.length > 0;
}
async function checkOrgOwner(orgId: string, userId: string): Promise<boolean> {
  const r = await pool.query("SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND role='owner'", [orgId, userId]);
  return r.rows.length > 0;
}

const STARTER_TOKENS = 100_000;    // 100K токенов новому пользователю
const REFILL_TOKENS  = 100_000;    // авто-пополнение при обнулении
const REFILL_LIMIT   = 10;         // максимум авто-пополнений (защита от бесконечного цикла)

/** Создаёт личный org для нового пользователя и начисляет стартовые токены */
async function ensurePersonalOrg(userId: string, displayName?: string): Promise<string> {
  const name = displayName || 'Пользователь';
  const orgName = `${name}-организация`;

  // Check for existing personal org
  const exist = await pool.query(
    `SELECT o.org_id FROM portal_organizations o
     JOIN portal_org_members m ON o.org_id=m.org_id
     WHERE m.user_id=$1 AND m.role='owner'
     LIMIT 1`, [userId]);
  if (exist.rows.length > 0) return exist.rows[0].org_id;

  const org = await pool.query(
    "INSERT INTO portal_organizations (name) VALUES ($1) RETURNING org_id", [orgName]);
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

function hashPassword(password: string): string {
  // scrypt: 64-bit salt + 64-byte hash, base64-encoded
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, salt, 64).toString("hex");
  return `${salt}:${hash}`;
}
function verifyPassword(password: string, stored: string): boolean {
  const [salt, hash] = stored.split(":");
  if (!salt || !hash) return false;
  const derived = scryptSync(password, salt, 64).toString("hex");
  return timingSafeEqual(Buffer.from(hash), Buffer.from(derived));
}

function safeError(e: any): string {
  return IS_PRODUCTION ? "internal_error" : e.message || String(e);
}

function safeJsonParse(s: any): any {
  if (!s) return null;
  if (typeof s === "object") return s;
  try { return JSON.parse(s); } catch { return null; }
}

/** In-memory OAuth state store — avoids cookie issues */
const oauthStates = new Map<string, { prefix: string; expires: number }>();

// Cleanup expired states every 5 minutes
setInterval(() => {
  const now = Date.now();
  for (const [k, v] of oauthStates) {
    if (v.expires < now) oauthStates.delete(k);
  }
}, 300_000);

/** Store OAuth state in memory, return state value */
function setOAuthState(_reply: any, prefix: string): string {
  const state = randomBytes(16).toString("hex");
  oauthStates.set(state, { prefix, expires: Date.now() + 600_000 });
  return state;
}

/** Validate OAuth state from memory. Returns true if valid. */
function validateOAuthState(req: any, _reply: any, prefix: string): boolean {
  const queryState = (req.query as any)?.state || "";
  if (!queryState) return false;
  const entry = oauthStates.get(queryState);
  if (!entry) return false;
  oauthStates.delete(queryState);
  return entry.prefix === prefix && entry.expires > Date.now();
}

async function main() {
  const app = Fastify({ logger: false });
  await app.register(cors, { origin: CORS_ORIGIN, credentials: true });

  // Rate limiting: 100 req/min per IP
  await app.register(rateLimit, { max: 100, timeWindow: "1 minute" });

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
      org_id uuid REFERENCES portal_organizations(org_id),
      title text NOT NULL DEFAULT 'Новый чат',
      model text NOT NULL DEFAULT 'qwen2.5-14b',
      share_token text UNIQUE,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    -- Migration: add org_id to existing chats (set to user's personal org)
    ALTER TABLE chats ADD COLUMN IF NOT EXISTS org_id uuid REFERENCES portal_organizations(org_id);
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
  await pool.query(POLICIES_DDL);

  // ==================== AUTH ====================

  // GitHub OAuth
  const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || "";
  const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET || "";

  app.get("/auth/github", async (_req, reply) => {
    if (!GITHUB_CLIENT_ID) return reply.status(500).send({ error: "GitHub OAuth not configured" });
    const state = setOAuthState(reply, "github");
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
        await ensurePersonalOrg(userId, displayName);
      } else {
        userId = user.rows[0].user_id;
        await pool.query(
          "UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4",
          [primaryEmail, displayName, avatarUrl, userId]
        );
      }

      const tok = signToken(userId);
      const redirectHost = process.env.PUBLIC_HOST || "localhost";
      setTokenCookie(reply, tok);
      return reply.redirect(`http://${redirectHost}/?aither_token=${tok}&user_id=${userId}&name=${encodeURIComponent(displayName)}`);
    } catch (e: any) {
      return reply.status(502).send({ error: "GitHub OAuth error: " + safeError(e) });
    }
  });

  // Google OAuth
  const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || "";
  const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET || "";

  app.get("/auth/google", async (_req, reply) => {
    if (!GOOGLE_CLIENT_ID) return reply.status(500).send({ error: "Google OAuth not configured" });
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

  app.get("/auth/google/callback", async (req: any, reply) => {
    if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET)
      return reply.status(500).send({ error: "Google OAuth not configured" });

    const { code } = req.query;
    if (!code) return reply.status(400).send({ error: "missing code" });
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
        await ensurePersonalOrg(userId, displayName);
      } else {
        userId = user.rows[0].user_id;
        await pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4",
          [email, displayName, avatarUrl, userId]);
      }

      const tok = signToken(userId);
      const redirectHost = process.env.PUBLIC_HOST || "localhost";
      setTokenCookie(reply, tok);
      return reply.redirect(`http://${redirectHost}/?aither_token=${tok}&user_id=${userId}&name=${encodeURIComponent(displayName)}`);
    } catch (e: any) {
      return reply.status(502).send({ error: "Google OAuth error: " + safeError(e) });
    }
  });

  // Yandex OAuth
  const YANDEX_CLIENT_ID = process.env.YANDEX_CLIENT_ID || "";
  const YANDEX_CLIENT_SECRET = process.env.YANDEX_CLIENT_SECRET || "";

  app.get("/auth/yandex", async (_req, reply) => {
    if (!YANDEX_CLIENT_ID) return reply.status(500).send({ error: "Yandex OAuth not configured" });
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

  app.get("/auth/yandex/callback", async (req: any, reply) => {
    if (!YANDEX_CLIENT_ID || !YANDEX_CLIENT_SECRET)
      return reply.status(500).send({ error: "Yandex OAuth not configured" });

    const { code } = req.query;
    if (!code) return reply.status(400).send({ error: "missing code" });
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
        await ensurePersonalOrg(userId, displayName);
      } else {
        userId = user.rows[0].user_id;
        await pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4",
          [email, displayName, avatarUrl, userId]);
      }

      const tok = signToken(userId);
      const redirectHost = process.env.PUBLIC_HOST || "localhost";
      setTokenCookie(reply, tok);
      return reply.redirect(`http://${redirectHost}/?aither_token=${tok}&user_id=${userId}&name=${encodeURIComponent(displayName)}`);
    } catch (e: any) {
      return reply.status(502).send({ error: "Yandex OAuth error: " + safeError(e) });
    }
  });

  // === LDAP Authentication (FreeIPA / ALD Pro / OpenLDAP) ===
  app.post("/auth/ldap", async (req: any, reply) => {
    if (!isLDAPEnabled())
      return reply.status(501).send({ error: "LDAP not configured" });

    const { username, password } = req.body || {};
    if (!username || !password)
      return reply.status(400).send({ error: "username and password required" });

    try {
      const ldapUser = await authenticateViaLDAP(username, password);
      if (!ldapUser)
        return reply.status(401).send({ error: "invalid ldap credentials" });

      // Upsert portal user
      const oauthId = `ldap:${ldapUser.uid}`;
      const provider = "ldap";

      let user = await pool.query(
        "SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2",
        [provider, oauthId]
      );
      let userId: string;
      if (user.rows.length === 0) {
        const ins = await pool.query(
          `INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, last_login_at)
           VALUES ($1,$2,$3,$4,now()) RETURNING user_id`,
          [provider, oauthId, ldapUser.email, ldapUser.displayName]
        );
        userId = ins.rows[0].user_id;
        await ensurePersonalOrg(userId, ldapUser.displayName);
      } else {
        userId = user.rows[0].user_id;
        await pool.query(
          "UPDATE portal_users SET email=$1, display_name=$2, last_login_at=now() WHERE user_id=$3",
          [ldapUser.email, ldapUser.displayName, userId]
        );
      }

      const tok = signToken(userId);
      setTokenCookie(reply, tok);
      return {
        access_token: tok,
        user: { user_id: userId, login: ldapUser.uid, email: ldapUser.email },
        ldap_groups: ldapUser.groups,
        ldap_role: ldapUser.role,
      };
    } catch (e: any) {
      return reply.status(502).send({ error: "LDAP error: " + safeError(e) });
    }
  });

  app.post("/auth/dev/login", async (req, reply) => {
    // Dev-провайдер отключён в продакшене (404 — endpoint не существует)
    if (IS_PRODUCTION) return reply.status(404).send({ error: "not_found" });
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
      await ensurePersonalOrg(userId, name);
    } else {
      userId = user.rows[0].user_id;
      await pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [userId]);
    }
    const tok = signToken(userId);
    setTokenCookie(reply, tok);
    return { access_token: tok, user: { user_id: userId, login: name, email } };
  });

  // === SaaS Signup ===
  app.post("/auth/signup", async (req: any, reply) => {
    const { email, password, org_name, invite_code } = req.body || {};
    if (!email || !password) return reply.status(400).send({ error: "email and password required" });
    if (password.length < 6) return reply.status(400).send({ error: "password must be at least 6 characters" });

    // Invitation-only: if INVITE_CODE set in env, must match
    const requiredCode = process.env.INVITE_CODE || "";
    if (requiredCode && invite_code !== requiredCode)
      return reply.status(403).send({ error: "registration requires valid invitation code" });

    const existing = await pool.query("SELECT user_id FROM portal_users WHERE email=$1 AND oauth_provider='email'", [email]);
    if (existing.rows.length > 0) return reply.status(409).send({ error: "email already registered" });

    const hash = hashPassword(password);
    const ins = await pool.query(
      "INSERT INTO portal_users (oauth_provider, oauth_id, email, password_hash, display_name, last_login_at) VALUES ('email',$1,$2,$3,$4,now()) RETURNING user_id",
      [email, email, hash, email.split("@")[0]]
    );
    const userId = ins.rows[0].user_id;
    const orgId = await ensurePersonalOrg(userId, email.split("@")[0]);

    // Create named org
    const orgName = org_name || "Моя организация";
    const newOrg = await pool.query("INSERT INTO portal_organizations (name) VALUES ($1) RETURNING org_id", [orgName]);
    const newOrgId = newOrg.rows[0].org_id;
    await pool.query("INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1,$2,'owner')", [newOrgId, userId]);
    // Create billing account for the org
    try {
      await pool.query(
        "INSERT INTO billing_accounts (org_id, reserved, total_tokens, meta) VALUES ($1,0,$2,'{}'::jsonb) ON CONFLICT (org_id) DO NOTHING",
        [newOrgId, STARTER_TOKENS]
      );
    } catch (e) { /* table may not exist yet */ }

    // Auto-create API key
    const key = "ak-" + randomBytes(24).toString("hex");
    await pool.query("INSERT INTO portal_api_keys (org_id, user_id, name, key_hash, api_key, api_key_prefix, status) VALUES ($1,$2,$3,$4,$5,$6,'active')",
      [newOrgId, userId, "default", key, key, "ak-"]);

    const tok = signToken(userId);
    setTokenCookie(reply, tok);
    return {
      access_token: tok,
      user: { user_id: userId, email, display_name: email.split("@")[0] },
      org: { org_id: newOrgId, name: orgName },
      api_key: key,
    };
  });

  // === SaaS Login ===
  app.post("/auth/login", async (req: any, reply) => {
    const { email, password } = req.body || {};
    if (!email || !password) return reply.status(400).send({ error: "email and password required" });

    const r = await pool.query("SELECT user_id, password_hash, display_name FROM portal_users WHERE email=$1 AND oauth_provider='email'", [email]);
    if (r.rows.length === 0) return reply.status(401).send({ error: "invalid credentials" });

    if (!verifyPassword(password, r.rows[0].password_hash)) return reply.status(401).send({ error: "invalid credentials" });

    await pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [r.rows[0].user_id]);
    const tok = signToken(r.rows[0].user_id);
    setTokenCookie(reply, tok);
    return {
      access_token: tok,
      user: { user_id: r.rows[0].user_id, email, display_name: r.rows[0].display_name },
    };
  });

  // ── External API Gateway (API-key auth, OpenAI-compatible) ──
  registerApiGateway(app, pool);

  app.get("/api/v1/me", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const r = await pool.query("SELECT user_id, display_name, email, avatar_url, oauth_provider, created_at FROM portal_users WHERE user_id=$1", [p.user_id]);
    if (r.rows.length === 0) return reply.status(404).send({ error: "user not found" });
    return { user: r.rows[0] };
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

  app.get("/api/v1/status", async (_r, reply) => {
    const k = await pool.query("SELECT count(*) FROM portal_api_keys WHERE status='active'");
    return reply.send({
      active_api_keys: Number(k.rows[0].count),
    });
  });
  
  app.get("/api/v1/core/status", async (_r, reply) => {
    try {
      const r = await gatewayFetch("/health");
      const text = await r.text();
      if (!text) return reply.send({ status: "ok", model: "vLLM", note: "health returned empty (vLLM direct)" });
      try { return reply.send(JSON.parse(text)); }
      catch { return reply.send({ status: "ok", raw: text.slice(0, 200) }); }
    } catch (e: any) {
      return reply.send({ status: "unreachable", error: safeError(e) });
    }
  });

  app.get("/api/v1/users", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    // Only show users who share an organization with the requester
    const r = await pool.query(
      `SELECT DISTINCT u.user_id, u.display_name, u.email, u.oauth_provider, u.created_at
       FROM portal_users u
       JOIN portal_org_members m ON u.user_id = m.user_id
       WHERE m.org_id IN (
         SELECT org_id FROM portal_org_members WHERE user_id = $1
       )
       ORDER BY u.created_at DESC`, [p.user_id]);
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
    } catch (e: any) { await client.query("ROLLBACK"); return reply.status(500).send({ error: safeError(e) }); }
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

  // ==================== ORG SECURITY POLICIES ====================

  app.get("/api/v1/orgs/:orgId/policy", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { orgId } = req.params;
    const m = await pool.query(
      "SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'",
      [orgId, p.user_id]);
    if (m.rows.length === 0) return reply.status(403).send({ error: "not a member" });
    try {
      const policy = await loadPolicy(pool, orgId);
      return { org_id: orgId, policy };
    } catch (e: any) {
      return reply.status(500).send({ error: safeError(e) });
    }
  });

  app.put("/api/v1/orgs/:orgId/policy", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { orgId } = req.params;
    if (!await checkOrgOwner(orgId, p.user_id))
      return reply.status(403).send({ error: "owner only" });

    const body: any = req.body || {};
    const allowedKeys = [
      "dlp_enabled", "jailbreak_detection", "sensitive_data_patterns",
      "allowed_ip_cidrs", "mfa_required", "session_timeout_min",
      "api_key_max_age_days", "api_key_rotation_required",
      "custom_rpm", "custom_tpm", "max_concurrent_requests",
      "allowed_models", "max_tokens_per_request",
      "chat_retention_days", "audit_log_retention_days",
      "chat_enabled",
    ];

    const updates: any = {};
    for (const key of allowedKeys) {
      if (key in body) updates[key] = body[key];
    }

    if (Object.keys(updates).length === 0)
      return reply.status(400).send({ error: "no valid policy fields provided" });

    const err = validatePolicy(updates);
    if (err) return reply.status(400).send({ error: err });

    try {
      const policy = await savePolicy(pool, orgId, updates);
      return { org_id: orgId, policy };
    } catch (e: any) {
      return reply.status(500).send({ error: safeError(e) });
    }
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

  /** Check if chat is enabled for any org the user belongs to. Returns org_id if enabled, null otherwise. */
  async function checkChatEnabled(userId: string, reply: any): Promise<string | null> {
    const orgs = await pool.query(
      `SELECT o.org_id FROM portal_organizations o
       JOIN portal_org_members m ON o.org_id = m.org_id
       WHERE m.user_id = $1 AND m.status = 'active'
       LIMIT 1`, [userId]);
    if (orgs.rows.length === 0) {
      reply.status(403).send({ error: "chat_disabled", detail: "no active organization" });
      return null;
    }
    const orgId = orgs.rows[0].org_id;
    const policy = await loadPolicy(pool, orgId);
    if (!policy.chat_enabled) {
      reply.status(403).send({ error: "chat_disabled", detail: "чат отключён в настройках безопасности организации" });
      return null;
    }
    return orgId;
  }

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
    const orgId = await checkChatEnabled(p.user_id, reply); if (!orgId) return;
    const r = await pool.query(
      `SELECT chat_id, title, model, share_token, created_at, updated_at
       FROM chats WHERE user_id=$1 AND org_id=$2 ORDER BY updated_at DESC LIMIT 50`,
      [p.user_id, orgId]);
    return { chats: r.rows };
  });

  // Create chat
  app.post("/api/v1/chats", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const orgId = await checkChatEnabled(p.user_id, reply); if (!orgId) return;
    const { title, model }: any = req.body || {};
    const r = await pool.query(
      `INSERT INTO chats (user_id, org_id, title, model) VALUES ($1,$2,$3,$4)
       RETURNING chat_id, title, model, created_at`,
      [p.user_id, orgId, title || "Новый чат", model || "qwen2.5-14b"]);
    return { chat: r.rows[0] };
  });

  // Get chat with messages
  app.get("/api/v1/chats/:chatId", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const orgId = await checkChatEnabled(p.user_id, reply); if (!orgId) return;
    const { chatId } = req.params;
    const c = await pool.query("SELECT * FROM chats WHERE chat_id=$1 AND user_id=$2 AND org_id=$3", [chatId, p.user_id, orgId]);
    if (c.rows.length === 0) return reply.status(404).send({ error: "chat not found" });
    const msgs = await pool.query(
      "SELECT message_id, role, content, tokens_used, created_at FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC",
      [chatId]);
    return { chat: c.rows[0], messages: msgs.rows };
  });

  // Delete chat
  app.delete("/api/v1/chats/:chatId", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const orgId = await checkChatEnabled(p.user_id, reply); if (!orgId) return;
    const { chatId } = req.params;
    const r = await pool.query("DELETE FROM chats WHERE chat_id=$1 AND user_id=$2 AND org_id=$3 RETURNING chat_id", [chatId, p.user_id, orgId]);
    if (r.rows.length === 0) return reply.status(404).send({ error: "chat not found" });
    return { deleted: true };
  });

  // Share chat (generate token)
  app.post("/api/v1/chats/:chatId/share", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    if (!await checkChatEnabled(p.user_id, reply)) return;
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
    if (!await checkChatEnabled(p.user_id, reply)) return;
    const { chatId } = req.params;
    const { content, org_id }: any = req.body || {};
    if (!content) return reply.status(400).send({ error: "content required" });

    // Get chat
    const c = await pool.query("SELECT * FROM chats WHERE chat_id=$1 AND user_id=$2", [chatId, p.user_id]);
    if (c.rows.length === 0) return reply.status(404).send({ error: "chat not found" });
    const chat = c.rows[0];

    // Save user message
    const userMsg = await pool.query(
      "INSERT INTO chat_messages (chat_id, role, content) VALUES ($1,'user',$2) RETURNING message_id, created_at",
      [chatId, content]);

    // Create delegation token for Gateway
    const delegationToken = DELEGATION_PRIVATE_KEY ? jwt.sign(
      { org_id: org_id || "", user_id: p.user_id },
      DELEGATION_PRIVATE_KEY, { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" }
    ) : "";

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
      const vllmEndpoint = CORE_API;

      // Call Gateway (with mTLS) which proxies to vLLM
      const vllmRes = await gatewayFetch("/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(delegationToken ? { "Authorization": "Bearer " + delegationToken } : {}),
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
      let vllmUsage = 0; // real token count from vLLM
      const reader = vllmRes.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") continue;
              try {
                const parsed = JSON.parse(data);
                const delta = parsed.choices?.[0]?.delta?.content || "";
                fullContent += delta;
                // Capture real token usage from vLLM
                if (parsed.usage?.total_tokens) vllmUsage = parsed.usage.total_tokens;
                // Forward to client
                reply.raw.write(`data: ${JSON.stringify({ delta })}\n\n`);
              } catch {}
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      // Use real vLLM token count, fall back to estimate
      const tokensUsed = vllmUsage || Math.ceil(fullContent.length / 4);

      // Deduct from billing account
      if (org_id) {
        await pool.query(
          "UPDATE billing_accounts SET total_tokens = GREATEST(total_tokens - $1, 0) WHERE org_id=$2",
          [tokensUsed, org_id]);
      }

      // Save assistant message
      await pool.query(
        "INSERT INTO chat_messages (chat_id, role, content, tokens_used) VALUES ($1,'assistant',$2,$3)",
        [chatId, fullContent, tokensUsed]);
      await pool.query("UPDATE chats SET updated_at=now() WHERE chat_id=$1", [chatId]);

      const newBalance = org_id ? (await pool.query(
        "SELECT total_tokens FROM billing_accounts WHERE org_id=$1", [org_id]
      )).rows[0]?.total_tokens : null;

      reply.raw.write(`data: ${JSON.stringify({ delta: "", done: true, tokens_used: tokensUsed, balance: Number(newBalance) })}\n\n`);
      reply.raw.end();
    } catch (e: any) {
      // Delete user message on error
      await pool.query("DELETE FROM chat_messages WHERE message_id=$1", [userMsg.rows[0].message_id]);
      if (!reply.raw.headersSent) {
        return reply.status(502).send({ error: "stream error: " + safeError(e) });
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

  // === Dashboard: aggregated usage for charts ===
  app.get("/api/v1/billing/dashboard", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const orgId = (req.query as any).org_id;
    if (!orgId) return reply.status(400).send({ error: "org_id required" });

    try {
      // Daily usage (last 30 days)
      const daily = await pool.query(
        `SELECT date(created_at) as day, coalesce(sum(tokens),0) as tokens, count(*) as requests
         FROM payment_transactions
         WHERE org_id=$1 AND status='succeeded' AND created_at > now() - interval '30 days'
         GROUP BY day ORDER BY day`, [orgId]);

      // Current month total
      const month = await pool.query(
        `SELECT coalesce(sum(tokens),0) as total, count(*) as count
         FROM payment_transactions
         WHERE org_id=$1 AND status='succeeded'
           AND date_trunc('month', created_at) = date_trunc('month', now())`, [orgId]);

      // Top models (from meta jsonb)
      const byModel = await pool.query(
        `SELECT COALESCE(meta->>'model','unknown') as model, coalesce(sum(tokens),0) as tokens, count(*) as requests
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
    } catch (e: any) {
      return reply.status(500).send({ error: safeError(e) });
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
      return reply.status(502).send({ error: "yookassa error: " + safeError(e) });
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
          "SELECT txn_id, org_id, tokens, status, meta FROM payment_transactions WHERE txn_id=$1",
          [txnId]);
        if (txn.rows.length === 0) return reply.send({ ok: false, error: "txn not found" });
        if (txn.rows[0].status === "succeeded") return reply.send({ ok: true, status: "already_processed" });

        const tier = payment.metadata?.tier;
        const txnMeta = safeJsonParse(txn.rows[0].meta) || {};
        const effectiveTier = tier || txnMeta.tier;

        // Mark succeeded + credit tokens
        await pool.query("BEGIN");
        await pool.query(
          "UPDATE payment_transactions SET status='succeeded', updated_at=now(), meta=$1 WHERE txn_id=$2",
          [JSON.stringify(payment), txnId]);

        if (txn.rows[0].tokens > 0) {
          await pool.query(
            `INSERT INTO billing_accounts (org_id, reserved, total_tokens)
             VALUES ($1, 0, $2)
             ON CONFLICT (org_id) DO UPDATE SET total_tokens = billing_accounts.total_tokens + $2`,
            [txn.rows[0].org_id, txn.rows[0].tokens]);
        }

        // If tier purchase — upgrade tier
        if (effectiveTier) {
          await pool.query(
            "UPDATE billing_accounts SET tier=$1, updated_at=now() WHERE org_id=$2",
            [effectiveTier, txn.rows[0].org_id]);
        }

        await pool.query("COMMIT");
        return reply.send({ ok: true, status: effectiveTier ? "tier_upgraded" : "credited" });
      }

      return reply.send({ ok: true, status: "ignored", event });
    } catch (e: any) {
      return reply.status(500).send({ ok: false, error: safeError(e) });
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

  // === Tariff plans ===
  app.get("/api/v1/tiers", async (_req: any, reply) => {
    try {
      const r = await pool.query(
        "SELECT tier_id, name, description, rpm_limit, tpm_limit, daily_request_limit, models, rag_enabled, priority, price_rub_month, features FROM subscription_tiers ORDER BY priority");
      return reply.send({ tiers: r.rows });
    } catch (e: any) {
      return reply.status(500).send({ error: safeError(e) });
    }
  });

  app.get("/api/v1/org/tier", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const orgId = (req.query as any).org_id;
    if (!orgId) return reply.status(400).send({ error: "org_id required" });
    try {
      const r = await pool.query(
        `SELECT b.tier, t.name, t.rpm_limit, t.tpm_limit, t.daily_request_limit, t.models, t.rag_enabled, t.priority, t.price_rub_month, t.features
         FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier = t.tier_id WHERE b.org_id=$1`, [orgId]);
      if (r.rows.length === 0) return reply.send({ org_id: orgId, tier: "free", name: "Free" });
      return reply.send(r.rows[0]);
    } catch (e: any) {
      return reply.status(500).send({ error: safeError(e) });
    }
  });

  // === Tier upgrade ===
  app.post("/api/v1/orgs/:orgId/upgrade", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { orgId } = req.params as any;
    const { tier }: any = req.body;
    if (!tier) return reply.status(400).send({ error: "tier required (free|standard|vip|enterprise)" });

    // Check org membership
    const m = await pool.query(
      "SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'",
      [orgId, p.user_id]);
    if (m.rows.length === 0) return reply.status(403).send({ error: "not a member" });

    // Validate tier exists
    const t = await pool.query("SELECT tier_id FROM subscription_tiers WHERE tier_id=$1", [tier]);
    if (t.rows.length === 0) return reply.status(400).send({ error: "invalid tier" });

    await pool.query("UPDATE billing_accounts SET tier=$1, updated_at=now() WHERE org_id=$2", [tier, orgId]);

    // Return updated tier info
    const r = await pool.query(
      `SELECT b.tier, t.name, t.rpm_limit, t.tpm_limit, t.daily_request_limit, t.models, t.rag_enabled, t.priority
       FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier = t.tier_id WHERE b.org_id=$1`, [orgId]);
    return reply.send({ ok: true, tier: r.rows[0] });
  });

  // === Purchase tier (with payment) ===
  app.post("/api/v1/orgs/:orgId/purchase-tier", async (req: any, reply) => {
    const p = auth(req, reply); if (!p) return;
    const { orgId } = req.params as any;
    const { tier }: any = req.body;
    if (!tier) return reply.status(400).send({ error: "tier required" });

    // Check org membership
    const m = await pool.query(
      "SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'",
      [orgId, p.user_id]);
    if (m.rows.length === 0) return reply.status(403).send({ error: "not a member" });

    // Get tier info
    const t = await pool.query(
      "SELECT tier_id, name, price_rub_month FROM subscription_tiers WHERE tier_id=$1", [tier]);
    if (t.rows.length === 0) return reply.status(400).send({ error: "invalid tier" });

    const tierInfo = t.rows[0];
    const price = Number(tierInfo.price_rub_month) || 0;

    // Free tier — upgrade immediately
    if (price === 0) {
      await pool.query("UPDATE billing_accounts SET tier=$1, updated_at=now() WHERE org_id=$2", [tier, orgId]);
      const r = await pool.query(
        "SELECT b.tier, t.name FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier=t.tier_id WHERE b.org_id=$1", [orgId]);
      return reply.send({ ok: true, tier: r.rows[0], paid: false });
    }

    // Paid tier — create transaction
    const txn = await pool.query(
      `INSERT INTO payment_transactions (org_id, user_id, provider, amount_rub, tokens, status, meta)
       VALUES ($1,$2,'yookassa',$3,0,'pending',$4) RETURNING txn_id`,
      [orgId, p.user_id, price, JSON.stringify({ tier, tier_name: tierInfo.name })]);

    const txnId: string = txn.rows[0].txn_id;

    // Dev mode — auto-succeed
    if (!YOOKASSA_SHOP_ID || !YOOKASSA_SECRET) {
      await pool.query("UPDATE billing_accounts SET tier=$1, updated_at=now() WHERE org_id=$2", [tier, orgId]);
      await pool.query(
        "UPDATE payment_transactions SET status='succeeded', updated_at=now(), meta=$1 WHERE txn_id=$2",
        [JSON.stringify({ dev_mode: true, tier }), txnId]);
      const r = await pool.query(
        "SELECT b.tier, t.name FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier=t.tier_id WHERE b.org_id=$1", [orgId]);
      return reply.send({ ok: true, tier: r.rows[0], paid: false, dev_mode: true });
    }

    // YooKassa payment
    try {
      const ykRes = await fetch("https://api.yookassa.ru/v3/payments", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Basic " + Buffer.from(YOOKASSA_SHOP_ID + ":" + YOOKASSA_SECRET).toString("base64"),
          "Idempotence-Key": txnId,
        },
        body: JSON.stringify({
          amount: { value: price.toFixed(2), currency: "RUB" },
          confirmation: { type: "redirect", return_url: `https://${process.env.PUBLIC_HOST || "localhost"}:10443/#tiers` },
          description: `Aither: тариф «${tierInfo.name}»`,
          metadata: { txn_id: txnId, org_id: orgId, tier },
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
      return reply.status(502).send({ error: "yookassa error: " + safeError(e) });
    }
  });

  // ==================== ADMIN PROXY ====================

  const ADMIN_KEY = process.env.ADMIN_KEY || "";

  // ── Check if current user has admin role (for frontend UI) ──
  app.get("/api/v1/admin/check", async (req: any, reply) => {
    // Parse cookie
    const cookieHeader = req.headers.cookie || "";
    const cookies: Record<string, string> = {};
    cookieHeader.split(";").forEach((c: string) => {
      const idx = c.indexOf("=");
      if (idx > 0) cookies[c.substring(0, idx).trim()] = c.substring(idx + 1).trim();
    });
    const cookieToken = cookies["aither_token"] || "";

    let p = cookieToken ? verifyToken(cookieToken) : null;
    if (!p) {
      const ah = req.headers.authorization || "";
      if (ah.startsWith("Bearer ")) p = verifyToken(ah.slice(7));
    }

    if (!p) return reply.send({ admin: false });

    // Super admin bypass — no org check needed
    if (await isSuperAdmin(p.user_id)) return reply.send({ admin: true });

    const orgs = await pool.query(
      "SELECT 1 FROM portal_org_members WHERE user_id=$1 AND role IN ('owner','billing_admin') LIMIT 1",
      [p.user_id]
    );
    return reply.send({ admin: orgs.rows.length > 0 });
  });

  // ── Serve admin.html — only to authenticated users with admin role ──
  app.get("/admin.html", async (req: any, reply) => {
    const adminHeader = req.headers["x-admin-key"] || "";
    const isAdminKey = ADMIN_KEY && adminHeader === ADMIN_KEY;

    if (!isAdminKey) {
      // Parse cookies (set during OAuth/login)
      const cookieHeader = req.headers.cookie || "";
      const cookies: Record<string, string> = {};
      cookieHeader.split(";").forEach((c: string) => {
        const idx = c.indexOf("=");
        if (idx > 0) cookies[c.substring(0, idx).trim()] = c.substring(idx + 1).trim();
      });
      const cookieToken = cookies["aither_token"] || "";

      // Try cookie first, then Authorization header
      let p = cookieToken ? verifyToken(cookieToken) : null;
      if (!p) {
        const ah = req.headers.authorization || "";
        if (ah.startsWith("Bearer ")) p = verifyToken(ah.slice(7));
      }

      if (!p) {
        // No valid auth — redirect to portal login
        return reply.redirect("/");
      }

      // Super admin bypass — no org check needed
      const isAdmin = await isSuperAdmin(p.user_id) || (await pool.query(
        "SELECT 1 FROM portal_org_members WHERE user_id=$1 AND role IN ('owner','billing_admin') LIMIT 1",
        [p.user_id]
      )).rows.length > 0;

      if (!isAdmin) {
        return reply.status(403).type("text/html").send(
          "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>403 — Aither Admin</title>" +
          "<style>body{font-family:system-ui;background:#0a0a0f;color:#e4e4ec;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}" +
          "div{text-align:center}h1{font-size:72px;margin:0;color:#f87171}p{color:#71718a;margin:8px 0 24px}a{color:#818cf8}</style></head>" +
          "<body><div><h1>403</h1><p>Доступ запрещён — требуются права администратора</p>" +
          "<a href='/'>← На портал</a></div></body></html>"
        );
      }
    }

    const fs = await import("fs");
    const html = fs.readFileSync("/root/aither-project/portal/static/admin.html", "utf8");
    return reply.type("text/html").send(html);
  });

  // Admin users — handled locally (portal DB, not billing DB)
  app.get("/api/v1/admin/users", async (req: any, reply) => {
    const adminHeader = req.headers["x-admin-key"] || "";
    const isAdminKey = ADMIN_KEY && adminHeader === ADMIN_KEY;
    if (!isAdminKey) {
      const p = auth(req, reply); if (!p) return;
      const orgs = await pool.query("SELECT role FROM portal_org_members WHERE user_id=$1 AND role='owner' AND status='active' LIMIT 1", [p.user_id]);
      if (orgs.rows.length === 0) return reply.status(403).send({ error: "admin access required" });
    }
    const r = await pool.query(`
      SELECT u.user_id, u.display_name, u.email, u.oauth_provider as provider,
             (SELECT count(*) FROM portal_org_members m WHERE m.user_id = u.user_id AND m.status = 'active') as org_count
      FROM portal_users u ORDER BY u.created_at DESC LIMIT 50`);
    return reply.send({ users: r.rows });
  });

  // User orgs
  app.get("/api/v1/admin/users/:userId/orgs", async (req: any, reply) => {
    const { userId } = req.params;
    const r = await pool.query(
      `SELECT m.role, m.status, o.org_id, o.name, COALESCE(b.total_tokens,0) AS balance, COALESCE(b.tier,'none') AS tier
       FROM portal_org_members m
       JOIN portal_organizations o ON o.org_id = m.org_id
       LEFT JOIN billing_accounts b ON b.org_id = o.org_id
       WHERE m.user_id = $1`, [userId]);
    return reply.send({ orgs: r.rows });
  });

  // Delete user
  app.delete("/api/v1/admin/users/:userId", async (req: any, reply) => {
    const { userId } = req.params;
    // Remove from all orgs
    await pool.query("DELETE FROM portal_org_members WHERE user_id = $1", [userId]);
    // Delete payment transactions
    await pool.query("DELETE FROM payment_transactions WHERE user_id = $1", [userId]);
    // Delete user
    await pool.query("DELETE FROM portal_users WHERE user_id = $1", [userId]);
    return reply.send({ status: "deleted", user_id: userId });
  });

  app.post("/api/v1/admin/users/:userId/role", async (req: any, reply) => {
    // Role change is not yet implemented — requires portal_users.role column
    return reply.send({ status: "ok", note: "role change not yet implemented" });
  });

  // Tiers — read from local subscription_tiers table (not proxied to Gateway)
  app.get("/api/v1/admin/tiers", async (_req: any, reply) => {
    const r = await pool.query(
      "SELECT tier_id, name, description, rpm_limit, tpm_limit, daily_request_limit AS daily_limit, " +
      "models, rag_enabled, priority, price_rub_month AS price_rub FROM subscription_tiers ORDER BY priority");
    return reply.send({ tiers: r.rows });
  });

  // Settings (LDAP) — stored in local portal_settings table, not proxied to Gateway
  app.get("/api/v1/admin/settings", async (req: any, reply) => {
    const r = await pool.query("SELECT key, value FROM portal_settings");
    const result: Record<string, string> = {};
    for (const row of r.rows) result[row.key] = row.value;
    return reply.send(result);
  });

  app.post("/api/v1/admin/settings", async (req: any, reply) => {
    const entries = Object.entries(req.body || {});
    for (const [key, value] of entries) {
      await pool.query(
        `INSERT INTO portal_settings (key, value) VALUES ($1, $2)
         ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()`,
        [key, String(value)]
      );
    }
    return reply.send({ status: "ok", updated: entries.length });
  });

  // ── Organizations (admin CRUD) ──
  app.get("/api/v1/admin/orgs", async (_req: any, reply) => {
    const r = await pool.query(`
      SELECT o.org_id, o.name, o.status, o.created_at,
             COALESCE(b.total_tokens, 0) AS balance,
             COALESCE(b.tier, 'none') AS tier,
             (SELECT COUNT(*) FROM portal_org_members m WHERE m.org_id = o.org_id AND m.status = 'active') AS member_count,
             (SELECT COUNT(*) FROM portal_api_keys k WHERE k.org_id = o.org_id AND k.status = 'active') AS key_count
      FROM portal_organizations o
      LEFT JOIN billing_accounts b ON b.org_id = o.org_id
      ORDER BY o.created_at DESC LIMIT 100`);
    return reply.send({ orgs: r.rows });
  });

  app.get("/api/v1/admin/orgs/:orgId", async (req: any, reply) => {
    const { orgId } = req.params;
    const org = await pool.query(
      `SELECT o.*, COALESCE(b.total_tokens,0) AS balance, COALESCE(b.reserved,0) AS reserved,
              COALESCE(b.tier, 'none') AS tier, b.meta AS billing_meta
       FROM portal_organizations o
       LEFT JOIN billing_accounts b ON b.org_id = o.org_id
       WHERE o.org_id = $1`, [orgId]);
    if (org.rows.length === 0) return reply.status(404).send({ error: "org not found" });

    const members = await pool.query(
      `SELECT m.*, u.display_name, u.email, u.user_id AS uid
       FROM portal_org_members m
       JOIN portal_users u ON u.user_id = m.user_id
       WHERE m.org_id = $1`, [orgId]);

    const keys = await pool.query(
      "SELECT key_id, api_key_prefix, name, status, created_at, last_used_at FROM portal_api_keys WHERE org_id = $1", [orgId]);

    return reply.send({ org: org.rows[0], members: members.rows, api_keys: keys.rows });
  });

  app.delete("/api/v1/admin/orgs/:orgId", async (req: any, reply) => {
    const { orgId } = req.params;
    // Cascade: policies (cascades), payments, members, keys, billing, org
    // Note: portal_org_policies has ON DELETE CASCADE — handled automatically
    await pool.query("DELETE FROM payment_transactions WHERE org_id = $1", [orgId]);
    await pool.query("DELETE FROM portal_org_members WHERE org_id = $1", [orgId]);
    await pool.query("DELETE FROM portal_api_keys WHERE org_id = $1", [orgId]);
    await pool.query("DELETE FROM billing_accounts WHERE org_id = $1", [orgId]);
    await pool.query("DELETE FROM portal_organizations WHERE org_id = $1", [orgId]);
    return reply.send({ status: "deleted", org_id: orgId });
  });

  // ── API Keys (admin) ──
  app.get("/api/v1/admin/apikeys", async (_req: any, reply) => {
    const r = await pool.query(`
      SELECT k.key_id, k.api_key_prefix, k.name, k.status, k.created_at, k.last_used_at,
             k.org_id, o.name AS org_name
      FROM portal_api_keys k
      LEFT JOIN portal_organizations o ON o.org_id = k.org_id
      ORDER BY k.created_at DESC LIMIT 200`);
    return reply.send({ keys: r.rows });
  });

  app.delete("/api/v1/admin/apikeys/:keyId", async (req: any, reply) => {
    const { keyId } = req.params;
    await pool.query("UPDATE portal_api_keys SET status = 'revoked' WHERE key_id = $1", [keyId]);
    return reply.send({ status: "revoked", key_id: keyId });
  });

  // Proxy /api/v1/admin/* → Gateway /admin/*
  app.all("/api/v1/admin/*", async (req: any, reply) => {
    // Admin key bypass: skip user auth for automated/admin-panel access
    const adminHeader = req.headers["x-admin-key"] || "";
    const isAdminKey = ADMIN_KEY && adminHeader === ADMIN_KEY;

    if (!isAdminKey) {
      // Normal flow: require authenticated user + org owner role
      const p = auth(req, reply); if (!p) return;
      const orgs = await pool.query(
        "SELECT role FROM portal_org_members WHERE user_id=$1 AND role='owner' AND status='active' LIMIT 1",
        [p.user_id]);
      if (orgs.rows.length === 0)
        return reply.status(403).send({ error: "admin access required" });
    }

    const path = (req.params as any)["*"];
    // Admin API is at Gateway root, not under /v1
    const gwUrl = `${CORE_API.replace(/\/v1\/?$/, "")}/admin/${path}`;
    const adminPath = `/admin/${path}`;
    try {
      const method = req.method;
      const headers: any = { "Content-Type": "application/json" };
      // Generate admin JWT — Gateway verifies with shared secret
      const ADMIN_JWT_SECRET = process.env.ADMIN_JWT_SECRET || "change-me";
      const adminToken = jwt.sign(
        { role: "admin", iat: Math.floor(Date.now() / 1000) },
        ADMIN_JWT_SECRET,
        { algorithm: "HS256", expiresIn: "5m" }
      );
      headers["Authorization"] = `Bearer ${adminToken}`;

      let body: string | undefined;
      if (method === "POST" || method === "PUT") {
        body = JSON.stringify(req.body);
      }

      const resp = await gatewayFetch(adminPath, { method, headers, body });
      const data = await resp.json();
      return reply.status(resp.status).send(data);
    } catch (e: any) {
      return reply.status(502).send({ error: "gateway unreachable", detail: safeError(e) });
    }
  });

  // При production: слушаем только localhost (nginx проксирует)
  const listenHost = IS_PRODUCTION ? "127.0.0.1" : "0.0.0.0";
  await app.listen({ port: PORT, host: listenHost });
  console.log(`Portal BFF v0.6.0 (security-hardened) on ${listenHost}:${PORT}`);
}
main().catch((e) => { console.error(e); process.exit(1); });
