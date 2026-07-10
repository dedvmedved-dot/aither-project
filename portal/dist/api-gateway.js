"use strict";
// ═══════════════════════════════════════════════════════════════
// Aither External API Gateway
// ═══════════════════════════════════════════════════════════════
// OpenAI-compatible API for external clients.
// Auth: API key (Bearer ak-...), not JWT cookies.
// Rate limiting: per-org, via Gateway.
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __read = (this && this.__read) || function (o, n) {
    var m = typeof Symbol === "function" && o[Symbol.iterator];
    if (!m) return o;
    var i = m.call(o), r, ar = [], e;
    try {
        while ((n === void 0 || n-- > 0) && !(r = i.next()).done) ar.push(r.value);
    }
    catch (error) { e = { error: error }; }
    finally {
        try {
            if (r && !r.done && (m = i["return"])) m.call(i);
        }
        finally { if (e) throw e.error; }
    }
    return ar;
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerApiGateway = registerApiGateway;
var crypto_1 = __importDefault(require("crypto"));
var MODEL_MAP = {
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
function authApiKey(req, reply, pool) {
    return __awaiter(this, void 0, void 0, function () {
        var ah, apiKey, r, k;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    ah = (req.headers.authorization || "").trim();
                    if (!ah.startsWith("Bearer ")) {
                        reply.status(401).send({ error: { message: "Missing API key. Use: Authorization: Bearer ak-...", type: "invalid_request_error", code: 401 } });
                        return [2 /*return*/, null];
                    }
                    apiKey = ah.slice(7);
                    if (!apiKey.startsWith("ak-")) {
                        reply.status(401).send({ error: { message: "Invalid API key format", type: "authentication_error", code: 401 } });
                        return [2 /*return*/, null];
                    }
                    return [4 /*yield*/, pool.query("SELECT key_id, org_id, name, status FROM portal_api_keys WHERE api_key=$1 AND status='active'", [apiKey])];
                case 1:
                    r = _a.sent();
                    if (r.rows.length === 0) {
                        reply.status(401).send({ error: { message: "Invalid or revoked API key", type: "authentication_error", code: 401 } });
                        return [2 /*return*/, null];
                    }
                    k = r.rows[0];
                    // Update last_used_at
                    return [4 /*yield*/, pool.query("UPDATE portal_api_keys SET last_used_at=now() WHERE key_id=$1", [k.key_id])];
                case 2:
                    // Update last_used_at
                    _a.sent();
                    return [2 /*return*/, { org_id: k.org_id, key_id: k.key_id, name: k.name, api_key: apiKey }];
            }
        });
    });
}
// ── Routes ────────────────────────────────────────────────────
function registerApiGateway(app, pool, CORE_API) {
    var _this = this;
    // GET /api/v1/models — public model list (no auth required for discovery)
    app.get("/api/v1/models", function (_r, reply) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            return [2 /*return*/, reply.send({
                    object: "list",
                    data: Object.entries(MODEL_MAP).map(function (_a) {
                        var _b = __read(_a, 2), id = _b[0], m = _b[1];
                        return ({
                            id: id,
                            object: "model",
                            owned_by: "aither",
                            display_name: m.display_name,
                            description: m.description,
                            max_tokens: id.endsWith("32b") ? 8192 : 4096,
                        });
                    }),
                })];
        });
    }); });
    // POST /api/v1/chat/completions — OpenAI-compatible, API key required
    app.post("/api/v1/chat/completions", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
        var key, _a, model, messages, max_tokens, temperature, stream, modelInfo, payload, resp, errBody, reader, encoder, decoder, _b, done, value, e_1, data, err_1;
        var _c, _d, _e;
        return __generator(this, function (_f) {
            switch (_f.label) {
                case 0: return [4 /*yield*/, authApiKey(req, reply, pool)];
                case 1:
                    key = _f.sent();
                    if (!key)
                        return [2 /*return*/];
                    _a = req.body || {}, model = _a.model, messages = _a.messages, max_tokens = _a.max_tokens, temperature = _a.temperature, stream = _a.stream;
                    if (!model) {
                        return [2 /*return*/, reply.status(400).send({ error: { message: "model is required", type: "invalid_request_error", code: 400 } })];
                    }
                    if (!messages || !Array.isArray(messages) || messages.length === 0) {
                        return [2 /*return*/, reply.status(400).send({ error: { message: "messages array is required", type: "invalid_request_error", code: 400 } })];
                    }
                    modelInfo = MODEL_MAP[model];
                    if (!modelInfo) {
                        return [2 /*return*/, reply.status(400).send({ error: { message: "Unknown model: ".concat(model), type: "invalid_request_error", code: 400 } })];
                    }
                    payload = {
                        model: modelInfo.vllm_path,
                        messages: messages,
                        max_tokens: max_tokens || 2048,
                        temperature: temperature !== null && temperature !== void 0 ? temperature : 0.7,
                        stream: stream !== false, // default: stream
                    };
                    _f.label = 2;
                case 2:
                    _f.trys.push([2, 14, , 15]);
                    return [4 /*yield*/, fetch(CORE_API + "/v1/chat/completions", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                "Authorization": "Bearer " + key.api_key,
                                "X-Org-Id": key.org_id,
                                "X-Api-Key-Id": key.key_id,
                            },
                            body: JSON.stringify(payload),
                        })];
                case 3:
                    resp = _f.sent();
                    if (!!resp.ok) return [3 /*break*/, 5];
                    return [4 /*yield*/, resp.text().catch(function () { return ""; })];
                case 4:
                    errBody = _f.sent();
                    return [2 /*return*/, reply.status(resp.status).send({ error: { message: "Gateway error: ".concat(resp.status), type: "api_error", code: resp.status } })];
                case 5:
                    if (!(payload.stream && resp.body)) return [3 /*break*/, 12];
                    // SSE stream passthrough
                    reply.raw.writeHead(200, {
                        "Content-Type": "text/event-stream",
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Request-Id": crypto_1.default.randomUUID(),
                    });
                    reader = resp.body.getReader();
                    encoder = new TextEncoder();
                    decoder = new TextDecoder();
                    _f.label = 6;
                case 6:
                    _f.trys.push([6, 10, , 11]);
                    _f.label = 7;
                case 7:
                    if (!true) return [3 /*break*/, 9];
                    return [4 /*yield*/, reader.read()];
                case 8:
                    _b = _f.sent(), done = _b.done, value = _b.value;
                    if (done) {
                        reply.raw.end();
                        return [3 /*break*/, 9];
                    }
                    reply.raw.write(value);
                    return [3 /*break*/, 7];
                case 9: return [3 /*break*/, 11];
                case 10:
                    e_1 = _f.sent();
                    reply.raw.end();
                    return [3 /*break*/, 11];
                case 11: return [2 /*return*/];
                case 12: return [4 /*yield*/, resp.json()];
                case 13:
                    data = _f.sent();
                    return [2 /*return*/, reply.send({
                            id: "chatcmpl-" + crypto_1.default.randomUUID().slice(0, 8),
                            object: "chat.completion",
                            created: Math.floor(Date.now() / 1000),
                            model: model,
                            choices: [{
                                    index: 0,
                                    message: { role: "assistant", content: ((_e = (_d = (_c = data.choices) === null || _c === void 0 ? void 0 : _c[0]) === null || _d === void 0 ? void 0 : _d.message) === null || _e === void 0 ? void 0 : _e.content) || "" },
                                    finish_reason: "stop",
                                }],
                            usage: data.usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
                        })];
                case 14:
                    err_1 = _f.sent();
                    return [2 /*return*/, reply.status(502).send({ error: { message: "Gateway unavailable", type: "api_error", code: 502 } })];
                case 15: return [2 /*return*/];
            }
        });
    }); });
    // GET /api/v1/health — public
    app.get("/api/v1/health", function (_r, reply) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            return [2 /*return*/, { status: "ok", service: "aither-api", version: "1.0" }];
        });
    }); });
}
