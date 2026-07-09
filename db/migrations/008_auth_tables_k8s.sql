-- Миграция: воссоздание auth-таблиц в K8s PG с точной схемой VPS2
BEGIN;

DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS chats CASCADE;
DROP TABLE IF EXISTS security_audit CASCADE;
DROP TABLE IF EXISTS payment_transactions CASCADE;
DROP TABLE IF EXISTS portal_api_keys CASCADE;
DROP TABLE IF EXISTS portal_org_members CASCADE;
DROP TABLE IF EXISTS portal_organizations CASCADE;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE portal_organizations (
    org_id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    aither_org_id uuid,
    status text DEFAULT 'active'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT portal_organizations_status_check CHECK ((status = ANY (ARRAY['active'::text, 'suspended'::text, 'deleted'::text])))
);
ALTER TABLE ONLY portal_organizations ADD CONSTRAINT portal_organizations_pkey PRIMARY KEY (org_id);

CREATE TABLE portal_org_members (
    membership_id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role text DEFAULT 'developer'::text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT portal_org_members_role_check CHECK ((role = ANY (ARRAY['owner'::text, 'billing_admin'::text, 'developer'::text, 'viewer'::text]))),
    CONSTRAINT portal_org_members_status_check CHECK ((status = ANY (ARRAY['active'::text, 'inactive'::text])))
);
ALTER TABLE ONLY portal_org_members ADD CONSTRAINT portal_org_members_pkey PRIMARY KEY (membership_id);
ALTER TABLE ONLY portal_org_members ADD CONSTRAINT portal_org_members_org_id_user_id_key UNIQUE (org_id, user_id);

CREATE TABLE portal_api_keys (
    key_id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid,
    api_key text NOT NULL,
    api_key_prefix text NOT NULL,
    name text DEFAULT 'default'::text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone,
    last_used_at timestamp with time zone,
    CONSTRAINT portal_api_keys_status_check CHECK ((status = ANY (ARRAY['active'::text, 'revoked'::text])))
);
ALTER TABLE ONLY portal_api_keys ADD CONSTRAINT portal_api_keys_pkey PRIMARY KEY (key_id);
ALTER TABLE ONLY portal_api_keys ADD CONSTRAINT portal_api_keys_api_key_key UNIQUE (api_key);

CREATE TABLE chats (
    chat_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    title text DEFAULT 'Новый чат'::text NOT NULL,
    model text DEFAULT 'qwen2.5-14b'::text NOT NULL,
    share_token text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    org_id text
);
ALTER TABLE ONLY chats ADD CONSTRAINT chats_pkey PRIMARY KEY (chat_id);
ALTER TABLE ONLY chats ADD CONSTRAINT chats_share_token_key UNIQUE (share_token);

CREATE TABLE chat_messages (
    message_id uuid DEFAULT gen_random_uuid() NOT NULL,
    chat_id uuid NOT NULL,
    role text NOT NULL,
    content text DEFAULT ''::text NOT NULL,
    tokens_used integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chat_messages_role_check CHECK ((role = ANY (ARRAY['user'::text, 'assistant'::text, 'system'::text])))
);
ALTER TABLE ONLY chat_messages ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (message_id);

CREATE TABLE security_audit (
    event_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    org_id uuid,
    chat_id uuid,
    category text NOT NULL,
    reason text NOT NULL,
    content_snippet text,
    model text,
    ip_address text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE ONLY security_audit ADD CONSTRAINT security_audit_pkey PRIMARY KEY (event_id);

CREATE TABLE payment_transactions (
    txn_id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid,
    user_id uuid,
    provider text DEFAULT 'yookassa'::text NOT NULL,
    provider_payment_id text,
    amount_rub numeric(12,2) NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    meta jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT payment_transactions_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'succeeded'::text, 'canceled'::text])))
);
ALTER TABLE ONLY payment_transactions ADD CONSTRAINT payment_transactions_pkey PRIMARY KEY (txn_id);

-- Foreign keys
ALTER TABLE ONLY portal_org_members ADD CONSTRAINT portal_org_members_org_id_fkey FOREIGN KEY (org_id) REFERENCES portal_organizations(org_id);
ALTER TABLE ONLY portal_org_members ADD CONSTRAINT portal_org_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES portal_users(user_id);
ALTER TABLE ONLY portal_api_keys ADD CONSTRAINT portal_api_keys_org_id_fkey FOREIGN KEY (org_id) REFERENCES portal_organizations(org_id);
ALTER TABLE ONLY chats ADD CONSTRAINT chats_user_id_fkey FOREIGN KEY (user_id) REFERENCES portal_users(user_id);
ALTER TABLE ONLY chat_messages ADD CONSTRAINT chat_messages_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE;
ALTER TABLE ONLY payment_transactions ADD CONSTRAINT payment_transactions_org_id_fkey FOREIGN KEY (org_id) REFERENCES portal_organizations(org_id);
ALTER TABLE ONLY payment_transactions ADD CONSTRAINT payment_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES portal_users(user_id);

COMMIT;
