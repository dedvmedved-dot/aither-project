# FRONTEND-INTEGRATION-FE02-AUDIT-CORRECTION
# ==========================================
# R7-R5-EMG-FE-03 | 2026-07-28

## FE-02 Status
**FAILED EXTERNAL AUDIT**

## Causes of Failure

1. **Unauthorized chat cutover**: Chat was routed Browser → Portal Backend → Gateway → Model.
   This constitutes an unauthorized production Gateway cutover. Gateway model routing is
   `NOT AUTHORIZED` per CHANGE-0022.

2. **Mandatory tests missing**:
   - Session revocation tests (SESSION-001 through SESSION-008)
   - Full RBAC suite (user→admin 403, operator, disabled user)
   - Organisation isolation tests (ISO-001 through ISO-005)
   - Browser E2E (20 tests required, 0 executed)
   - RAG isolation tests

3. **Incomplete API routes**:
   - GET /admin/organisations → 404 (Gateway endpoint not implemented)
   - /admin/security/events → not tested
   - /admin/billing/stats → not tested
   - Usage /me/models, /me/daily → not verified at Gateway level

4. **Unsafe identity fallbacks**:
   - `org_id = user.org_id or "1"` — fallback grants access
   - Empty scopes → default global scopes granted
   - `tier = "free"` as hardcoded fallback

5. **Session revocation defect**:
   - Logout does not reliably revoke sessions
   - Disabled user sessions not revoked
   - Session existence/revoked/expiry not checked on each request

## Correction Plan (FE-03)
- S2: Rollback chat route to direct upstream
- S4: Remove all entitlement fallbacks
- S5: Fix session lifecycle
- S6-S11: Complete remaining gates
- S10-13: Full RBAC, isolation, E2E suite
