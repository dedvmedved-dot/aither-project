-- Fix: org_id type UUID → TEXT
-- Портал передаёт короткую форму org_id (8 символов), а не полный UUID.
-- Колонки типа uuid не принимают короткую форму → ошибки 500/402.

-- VPS2 (портал) — таблица chats
ALTER TABLE chats DROP CONSTRAINT IF EXISTS chats_org_id_fkey;
ALTER TABLE chats ALTER COLUMN org_id TYPE text;

-- K8s PostgreSQL (Gateway) — таблицы биллинга и учёта
ALTER TABLE billing_accounts ALTER COLUMN org_id TYPE text;
ALTER TABLE billing_ledger ALTER COLUMN org_id TYPE text;
ALTER TABLE usage_records ALTER COLUMN org_id TYPE text;
