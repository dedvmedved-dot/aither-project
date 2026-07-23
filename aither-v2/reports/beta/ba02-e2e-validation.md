# Stage BA-02 — E2E Validation Report

**Date:** 2026-07-23
**Status:** ⚠️ PARTIAL (see notes)

## Test Environment

- Portal Frontend: `http://aither-portal-frontend:80` (nginx, Stage 15 SPA) ✅
- BFF: `http://aither-bff:8000` (session-based auth) ✅
- Portal Backend: `10.129.13.78:5000/aither-portal-backend:ba02-014f91b` (with proxy routes) ✅
- AI Platform: `10.129.13.78:5000/aither-ai-platform:ba01r-fix` (with Gateway API Key fix) ✅

## E2E User Flow Results

| Step | Test | Result | Notes |
|------|------|--------|-------|
| 1 | Portal SPA loads | ✅ PASS | HTTP 200, 16.5KB, login UI embedded |
| 2 | BFF Login (session cookies) | ✅ PASS | session_id obtained |
| 3 | Models via BFF | ✅ PASS | 2 models: qwen-14b (chat), qwen-32b-base (completion) |
| 4 | Chat creation (BFF) | ❌ FAIL | BFF `/api/v1/conversations` returns 404 — BFF does not implement conversations API |
| 5 | Message via OpenAI API | ✅ PASS | HTTP 200, model responds |
| 6 | Chat persistence | ⏳ NOT TESTED | Requires working conversations API |
| 7 | Multi-model | ✅ PARTIAL | 32B model works; 14B not accessible via Gateway |
| 8 | API Key (no key → 401) | ✅ PASS | |
| 8 | API Key (invalid → 401) | ✅ PASS | |
| 9 | Hermes 10x requests | ⏳ NOT TESTED | K8s API intermittency blocked full test suite |

## Known Limitation: BFF vs Portal Backend

Architecture context:
- **BFF** (`aither-bff`) — old service, session-based auth, supports login/models/chat/completions but **not** conversations API
- **Portal Backend** (`aither-portal-backend`) — new service with proxy routes to AI Platform, supports conversations API but uses different auth model (JWT from Identity, not BFF sessions)
- **Portal Frontend** SPA uses **BFF** for login/auth and **Portal Backend** for API operations

The conversations API works via Portal Backend → AI Platform, but the E2E flow from Portal Frontend through BFF sessions to Portal Backend conversations was not fully tested due to K8s API instability.

## Evidence

- Portal SPA: `evidence/beta/ba02/browser/`
- API tests: executed from portal-backend pod
- Note: Full Playwright browser test was prepared (`playwright_e2e.py`) but port-forward instability prevented completion
