import Fastify from "fastify";
import cors from "@fastify/cors";
import jwt from "jsonwebtoken";
import { Pool } from "pg";

const PORT = 3000;
const pgHost = "127.0.0.1";
const pgPort = 5432;
const pgUser = "portal";
const pgDb = "portal";
const DB_URL = "postgres://" + pgUser + "@" + pgHost + ":" + String(pgPort) + "/" + pgDb;
const CORE_API = "http://10.129.13.78:30900/v1";
const JWT_SEC = process.env.JWT_SECRET || (() => { throw new Error("JWT_SECRET environment variable is required. See portal/.env.example"); })();

function signToken(uid: string): string {
  return jwt.sign({ user_id: uid }, JWT_SEC, { expiresIn: "7d" });
}
function verifyToken(tok: string): any {
  try { return jwt.verify(tok, JWT_SEC); } catch { return null; }
}

const pool = new Pool({ connectionString: DB_URL });
const app = Fastify({ logger: true });

async function main() {
  await app.register(cors, { origin: true });

  // Health
  app.get("/health", async () => {
    let ok = false;
    try { await pool.query("SELECT 1"); ok = true; } catch {}
    return { status: "ok", service: "portal-bff", database: ok ? "connected" : "error" };
  });

  // Dev login
  app.post("/auth/dev/login", async (req: any, reply: any) => {
    const { name, email, oauthId: _oid } = req.body || {};
    if (!name) return reply.status(400).send({ error: "name required" });
    const oid = _oid || "dev-" + name;
    const ue = (email && email.includes("@")) ? email : name + "@dev.local";

    let user = await pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["dev", oid]);
    let userId: string;
    if (user.rows.length === 0) {
      const ins = await pool.query(
        "INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, last_login_at) VALUES ($1,$2,$3,$4,now()) RETURNING user_id",
        ["dev", oid, ue, name]
      );
      userId = ins.rows[0].user_id;
    } else {
      userId = user.rows[0].user_id;
      await pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [userId]);
    }
    const tok = signToken(userId);
    return { access_token: tok, user: { user_id: userId, login: name, email: ue } };
  });

  // Me
  app.get("/api/v1/me", async (req: any, reply: any) => {
    const ah = req.headers.authorization || "";
    if (!ah.startsWith("Bearer ")) return reply.status(401).send({ error: "unauthorized" });
    const p = verifyToken(ah.slice(7));
    if (!p) return reply.status(401).send({ error: "invalid_token" });
    const r = await pool.query("SELECT user_id, display_name, email, avatar_url, oauth_provider, created_at FROM portal_users WHERE user_id=$1", [p.user_id]);
    if (r.rows.length === 0) return reply.status(404).send({ error: "user not found" });
    return { user: r.rows[0] };
  });

  // Status
  app.get("/api/v1/status", async () => {
    const o = await pool.query("SELECT count(*) FROM portal_organizations");
    const u = await pool.query("SELECT count(*) FROM portal_users");
    return { version: "0.2.0", orgs: Number(o.rows[0].count), users: Number(u.rows[0].count) };
  });

  // Core proxy
  app.get("/api/v1/core/status", async (_r: any, reply: any) => {
    try {
      const r = await fetch(CORE_API + "/health");
      return reply.send(await r.json());
    } catch (e: any) {
      return reply.status(502).send({ error: "core_unreachable", detail: e.message });
    }
  });

  // Orgs
  app.get("/api/v1/orgs", async (req: any, reply: any) => {
    const ah = req.headers.authorization || "";
    if (!ah.startsWith("Bearer ")) return reply.status(401).send({ error: "unauthorized" });
    const p = verifyToken(ah.slice(7));
    if (!p) return reply.status(401).send({ error: "invalid_token" });
    const r = await pool.query(
      "SELECT o.org_id, o.name, o.status, o.created_at FROM portal_organizations o JOIN portal_org_members m ON o.org_id=m.org_id WHERE m.user_id=$1 ORDER BY o.created_at DESC",
      [p.user_id]
    );
    return { orgs: r.rows };
  });

  // Users
  app.get("/api/v1/users", async () => {
    const r = await pool.query("SELECT user_id, display_name, email, oauth_provider, created_at FROM portal_users ORDER BY created_at DESC");
    return { users: r.rows };
  });

  await app.listen({ port: PORT, host: "0.0.0.0" });
  console.log("Portal BFF v0.2.0 on :" + PORT);
}

main().catch(e => { console.error(e); process.exit(1); });
