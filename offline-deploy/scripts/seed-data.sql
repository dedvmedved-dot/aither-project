-- seed-data.sql — начальные данные для платформы
-- Создаёт администратора, организацию по умолчанию, схему биллинга

-- Схема биллинга (если не создана)
CREATE TABLE IF NOT EXISTS billing_accounts (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(64) UNIQUE NOT NULL,
    balance BIGINT NOT NULL DEFAULT 100000,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing_ledger (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL,
    amount BIGINT NOT NULL,
    operation VARCHAR(32) NOT NULL,
    model_id VARCHAR(64),
    tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL,
    key_hash VARCHAR(128) UNIQUE NOT NULL,
    key_prefix VARCHAR(16) NOT NULL,
    name VARCHAR(255),
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Начальный seed (будет выполнен через Portal BFF при первом запуске)
-- Регистрация первого администратора происходит через create-admin.sh
