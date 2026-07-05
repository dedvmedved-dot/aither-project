BEGIN;

CREATE TABLE portal_organizations (
    org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    aither_org_id UUID,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE portal_users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oauth_provider TEXT NOT NULL DEFAULT 'github',
    oauth_id TEXT NOT NULL,
    email TEXT,
    display_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ,
    UNIQUE(oauth_provider, oauth_id)
);

CREATE TABLE portal_org_members (
    membership_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES portal_organizations(org_id),
    user_id UUID NOT NULL REFERENCES portal_users(user_id),
    role TEXT NOT NULL DEFAULT 'developer'
        CHECK (role IN ('owner', 'billing_admin', 'developer', 'viewer')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(org_id, user_id)
);

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

COMMIT;
