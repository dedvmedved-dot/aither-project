"use strict";
// ═══════════════════════════════════════════════════════════════
// Aither External API Gateway
// ═══════════════════════════════════════════════════════════════
// OpenAI-compatible API for external clients.
// Auth: API key (Bearer ak-...), not JWT cookies.
// Rate limiting: per-org, via Gateway.
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerApiGateway = registerApiGateway;
const crypto_1 = __importDefault(require("crypto"));
const server_1 = require("./server");
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
async function authApiKey(req, reply, pool) {
    const ah = (req.headers.authorization || "").trim();
    if (!ah.startsWith("Bearer ")) {
        reply.status(401).send({ error: { message: "Missing API key. Use: Authorization: Bearer ak-...", type: "invalid_request_error", code: 401 } });
        return null;
    }
    const apiKey = ah.slice(7);
    if (!apiKey.startsWith("ak-")) {
        reply.status(401).send({ error: { message: "Invalid API key format", type: "authentication_error", code: 401 } });
        return null;
    }
    const r = await pool.query("SELECT key_id, org_id, name, status FROM portal_api_keys WHERE api_key=$1 AND status='active'", [apiKey]);
    if (r.rows.length === 0) {
        reply.status(401).send({ error: { message: "Invalid or revoked API key", type: "authentication_error", code: 401 } });
        return null;
    }
    const k = r.rows[0];
    // Update last_used_at
    await pool.query("UPDATE portal_api_keys SET last_used_at=now() WHERE key_id=$1", [k.key_id]);
    return { org_id: k.org_id, key_id: k.key_id, name: k.name, api_key: apiKey };
}
// ── Routes ────────────────────────────────────────────────────
function registerApiGateway(app, pool) {
    // GET /api/v1/models — public model list (no auth required for discovery)
    app.get("/api/v1/models", async (_r, reply) => {
        return reply.send({
            object: "list",
            data: Object.entries(MODEL_MAP).map(([id, m]) => ({
                id,
                object: "model",
                owned_by: "aither",
                display_name: m.display_name,
                description: m.description,
                max_tokens: id.endsWith("32b") ? 8192 : 4096,
            })),
        });
    });
    // POST /api/v1/chat/completions — OpenAI-compatible, API key required
    app.post("/api/v1/chat/completions", async (req, reply) => {
        const key = await authApiKey(req, reply, pool);
        if (!key)
            return;
        const { model, messages, max_tokens, temperature, stream } = req.body || {};
        if (!model) {
            return reply.status(400).send({ error: { message: "model is required", type: "invalid_request_error", code: 400 } });
        }
        if (!messages || !Array.isArray(messages) || messages.length === 0) {
            return reply.status(400).send({ error: { message: "messages array is required", type: "invalid_request_error", code: 400 } });
        }
        const modelInfo = MODEL_MAP[model];
        if (!modelInfo) {
            return reply.status(400).send({ error: { message: `Unknown model: ${model}`, type: "invalid_request_error", code: 400 } });
        }
        const payload = {
            model: modelInfo.vllm_path,
            messages,
            max_tokens: max_tokens || 2048,
            temperature: temperature ?? 0.7,
            stream: stream !== false, // default: stream
        };
        try {
            // Proxy to Gateway (with mTLS) — Gateway handles API key auth + billing
            const resp = await (0, server_1.gatewayFetch)("/v1/chat/completions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + key.api_key,
                    "X-Org-Id": key.org_id,
                    "X-Api-Key-Id": key.key_id,
                },
                body: JSON.stringify(payload),
            });
            if (!resp.ok) {
                const errBody = await resp.text().catch(() => "");
                return reply.status(resp.status).send({ error: { message: `Gateway error: ${resp.status}`, type: "api_error", code: resp.status } });
            }
            if (payload.stream && resp.body) {
                // SSE stream passthrough
                reply.raw.writeHead(200, {
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-Id": crypto_1.default.randomUUID(),
                });
                const reader = resp.body.getReader();
                const encoder = new TextEncoder();
                const decoder = new TextDecoder();
                try {
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) {
                            reply.raw.end();
                            break;
                        }
                        reply.raw.write(value);
                    }
                }
                catch (e) {
                    reply.raw.end();
                }
                return;
            }
            // Non-streaming response
            const data = await resp.json();
            return reply.send({
                id: "chatcmpl-" + crypto_1.default.randomUUID().slice(0, 8),
                object: "chat.completion",
                created: Math.floor(Date.now() / 1000),
                model,
                choices: [{
                        index: 0,
                        message: { role: "assistant", content: data.choices?.[0]?.message?.content || "" },
                        finish_reason: "stop",
                    }],
                usage: data.usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
            });
        }
        catch (err) {
            return reply.status(502).send({ error: { message: "Gateway unavailable", type: "api_error", code: 502 } });
        }
    });
    // GET /api/v1/health — public
    app.get("/api/v1/health", async (_r, reply) => {
        return { status: "ok", service: "aither-api", version: "1.0" };
    });
}
