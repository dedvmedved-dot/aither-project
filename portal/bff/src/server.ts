import Fastify from "fastify";
import cors from "@fastify/cors";
import { Pool } from "pg";

const PORT = parseInt(process.env.PORT || "3000", 10);
const DATABASE_URL = process.env.DATABASE_URL || "postgres://portal:portal-secret@localhost:5432/portal";
const CORE_API_URL = process.env.CORE_API_URL || "http://10.129.13.78:30900/v1";
const CORE_API_TOKEN = process.env.CORE_API_TOKEN || "dev-delegation-token";

const pool = new Pool({ connectionString: DATABASE_URL });

const app = Fastify({ logger: true });

async function start() {
  await app.register(cors, { origin: true });

  // Health check
  app.get("/health", async () => {
    let dbOk = false;
    try {
      await pool.query("SELECT 1");
      dbOk = true;
    } catch {}
    return {
      status: "ok",
      service: "portal-bff",
      database: dbOk ? "connected" : "error",
      core_api: CORE_API_URL,
    };
  });

  // API v1 status
  app.get("/api/v1/status", async () => {
    let orgsCount = 0;
    let usersCount = 0;
    try {
      const o = await pool.query("SELECT count(*) FROM portal_organizations");
      orgsCount = parseInt(o.rows[0].count, 10);
      const u = await pool.query("SELECT count(*) FROM portal_users");
      usersCount = parseInt(u.rows[0].count, 10);
    } catch {}
    return {
      version: "0.1.0",
      orgs: orgsCount,
      users: usersCount,
    };
  });

  // Proxy to Core API (delegation)
  app.get("/api/v1/core/status", async (_req, reply) => {
    try {
      const res = await fetch(`${CORE_API_URL}/health`, {
        headers: { Authorization: `Bearer ${CORE_API_TOKEN}` },
      });
      const data = await res.json();
      return reply.send(data);
    } catch (e: any) {
      return reply.status(502).send({ error: "core_unreachable", detail: e.message });
    }
  });

  // List orgs
  app.get("/api/v1/orgs", async (_req, reply) => {
    try {
      const r = await pool.query(
        "SELECT org_id, name, aither_org_id, status, created_at FROM portal_organizations ORDER BY created_at DESC"
      );
      return reply.send({ orgs: r.rows });
    } catch (e: any) {
      return reply.status(500).send({ error: e.message });
    }
  });

  // List users
  app.get("/api/v1/users", async (_req, reply) => {
    try {
      const r = await pool.query(
        "SELECT user_id, display_name, email, oauth_provider, created_at FROM portal_users ORDER BY created_at DESC"
      );
      return reply.send({ users: r.rows });
    } catch (e: any) {
      return reply.status(500).send({ error: e.message });
    }
  });

  await app.listen({ port: PORT, host: "0.0.0.0" });
  console.log(`Portal BFF listening on :${PORT}`);
}

start().catch((err) => {
  console.error(err);
  process.exit(1);
});
