#!/usr/bin/env python3
"""Create billing_idempotency table and enhance gateway_idempotency."""
import os, psycopg2, sys

PG_URL = os.environ.get("PG_URL", "postgresql://postgres:aiops_pass@postgres.aiops.svc:5432/aither")
conn = psycopg2.connect(PG_URL)
cur = conn.cursor()

DDL = """
-- Enhanced idempotency table for billing operations
CREATE TABLE IF NOT EXISTS billing_idempotency (
    idempotency_key     VARCHAR(128) PRIMARY KEY,
    request_fingerprint VARCHAR(64) NOT NULL,
    organisation        VARCHAR(64) NOT NULL,
    model               VARCHAR(64),
    reservation_id      VARCHAR(64),
    processing_status   VARCHAR(32) NOT NULL DEFAULT 'pending',
    http_status         INTEGER,
    sanitized_response_ref TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    expiry              TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Add fingerprint column to gateway_idempotency if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'gateway_idempotency' AND column_name = 'request_fingerprint'
    ) THEN
        ALTER TABLE gateway_idempotency ADD COLUMN request_fingerprint VARCHAR(64);
        ALTER TABLE gateway_idempotency ADD COLUMN http_status INTEGER;
        ALTER TABLE gateway_idempotency ADD COLUMN sanitized_response_ref TEXT;
        ALTER TABLE gateway_idempotency ADD COLUMN completed_at TIMESTAMPTZ;
        ALTER TABLE gateway_idempotency ADD COLUMN expiry TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours');
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_billing_idempotency_expiry ON billing_idempotency(expiry);
CREATE INDEX IF NOT EXISTS idx_billing_idempotency_org ON billing_idempotency(organisation);
CREATE INDEX IF NOT EXISTS idx_gateway_idempotency_expiry ON gateway_idempotency(expiry);
"""

cur.execute(DDL)
conn.commit()
print("Tables created/updated successfully")

# Verify
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='billing_idempotency' ORDER BY ordinal_position")
print("\nbilling_idempotency columns:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='gateway_idempotency' ORDER BY ordinal_position")
print("\ngateway_idempotency columns:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
print("\nDone.")
