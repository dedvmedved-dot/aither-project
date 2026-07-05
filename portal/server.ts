import Fastify from "fastify";
import cors from "@fastify/cors";
import jwt from "jsonwebtoken";
import { Pool } from "pg";
import { randomBytes } from "crypto";

const PORT = 3000;
const JWT_SECRET = process.env.JWT_SECRET || "dev-jwt-secret-change-me";
const CORE_API = process.env.CORE_API || "http://10.129.13.78:30900";

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
  `);

  // Health
  app.get("/health", async () => {
    await pool.query("SELECT 1");
    return { status: "ok", database: "connected" };
  });

  // ==================== AUTH ====================

  // Dev login
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
    } else {
      userId = user.rows[0].user_id;
      await pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [userId]);
    }
    const tok = signToken(userId);
    return { access_token: tok, user: { user_id: userId, login: name, email } };
  });

  // Me
  app.get("/api/v1/me", async (req: any, reply) => {
    const p = auth(req, reply);
    if (!p) return;
    const r = await pool.query("SELECT user_id, display_name, email, avatar_url, oauth_provider, created_at FROM portal_users WHERE user_id=$1", [p.user_id]);
    if (r.rows.length === 0) return reply.status(404).send({ error: "user not found" });
    return { user: r.rows[0] };
  });

  // Status
  app.get("/api/v1/status", async () => {
    const o = await pool.query("SELECT count(*) FROM portal_organizations");
    const u = await pool.query("SELECT count(*) FROM portal_users");
    const k = await pool.query("SELECT count(*) FROM portal_api_keys WHERE status='active'");
    return {
      version: "0.3.0",
      orgs: Number(o.rows[0].count),
      users: Number(u.rows[0].count),
      active_keys: Number(k.rows[0].count),
    };
  });

  // Core proxy
  app.get("/api/v1/core/status", async (_r, reply) => {
    try {
      const r = await fetch(CORE_API + "/health");
      return reply.send(await r.json());
    } catch (e: any) {
      return reply.status(502).send({ error: "core_unreachable", detail: e.message });
    }
  });

  // Users list
  app.get("/api/v1/users", async () => {
    const r = await pool.query("SELECT user_id, display_name, email, oauth_provider, created_at FROM portal_users ORDER BY created_at DESC");
    return { users: r.rows };
  });

  // ==================== ORGS ====================

  // List my orgs
  app.get("/api/v1/orgs", async (req: any, reply) => {
    const p = auth(req, reply);
    if (!p) return;
    const r = await pool.query(
      `SELECT o.org_id, o.name, o.status, o.created_at, m.role
       FROM portal_organizations o
       JOIN portal_org_members m ON o.org_id = m.org_id
       WHERE m.user_id = $1 AND m.status = 'active'
       ORDER BY o.created_at DESC`,
      [p.user_id]
    );
    return { orgs: r.rows };
  });

  // Create org
  app.post("/api/v1/orgs", async (req: any, reply) => {
    const p = auth(req, reply);
    if (!p) return;
    const { name }: any = req.body;
    if (!name || typeof name !== "string" || name.trim().length === 0) {
      return reply.status(400).send({ error: "name is required" });
    }
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const org = await client.query(
        "INSERT INTO portal_organizations (name) VALUES ($1) RETURNING org_id, name, status, created_at",
        [name.trim()]
      );
      const o = org.rows[0];
      await client.query(
        "INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1, $2, 'owner')",
        [o.org_id, p.user_id]
      );
      await client.query("COMMIT");
      return { org: { ...o, role: "owner" } };
    } catch (e: any) {
      await client.query("ROLLBACK");
      return reply.status(500).send({ error: e.message });
    } finally {
      client.release();
    }
  });

  // Get org detail
  app.get("/api/v1/orgs/:orgId", async (req: any, reply) => {
    const p = auth(req, reply);
    if (!p) return;
    const { orgId } = req.params;
    const r = await pool.query(
      `SELECT o.org_id, o.name, o.status, o.created_at, m.role
       FROM portal_organizations o
       JOIN portal_org_members m ON o.org_id = m.org_id
       WHERE o.org_id = $1 AND m.user_id = $2`,
      [orgId, p.user_id]
    );
    if (r.rows.length === 0) return reply.status(404).send({ error: "org not found" });
    return { org: r.rows[0] };
  });

  // ==================== API KEYS ====================

  // List keys for org
  app.get("/api/v1/orgs/:orgId/api-keys", async (req: any, reply) => {
    const p = auth(req, reply);
    if (!p) return;
    const { orgId } = req.params;
    const m = await pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id]);
    if (m.rows.length === 0) return reply.status(403).send({ error: "not a member of this org" });
    const r = await pool.query(
      `SELECT key_id, api_key_prefix, name, status, created_at, expires_at, last_used_at
       FROM portal_api_keys WHERE org_id = $1 AND status != 'revoked'
       ORDER BY created_at DESC`,
      [orgId]
    );
    return { keys: r.rows };
  });

  // Create key (owner only)
  app.post("/api/v1/orgs/:orgId/api-keys", async (req: any, reply) => {
    const p = auth(req, reply);
    if (!p) return;
    const { orgId } = req.params;
    if (!await checkOrgOwner(orgId, p.user_id)) {
      return reply.status(403).send({ error: "only org owner can create keys" });
    }
    const apiKey = "ak-" + randomBytes(24).toString("hex");  // ak- + 48 hex = 51 chars
    const apiKeyPrefix = apiKey.slice(0, 11); // "ak-XXXXXXXX"
    const name: string = (req.body as any)?.name || "default";
    const r = await pool.query(
      `INSERT INTO portal_api_keys (org_id, api_key, api_key_prefix, name)
       VALUES ($1, $2, $3, $4)
       RETURNING key_id, api_key_prefix, name, status, created_at`,
      [orgId, apiKey, apiKeyPrefix, name]
    );
    return { key: { ...r.rows[0], api_key: apiKey } };
  });

  // Revoke key (owner only)
  app.delete("/api/v1/orgs/:orgId/api-keys/:keyId", async (req: any, reply) => {
    const p = auth(req, reply);
    if (!p) return;
    const { orgId, keyId } = req.params;
    if (!await checkOrgOwner(orgId, p.user_id)) {
      return reply.status(403).send({ error: "only org owner can revoke keys" });
    }
    const r = await pool.query(
      "UPDATE portal_api_keys SET status='revoked' WHERE key_id=$1 AND org_id=$2 RETURNING key_id, status",
      [keyId, orgId]
    );
    if (r.rows.length === 0) return reply.status(404).send({ error: "key not found" });
    return { key: r.rows[0] };
  });

  // ==================== DELEGATION ====================

  // Delegation private key (RS256) for signing delegation JWTs to Gateway
  const fs = require("fs");
  const DELEGATION_PRIVATE_KEY = (() => {
    try { return fs.readFileSync("/app/delegation/private.pem", "utf8"); } catch {}
    try { return fs.readFileSync("./delegation/private.pem", "utf8"); } catch {}
    return process.env.DELEGATION_PRIVATE_KEY || "";
  })();

  // Get delegation token (JWT RS256, short-lived, for Gateway on 40.51)
  app.post("/api/v1/orgs/:orgId/delegate", async (req: any, reply) => {
    const p = auth(req, reply);
    if (!p) return;
    const { orgId } = req.params;
    const { api_key }: any = req.body;
    if (!api_key) return reply.status(400).send({ error: "api_key is required" });

    // Validate API key belongs to org and is active
    const k = await pool.query(
      "SELECT key_id FROM portal_api_keys WHERE org_id=$1 AND api_key=$2 AND status='active'",
      [orgId, api_key]
    );
    if (k.rows.length === 0) {
      return reply.status(403).send({ error: "invalid or revoked api key" });
    }

    // Check user is member of org
    const m = await pool.query(
      "SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'",
      [orgId, p.user_id]
    );
    if (m.rows.length === 0) {
      return reply.status(403).send({ error: "not a member of this org" });
    }

    // Update last_used_at
    await pool.query("UPDATE portal_api_keys SET last_used_at=now() WHERE key_id=$1", [k.rows[0].key_id]);

    // Generate delegation JWT (RS256, 5 min)
    const delegationToken = jwt.sign(
      { org_id: orgId, key_id: k.rows[0].key_id, user_id: p.user_id },
      DELEGATION_PRIVATE_KEY,
      { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" }
    );

    return { delegation_token: delegationToken, expires_in: 300 };
  });

  await app.listen({ port: PORT, host: "0.0.0.0" });
  console.log("Portal BFF v0.4.0 on :" + PORT);
}
main().catch((e) => { console.error(e); process.exit(1); });
