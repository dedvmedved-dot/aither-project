# BFF-RECOVERY-REPORT
# ===================
# R7-R5-EMG-FE-02 | 2026-07-28

## Background
Production BFF (`aither-bff`) was in CrashLoopBackOff due to f-string syntax errors at `/app/app.py:249`.
14 identical f-string bugs found and fixed. Additionally, ConfigMap `aither-bff-config` was overwriting
the image's app.py, and uvicorn CMD was incorrect.

## Recovery Steps
1. Fixed 14 f-string syntax errors (safe quoting with single-quoted 'EMPTY')
2. Rebuilt Docker image for BFF
3. Updated ConfigMap to match fixed file
4. Fixed uvicorn CMD in deployment
5. BFF restored to 2/2 Ready

## Current BFF State
- BFF is RESTORED and serving production traffic
- Chat endpoint migrated to portal-backend with delegation JWT (Variant A)
- `services/bff-prod/app.py` marked SUPERSEDED
- Authoritative source: `services/portal-backend/app/main.py`
- BFF Dockerfile in `tools/bff/` transitioning to portal-backend source

## Production Chat Route
Browser → Portal Nginx → Portal Backend (delegation JWT) → Gateway → AI Platform
Raw API keys NOT stored in process memory.
