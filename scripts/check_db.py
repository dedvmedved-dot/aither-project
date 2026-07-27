#!/usr/bin/env python3
"""Check DB schema."""
import os, psycopg2

PG_URL = os.environ["PG_URL"]  # mandatory

conn = psycopg2.connect(PG_URL)
cur = conn.cursor()

# Check idempotency tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%idempotency%'")
print("Idempotency tables:", cur.fetchall())

# Check gateway_idempotency columns
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'gateway_idempotency'")
cols = cur.fetchall()
print("gateway_idempotency columns:", cols)

# Check billing_idempotency columns
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'billing_idempotency'")
cols2 = cur.fetchall()
print("billing_idempotency columns:", cols2)

# Check all tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
tables = cur.fetchall()
print("All tables:", tables)

conn.close()
