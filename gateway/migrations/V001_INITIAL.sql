-- V001_INITIAL: Initial schema for Aither Gateway
-- Created: CHANGE-0022-C2

CREATE TABLE IF NOT EXISTS billing_accounts (
    org_id VARCHAR(128) PRIMARY KEY,
    balance BIGINT NOT NULL DEFAULT 1000000 CHECK (balance >= 0),
    reserved BIGINT NOT NULL DEFAULT 0 CHECK (reserved >= 0),
    tier VARCHAR(32) NOT NULL DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing_ledger (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(128) NOT NULL,
    reservation_id VARCHAR(64) NOT NULL,
    operation VARCHAR(16) NOT NULL CHECK (operation IN ('reserve','settle','refund','reaper_refund')),
    amount BIGINT NOT NULL,
    balance_before BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing_reservations (
    reservation_id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(128) NOT NULL,
    idempotency_key VARCHAR(256) NOT NULL UNIQUE,
    request_id VARCHAR(64),
    user_id VARCHAR(128),
    model_id VARCHAR(64),
    estimated_input_tokens INT DEFAULT 0,
    max_output_tokens INT DEFAULT 256,
    reserved_amount BIGINT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'reserved' CHECK (status IN ('reserved','settled','refunded','expired','failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '5 minutes'
);

CREATE TABLE IF NOT EXISTS usage_records (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL,
    org_id VARCHAR(128) NOT NULL,
    model_id VARCHAR(64),
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    http_status INT,
    billing_status VARCHAR(16),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portal_api_keys (
    api_key VARCHAR(256) PRIMARY KEY,
    org_id VARCHAR(128) NOT NULL,
    user_id VARCHAR(128),
    tier VARCHAR(32) DEFAULT 'free',
    status VARCHAR(16) DEFAULT 'active' CHECK (status IN ('active','revoked','expired')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gateway_audit_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    org_id VARCHAR(128),
    user_id VARCHAR(128),
    request_id VARCHAR(64),
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gateway_idempotency (
    idempotency_key VARCHAR(256) PRIMARY KEY,
    org_id VARCHAR(128) NOT NULL,
    reservation_id VARCHAR(64),
    result_status VARCHAR(16),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscription_tiers (
    tier VARCHAR(32) PRIMARY KEY,
    rpm_limit INT DEFAULT 300,
    tpm_limit INT DEFAULT 100000,
    daily_request_limit INT DEFAULT 1000,
    daily_token_limit INT DEFAULT 1000000,
    model_scope TEXT DEFAULT 'qwen-14b',
    has_rag BOOLEAN DEFAULT false,
    has_32b BOOLEAN DEFAULT false,
    priority INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS model_drain_state (
    model_id VARCHAR(64) PRIMARY KEY,
    drained BOOLEAN DEFAULT false,
    drained_at TIMESTAMPTZ,
    drain_reason TEXT
);

CREATE TABLE IF NOT EXISTS rag_documents (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(128) NOT NULL,
    collection_name VARCHAR(128) NOT NULL DEFAULT 'default',
    document_id VARCHAR(256) NOT NULL,
    title VARCHAR(512),
    content_hash VARCHAR(128),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, collection_name, document_id)
);

CREATE TABLE IF NOT EXISTS rag_collections (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(128) NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, name)
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO subscription_tiers (tier, rpm_limit, tpm_limit) VALUES ('free', 300, 100000) ON CONFLICT DO NOTHING;
INSERT INTO schema_migrations (version) VALUES ('V001_INITIAL') ON CONFLICT DO NOTHING;
