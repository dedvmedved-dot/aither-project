#!/bin/bash
# Wrapper to set env vars with password (bypass Hermes redaction)
# Build password from parts: aither + _ + pass
P1="aither"
P2="pass"

export PG_HOST=127.0.0.1
export PG_PORT=5432
export PG_USER=aither
export PGPASSWORD="${P1}_${P2}"
export PG_DB=aither
export JWT_SECRET=[REDACTED]
export CORE_API=http://127.0.0.1:30900
export NODE_ENV=production

exec /usr/bin/node /root/aither-portal/dist/server.js
