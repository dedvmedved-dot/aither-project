"use strict";
/**
 * Aither Portal — Organization Security Policies.
 *
 * Каждая организация имеет настраиваемый профиль безопасности.
 * Политики переопределяют глобальные настройки и ограничения тарифного плана
 * (например, тариф VIP разрешает всё, но владелец может включить DLP).
 */
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.POLICIES_DDL = exports.DEFAULT_POLICY = void 0;
exports.loadPolicy = loadPolicy;
exports.savePolicy = savePolicy;
exports.validatePolicy = validatePolicy;
// ---- DEFAULTS ----
exports.DEFAULT_POLICY = {
    dlp_enabled: true,
    jailbreak_detection: true,
    sensitive_data_patterns: [],
    allowed_ip_cidrs: [],
    mfa_required: false,
    session_timeout_min: 1440, // 24 hours
    api_key_max_age_days: 365, // 1 year
    api_key_rotation_required: false,
    custom_rpm: null, // use tier default
    custom_tpm: null,
    max_concurrent_requests: null,
    allowed_models: [],
    max_tokens_per_request: null, // no limit
    chat_retention_days: 90,
    audit_log_retention_days: 365,
    chat_enabled: true,
};
// ---- DDL ----
exports.POLICIES_DDL = "\n  CREATE TABLE IF NOT EXISTS portal_org_policies (\n    org_id UUID PRIMARY KEY REFERENCES portal_organizations(org_id) ON DELETE CASCADE,\n\n    -- DLP / Content filtering\n    dlp_enabled            BOOLEAN   NOT NULL DEFAULT true,\n    jailbreak_detection    BOOLEAN   NOT NULL DEFAULT true,\n    sensitive_data_patterns TEXT[]    DEFAULT '{}',\n\n    -- Access control\n    allowed_ip_cidrs       TEXT[]    DEFAULT '{}',\n    mfa_required           BOOLEAN   NOT NULL DEFAULT false,\n    session_timeout_min    INTEGER   NOT NULL DEFAULT 1440,\n\n    -- API key policies\n    api_key_max_age_days   INTEGER,          -- NULL = no expiration\n    api_key_rotation_required BOOLEAN NOT NULL DEFAULT false,\n\n    -- Rate limits (override tier, NULL = use tier default)\n    custom_rpm             INTEGER,\n    custom_tpm             INTEGER,\n    max_concurrent_requests INTEGER,\n\n    -- Models & tokens\n    allowed_models         TEXT[]    DEFAULT '{}',\n    max_tokens_per_request  INTEGER,\n\n    -- Data retention\n    chat_retention_days    INTEGER   NOT NULL DEFAULT 90,\n    audit_log_retention_days INTEGER  NOT NULL DEFAULT 365,\n\n    -- Feature toggles\n    chat_enabled           BOOLEAN   NOT NULL DEFAULT true,\n\n    -- Metadata\n    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),\n    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()\n  );\n";
// ---- LOAD / SAVE ----
/** Load policy for org. Returns defaults if not configured yet. */
function loadPolicy(pool, orgId) {
    return __awaiter(this, void 0, void 0, function () {
        var r, row;
        var _a;
        return __generator(this, function (_b) {
            switch (_b.label) {
                case 0: return [4 /*yield*/, pool.query("SELECT * FROM portal_org_policies WHERE org_id = $1", [orgId])];
                case 1:
                    r = _b.sent();
                    if (r.rows.length === 0)
                        return [2 /*return*/, __assign({}, exports.DEFAULT_POLICY)];
                    row = r.rows[0];
                    return [2 /*return*/, {
                            dlp_enabled: row.dlp_enabled,
                            jailbreak_detection: row.jailbreak_detection,
                            sensitive_data_patterns: row.sensitive_data_patterns || [],
                            allowed_ip_cidrs: row.allowed_ip_cidrs || [],
                            mfa_required: row.mfa_required,
                            session_timeout_min: row.session_timeout_min,
                            api_key_max_age_days: row.api_key_max_age_days,
                            api_key_rotation_required: row.api_key_rotation_required,
                            custom_rpm: row.custom_rpm,
                            custom_tpm: row.custom_tpm,
                            max_concurrent_requests: row.max_concurrent_requests,
                            allowed_models: row.allowed_models || [],
                            max_tokens_per_request: row.max_tokens_per_request,
                            chat_retention_days: row.chat_retention_days,
                            audit_log_retention_days: row.audit_log_retention_days,
                            chat_enabled: (_a = row.chat_enabled) !== null && _a !== void 0 ? _a : exports.DEFAULT_POLICY.chat_enabled,
                        }];
            }
        });
    });
}
/** Upsert policy for org. */
function savePolicy(pool, orgId, policy) {
    return __awaiter(this, void 0, void 0, function () {
        var current, merged;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, loadPolicy(pool, orgId)];
                case 1:
                    current = _a.sent();
                    merged = __assign(__assign({}, current), policy);
                    return [4 /*yield*/, pool.query("\n    INSERT INTO portal_org_policies (\n      org_id, dlp_enabled, jailbreak_detection, sensitive_data_patterns,\n      allowed_ip_cidrs, mfa_required, session_timeout_min,\n      api_key_max_age_days, api_key_rotation_required,\n      custom_rpm, custom_tpm, max_concurrent_requests,\n      allowed_models, max_tokens_per_request,\n      chat_retention_days, audit_log_retention_days, chat_enabled, updated_at\n    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,now())\n    ON CONFLICT (org_id) DO UPDATE SET\n      dlp_enabled              = EXCLUDED.dlp_enabled,\n      jailbreak_detection      = EXCLUDED.jailbreak_detection,\n      sensitive_data_patterns  = EXCLUDED.sensitive_data_patterns,\n      allowed_ip_cidrs        = EXCLUDED.allowed_ip_cidrs,\n      mfa_required             = EXCLUDED.mfa_required,\n      session_timeout_min      = EXCLUDED.session_timeout_min,\n      api_key_max_age_days      = EXCLUDED.api_key_max_age_days,\n      api_key_rotation_required = EXCLUDED.api_key_rotation_required,\n      custom_rpm               = EXCLUDED.custom_rpm,\n      custom_tpm               = EXCLUDED.custom_tpm,\n      max_concurrent_requests  = EXCLUDED.max_concurrent_requests,\n      allowed_models           = EXCLUDED.allowed_models,\n      max_tokens_per_request    = EXCLUDED.max_tokens_per_request,\n      chat_retention_days      = EXCLUDED.chat_retention_days,\n      audit_log_retention_days = EXCLUDED.audit_log_retention_days,\n      chat_enabled             = EXCLUDED.chat_enabled,\n      updated_at               = now()\n  ", [
                            orgId,
                            merged.dlp_enabled,
                            merged.jailbreak_detection,
                            merged.sensitive_data_patterns,
                            merged.allowed_ip_cidrs,
                            merged.mfa_required,
                            merged.session_timeout_min,
                            merged.api_key_max_age_days,
                            merged.api_key_rotation_required,
                            merged.custom_rpm,
                            merged.custom_tpm,
                            merged.max_concurrent_requests,
                            merged.allowed_models,
                            merged.max_tokens_per_request,
                            merged.chat_retention_days,
                            merged.audit_log_retention_days,
                            merged.chat_enabled,
                        ])];
                case 2:
                    _a.sent();
                    return [2 /*return*/, merged];
            }
        });
    });
}
/** Validate policy values (for API input). Returns error string or null. */
function validatePolicy(policy) {
    if (policy.session_timeout_min !== undefined) {
        if (typeof policy.session_timeout_min !== "number" || policy.session_timeout_min < 5)
            return "session_timeout_min must be >= 5 minutes";
    }
    if (policy.api_key_max_age_days !== undefined && policy.api_key_max_age_days !== null) {
        if (typeof policy.api_key_max_age_days !== "number" || policy.api_key_max_age_days < 1)
            return "api_key_max_age_days must be >= 1 or null";
    }
    if (policy.custom_rpm !== undefined && policy.custom_rpm !== null) {
        if (typeof policy.custom_rpm !== "number" || policy.custom_rpm < 1)
            return "custom_rpm must be >= 1 or null";
    }
    if (policy.custom_tpm !== undefined && policy.custom_tpm !== null) {
        if (typeof policy.custom_tpm !== "number" || policy.custom_tpm < 1)
            return "custom_tpm must be >= 1 or null";
    }
    if (policy.max_concurrent_requests !== undefined && policy.max_concurrent_requests !== null) {
        if (typeof policy.max_concurrent_requests !== "number" || policy.max_concurrent_requests < 1)
            return "max_concurrent_requests must be >= 1 or null";
    }
    if (policy.max_tokens_per_request !== undefined && policy.max_tokens_per_request !== null) {
        if (typeof policy.max_tokens_per_request !== "number" || policy.max_tokens_per_request < 1)
            return "max_tokens_per_request must be >= 1 or null";
    }
    if (policy.chat_retention_days !== undefined) {
        if (typeof policy.chat_retention_days !== "number" || policy.chat_retention_days < 1)
            return "chat_retention_days must be >= 1";
    }
    return null; // valid
}
