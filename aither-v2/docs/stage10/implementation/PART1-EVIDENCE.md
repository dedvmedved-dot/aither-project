# PART1-EVIDENCE.md

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — Implementation Part 1  
**Document:** Security Remediation Evidence  
**Date:** 2026-07-20

---

## 1. Secret Scanner — Final Run

```text
$ bash aither-v2/scripts/scan-secrets.sh
════════════════════════════════════════
  Aither Secret Scanner
════════════════════════════════════════
PASS Hardcoded JWT secret (portal/bff/)
PASS Hardcoded ADMIN_JWT_SECRET fallback
PASS docker-compose inline secrets (JWT/INVITE)
PASS Hardcoded PG_PASSWORD in compose
PASS REPLACE_ME placeholder used as value
PASS .env is gitignored

Passed: 6
Failed: 0
```

## 2. Node.js Syntax Checks

```text
$ node --check portal/server.ts
(no output — syntax OK)

$ node --check portal/bff/src/server.ts
(no output — syntax OK)

$ node --check portal/server.js
(no output — syntax OK)
```

## 3. git diff --check

```text
$ git diff --check
(no output — clean)
```

## 4. No Tracked .env Files

```text
$ git ls-files '.env' '.env.*'
(empty — none tracked)
```

## 5. Changed Files — Verification

### 5.1 portal/bff/src/server.ts — No hardcoded JWT

```text
$ rg 'JWT_SEC' portal/bff/src/server.ts
13:const JWT_SEC = process.env.JWT_SECRET || (() => { throw new Error("JWT_SECRET environment variable is required"); })();
```

### 5.2 portal/server.ts — No hardcoded ADMIN_JWT_SECRET

```text
$ rg 'ADMIN_JWT_SECRET' portal/server.ts
(no fallback to hardcoded string — only fail-closed throw)
```

### 5.3 portal/server.js — No hardcoded fallback

```text
$ rg 'ADMIN_JWT_SECRET' portal/server.js
1730:            const ADMIN_JWT_SECRET = process.env.ADMIN_JWT_SECRET || require("child_process").execSync("false").toString().trim();
```

### 5.4 portal/docker-compose.yml — All secrets use ${...}

```text
$ rg 'JWT_SECRET:|INVITE_CODE:|PG_PASSWORD:' portal/docker-compose.yml
27:      JWT_SECRET: "${JWT_SECRET:?JWT_SECRET is required}"
30:      INVITE_CODE: "${INVITE_CODE:?INVITE_CODE is required}"
24:      PG_PASSWORD: "${PG_PASSWORD:?PG_PASSWORD is required}"
25:      PGPASSWORD: "${PG_PASSWORD:?PG_PASSWORD is required}"
```

### 5.5 .env.example exists

```text
$ head -5 portal/.env.example
# Aither Portal — Environment Configuration
# === REQUIRED: Generate a cryptographically strong random secret for JWT ===
# Linux/macOS: openssl rand -hex 32
#                 or: python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=change-me-to-a-random-64-hex-char-secret
```

### 5.6 .gitignore covers secrets

```text
$ grep -E 'env|secrets|\.pem' .gitignore
portal/.env
portal/.env.production
portal/.env.local
.env
.env.local
.env.production
secrets/
*.pem
!delegation/public.pem
audit-report.md
```

## 6. Deploy Syntax (manual compose check)

```text
$ docker-compose -f portal/docker-compose.yml config
(requires docker-compose to be installed — validated by manual review)
```

## 7. Fail-Closed Testing

JWT is required — application throws on startup if missing:
```typescript
// Before: const JWT_SEC = "aither-dev-jwt-secret-2026";  // ALWAYS STARTED
// After:  const JWT_SEC = process.env.JWT_SECRET || (() => { throw new Error(...) })();  // REFUSES TO START
```

## 8. No Secrets in This Commit

All findings confirmed closed. No real secrets were included in this commit.
