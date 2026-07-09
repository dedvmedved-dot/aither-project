-- Этап 5: Multi-tenant — тарифные планы (Free/Standard/VIP/Enterprise)
-- Выполнить на K8s PostgreSQL (Gateway)

BEGIN;

-- 1. Таблица тарифов
CREATE TABLE IF NOT EXISTS subscription_tiers (
    tier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    rpm_limit INTEGER NOT NULL,
    tpm_limit INTEGER NOT NULL,
    daily_request_limit INTEGER,          -- NULL = безлимит
    models TEXT[] NOT NULL DEFAULT '{}',   -- какие модели доступны
    rag_enabled BOOLEAN NOT NULL DEFAULT false,
    priority INTEGER NOT NULL DEFAULT 0,   -- выше = лучше очередь
    price_rub_month INTEGER,               -- NULL = бесплатно
    features TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Добавляем tier в billing_accounts
ALTER TABLE billing_accounts ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'free';

-- 3. Seed-данные: 4 тарифа
INSERT INTO subscription_tiers (tier_id, name, description, rpm_limit, tpm_limit, daily_request_limit, models, rag_enabled, priority, price_rub_month, features) VALUES

('free', 'Free', 'Для ознакомления и тестирования', 30, 30000, 100,
 ARRAY['qwen2.5-14b'],
 false, 0, NULL,
 ARRAY['Доступ к 14B модели','100 запросов/день','Общая очередь','Базовый чат']),

('standard', 'Standard', 'Для регулярной работы', 60, 100000, 1000,
 ARRAY['qwen2.5-14b', 'qwen2.5-32b'],
 false, 10, 1990,
 ARRAY['Обе модели (14B + 32B)','1000 запросов/день','Приоритетная очередь','API-доступ','Техподдержка в чате']),

('vip', 'VIP', 'Для интенсивной разработки', 120, 200000, 10000,
 ARRAY['qwen2.5-14b', 'qwen2.5-32b', 'astra-14b'],
 true, 20, 4990,
 ARRAY['Все модели + LoRA','RAG-подсистема','10000 запросов/день','Выделенные GPU-слоты','Приоритетная поддержка','Audit-log']),

('enterprise', 'Enterprise', 'On-premise и кастомные решения', 999999, 99999999, NULL,
 ARRAY['qwen2.5-14b', 'qwen2.5-32b', 'astra-14b'],
 true, 100, NULL,
 ARRAY['On-premise развёртывание','Кастомные модели','SLA 99.9%','Выделенная инфраструктура','Аудит безопасности','Персональный менеджер'])

ON CONFLICT (tier_id) DO UPDATE SET
    rpm_limit = EXCLUDED.rpm_limit,
    tpm_limit = EXCLUDED.tpm_limit,
    daily_request_limit = EXCLUDED.daily_request_limit,
    models = EXCLUDED.models,
    rag_enabled = EXCLUDED.rag_enabled,
    priority = EXCLUDED.priority,
    features = EXCLUDED.features;

COMMIT;
