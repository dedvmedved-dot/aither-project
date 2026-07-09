"use strict";
/**
 * Aither Portal — Organization Security Policies.
 *
 * Каждая организация имеет настраиваемый профиль безопасности.
 * Политики переопределяют глобальные настройки и ограничения тарифного плана
 * (например, тариф VIP разрешает всё, но владелец может включить DLP).
 */
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
};
// ---- DDL ----
exports.POLICIES_DDL = `
  CREATE TABLE IF NOT EXISTS portal_org_policies (
    org_id UUID PRIMARY KEY REFERENCES portal_organizations(org_id) ON DELETE CASCADE,

    -- DLP / Content filtering
    dlp_enabled            BOOLEAN   NOT NULL DEFAULT true,
    jailbreak_detection    BOOLEAN   NOT NULL DEFAULT true,
    sensitive_data_patterns TEXT[]    DEFAULT '{}',

    -- Access control
    allowed_ip_cidrs       TEXT[]    DEFAULT '{}',
    mfa_required           BOOLEAN   NOT NULL DEFAULT false,
    session_timeout_min    INTEGER   NOT NULL DEFAULT 1440,

    -- API key policies
    api_key_max_age_days   INTEGER,          -- NULL = no expiration
    api_key_rotation_required BOOLEAN NOT NULL DEFAULT false,

    -- Rate limits (override tier, NULL = use tier default)
    custom_rpm             INTEGER,
    custom_tpm             INTEGER,
    max_concurrent_requests INTEGER,

    -- Models & tokens
    allowed_models         TEXT[]    DEFAULT '{}',
    max_tokens_per_request  INTEGER,

    -- Data retention
    chat_retention_days    INTEGER   NOT NULL DEFAULT 90,
    audit_log_retention_days INTEGER  NOT NULL DEFAULT 365,

    -- Metadata
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
  );
`;
// ---- LOAD / SAVE ----
/** Load policy for org. Returns defaults if not configured yet. */
async function loadPolicy(pool, orgId) {
    const r = await pool.query("SELECT * FROM portal_org_policies WHERE org_id = $1", [orgId]);
    if (r.rows.length === 0)
        return { ...exports.DEFAULT_POLICY };
    const row = r.rows[0];
    return {
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
    };
}
/** Upsert policy for org. */
async function savePolicy(pool, orgId, policy) {
    const current = await loadPolicy(pool, orgId);
    const merged = { ...current, ...policy };
    await pool.query(`
    INSERT INTO portal_org_policies (
      org_id, dlp_enabled, jailbreak_detection, sensitive_data_patterns,
      allowed_ip_cidrs, mfa_required, session_timeout_min,
      api_key_max_age_days, api_key_rotation_required,
      custom_rpm, custom_tpm, max_concurrent_requests,
      allowed_models, max_tokens_per_request,
      chat_retention_days, audit_log_retention_days, updated_at
    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,now())
    ON CONFLICT (org_id) DO UPDATE SET
      dlp_enabled              = EXCLUDED.dlp_enabled,
      jailbreak_detection      = EXCLUDED.jailbreak_detection,
      sensitive_data_patterns  = EXCLUDED.sensitive_data_patterns,
      allowed_ip_cidrs        = EXCLUDED.allowed_ip_cidrs,
      mfa_required             = EXCLUDED.mfa_required,
      session_timeout_min      = EXCLUDED.session_timeout_min,
      api_key_max_age_days      = EXCLUDED.api_key_max_age_days,
      api_key_rotation_required = EXCLUDED.api_key_rotation_required,
      custom_rpm               = EXCLUDED.custom_rpm,
      custom_tpm               = EXCLUDED.custom_tpm,
      max_concurrent_requests  = EXCLUDED.max_concurrent_requests,
      allowed_models           = EXCLUDED.allowed_models,
      max_tokens_per_request    = EXCLUDED.max_tokens_per_request,
      chat_retention_days      = EXCLUDED.chat_retention_days,
      audit_log_retention_days = EXCLUDED.audit_log_retention_days,
      updated_at               = now()
  `, [
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
    ]);
    return merged;
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
