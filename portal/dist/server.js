"use strict";
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
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
var __values = (this && this.__values) || function(o) {
    var s = typeof Symbol === "function" && Symbol.iterator, m = s && o[s], i = 0;
    if (m) return m.call(o);
    if (o && typeof o.length === "number") return {
        next: function () {
            if (o && i >= o.length) o = void 0;
            return { value: o && o[i++], done: !o };
        }
    };
    throw new TypeError(s ? "Object is not iterable." : "Symbol.iterator is not defined.");
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
require("dotenv/config");
var fastify_1 = __importDefault(require("fastify"));
var cors_1 = __importDefault(require("@fastify/cors"));
var rate_limit_1 = __importDefault(require("@fastify/rate-limit"));
var jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
var pg_1 = require("pg");
var crypto_1 = require("crypto");
var ldap_1 = require("./ldap");
var policies_1 = require("./policies");
var api_gateway_1 = require("./api-gateway");
var PORT = 3000;
var JWT_SECRET = process.env.JWT_SECRET || (function () { throw new Error("JWT_SECRET env required"); })();
var CORE_API = process.env.CORE_API || "http://gateway:8080";
var IS_PRODUCTION = process.env.NODE_ENV === "production";
var PUBLIC_HOST = process.env.PUBLIC_HOST || "localhost";
var CORS_ORIGIN = process.env.CORS_ORIGIN || (IS_PRODUCTION ? "https://".concat(PUBLIC_HOST) : "http://".concat(PUBLIC_HOST));
var pool = new pg_1.Pool({
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
    catch (_a) {
        return null;
    }
}
function auth(req, reply) {
    var ah = req.headers.authorization || "";
    if (!ah.startsWith("Bearer ")) {
        reply.status(401).send({ error: "unauthorized" });
        return null;
    }
    var p = verifyToken(ah.slice(7));
    if (!p) {
        reply.status(401).send({ error: "invalid_token" });
        return null;
    }
    return p;
}
function checkOrgOwner(orgId, userId) {
    return __awaiter(this, void 0, void 0, function () {
        var r;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, pool.query("SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND role='owner'", [orgId, userId])];
                case 1:
                    r = _a.sent();
                    return [2 /*return*/, r.rows.length > 0];
            }
        });
    });
}
var STARTER_TOKENS = 100000; // 100K токенов новому пользователю
var REFILL_TOKENS = 100000; // авто-пополнение при обнулении
var REFILL_LIMIT = 10; // максимум авто-пополнений (защита от бесконечного цикла)
/** Создаёт личный org для нового пользователя и начисляет стартовые токены */
function ensurePersonalOrg(userId) {
    return __awaiter(this, void 0, void 0, function () {
        var exist, org, orgId;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, pool.query("SELECT o.org_id FROM portal_organizations o\n     JOIN portal_org_members m ON o.org_id=m.org_id\n     WHERE m.user_id=$1 AND o.name='\u041B\u0438\u0447\u043D\u044B\u0439'", [userId])];
                case 1:
                    exist = _a.sent();
                    if (exist.rows.length > 0)
                        return [2 /*return*/, exist.rows[0].org_id];
                    return [4 /*yield*/, pool.query("INSERT INTO portal_organizations (name) VALUES ('Личный') RETURNING org_id")];
                case 2:
                    org = _a.sent();
                    orgId = org.rows[0].org_id;
                    return [4 /*yield*/, pool.query("INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1,$2,'owner')", [orgId, userId])];
                case 3:
                    _a.sent();
                    return [4 /*yield*/, pool.query("INSERT INTO billing_accounts (org_id, reserved, total_tokens, meta)\n     VALUES ($1,0,$2,'{}'::jsonb)\n     ON CONFLICT (org_id) DO NOTHING", [orgId, STARTER_TOKENS])];
                case 4:
                    _a.sent();
                    console.log("[auto-balance] new user ".concat(userId, ": personal org ").concat(orgId, " + ").concat(STARTER_TOKENS, " tokens"));
                    return [2 /*return*/, orgId];
            }
        });
    });
}
function hashPassword(password) {
    // scrypt: 64-bit salt + 64-byte hash, base64-encoded
    var salt = (0, crypto_1.randomBytes)(16).toString("hex");
    var hash = (0, crypto_1.scryptSync)(password, salt, 64).toString("hex");
    return "".concat(salt, ":").concat(hash);
}
function verifyPassword(password, stored) {
    var _a = __read(stored.split(":"), 2), salt = _a[0], hash = _a[1];
    if (!salt || !hash)
        return false;
    var derived = (0, crypto_1.scryptSync)(password, salt, 64).toString("hex");
    return (0, crypto_1.timingSafeEqual)(Buffer.from(hash), Buffer.from(derived));
}
function safeError(e) {
    return IS_PRODUCTION ? "internal_error" : e.message || String(e);
}
function safeJsonParse(s) {
    if (!s)
        return null;
    if (typeof s === "object")
        return s;
    try {
        return JSON.parse(s);
    }
    catch (_a) {
        return null;
    }
}
/** In-memory OAuth state store — avoids cookie issues */
var oauthStates = new Map();
// Cleanup expired states every 5 minutes
setInterval(function () {
    var e_1, _a;
    var now = Date.now();
    try {
        for (var oauthStates_1 = __values(oauthStates), oauthStates_1_1 = oauthStates_1.next(); !oauthStates_1_1.done; oauthStates_1_1 = oauthStates_1.next()) {
            var _b = __read(oauthStates_1_1.value, 2), k = _b[0], v = _b[1];
            if (v.expires < now)
                oauthStates.delete(k);
        }
    }
    catch (e_1_1) { e_1 = { error: e_1_1 }; }
    finally {
        try {
            if (oauthStates_1_1 && !oauthStates_1_1.done && (_a = oauthStates_1.return)) _a.call(oauthStates_1);
        }
        finally { if (e_1) throw e_1.error; }
    }
}, 300000);
/** Store OAuth state in memory, return state value */
function setOAuthState(_reply, prefix) {
    var state = (0, crypto_1.randomBytes)(16).toString("hex");
    oauthStates.set(state, { prefix: prefix, expires: Date.now() + 600000 });
    return state;
}
/** Validate OAuth state from memory. Returns true if valid. */
function validateOAuthState(req, _reply, prefix) {
    var _a;
    var queryState = ((_a = req.query) === null || _a === void 0 ? void 0 : _a.state) || "";
    if (!queryState)
        return false;
    var entry = oauthStates.get(queryState);
    if (!entry)
        return false;
    oauthStates.delete(queryState);
    return entry.prefix === prefix && entry.expires > Date.now();
}
function main() {
    return __awaiter(this, void 0, void 0, function () {
        // ==================== CHATS ====================
        /** Check if chat is enabled for any org the user belongs to. Returns true if enabled. */
        function checkChatEnabled(userId, reply) {
            return __awaiter(this, void 0, void 0, function () {
                var orgs, policy;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4 /*yield*/, pool.query("SELECT o.org_id FROM portal_organizations o\n       JOIN portal_org_members m ON o.org_id = m.org_id\n       WHERE m.user_id = $1 AND m.status = 'active'\n       LIMIT 1", [userId])];
                        case 1:
                            orgs = _a.sent();
                            if (orgs.rows.length === 0) {
                                reply.status(403).send({ error: "chat_disabled", detail: "no active organization" });
                                return [2 /*return*/, false];
                            }
                            return [4 /*yield*/, (0, policies_1.loadPolicy)(pool, orgs.rows[0].org_id)];
                        case 2:
                            policy = _a.sent();
                            if (!policy.chat_enabled) {
                                reply.status(403).send({ error: "chat_disabled", detail: "чат отключён в настройках безопасности организации" });
                                return [2 /*return*/, false];
                            }
                            return [2 /*return*/, true];
                    }
                });
            });
        }
        // Get org's active API key (for delegation in chat)
        function getOrgApiKey(orgId) {
            return __awaiter(this, void 0, void 0, function () {
                var r;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4 /*yield*/, pool.query("SELECT api_key FROM portal_api_keys WHERE org_id=$1 AND status='active' ORDER BY created_at ASC LIMIT 1", [orgId])];
                        case 1:
                            r = _a.sent();
                            return [2 /*return*/, r.rows.length > 0 ? r.rows[0].api_key : null];
                    }
                });
            });
        }
        // Get delegation token for org (auto-creates API key if needed)
        function getDelegationToken(orgId, userId) {
            return __awaiter(this, void 0, void 0, function () {
                var apiKey, apiKeyPrefix;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4 /*yield*/, getOrgApiKey(orgId)];
                        case 1:
                            apiKey = _a.sent();
                            if (!!apiKey) return [3 /*break*/, 3];
                            // Auto-create first API key for org
                            apiKey = "ak-" + (0, crypto_1.randomBytes)(24).toString("hex");
                            apiKeyPrefix = apiKey.slice(0, 11);
                            return [4 /*yield*/, pool.query("INSERT INTO portal_api_keys (org_id, api_key, api_key_prefix, name) VALUES ($1,$2,$3,'auto')", [orgId, apiKey, apiKeyPrefix])];
                        case 2:
                            _a.sent();
                            _a.label = 3;
                        case 3: return [2 /*return*/, jsonwebtoken_1.default.sign({ org_id: orgId, key_id: "chat", user_id: userId }, DELEGATION_PRIVATE_KEY, { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" })];
                    }
                });
            });
        }
        var app, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, YANDEX_CLIENT_ID, YANDEX_CLIENT_SECRET, MODEL_MAP, fs, DELEGATION_PRIVATE_KEY, YOOKASSA_SHOP_ID, YOOKASSA_SECRET, TOKENS_PER_RUBLE, ADMIN_KEY, listenHost;
        var _this = this;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    app = (0, fastify_1.default)({ logger: false });
                    return [4 /*yield*/, app.register(cors_1.default, { origin: CORS_ORIGIN, credentials: true })];
                case 1:
                    _a.sent();
                    // Rate limiting: 100 req/min per IP
                    return [4 /*yield*/, app.register(rate_limit_1.default, { max: 100, timeWindow: "1 minute" })];
                case 2:
                    // Rate limiting: 100 req/min per IP
                    _a.sent();
                    // DDL
                    return [4 /*yield*/, pool.query("\n    CREATE TABLE IF NOT EXISTS portal_users (\n      user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n      oauth_provider text NOT NULL DEFAULT 'github',\n      oauth_id text NOT NULL,\n      email text,\n      password_hash text,\n      display_name text,\n      avatar_url text,\n      created_at timestamptz NOT NULL DEFAULT now(),\n      last_login_at timestamptz,\n      UNIQUE(oauth_provider, oauth_id)\n    );\n    CREATE TABLE IF NOT EXISTS portal_organizations (\n      org_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n      name text NOT NULL,\n      aither_org_id uuid,\n      status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','deleted')),\n      created_at timestamptz NOT NULL DEFAULT now(),\n      updated_at timestamptz NOT NULL DEFAULT now()\n    );\n    CREATE TABLE IF NOT EXISTS portal_org_members (\n      membership_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n      org_id uuid NOT NULL REFERENCES portal_organizations(org_id),\n      user_id uuid NOT NULL REFERENCES portal_users(user_id),\n      role text NOT NULL DEFAULT 'developer' CHECK (role IN ('owner','billing_admin','developer','viewer')),\n      status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),\n      created_at timestamptz NOT NULL DEFAULT now(),\n      UNIQUE(org_id, user_id)\n    );\n    CREATE TABLE IF NOT EXISTS portal_api_keys (\n      key_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n      org_id uuid REFERENCES portal_organizations(org_id),\n      api_key text NOT NULL UNIQUE,\n      api_key_prefix text NOT NULL,\n      name text NOT NULL DEFAULT 'default',\n      status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),\n      created_at timestamptz NOT NULL DEFAULT now(),\n      expires_at timestamptz,\n      last_used_at timestamptz\n    );\n    CREATE TABLE IF NOT EXISTS chats (\n      chat_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n      user_id uuid NOT NULL REFERENCES portal_users(user_id),\n      title text NOT NULL DEFAULT '\u041D\u043E\u0432\u044B\u0439 \u0447\u0430\u0442',\n      model text NOT NULL DEFAULT 'qwen2.5-14b',\n      share_token text UNIQUE,\n      created_at timestamptz NOT NULL DEFAULT now(),\n      updated_at timestamptz NOT NULL DEFAULT now()\n    );\n    CREATE TABLE IF NOT EXISTS chat_messages (\n      message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n      chat_id uuid NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,\n      role text NOT NULL CHECK (role IN ('user','assistant','system')),\n      content text NOT NULL DEFAULT '',\n      tokens_used int NOT NULL DEFAULT 0,\n      created_at timestamptz NOT NULL DEFAULT now()\n    );\n    CREATE TABLE IF NOT EXISTS payment_transactions (\n      txn_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n      org_id uuid REFERENCES portal_organizations(org_id),\n      user_id uuid REFERENCES portal_users(user_id),\n      provider text NOT NULL DEFAULT 'yookassa',\n      provider_payment_id text,\n      amount_rub numeric(12,2) NOT NULL,\n      tokens int NOT NULL DEFAULT 0,\n      status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','succeeded','canceled')),\n      meta jsonb DEFAULT '{}',\n      created_at timestamptz NOT NULL DEFAULT now(),\n      updated_at timestamptz NOT NULL DEFAULT now()\n    );\n    CREATE TABLE IF NOT EXISTS billing_accounts (\n      org_id uuid PRIMARY KEY REFERENCES portal_organizations(org_id),\n      reserved bigint NOT NULL DEFAULT 0,\n      total_tokens bigint NOT NULL DEFAULT 0\n    );\n  ")];
                case 3:
                    // DDL
                    _a.sent();
                    return [4 /*yield*/, pool.query(policies_1.POLICIES_DDL)];
                case 4:
                    _a.sent();
                    GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || "";
                    GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET || "";
                    app.get("/auth/github", function (_req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var state, params;
                        return __generator(this, function (_a) {
                            if (!GITHUB_CLIENT_ID)
                                return [2 /*return*/, reply.status(500).send({ error: "GitHub OAuth not configured" })];
                            state = setOAuthState(reply, "github");
                            params = new URLSearchParams({
                                client_id: GITHUB_CLIENT_ID,
                                redirect_uri: process.env.GITHUB_REDIRECT_URI || "http://".concat(process.env.PUBLIC_HOST || "localhost", "/auth/github/callback"),
                                scope: "read:user user:email",
                                state: state,
                            });
                            return [2 /*return*/, reply.redirect("https://github.com/login/oauth/authorize?".concat(params))];
                        });
                    }); });
                    app.get("/auth/github/callback", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var _a, code, state, tokenRes, tokenData, accessToken, _b, userRes, emailsRes, ghUser, emails, primaryEmail, oauthId, displayName, avatarUrl, user, userId, ins, tok, redirectHost, e_2;
                        var _c, _d;
                        return __generator(this, function (_e) {
                            switch (_e.label) {
                                case 0:
                                    if (!GITHUB_CLIENT_ID || !GITHUB_CLIENT_SECRET)
                                        return [2 /*return*/, reply.status(500).send({ error: "GitHub OAuth not configured" })];
                                    _a = req.query, code = _a.code, state = _a.state;
                                    if (!code)
                                        return [2 /*return*/, reply.status(400).send({ error: "missing code" })];
                                    if (!validateOAuthState(req, reply, "github"))
                                        return [2 /*return*/, reply.status(403).send({ error: "invalid_state" })];
                                    _e.label = 1;
                                case 1:
                                    _e.trys.push([1, 13, , 14]);
                                    return [4 /*yield*/, fetch("https://github.com/login/oauth/access_token", {
                                            method: "POST",
                                            headers: { "Accept": "application/json", "Content-Type": "application/json" },
                                            body: JSON.stringify({
                                                client_id: GITHUB_CLIENT_ID,
                                                client_secret: GITHUB_CLIENT_SECRET,
                                                code: code,
                                                redirect_uri: process.env.GITHUB_REDIRECT_URI || "http://".concat(process.env.PUBLIC_HOST || "localhost", "/auth/github/callback"),
                                            }),
                                        })];
                                case 2:
                                    tokenRes = _e.sent();
                                    return [4 /*yield*/, tokenRes.json()];
                                case 3:
                                    tokenData = _e.sent();
                                    if (tokenData.error)
                                        return [2 /*return*/, reply.status(403).send({ error: tokenData.error_description || tokenData.error })];
                                    accessToken = tokenData.access_token;
                                    return [4 /*yield*/, Promise.all([
                                            fetch("https://api.github.com/user", { headers: { Authorization: "Bearer ".concat(accessToken), "User-Agent": "aither-portal" } }),
                                            fetch("https://api.github.com/user/emails", { headers: { Authorization: "Bearer ".concat(accessToken), "User-Agent": "aither-portal" } }),
                                        ])];
                                case 4:
                                    _b = __read.apply(void 0, [_e.sent(), 2]), userRes = _b[0], emailsRes = _b[1];
                                    return [4 /*yield*/, userRes.json()];
                                case 5:
                                    ghUser = _e.sent();
                                    return [4 /*yield*/, emailsRes.json()];
                                case 6:
                                    emails = _e.sent();
                                    primaryEmail = ((_c = emails.find(function (e) { return e.primary; })) === null || _c === void 0 ? void 0 : _c.email) || ((_d = emails[0]) === null || _d === void 0 ? void 0 : _d.email) || "";
                                    oauthId = String(ghUser.id);
                                    displayName = ghUser.name || ghUser.login;
                                    avatarUrl = ghUser.avatar_url || "";
                                    return [4 /*yield*/, pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["github", oauthId])];
                                case 7:
                                    user = _e.sent();
                                    userId = void 0;
                                    if (!(user.rows.length === 0)) return [3 /*break*/, 10];
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, avatar_url, last_login_at)\n           VALUES ($1,$2,$3,$4,$5,now()) RETURNING user_id", ["github", oauthId, primaryEmail, displayName, avatarUrl])];
                                case 8:
                                    ins = _e.sent();
                                    userId = ins.rows[0].user_id;
                                    return [4 /*yield*/, ensurePersonalOrg(userId)];
                                case 9:
                                    _e.sent();
                                    return [3 /*break*/, 12];
                                case 10:
                                    userId = user.rows[0].user_id;
                                    return [4 /*yield*/, pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4", [primaryEmail, displayName, avatarUrl, userId])];
                                case 11:
                                    _e.sent();
                                    _e.label = 12;
                                case 12:
                                    tok = signToken(userId);
                                    redirectHost = process.env.PUBLIC_HOST || "localhost";
                                    return [2 /*return*/, reply.redirect("http://".concat(redirectHost, "/?aither_token=").concat(tok, "&user_id=").concat(userId, "&name=").concat(encodeURIComponent(displayName)))];
                                case 13:
                                    e_2 = _e.sent();
                                    return [2 /*return*/, reply.status(502).send({ error: "GitHub OAuth error: " + safeError(e_2) })];
                                case 14: return [2 /*return*/];
                            }
                        });
                    }); });
                    GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || "";
                    GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET || "";
                    app.get("/auth/google", function (_req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var state, redirectUri, params;
                        return __generator(this, function (_a) {
                            if (!GOOGLE_CLIENT_ID)
                                return [2 /*return*/, reply.status(500).send({ error: "Google OAuth not configured" })];
                            state = setOAuthState(reply, "google");
                            redirectUri = process.env.GOOGLE_REDIRECT_URI || "http://".concat(process.env.PUBLIC_HOST || "localhost", "/auth/google/callback");
                            params = new URLSearchParams({
                                client_id: GOOGLE_CLIENT_ID,
                                redirect_uri: redirectUri,
                                response_type: "code",
                                scope: "openid profile email",
                                state: state,
                            });
                            return [2 /*return*/, reply.redirect("https://accounts.google.com/o/oauth2/v2/auth?".concat(params))];
                        });
                    }); });
                    app.get("/auth/google/callback", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var code, redirectUri, tokenRes, tokenData, userRes, gu, oauthId, displayName, email, avatarUrl, user, userId, ins, tok, redirectHost, e_3;
                        var _a;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET)
                                        return [2 /*return*/, reply.status(500).send({ error: "Google OAuth not configured" })];
                                    code = req.query.code;
                                    if (!code)
                                        return [2 /*return*/, reply.status(400).send({ error: "missing code" })];
                                    if (!validateOAuthState(req, reply, "google"))
                                        return [2 /*return*/, reply.status(403).send({ error: "invalid_state" })];
                                    _b.label = 1;
                                case 1:
                                    _b.trys.push([1, 12, , 13]);
                                    redirectUri = process.env.GOOGLE_REDIRECT_URI || "http://".concat(process.env.PUBLIC_HOST || "localhost", "/auth/google/callback");
                                    return [4 /*yield*/, fetch("https://oauth2.googleapis.com/token", {
                                            method: "POST",
                                            headers: { "Content-Type": "application/x-www-form-urlencoded" },
                                            body: new URLSearchParams({
                                                client_id: GOOGLE_CLIENT_ID,
                                                client_secret: GOOGLE_CLIENT_SECRET,
                                                code: code,
                                                redirect_uri: redirectUri,
                                                grant_type: "authorization_code",
                                            }),
                                        })];
                                case 2:
                                    tokenRes = _b.sent();
                                    return [4 /*yield*/, tokenRes.json()];
                                case 3:
                                    tokenData = _b.sent();
                                    if (tokenData.error)
                                        return [2 /*return*/, reply.status(403).send({ error: tokenData.error_description || tokenData.error })];
                                    return [4 /*yield*/, fetch("https://openidconnect.googleapis.com/v1/userinfo", {
                                            headers: { Authorization: "Bearer ".concat(tokenData.access_token) },
                                        })];
                                case 4:
                                    userRes = _b.sent();
                                    return [4 /*yield*/, userRes.json()];
                                case 5:
                                    gu = _b.sent();
                                    oauthId = gu.sub;
                                    displayName = gu.name || ((_a = gu.email) === null || _a === void 0 ? void 0 : _a.split("@")[0]) || "";
                                    email = gu.email || "";
                                    avatarUrl = gu.picture || "";
                                    return [4 /*yield*/, pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["google", oauthId])];
                                case 6:
                                    user = _b.sent();
                                    userId = void 0;
                                    if (!(user.rows.length === 0)) return [3 /*break*/, 9];
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, avatar_url, last_login_at)\n           VALUES ($1,$2,$3,$4,$5,now()) RETURNING user_id", ["google", oauthId, email, displayName, avatarUrl])];
                                case 7:
                                    ins = _b.sent();
                                    userId = ins.rows[0].user_id;
                                    return [4 /*yield*/, ensurePersonalOrg(userId)];
                                case 8:
                                    _b.sent();
                                    return [3 /*break*/, 11];
                                case 9:
                                    userId = user.rows[0].user_id;
                                    return [4 /*yield*/, pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4", [email, displayName, avatarUrl, userId])];
                                case 10:
                                    _b.sent();
                                    _b.label = 11;
                                case 11:
                                    tok = signToken(userId);
                                    redirectHost = process.env.PUBLIC_HOST || "localhost";
                                    return [2 /*return*/, reply.redirect("http://".concat(redirectHost, "/?aither_token=").concat(tok, "&user_id=").concat(userId, "&name=").concat(encodeURIComponent(displayName)))];
                                case 12:
                                    e_3 = _b.sent();
                                    return [2 /*return*/, reply.status(502).send({ error: "Google OAuth error: " + safeError(e_3) })];
                                case 13: return [2 /*return*/];
                            }
                        });
                    }); });
                    YANDEX_CLIENT_ID = process.env.YANDEX_CLIENT_ID || "";
                    YANDEX_CLIENT_SECRET = process.env.YANDEX_CLIENT_SECRET || "";
                    app.get("/auth/yandex", function (_req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var state, params;
                        return __generator(this, function (_a) {
                            if (!YANDEX_CLIENT_ID)
                                return [2 /*return*/, reply.status(500).send({ error: "Yandex OAuth not configured" })];
                            state = setOAuthState(reply, "yandex");
                            params = new URLSearchParams({
                                client_id: YANDEX_CLIENT_ID,
                                redirect_uri: process.env.YANDEX_REDIRECT_URI || "http://".concat(process.env.PUBLIC_HOST || "localhost", "/auth/yandex/callback"),
                                response_type: "code",
                                scope: "login:email login:info",
                                state: state,
                            });
                            return [2 /*return*/, reply.redirect("https://oauth.yandex.ru/authorize?".concat(params))];
                        });
                    }); });
                    app.get("/auth/yandex/callback", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var code, tokenRes, tokenData, userRes, yu, oauthId, displayName, email, avatarUrl, user, userId, ins, tok, redirectHost, e_4;
                        var _a;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    if (!YANDEX_CLIENT_ID || !YANDEX_CLIENT_SECRET)
                                        return [2 /*return*/, reply.status(500).send({ error: "Yandex OAuth not configured" })];
                                    code = req.query.code;
                                    if (!code)
                                        return [2 /*return*/, reply.status(400).send({ error: "missing code" })];
                                    if (!validateOAuthState(req, reply, "yandex"))
                                        return [2 /*return*/, reply.status(403).send({ error: "invalid_state" })];
                                    _b.label = 1;
                                case 1:
                                    _b.trys.push([1, 12, , 13]);
                                    return [4 /*yield*/, fetch("https://oauth.yandex.ru/token", {
                                            method: "POST",
                                            headers: { "Content-Type": "application/x-www-form-urlencoded" },
                                            body: new URLSearchParams({
                                                grant_type: "authorization_code",
                                                code: code,
                                                client_id: YANDEX_CLIENT_ID,
                                                client_secret: YANDEX_CLIENT_SECRET,
                                            }),
                                        })];
                                case 2:
                                    tokenRes = _b.sent();
                                    return [4 /*yield*/, tokenRes.json()];
                                case 3:
                                    tokenData = _b.sent();
                                    if (tokenData.error)
                                        return [2 /*return*/, reply.status(403).send({ error: tokenData.error_description || tokenData.error })];
                                    return [4 /*yield*/, fetch("https://login.yandex.ru/info?format=json", {
                                            headers: { Authorization: "OAuth ".concat(tokenData.access_token) },
                                        })];
                                case 4:
                                    userRes = _b.sent();
                                    return [4 /*yield*/, userRes.json()];
                                case 5:
                                    yu = _b.sent();
                                    oauthId = yu.id;
                                    displayName = yu.real_name || yu.login || ((_a = yu.default_email) === null || _a === void 0 ? void 0 : _a.split("@")[0]) || "";
                                    email = yu.default_email || "";
                                    avatarUrl = yu.default_avatar_id
                                        ? "https://avatars.yandex.net/get-yapic/".concat(yu.default_avatar_id, "/islands-200")
                                        : "";
                                    return [4 /*yield*/, pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["yandex", oauthId])];
                                case 6:
                                    user = _b.sent();
                                    userId = void 0;
                                    if (!(user.rows.length === 0)) return [3 /*break*/, 9];
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, avatar_url, last_login_at)\n           VALUES ($1,$2,$3,$4,$5,now()) RETURNING user_id", ["yandex", oauthId, email, displayName, avatarUrl])];
                                case 7:
                                    ins = _b.sent();
                                    userId = ins.rows[0].user_id;
                                    return [4 /*yield*/, ensurePersonalOrg(userId)];
                                case 8:
                                    _b.sent();
                                    return [3 /*break*/, 11];
                                case 9:
                                    userId = user.rows[0].user_id;
                                    return [4 /*yield*/, pool.query("UPDATE portal_users SET email=$1, display_name=$2, avatar_url=$3, last_login_at=now() WHERE user_id=$4", [email, displayName, avatarUrl, userId])];
                                case 10:
                                    _b.sent();
                                    _b.label = 11;
                                case 11:
                                    tok = signToken(userId);
                                    redirectHost = process.env.PUBLIC_HOST || "localhost";
                                    return [2 /*return*/, reply.redirect("http://".concat(redirectHost, "/?aither_token=").concat(tok, "&user_id=").concat(userId, "&name=").concat(encodeURIComponent(displayName)))];
                                case 12:
                                    e_4 = _b.sent();
                                    return [2 /*return*/, reply.status(502).send({ error: "Yandex OAuth error: " + safeError(e_4) })];
                                case 13: return [2 /*return*/];
                            }
                        });
                    }); });
                    // === LDAP Authentication (FreeIPA / ALD Pro / OpenLDAP) ===
                    app.post("/auth/ldap", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var _a, username, password, ldapUser, oauthId, provider, user, userId, ins, tok, e_5;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    if (!(0, ldap_1.isLDAPEnabled)())
                                        return [2 /*return*/, reply.status(501).send({ error: "LDAP not configured" })];
                                    _a = req.body || {}, username = _a.username, password = _a.password;
                                    if (!username || !password)
                                        return [2 /*return*/, reply.status(400).send({ error: "username and password required" })];
                                    _b.label = 1;
                                case 1:
                                    _b.trys.push([1, 9, , 10]);
                                    return [4 /*yield*/, (0, ldap_1.authenticateViaLDAP)(username, password)];
                                case 2:
                                    ldapUser = _b.sent();
                                    if (!ldapUser)
                                        return [2 /*return*/, reply.status(401).send({ error: "invalid ldap credentials" })];
                                    oauthId = "ldap:".concat(ldapUser.uid);
                                    provider = "ldap";
                                    return [4 /*yield*/, pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", [provider, oauthId])];
                                case 3:
                                    user = _b.sent();
                                    userId = void 0;
                                    if (!(user.rows.length === 0)) return [3 /*break*/, 6];
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, last_login_at)\n           VALUES ($1,$2,$3,$4,now()) RETURNING user_id", [provider, oauthId, ldapUser.email, ldapUser.displayName])];
                                case 4:
                                    ins = _b.sent();
                                    userId = ins.rows[0].user_id;
                                    return [4 /*yield*/, ensurePersonalOrg(userId)];
                                case 5:
                                    _b.sent();
                                    return [3 /*break*/, 8];
                                case 6:
                                    userId = user.rows[0].user_id;
                                    return [4 /*yield*/, pool.query("UPDATE portal_users SET email=$1, display_name=$2, last_login_at=now() WHERE user_id=$3", [ldapUser.email, ldapUser.displayName, userId])];
                                case 7:
                                    _b.sent();
                                    _b.label = 8;
                                case 8:
                                    tok = signToken(userId);
                                    return [2 /*return*/, {
                                            access_token: tok,
                                            user: { user_id: userId, login: ldapUser.uid, email: ldapUser.email },
                                            ldap_groups: ldapUser.groups,
                                            ldap_role: ldapUser.role,
                                        }];
                                case 9:
                                    e_5 = _b.sent();
                                    return [2 /*return*/, reply.status(502).send({ error: "LDAP error: " + safeError(e_5) })];
                                case 10: return [2 /*return*/];
                            }
                        });
                    }); });
                    app.post("/auth/dev/login", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var name, oid, email, user, userId, ins, tok;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    // Dev-провайдер отключён в продакшене (404 — endpoint не существует)
                                    if (IS_PRODUCTION)
                                        return [2 /*return*/, reply.status(404).send({ error: "not_found" })];
                                    name = req.body.name;
                                    if (!name)
                                        return [2 /*return*/, { error: "name required" }];
                                    oid = name.toLowerCase().replace(/[^a-z0-9]/g, "-");
                                    email = name.includes("@") ? name : name + "@dev.local";
                                    return [4 /*yield*/, pool.query("SELECT user_id FROM portal_users WHERE oauth_provider=$1 AND oauth_id=$2", ["dev", oid])];
                                case 1:
                                    user = _a.sent();
                                    if (!(user.rows.length === 0)) return [3 /*break*/, 4];
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_users (oauth_provider, oauth_id, email, display_name, last_login_at) VALUES ($1,$2,$3,$4,now()) RETURNING user_id", ["dev", oid, email, name])];
                                case 2:
                                    ins = _a.sent();
                                    userId = ins.rows[0].user_id;
                                    return [4 /*yield*/, ensurePersonalOrg(userId)];
                                case 3:
                                    _a.sent();
                                    return [3 /*break*/, 6];
                                case 4:
                                    userId = user.rows[0].user_id;
                                    return [4 /*yield*/, pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [userId])];
                                case 5:
                                    _a.sent();
                                    _a.label = 6;
                                case 6:
                                    tok = signToken(userId);
                                    return [2 /*return*/, { access_token: tok, user: { user_id: userId, login: name, email: email } }];
                            }
                        });
                    }); });
                    // === SaaS Signup ===
                    app.post("/auth/signup", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var _a, email, password, org_name, invite_code, requiredCode, existing, hash, ins, userId, orgId, orgName, newOrg, newOrgId, e_6, key, tok;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    _a = req.body || {}, email = _a.email, password = _a.password, org_name = _a.org_name, invite_code = _a.invite_code;
                                    if (!email || !password)
                                        return [2 /*return*/, reply.status(400).send({ error: "email and password required" })];
                                    if (password.length < 6)
                                        return [2 /*return*/, reply.status(400).send({ error: "password must be at least 6 characters" })];
                                    requiredCode = process.env.INVITE_CODE || "";
                                    if (requiredCode && invite_code !== requiredCode)
                                        return [2 /*return*/, reply.status(403).send({ error: "registration requires valid invitation code" })];
                                    return [4 /*yield*/, pool.query("SELECT user_id FROM portal_users WHERE email=$1 AND oauth_provider='email'", [email])];
                                case 1:
                                    existing = _b.sent();
                                    if (existing.rows.length > 0)
                                        return [2 /*return*/, reply.status(409).send({ error: "email already registered" })];
                                    hash = hashPassword(password);
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_users (oauth_provider, oauth_id, email, password_hash, display_name, last_login_at) VALUES ('email',$1,$2,$3,$4,now()) RETURNING user_id", [email, email, hash, email.split("@")[0]])];
                                case 2:
                                    ins = _b.sent();
                                    userId = ins.rows[0].user_id;
                                    return [4 /*yield*/, ensurePersonalOrg(userId)];
                                case 3:
                                    orgId = _b.sent();
                                    orgName = org_name || "Моя организация";
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_organizations (name) VALUES ($1) RETURNING org_id", [orgName])];
                                case 4:
                                    newOrg = _b.sent();
                                    newOrgId = newOrg.rows[0].org_id;
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1,$2,'owner')", [newOrgId, userId])];
                                case 5:
                                    _b.sent();
                                    _b.label = 6;
                                case 6:
                                    _b.trys.push([6, 8, , 9]);
                                    return [4 /*yield*/, pool.query("INSERT INTO billing_accounts (org_id, reserved, total_tokens, meta) VALUES ($1,0,$2,'{}'::jsonb) ON CONFLICT (org_id) DO NOTHING", [newOrgId, STARTER_TOKENS])];
                                case 7:
                                    _b.sent();
                                    return [3 /*break*/, 9];
                                case 8:
                                    e_6 = _b.sent();
                                    return [3 /*break*/, 9];
                                case 9:
                                    key = "ak-" + (0, crypto_1.randomBytes)(24).toString("hex");
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_api_keys (org_id, user_id, name, key_hash, api_key, api_key_prefix, status) VALUES ($1,$2,$3,$4,$5,$6,'active')", [newOrgId, userId, "default", key, key, "ak-"])];
                                case 10:
                                    _b.sent();
                                    tok = signToken(userId);
                                    return [2 /*return*/, {
                                            access_token: tok,
                                            user: { user_id: userId, email: email, display_name: email.split("@")[0] },
                                            org: { org_id: newOrgId, name: orgName },
                                            api_key: key,
                                        }];
                            }
                        });
                    }); });
                    // === SaaS Login ===
                    app.post("/auth/login", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var _a, email, password, r, tok;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    _a = req.body || {}, email = _a.email, password = _a.password;
                                    if (!email || !password)
                                        return [2 /*return*/, reply.status(400).send({ error: "email and password required" })];
                                    return [4 /*yield*/, pool.query("SELECT user_id, password_hash, display_name FROM portal_users WHERE email=$1 AND oauth_provider='email'", [email])];
                                case 1:
                                    r = _b.sent();
                                    if (r.rows.length === 0)
                                        return [2 /*return*/, reply.status(401).send({ error: "invalid credentials" })];
                                    if (!verifyPassword(password, r.rows[0].password_hash))
                                        return [2 /*return*/, reply.status(401).send({ error: "invalid credentials" })];
                                    return [4 /*yield*/, pool.query("UPDATE portal_users SET last_login_at=now() WHERE user_id=$1", [r.rows[0].user_id])];
                                case 2:
                                    _b.sent();
                                    tok = signToken(r.rows[0].user_id);
                                    return [2 /*return*/, {
                                            access_token: tok,
                                            user: { user_id: r.rows[0].user_id, email: email, display_name: r.rows[0].display_name },
                                        }];
                            }
                        });
                    }); });
                    // ── External API Gateway (API-key auth, OpenAI-compatible) ──
                    (0, api_gateway_1.registerApiGateway)(app, pool, CORE_API);
                    app.get("/api/v1/me", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, pool.query("SELECT user_id, display_name, email, avatar_url, oauth_provider, created_at FROM portal_users WHERE user_id=$1", [p.user_id])];
                                case 1:
                                    r = _a.sent();
                                    if (r.rows.length === 0)
                                        return [2 /*return*/, reply.status(404).send({ error: "user not found" })];
                                    return [2 /*return*/, { user: r.rows[0] }];
                            }
                        });
                    }); });
                    MODEL_MAP = {
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
                    app.get("/api/v1/status", function (_r, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var k;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0: return [4 /*yield*/, pool.query("SELECT count(*) FROM portal_api_keys WHERE status='active'")];
                                case 1:
                                    k = _a.sent();
                                    return [2 /*return*/, reply.send({
                                            active_api_keys: Number(k.rows[0].count),
                                        })];
                            }
                        });
                    }); });
                    app.get("/api/v1/core/status", function (_r, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var r, text, e_7;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    _a.trys.push([0, 3, , 4]);
                                    return [4 /*yield*/, fetch(CORE_API + "/health")];
                                case 1:
                                    r = _a.sent();
                                    return [4 /*yield*/, r.text()];
                                case 2:
                                    text = _a.sent();
                                    if (!text)
                                        return [2 /*return*/, reply.send({ status: "ok", model: "vLLM", note: "health returned empty (vLLM direct)" })];
                                    try {
                                        return [2 /*return*/, reply.send(JSON.parse(text))];
                                    }
                                    catch (_b) {
                                        return [2 /*return*/, reply.send({ status: "ok", raw: text.slice(0, 200) })];
                                    }
                                    return [3 /*break*/, 4];
                                case 3:
                                    e_7 = _a.sent();
                                    return [2 /*return*/, reply.send({ status: "unreachable", error: safeError(e_7) })];
                                case 4: return [2 /*return*/];
                            }
                        });
                    }); });
                    app.get("/api/v1/users", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, pool.query("SELECT DISTINCT u.user_id, u.display_name, u.email, u.oauth_provider, u.created_at\n       FROM portal_users u\n       JOIN portal_org_members m ON u.user_id = m.user_id\n       WHERE m.org_id IN (\n         SELECT org_id FROM portal_org_members WHERE user_id = $1\n       )\n       ORDER BY u.created_at DESC", [p.user_id])];
                                case 1:
                                    r = _a.sent();
                                    return [2 /*return*/, { users: r.rows }];
                            }
                        });
                    }); });
                    // ==================== ORGS ====================
                    app.get("/api/v1/orgs", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, pool.query("SELECT o.org_id, o.name, o.status, o.created_at, m.role\n       FROM portal_organizations o\n       JOIN portal_org_members m ON o.org_id = m.org_id\n       WHERE m.user_id = $1 AND m.status = 'active'\n       ORDER BY o.created_at DESC", [p.user_id])];
                                case 1:
                                    r = _a.sent();
                                    return [2 /*return*/, { orgs: r.rows }];
                            }
                        });
                    }); });
                    app.post("/api/v1/orgs", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, name, client, org, o, e_8;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    name = req.body.name;
                                    if (!name || typeof name !== "string" || name.trim().length === 0)
                                        return [2 /*return*/, reply.status(400).send({ error: "name is required" })];
                                    return [4 /*yield*/, pool.connect()];
                                case 1:
                                    client = _a.sent();
                                    _a.label = 2;
                                case 2:
                                    _a.trys.push([2, 7, 9, 10]);
                                    return [4 /*yield*/, client.query("BEGIN")];
                                case 3:
                                    _a.sent();
                                    return [4 /*yield*/, client.query("INSERT INTO portal_organizations (name) VALUES ($1) RETURNING org_id, name, status, created_at", [name.trim()])];
                                case 4:
                                    org = _a.sent();
                                    o = org.rows[0];
                                    return [4 /*yield*/, client.query("INSERT INTO portal_org_members (org_id, user_id, role) VALUES ($1, $2, 'owner')", [o.org_id, p.user_id])];
                                case 5:
                                    _a.sent();
                                    return [4 /*yield*/, client.query("COMMIT")];
                                case 6:
                                    _a.sent();
                                    return [2 /*return*/, { org: __assign(__assign({}, o), { role: "owner" }) }];
                                case 7:
                                    e_8 = _a.sent();
                                    return [4 /*yield*/, client.query("ROLLBACK")];
                                case 8:
                                    _a.sent();
                                    return [2 /*return*/, reply.status(500).send({ error: safeError(e_8) })];
                                case 9:
                                    client.release();
                                    return [7 /*endfinally*/];
                                case 10: return [2 /*return*/];
                            }
                        });
                    }); });
                    app.get("/api/v1/orgs/:orgId", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.params.orgId;
                                    return [4 /*yield*/, pool.query("SELECT o.org_id, o.name, o.status, o.created_at, m.role\n       FROM portal_organizations o JOIN portal_org_members m ON o.org_id = m.org_id\n       WHERE o.org_id = $1 AND m.user_id = $2", [orgId, p.user_id])];
                                case 1:
                                    r = _a.sent();
                                    if (r.rows.length === 0)
                                        return [2 /*return*/, reply.status(404).send({ error: "org not found" })];
                                    return [2 /*return*/, { org: r.rows[0] }];
                            }
                        });
                    }); });
                    // ==================== ORG SECURITY POLICIES ====================
                    app.get("/api/v1/orgs/:orgId/policy", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, m, policy, e_9;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.params.orgId;
                                    return [4 /*yield*/, pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id])];
                                case 1:
                                    m = _a.sent();
                                    if (m.rows.length === 0)
                                        return [2 /*return*/, reply.status(403).send({ error: "not a member" })];
                                    _a.label = 2;
                                case 2:
                                    _a.trys.push([2, 4, , 5]);
                                    return [4 /*yield*/, (0, policies_1.loadPolicy)(pool, orgId)];
                                case 3:
                                    policy = _a.sent();
                                    return [2 /*return*/, { org_id: orgId, policy: policy }];
                                case 4:
                                    e_9 = _a.sent();
                                    return [2 /*return*/, reply.status(500).send({ error: safeError(e_9) })];
                                case 5: return [2 /*return*/];
                            }
                        });
                    }); });
                    app.put("/api/v1/orgs/:orgId/policy", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, body, allowedKeys, updates, allowedKeys_1, allowedKeys_1_1, key, err, policy, e_10;
                        var e_11, _a;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.params.orgId;
                                    return [4 /*yield*/, checkOrgOwner(orgId, p.user_id)];
                                case 1:
                                    if (!(_b.sent()))
                                        return [2 /*return*/, reply.status(403).send({ error: "owner only" })];
                                    body = req.body || {};
                                    allowedKeys = [
                                        "dlp_enabled", "jailbreak_detection", "sensitive_data_patterns",
                                        "allowed_ip_cidrs", "mfa_required", "session_timeout_min",
                                        "api_key_max_age_days", "api_key_rotation_required",
                                        "custom_rpm", "custom_tpm", "max_concurrent_requests",
                                        "allowed_models", "max_tokens_per_request",
                                        "chat_retention_days", "audit_log_retention_days",
                                        "chat_enabled",
                                    ];
                                    updates = {};
                                    try {
                                        for (allowedKeys_1 = __values(allowedKeys), allowedKeys_1_1 = allowedKeys_1.next(); !allowedKeys_1_1.done; allowedKeys_1_1 = allowedKeys_1.next()) {
                                            key = allowedKeys_1_1.value;
                                            if (key in body)
                                                updates[key] = body[key];
                                        }
                                    }
                                    catch (e_11_1) { e_11 = { error: e_11_1 }; }
                                    finally {
                                        try {
                                            if (allowedKeys_1_1 && !allowedKeys_1_1.done && (_a = allowedKeys_1.return)) _a.call(allowedKeys_1);
                                        }
                                        finally { if (e_11) throw e_11.error; }
                                    }
                                    if (Object.keys(updates).length === 0)
                                        return [2 /*return*/, reply.status(400).send({ error: "no valid policy fields provided" })];
                                    err = (0, policies_1.validatePolicy)(updates);
                                    if (err)
                                        return [2 /*return*/, reply.status(400).send({ error: err })];
                                    _b.label = 2;
                                case 2:
                                    _b.trys.push([2, 4, , 5]);
                                    return [4 /*yield*/, (0, policies_1.savePolicy)(pool, orgId, updates)];
                                case 3:
                                    policy = _b.sent();
                                    return [2 /*return*/, { org_id: orgId, policy: policy }];
                                case 4:
                                    e_10 = _b.sent();
                                    return [2 /*return*/, reply.status(500).send({ error: safeError(e_10) })];
                                case 5: return [2 /*return*/];
                            }
                        });
                    }); });
                    // ==================== API KEYS ====================
                    app.get("/api/v1/orgs/:orgId/api-keys", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, m, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.params.orgId;
                                    return [4 /*yield*/, pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id])];
                                case 1:
                                    m = _a.sent();
                                    if (m.rows.length === 0)
                                        return [2 /*return*/, reply.status(403).send({ error: "not a member" })];
                                    return [4 /*yield*/, pool.query("SELECT key_id, api_key_prefix, name, status, created_at, expires_at, last_used_at\n       FROM portal_api_keys WHERE org_id=$1 AND status!='revoked' ORDER BY created_at DESC", [orgId])];
                                case 2:
                                    r = _a.sent();
                                    return [2 /*return*/, { keys: r.rows }];
                            }
                        });
                    }); });
                    app.post("/api/v1/orgs/:orgId/api-keys", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, apiKey, apiKeyPrefix, name, r;
                        var _a;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.params.orgId;
                                    return [4 /*yield*/, checkOrgOwner(orgId, p.user_id)];
                                case 1:
                                    if (!(_b.sent()))
                                        return [2 /*return*/, reply.status(403).send({ error: "owner only" })];
                                    apiKey = "ak-" + (0, crypto_1.randomBytes)(24).toString("hex");
                                    apiKeyPrefix = apiKey.slice(0, 11);
                                    name = ((_a = req.body) === null || _a === void 0 ? void 0 : _a.name) || "default";
                                    return [4 /*yield*/, pool.query("INSERT INTO portal_api_keys (org_id, api_key, api_key_prefix, name)\n       VALUES ($1,$2,$3,$4) RETURNING key_id, api_key_prefix, name, status, created_at", [orgId, apiKey, apiKeyPrefix, name])];
                                case 2:
                                    r = _b.sent();
                                    return [2 /*return*/, { key: __assign(__assign({}, r.rows[0]), { api_key: apiKey }) }];
                            }
                        });
                    }); });
                    app.delete("/api/v1/orgs/:orgId/api-keys/:keyId", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, _a, orgId, keyId, r;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    _a = req.params, orgId = _a.orgId, keyId = _a.keyId;
                                    return [4 /*yield*/, checkOrgOwner(orgId, p.user_id)];
                                case 1:
                                    if (!(_b.sent()))
                                        return [2 /*return*/, reply.status(403).send({ error: "owner only" })];
                                    return [4 /*yield*/, pool.query("UPDATE portal_api_keys SET status='revoked' WHERE key_id=$1 AND org_id=$2 RETURNING key_id, status", [keyId, orgId])];
                                case 2:
                                    r = _b.sent();
                                    if (r.rows.length === 0)
                                        return [2 /*return*/, reply.status(404).send({ error: "key not found" })];
                                    return [2 /*return*/, { key: r.rows[0] }];
                            }
                        });
                    }); });
                    fs = require("fs");
                    DELEGATION_PRIVATE_KEY = (function () {
                        try {
                            return fs.readFileSync("/app/delegation/private.pem", "utf8");
                        }
                        catch (_a) { }
                        try {
                            return fs.readFileSync("./delegation/private.pem", "utf8");
                        }
                        catch (_b) { }
                        return process.env.DELEGATION_PRIVATE_KEY || "";
                    })();
                    app.post("/api/v1/orgs/:orgId/delegate", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, api_key, k, m, delegationToken;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.params.orgId;
                                    api_key = req.body.api_key;
                                    if (!api_key)
                                        return [2 /*return*/, reply.status(400).send({ error: "api_key required" })];
                                    return [4 /*yield*/, pool.query("SELECT key_id FROM portal_api_keys WHERE org_id=$1 AND api_key=$2 AND status='active'", [orgId, api_key])];
                                case 1:
                                    k = _a.sent();
                                    if (k.rows.length === 0)
                                        return [2 /*return*/, reply.status(403).send({ error: "invalid or revoked" })];
                                    return [4 /*yield*/, pool.query("SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id])];
                                case 2:
                                    m = _a.sent();
                                    if (m.rows.length === 0)
                                        return [2 /*return*/, reply.status(403).send({ error: "not a member" })];
                                    return [4 /*yield*/, pool.query("UPDATE portal_api_keys SET last_used_at=now() WHERE key_id=$1", [k.rows[0].key_id])];
                                case 3:
                                    _a.sent();
                                    delegationToken = jsonwebtoken_1.default.sign({ org_id: orgId, key_id: k.rows[0].key_id, user_id: p.user_id }, DELEGATION_PRIVATE_KEY, { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" });
                                    return [2 /*return*/, { delegation_token: delegationToken, expires_in: 300 }];
                            }
                        });
                    }); });
                    // List chats
                    app.get("/api/v1/chats", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, checkChatEnabled(p.user_id, reply)];
                                case 1:
                                    if (!(_a.sent()))
                                        return [2 /*return*/];
                                    return [4 /*yield*/, pool.query("SELECT chat_id, title, model, share_token, created_at, updated_at\n       FROM chats WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 50", [p.user_id])];
                                case 2:
                                    r = _a.sent();
                                    return [2 /*return*/, { chats: r.rows }];
                            }
                        });
                    }); });
                    // Create chat
                    app.post("/api/v1/chats", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, _a, title, model, r;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, checkChatEnabled(p.user_id, reply)];
                                case 1:
                                    if (!(_b.sent()))
                                        return [2 /*return*/];
                                    _a = req.body || {}, title = _a.title, model = _a.model;
                                    return [4 /*yield*/, pool.query("INSERT INTO chats (user_id, title, model) VALUES ($1,$2,$3)\n       RETURNING chat_id, title, model, created_at", [p.user_id, title || "Новый чат", model || "qwen2.5-14b"])];
                                case 2:
                                    r = _b.sent();
                                    return [2 /*return*/, { chat: r.rows[0] }];
                            }
                        });
                    }); });
                    // Get chat with messages
                    app.get("/api/v1/chats/:chatId", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, chatId, c, msgs;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, checkChatEnabled(p.user_id, reply)];
                                case 1:
                                    if (!(_a.sent()))
                                        return [2 /*return*/];
                                    chatId = req.params.chatId;
                                    return [4 /*yield*/, pool.query("SELECT * FROM chats WHERE chat_id=$1 AND user_id=$2", [chatId, p.user_id])];
                                case 2:
                                    c = _a.sent();
                                    if (c.rows.length === 0)
                                        return [2 /*return*/, reply.status(404).send({ error: "chat not found" })];
                                    return [4 /*yield*/, pool.query("SELECT message_id, role, content, tokens_used, created_at FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC", [chatId])];
                                case 3:
                                    msgs = _a.sent();
                                    return [2 /*return*/, { chat: c.rows[0], messages: msgs.rows }];
                            }
                        });
                    }); });
                    // Delete chat
                    app.delete("/api/v1/chats/:chatId", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, chatId, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, checkChatEnabled(p.user_id, reply)];
                                case 1:
                                    if (!(_a.sent()))
                                        return [2 /*return*/];
                                    chatId = req.params.chatId;
                                    return [4 /*yield*/, pool.query("DELETE FROM chats WHERE chat_id=$1 AND user_id=$2 RETURNING chat_id", [chatId, p.user_id])];
                                case 2:
                                    r = _a.sent();
                                    if (r.rows.length === 0)
                                        return [2 /*return*/, reply.status(404).send({ error: "chat not found" })];
                                    return [2 /*return*/, { deleted: true }];
                            }
                        });
                    }); });
                    // Share chat (generate token)
                    app.post("/api/v1/chats/:chatId/share", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, chatId, shareToken, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, checkChatEnabled(p.user_id, reply)];
                                case 1:
                                    if (!(_a.sent()))
                                        return [2 /*return*/];
                                    chatId = req.params.chatId;
                                    shareToken = (0, crypto_1.randomBytes)(16).toString("hex");
                                    return [4 /*yield*/, pool.query("UPDATE chats SET share_token=$1 WHERE chat_id=$2 AND user_id=$3 RETURNING chat_id, share_token", [shareToken, chatId, p.user_id])];
                                case 2:
                                    r = _a.sent();
                                    if (r.rows.length === 0)
                                        return [2 /*return*/, reply.status(404).send({ error: "chat not found" })];
                                    return [2 /*return*/, { share_token: shareToken, url: "/shared/".concat(shareToken) }];
                            }
                        });
                    }); });
                    // View shared chat (no auth)
                    app.get("/api/v1/shared/:shareToken", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var shareToken, c, msgs;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    shareToken = req.params.shareToken;
                                    return [4 /*yield*/, pool.query("SELECT chat_id, title, model, created_at FROM chats WHERE share_token=$1", [shareToken])];
                                case 1:
                                    c = _a.sent();
                                    if (c.rows.length === 0)
                                        return [2 /*return*/, reply.status(404).send({ error: "not found" })];
                                    return [4 /*yield*/, pool.query("SELECT role, content, created_at FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC", [c.rows[0].chat_id])];
                                case 2:
                                    msgs = _a.sent();
                                    return [2 /*return*/, { chat: c.rows[0], messages: msgs.rows }];
                            }
                        });
                    }); });
                    // Send message + stream AI response
                    app.post("/api/v1/chats/:chatId/messages", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, chatId, _a, content, org_id, c, chat, userMsg, delegationToken, history, messages, title, modelInfo, vllmModel, vllmEndpoint, vllmRes, fullContent, reader, decoder, buffer, _b, done, value, lines, lines_1, lines_1_1, line, data, parsed, delta, tokensUsed, e_12;
                        var e_13, _c;
                        var _d, _e, _f;
                        return __generator(this, function (_g) {
                            switch (_g.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, checkChatEnabled(p.user_id, reply)];
                                case 1:
                                    if (!(_g.sent()))
                                        return [2 /*return*/];
                                    chatId = req.params.chatId;
                                    _a = req.body || {}, content = _a.content, org_id = _a.org_id;
                                    if (!content)
                                        return [2 /*return*/, reply.status(400).send({ error: "content required" })];
                                    return [4 /*yield*/, pool.query("SELECT * FROM chats WHERE chat_id=$1 AND user_id=$2", [chatId, p.user_id])];
                                case 2:
                                    c = _g.sent();
                                    if (c.rows.length === 0)
                                        return [2 /*return*/, reply.status(404).send({ error: "chat not found" })];
                                    chat = c.rows[0];
                                    return [4 /*yield*/, pool.query("INSERT INTO chat_messages (chat_id, role, content) VALUES ($1,'user',$2) RETURNING message_id, created_at", [chatId, content])];
                                case 3:
                                    userMsg = _g.sent();
                                    delegationToken = DELEGATION_PRIVATE_KEY ? jsonwebtoken_1.default.sign({ org_id: org_id || "", user_id: p.user_id }, DELEGATION_PRIVATE_KEY, { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" }) : "";
                                    return [4 /*yield*/, pool.query("SELECT role, content FROM chat_messages WHERE chat_id=$1 ORDER BY created_at ASC", [chatId])];
                                case 4:
                                    history = _g.sent();
                                    messages = history.rows.map(function (m) { return ({ role: m.role, content: m.content }); });
                                    if (!(chat.title === "Новый чат" && history.rows.filter(function (m) { return m.role === "user"; }).length === 1)) return [3 /*break*/, 6];
                                    title = content.slice(0, 50).replace(/\n/g, " ");
                                    return [4 /*yield*/, pool.query("UPDATE chats SET title=$1 WHERE chat_id=$2", [title, chatId])];
                                case 5:
                                    _g.sent();
                                    _g.label = 6;
                                case 6:
                                    _g.trys.push([6, 18, , 20]);
                                    modelInfo = MODEL_MAP[chat.model] || MODEL_MAP["qwen2.5-14b"];
                                    vllmModel = modelInfo.vllm_path;
                                    vllmEndpoint = CORE_API;
                                    return [4 /*yield*/, fetch(vllmEndpoint + "/v1/chat/completions", {
                                            method: "POST",
                                            headers: __assign({ "Content-Type": "application/json" }, (delegationToken ? { "Authorization": "Bearer " + delegationToken } : {})),
                                            body: JSON.stringify({
                                                model: vllmModel,
                                                messages: __spreadArray(__spreadArray([], __read(messages), false), [{ role: "user", content: content }], false),
                                                max_tokens: 2048,
                                                temperature: 0.7,
                                                stream: true,
                                            }),
                                        })];
                                case 7:
                                    vllmRes = _g.sent();
                                    if (!(!vllmRes.ok || !vllmRes.body)) return [3 /*break*/, 9];
                                    // Delete user message on error
                                    return [4 /*yield*/, pool.query("DELETE FROM chat_messages WHERE message_id=$1", [userMsg.rows[0].message_id])];
                                case 8:
                                    // Delete user message on error
                                    _g.sent();
                                    return [2 /*return*/, reply.status(502).send({ error: "vLLM error: " + vllmRes.status })];
                                case 9:
                                    // Stream SSE to client
                                    reply.raw.writeHead(200, {
                                        "Content-Type": "text/event-stream",
                                        "Cache-Control": "no-cache",
                                        "Connection": "keep-alive",
                                    });
                                    fullContent = "";
                                    reader = vllmRes.body.getReader();
                                    decoder = new TextDecoder();
                                    buffer = "";
                                    _g.label = 10;
                                case 10:
                                    _g.trys.push([10, , 14, 15]);
                                    _g.label = 11;
                                case 11:
                                    if (!true) return [3 /*break*/, 13];
                                    return [4 /*yield*/, reader.read()];
                                case 12:
                                    _b = _g.sent(), done = _b.done, value = _b.value;
                                    if (done)
                                        return [3 /*break*/, 13];
                                    buffer += decoder.decode(value, { stream: true });
                                    lines = buffer.split("\n");
                                    buffer = lines.pop() || "";
                                    try {
                                        for (lines_1 = (e_13 = void 0, __values(lines)), lines_1_1 = lines_1.next(); !lines_1_1.done; lines_1_1 = lines_1.next()) {
                                            line = lines_1_1.value;
                                            if (line.startsWith("data: ")) {
                                                data = line.slice(6);
                                                if (data === "[DONE]")
                                                    continue;
                                                try {
                                                    parsed = JSON.parse(data);
                                                    delta = ((_f = (_e = (_d = parsed.choices) === null || _d === void 0 ? void 0 : _d[0]) === null || _e === void 0 ? void 0 : _e.delta) === null || _f === void 0 ? void 0 : _f.content) || "";
                                                    fullContent += delta;
                                                    // Forward to client
                                                    reply.raw.write("data: ".concat(JSON.stringify({ delta: delta }), "\n\n"));
                                                }
                                                catch (_h) { }
                                            }
                                        }
                                    }
                                    catch (e_13_1) { e_13 = { error: e_13_1 }; }
                                    finally {
                                        try {
                                            if (lines_1_1 && !lines_1_1.done && (_c = lines_1.return)) _c.call(lines_1);
                                        }
                                        finally { if (e_13) throw e_13.error; }
                                    }
                                    return [3 /*break*/, 11];
                                case 13: return [3 /*break*/, 15];
                                case 14:
                                    reader.releaseLock();
                                    return [7 /*endfinally*/];
                                case 15:
                                    tokensUsed = Math.ceil(fullContent.length / 4);
                                    return [4 /*yield*/, pool.query("INSERT INTO chat_messages (chat_id, role, content, tokens_used) VALUES ($1,'assistant',$2,$3)", [chatId, fullContent, tokensUsed])];
                                case 16:
                                    _g.sent();
                                    return [4 /*yield*/, pool.query("UPDATE chats SET updated_at=now() WHERE chat_id=$1", [chatId])];
                                case 17:
                                    _g.sent();
                                    reply.raw.write("data: ".concat(JSON.stringify({ delta: "", done: true, tokens_used: tokensUsed }), "\n\n"));
                                    reply.raw.end();
                                    return [3 /*break*/, 20];
                                case 18:
                                    e_12 = _g.sent();
                                    // Delete user message on error
                                    return [4 /*yield*/, pool.query("DELETE FROM chat_messages WHERE message_id=$1", [userMsg.rows[0].message_id])];
                                case 19:
                                    // Delete user message on error
                                    _g.sent();
                                    if (!reply.raw.headersSent) {
                                        return [2 /*return*/, reply.status(502).send({ error: "stream error: " + safeError(e_12) })];
                                    }
                                    reply.raw.end();
                                    return [3 /*break*/, 20];
                                case 20: return [2 /*return*/];
                            }
                        });
                    }); });
                    // ==================== BALANCE (local) ====================
                    app.get("/api/v1/billing", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, r, total, meta, refillCount, e_14;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.query.org_id;
                                    if (!orgId)
                                        return [2 /*return*/, reply.status(400).send({ error: "org_id required" })];
                                    _a.label = 1;
                                case 1:
                                    _a.trys.push([1, 5, , 6]);
                                    return [4 /*yield*/, pool.query("SELECT total_tokens, reserved, meta FROM billing_accounts WHERE org_id=$1", [orgId])];
                                case 2:
                                    r = _a.sent();
                                    if (r.rows.length === 0)
                                        return [2 /*return*/, reply.send({ org_id: orgId, total_tokens: 0, reserved: 0 })];
                                    total = Number(r.rows[0].total_tokens);
                                    meta = r.rows[0].meta || {};
                                    refillCount = meta.refill_count || 0;
                                    if (!(total <= 0 && refillCount < REFILL_LIMIT)) return [3 /*break*/, 4];
                                    return [4 /*yield*/, pool.query("UPDATE billing_accounts SET total_tokens = total_tokens + $1,\n           meta = jsonb_set(COALESCE(meta,'{}'::jsonb),'{refill_count}',$2::jsonb),\n           updated_at = now() WHERE org_id=$3", [REFILL_TOKENS, JSON.stringify(refillCount + 1), orgId])];
                                case 3:
                                    _a.sent();
                                    total += REFILL_TOKENS;
                                    console.log("[auto-refill] org ".concat(orgId, ": +").concat(REFILL_TOKENS, " tokens (refill #").concat(refillCount + 1, "/").concat(REFILL_LIMIT, ")"));
                                    _a.label = 4;
                                case 4: return [2 /*return*/, reply.send({ org_id: orgId, total_tokens: total, reserved: Number(r.rows[0].reserved) })];
                                case 5:
                                    e_14 = _a.sent();
                                    return [2 /*return*/, reply.send({ org_id: orgId, total_tokens: 0, reserved: 0, note: "billing_accounts table missing" })];
                                case 6: return [2 /*return*/];
                            }
                        });
                    }); });
                    app.get("/api/v1/usage", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, r, e_15;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.query.org_id;
                                    if (!orgId)
                                        return [2 /*return*/, reply.status(400).send({ error: "org_id required" })];
                                    _a.label = 1;
                                case 1:
                                    _a.trys.push([1, 3, , 4]);
                                    return [4 /*yield*/, pool.query("SELECT count(*), coalesce(sum(tokens),0) FROM payment_transactions WHERE org_id=$1 AND status='succeeded'", [orgId])];
                                case 2:
                                    r = _a.sent();
                                    return [2 /*return*/, reply.send({ org_id: orgId, payments: Number(r.rows[0].count), total_tokens: Number(r.rows[0].sum) })];
                                case 3:
                                    e_15 = _a.sent();
                                    return [2 /*return*/, reply.send({ org_id: orgId, payments: 0, total_tokens: 0 })];
                                case 4: return [2 /*return*/];
                            }
                        });
                    }); });
                    // === Dashboard: aggregated usage for charts ===
                    app.get("/api/v1/billing/dashboard", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, daily, month, byModel, bal, balance, e_16;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.query.org_id;
                                    if (!orgId)
                                        return [2 /*return*/, reply.status(400).send({ error: "org_id required" })];
                                    _a.label = 1;
                                case 1:
                                    _a.trys.push([1, 6, , 7]);
                                    return [4 /*yield*/, pool.query("SELECT date(created_at) as day, coalesce(sum(tokens),0) as tokens, count(*) as requests\n         FROM payment_transactions\n         WHERE org_id=$1 AND status='succeeded' AND created_at > now() - interval '30 days'\n         GROUP BY day ORDER BY day", [orgId])];
                                case 2:
                                    daily = _a.sent();
                                    return [4 /*yield*/, pool.query("SELECT coalesce(sum(tokens),0) as total, count(*) as count\n         FROM payment_transactions\n         WHERE org_id=$1 AND status='succeeded'\n           AND date_trunc('month', created_at) = date_trunc('month', now())", [orgId])];
                                case 3:
                                    month = _a.sent();
                                    return [4 /*yield*/, pool.query("SELECT COALESCE(meta->>'model','unknown') as model, coalesce(sum(tokens),0) as tokens, count(*) as requests\n         FROM payment_transactions\n         WHERE org_id=$1 AND status='succeeded' AND created_at > now() - interval '30 days'\n         GROUP BY meta->>'model' ORDER BY tokens DESC LIMIT 10", [orgId])];
                                case 4:
                                    byModel = _a.sent();
                                    return [4 /*yield*/, pool.query("SELECT total_tokens, reserved FROM billing_accounts WHERE org_id=$1", [orgId])];
                                case 5:
                                    bal = _a.sent();
                                    balance = bal.rows.length > 0 ? { total_tokens: Number(bal.rows[0].total_tokens), reserved: Number(bal.rows[0].reserved) } : { total_tokens: 0, reserved: 0 };
                                    return [2 /*return*/, reply.send({
                                            org_id: orgId,
                                            balance: balance,
                                            daily: daily.rows,
                                            month: month.rows[0] ? { total: Number(month.rows[0].total), count: Number(month.rows[0].count) } : { total: 0, count: 0 },
                                            by_model: byModel.rows,
                                        })];
                                case 6:
                                    e_16 = _a.sent();
                                    return [2 /*return*/, reply.status(500).send({ error: safeError(e_16) })];
                                case 7: return [2 /*return*/];
                            }
                        });
                    }); });
                    YOOKASSA_SHOP_ID = process.env.YOOKASSA_SHOP_ID || "";
                    YOOKASSA_SECRET = process.env.YOOKASSA_SECRET || "";
                    TOKENS_PER_RUBLE = 1000;
                    // Create payment → redirect to YooKassa
                    app.post("/api/v1/billing/topup", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, _a, org_id, amount_rub, m, tokens, txn, txnId, idempotenceKey, ykRes, ykData, e_17;
                        var _b;
                        return __generator(this, function (_c) {
                            switch (_c.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    _a = req.body, org_id = _a.org_id, amount_rub = _a.amount_rub;
                                    if (!org_id || !amount_rub || amount_rub < 1)
                                        return [2 /*return*/, reply.status(400).send({ error: "org_id and amount_rub (>=1) required" })];
                                    return [4 /*yield*/, pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [org_id, p.user_id])];
                                case 1:
                                    m = _c.sent();
                                    if (m.rows.length === 0)
                                        return [2 /*return*/, reply.status(403).send({ error: "not a member" })];
                                    tokens = Math.floor(amount_rub * TOKENS_PER_RUBLE);
                                    return [4 /*yield*/, pool.query("INSERT INTO payment_transactions (org_id, user_id, provider, amount_rub, tokens, status, meta)\n       VALUES ($1,$2,'yookassa',$3,$4,'pending','{}'::jsonb) RETURNING txn_id", [org_id, p.user_id, amount_rub, tokens])];
                                case 2:
                                    txn = _c.sent();
                                    txnId = txn.rows[0].txn_id;
                                    if (!(!YOOKASSA_SHOP_ID || !YOOKASSA_SECRET)) return [3 /*break*/, 5];
                                    return [4 /*yield*/, pool.query("UPDATE payment_transactions SET status='succeeded', updated_at=now(), meta=$1 WHERE txn_id=$2", [JSON.stringify({ dev_mode: true }), txnId])];
                                case 3:
                                    _c.sent();
                                    // Credit tokens directly (simulate YooKassa callback)
                                    return [4 /*yield*/, pool.query("INSERT INTO billing_accounts (org_id, reserved, total_tokens)\n         VALUES ($1, 0, $2)\n         ON CONFLICT (org_id) DO UPDATE SET total_tokens = billing_accounts.total_tokens + $2", [org_id, tokens])];
                                case 4:
                                    // Credit tokens directly (simulate YooKassa callback)
                                    _c.sent();
                                    return [2 /*return*/, reply.send({
                                            ok: true,
                                            txn_id: txnId,
                                            status: "succeeded",
                                            tokens: tokens,
                                            dev_mode: true,
                                        })];
                                case 5:
                                    _c.trys.push([5, 10, , 11]);
                                    idempotenceKey = txnId;
                                    return [4 /*yield*/, fetch("https://api.yookassa.ru/v3/payments", {
                                            method: "POST",
                                            headers: {
                                                "Content-Type": "application/json",
                                                "Authorization": "Basic " + Buffer.from(YOOKASSA_SHOP_ID + ":" + YOOKASSA_SECRET).toString("base64"),
                                                "Idempotence-Key": idempotenceKey,
                                            },
                                            body: JSON.stringify({
                                                amount: { value: amount_rub.toFixed(2), currency: "RUB" },
                                                confirmation: { type: "redirect", return_url: "http://".concat(process.env.PUBLIC_HOST || "localhost", "/") },
                                                description: "\u041F\u043E\u043F\u043E\u043B\u043D\u0435\u043D\u0438\u0435 Aither: ".concat(tokens.toLocaleString(), " \u0442\u043E\u043A\u0435\u043D\u043E\u0432"),
                                                metadata: { txn_id: txnId, org_id: org_id },
                                            }),
                                        })];
                                case 6:
                                    ykRes = _c.sent();
                                    return [4 /*yield*/, ykRes.json()];
                                case 7:
                                    ykData = _c.sent();
                                    if (!(ykRes.ok && ((_b = ykData.confirmation) === null || _b === void 0 ? void 0 : _b.confirmation_url))) return [3 /*break*/, 9];
                                    return [4 /*yield*/, pool.query("UPDATE payment_transactions SET provider_payment_id=$1, meta=$2 WHERE txn_id=$3", [ykData.id, JSON.stringify(ykData), txnId])];
                                case 8:
                                    _c.sent();
                                    return [2 /*return*/, reply.send({
                                            ok: true,
                                            txn_id: txnId,
                                            confirmation_url: ykData.confirmation.confirmation_url,
                                            status: "pending",
                                        })];
                                case 9: return [2 /*return*/, reply.status(502).send({ error: "yookassa error", detail: ykData })];
                                case 10:
                                    e_17 = _c.sent();
                                    return [2 /*return*/, reply.status(502).send({ error: "yookassa error: " + safeError(e_17) })];
                                case 11: return [2 /*return*/];
                            }
                        });
                    }); });
                    // YooKassa webhook — called by YooKassa when payment status changes
                    app.post("/api/v1/billing/webhook", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var body, event_1, payment, txnId, txn, tier, txnMeta, effectiveTier, e_18;
                        var _a, _b;
                        return __generator(this, function (_c) {
                            switch (_c.label) {
                                case 0:
                                    _c.trys.push([0, 10, , 11]);
                                    body = req.body;
                                    event_1 = body === null || body === void 0 ? void 0 : body.event;
                                    payment = body === null || body === void 0 ? void 0 : body.object;
                                    if (!(event_1 === "payment.succeeded" && (payment === null || payment === void 0 ? void 0 : payment.status) === "succeeded")) return [3 /*break*/, 9];
                                    txnId = (_a = payment.metadata) === null || _a === void 0 ? void 0 : _a.txn_id;
                                    if (!txnId)
                                        return [2 /*return*/, reply.send({ ok: false, error: "no txn_id in metadata" })];
                                    return [4 /*yield*/, pool.query("SELECT txn_id, org_id, tokens, status, meta FROM payment_transactions WHERE txn_id=$1", [txnId])];
                                case 1:
                                    txn = _c.sent();
                                    if (txn.rows.length === 0)
                                        return [2 /*return*/, reply.send({ ok: false, error: "txn not found" })];
                                    if (txn.rows[0].status === "succeeded")
                                        return [2 /*return*/, reply.send({ ok: true, status: "already_processed" })];
                                    tier = (_b = payment.metadata) === null || _b === void 0 ? void 0 : _b.tier;
                                    txnMeta = safeJsonParse(txn.rows[0].meta) || {};
                                    effectiveTier = tier || txnMeta.tier;
                                    // Mark succeeded + credit tokens
                                    return [4 /*yield*/, pool.query("BEGIN")];
                                case 2:
                                    // Mark succeeded + credit tokens
                                    _c.sent();
                                    return [4 /*yield*/, pool.query("UPDATE payment_transactions SET status='succeeded', updated_at=now(), meta=$1 WHERE txn_id=$2", [JSON.stringify(payment), txnId])];
                                case 3:
                                    _c.sent();
                                    if (!(txn.rows[0].tokens > 0)) return [3 /*break*/, 5];
                                    return [4 /*yield*/, pool.query("INSERT INTO billing_accounts (org_id, reserved, total_tokens)\n             VALUES ($1, 0, $2)\n             ON CONFLICT (org_id) DO UPDATE SET total_tokens = billing_accounts.total_tokens + $2", [txn.rows[0].org_id, txn.rows[0].tokens])];
                                case 4:
                                    _c.sent();
                                    _c.label = 5;
                                case 5:
                                    if (!effectiveTier) return [3 /*break*/, 7];
                                    return [4 /*yield*/, pool.query("UPDATE billing_accounts SET tier=$1, updated_at=now() WHERE org_id=$2", [effectiveTier, txn.rows[0].org_id])];
                                case 6:
                                    _c.sent();
                                    _c.label = 7;
                                case 7: return [4 /*yield*/, pool.query("COMMIT")];
                                case 8:
                                    _c.sent();
                                    return [2 /*return*/, reply.send({ ok: true, status: effectiveTier ? "tier_upgraded" : "credited" })];
                                case 9: return [2 /*return*/, reply.send({ ok: true, status: "ignored", event: event_1 })];
                                case 10:
                                    e_18 = _c.sent();
                                    return [2 /*return*/, reply.status(500).send({ ok: false, error: safeError(e_18) })];
                                case 11: return [2 /*return*/];
                            }
                        });
                    }); });
                    // List payment transactions for org
                    app.get("/api/v1/billing/payments", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, m, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.query.org_id;
                                    if (!orgId)
                                        return [2 /*return*/, reply.status(400).send({ error: "org_id required" })];
                                    return [4 /*yield*/, pool.query("SELECT 1 FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id])];
                                case 1:
                                    m = _a.sent();
                                    if (m.rows.length === 0)
                                        return [2 /*return*/, reply.status(403).send({ error: "not a member" })];
                                    return [4 /*yield*/, pool.query("SELECT txn_id, provider, amount_rub, tokens, status, created_at\n       FROM payment_transactions WHERE org_id=$1 ORDER BY created_at DESC LIMIT 50", [orgId])];
                                case 2:
                                    r = _a.sent();
                                    return [2 /*return*/, reply.send({ payments: r.rows })];
                            }
                        });
                    }); });
                    // === Tariff plans ===
                    app.get("/api/v1/tiers", function (_req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var r, e_19;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    _a.trys.push([0, 2, , 3]);
                                    return [4 /*yield*/, pool.query("SELECT tier_id, name, description, rpm_limit, tpm_limit, daily_request_limit, models, rag_enabled, priority, price_rub_month, features FROM subscription_tiers ORDER BY priority")];
                                case 1:
                                    r = _a.sent();
                                    return [2 /*return*/, reply.send({ tiers: r.rows })];
                                case 2:
                                    e_19 = _a.sent();
                                    return [2 /*return*/, reply.status(500).send({ error: safeError(e_19) })];
                                case 3: return [2 /*return*/];
                            }
                        });
                    }); });
                    app.get("/api/v1/org/tier", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, r, e_20;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.query.org_id;
                                    if (!orgId)
                                        return [2 /*return*/, reply.status(400).send({ error: "org_id required" })];
                                    _a.label = 1;
                                case 1:
                                    _a.trys.push([1, 3, , 4]);
                                    return [4 /*yield*/, pool.query("SELECT b.tier, t.name, t.rpm_limit, t.tpm_limit, t.daily_request_limit, t.models, t.rag_enabled, t.priority, t.price_rub_month, t.features\n         FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier = t.tier_id WHERE b.org_id=$1", [orgId])];
                                case 2:
                                    r = _a.sent();
                                    if (r.rows.length === 0)
                                        return [2 /*return*/, reply.send({ org_id: orgId, tier: "free", name: "Free" })];
                                    return [2 /*return*/, reply.send(r.rows[0])];
                                case 3:
                                    e_20 = _a.sent();
                                    return [2 /*return*/, reply.status(500).send({ error: safeError(e_20) })];
                                case 4: return [2 /*return*/];
                            }
                        });
                    }); });
                    // === Tier upgrade ===
                    app.post("/api/v1/orgs/:orgId/upgrade", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, tier, m, t, r;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.params.orgId;
                                    tier = req.body.tier;
                                    if (!tier)
                                        return [2 /*return*/, reply.status(400).send({ error: "tier required (free|standard|vip|enterprise)" })];
                                    return [4 /*yield*/, pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id])];
                                case 1:
                                    m = _a.sent();
                                    if (m.rows.length === 0)
                                        return [2 /*return*/, reply.status(403).send({ error: "not a member" })];
                                    return [4 /*yield*/, pool.query("SELECT tier_id FROM subscription_tiers WHERE tier_id=$1", [tier])];
                                case 2:
                                    t = _a.sent();
                                    if (t.rows.length === 0)
                                        return [2 /*return*/, reply.status(400).send({ error: "invalid tier" })];
                                    return [4 /*yield*/, pool.query("UPDATE billing_accounts SET tier=$1, updated_at=now() WHERE org_id=$2", [tier, orgId])];
                                case 3:
                                    _a.sent();
                                    return [4 /*yield*/, pool.query("SELECT b.tier, t.name, t.rpm_limit, t.tpm_limit, t.daily_request_limit, t.models, t.rag_enabled, t.priority\n       FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier = t.tier_id WHERE b.org_id=$1", [orgId])];
                                case 4:
                                    r = _a.sent();
                                    return [2 /*return*/, reply.send({ ok: true, tier: r.rows[0] })];
                            }
                        });
                    }); });
                    // === Purchase tier (with payment) ===
                    app.post("/api/v1/orgs/:orgId/purchase-tier", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var p, orgId, tier, m, t, tierInfo, price, r, txn, txnId, r, ykRes, ykData, e_21;
                        var _a;
                        return __generator(this, function (_b) {
                            switch (_b.label) {
                                case 0:
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    orgId = req.params.orgId;
                                    tier = req.body.tier;
                                    if (!tier)
                                        return [2 /*return*/, reply.status(400).send({ error: "tier required" })];
                                    return [4 /*yield*/, pool.query("SELECT role FROM portal_org_members WHERE org_id=$1 AND user_id=$2 AND status='active'", [orgId, p.user_id])];
                                case 1:
                                    m = _b.sent();
                                    if (m.rows.length === 0)
                                        return [2 /*return*/, reply.status(403).send({ error: "not a member" })];
                                    return [4 /*yield*/, pool.query("SELECT tier_id, name, price_rub_month FROM subscription_tiers WHERE tier_id=$1", [tier])];
                                case 2:
                                    t = _b.sent();
                                    if (t.rows.length === 0)
                                        return [2 /*return*/, reply.status(400).send({ error: "invalid tier" })];
                                    tierInfo = t.rows[0];
                                    price = Number(tierInfo.price_rub_month) || 0;
                                    if (!(price === 0)) return [3 /*break*/, 5];
                                    return [4 /*yield*/, pool.query("UPDATE billing_accounts SET tier=$1, updated_at=now() WHERE org_id=$2", [tier, orgId])];
                                case 3:
                                    _b.sent();
                                    return [4 /*yield*/, pool.query("SELECT b.tier, t.name FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier=t.tier_id WHERE b.org_id=$1", [orgId])];
                                case 4:
                                    r = _b.sent();
                                    return [2 /*return*/, reply.send({ ok: true, tier: r.rows[0], paid: false })];
                                case 5: return [4 /*yield*/, pool.query("INSERT INTO payment_transactions (org_id, user_id, provider, amount_rub, tokens, status, meta)\n       VALUES ($1,$2,'yookassa',$3,0,'pending',$4) RETURNING txn_id", [orgId, p.user_id, price, JSON.stringify({ tier: tier, tier_name: tierInfo.name })])];
                                case 6:
                                    txn = _b.sent();
                                    txnId = txn.rows[0].txn_id;
                                    if (!(!YOOKASSA_SHOP_ID || !YOOKASSA_SECRET)) return [3 /*break*/, 10];
                                    return [4 /*yield*/, pool.query("UPDATE billing_accounts SET tier=$1, updated_at=now() WHERE org_id=$2", [tier, orgId])];
                                case 7:
                                    _b.sent();
                                    return [4 /*yield*/, pool.query("UPDATE payment_transactions SET status='succeeded', updated_at=now(), meta=$1 WHERE txn_id=$2", [JSON.stringify({ dev_mode: true, tier: tier }), txnId])];
                                case 8:
                                    _b.sent();
                                    return [4 /*yield*/, pool.query("SELECT b.tier, t.name FROM billing_accounts b LEFT JOIN subscription_tiers t ON b.tier=t.tier_id WHERE b.org_id=$1", [orgId])];
                                case 9:
                                    r = _b.sent();
                                    return [2 /*return*/, reply.send({ ok: true, tier: r.rows[0], paid: false, dev_mode: true })];
                                case 10:
                                    _b.trys.push([10, 15, , 16]);
                                    return [4 /*yield*/, fetch("https://api.yookassa.ru/v3/payments", {
                                            method: "POST",
                                            headers: {
                                                "Content-Type": "application/json",
                                                "Authorization": "Basic " + Buffer.from(YOOKASSA_SHOP_ID + ":" + YOOKASSA_SECRET).toString("base64"),
                                                "Idempotence-Key": txnId,
                                            },
                                            body: JSON.stringify({
                                                amount: { value: price.toFixed(2), currency: "RUB" },
                                                confirmation: { type: "redirect", return_url: "https://".concat(process.env.PUBLIC_HOST || "localhost", ":10443/#tiers") },
                                                description: "Aither: \u0442\u0430\u0440\u0438\u0444 \u00AB".concat(tierInfo.name, "\u00BB"),
                                                metadata: { txn_id: txnId, org_id: orgId, tier: tier },
                                            }),
                                        })];
                                case 11:
                                    ykRes = _b.sent();
                                    return [4 /*yield*/, ykRes.json()];
                                case 12:
                                    ykData = _b.sent();
                                    if (!(ykRes.ok && ((_a = ykData.confirmation) === null || _a === void 0 ? void 0 : _a.confirmation_url))) return [3 /*break*/, 14];
                                    return [4 /*yield*/, pool.query("UPDATE payment_transactions SET provider_payment_id=$1, meta=$2 WHERE txn_id=$3", [ykData.id, JSON.stringify(ykData), txnId])];
                                case 13:
                                    _b.sent();
                                    return [2 /*return*/, reply.send({
                                            ok: true,
                                            txn_id: txnId,
                                            confirmation_url: ykData.confirmation.confirmation_url,
                                            status: "pending",
                                        })];
                                case 14: return [2 /*return*/, reply.status(502).send({ error: "yookassa error", detail: ykData })];
                                case 15:
                                    e_21 = _b.sent();
                                    return [2 /*return*/, reply.status(502).send({ error: "yookassa error: " + safeError(e_21) })];
                                case 16: return [2 /*return*/];
                            }
                        });
                    }); });
                    ADMIN_KEY = process.env.ADMIN_KEY || "";
                    // Proxy /api/v1/admin/* → Gateway /admin/*
                    // Admin users — handled locally (portal DB)
    app.get("/api/v1/admin/users", function (req, reply) { return __awaiter(void 0, void 0, void 0, function () {
        var adminHeader, isAdminKey, p, orgs, r;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    adminHeader = req.headers["x-admin-key"] || "";
                    isAdminKey = ADMIN_KEY && adminHeader === ADMIN_KEY;
                    if (isAdminKey) return [3 /*break*/, 3];
                    p = auth(req, reply);
                    if (!p) return [2 /*return*/];
                    return [4 /*yield*/, pool.query("SELECT role FROM portal_org_members WHERE user_id= AND role='owner' AND status='active' LIMIT 1", [p.user_id])];
                case 1:
                    orgs = _a.sent();
                    if (!(orgs.rows.length === 0)) return [3 /*break*/, 3];
                    return [2 /*return*/, reply.status(403).send({ error: "admin access required" })];
                case 2: return [3 /*break*/, 3];
                case 3: return [4 /*yield*/, pool.query("SELECT u.user_id, u.display_name, u.email, u.oauth_provider as provider, (SELECT count(*) FROM portal_org_members m WHERE m.user_id = u.user_id AND m.status = 'active') as org_count FROM portal_users u ORDER BY u.created_at DESC LIMIT 50")];
                case 4:
                    r = _a.sent();
                    return [2 /*return*/, reply.send({ users: r.rows })];
            }
        });
    }); });

    app.post("/api/v1/admin/users/:userId/role", function (req, reply) { return __awaiter(void 0, void 0, void 0, function () {
        return __generator(this, function (_a) {
            return [2 /*return*/, reply.send({ status: "ok", note: "role change not yet implemented" })];
        });
    }); });

    app.get("/api/v1/admin/tiers", function (req, reply) { return __awaiter(void 0, void 0, void 0, function () {
        var r;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, pool.query("SELECT * FROM subscription_tiers ORDER BY name")];
                case 1:
                    r = _a.sent();
                    return [2 /*return*/, reply.send({ tiers: r.rows })];
            }
        });
    }); });

app.all("/api/v1/admin/*", function (req, reply) { return __awaiter(_this, void 0, void 0, function () {
                        var adminHeader, isAdminKey, p, orgs, path, gwUrl, method, headers, ADMIN_JWT_SECRET, adminToken, body, resp, data, e_22;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    adminHeader = req.headers["x-admin-key"] || "";
                                    isAdminKey = ADMIN_KEY && adminHeader === ADMIN_KEY;
                                    if (!!isAdminKey) return [3 /*break*/, 2];
                                    p = auth(req, reply);
                                    if (!p)
                                        return [2 /*return*/];
                                    return [4 /*yield*/, pool.query("SELECT role FROM portal_org_members WHERE user_id=$1 AND role='owner' AND status='active' LIMIT 1", [p.user_id])];
                                case 1:
                                    orgs = _a.sent();
                                    if (orgs.rows.length === 0)
                                        return [2 /*return*/, reply.status(403).send({ error: "admin access required" })];
                                    _a.label = 2;
                                case 2:
                                    path = req.params["*"];
                                    gwUrl = "".concat(CORE_API.replace(/\/v1\/?$/, ""), "/admin/").concat(path);
                                    _a.label = 3;
                                case 3:
                                    _a.trys.push([3, 6, , 7]);
                                    method = req.method;
                                    headers = { "Content-Type": "application/json", "X-Admin-Key": adminHeader };
                                    ADMIN_JWT_SECRET = process.env.ADMIN_JWT_SECRET || "aither-admin-secret";
                                    adminToken = jsonwebtoken_1.default.sign({ role: "admin", iat: Math.floor(Date.now() / 1000) }, ADMIN_JWT_SECRET, { algorithm: "HS256", expiresIn: "5m" });
                                    headers["Authorization"] = "Bearer ".concat(adminToken);
                                    body = void 0;
                                    if (method === "POST" || method === "PUT") {
                                        body = JSON.stringify(req.body);
                                        headers["Content-Length"] = String(body.length);
                                    }
                                    return [4 /*yield*/, fetch(gwUrl, { method: method, headers: headers, body: body })];
                                case 4:
                                    resp = _a.sent();
                                    return [4 /*yield*/, resp.json()];
                                case 5:
                                    data = _a.sent();
                                    return [2 /*return*/, reply.status(resp.status).send(data)];
                                case 6:
                                    e_22 = _a.sent();
                                    return [2 /*return*/, reply.status(502).send({ error: "gateway unreachable", detail: safeError(e_22) })];
                                case 7: return [2 /*return*/];
                            }
                        });
                    }); });
                    listenHost = IS_PRODUCTION ? "127.0.0.1" : "0.0.0.0";
                    return [4 /*yield*/, app.listen({ port: PORT, host: listenHost })];
                case 5:
                    _a.sent();
                    console.log("Portal BFF v0.6.0 (security-hardened) on ".concat(listenHost, ":").concat(PORT));
                    return [2 /*return*/];
            }
        });
    });
}
main().catch(function (e) { console.error(e); process.exit(1); });
