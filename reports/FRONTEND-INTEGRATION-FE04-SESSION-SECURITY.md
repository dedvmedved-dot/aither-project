# FRONTEND-INTEGRATION-FE04-SESSION-SECURITY
# =========================================
# R7-R5-EMG-FE-04 | 2026-07-28

## Session Security Architecture (FE-04)

### get_current_user() — Fresh DB Rights

Every authenticated request now:
1. Validates JWT signature and expiry
2. Checks session exists, not revoked, not expired
3. **Loads current role, org_id, scopes, tier, org_status from DB**
4. **If role changed → revokes ALL sessions, returns 401**
5. **If user disabled → revokes ALL sessions, returns 403**
6. Returns fresh payload with current DB values

### /me endpoint

Returns:
- id, username, role, disabled
- **org_id, org_name, org_status, tier, scopes** (new in FE-04)
- Inactive org → 403
- Missing tier → 403

### Entitlement enforcement

- **No COALESCE fallbacks**: tier is authoritative from DB, not defaulted to 'free'
- **No automatic org assignment**: users without org are PENDING ENTITLEMENT
- **LDAP no longer auto-creates users** with default org/scopes
- **Bootstrap admin** created with explicit org_id + scopes

### Model Scope Enforcement (Direct Chat)

Chat route checks:
1. org_id assigned
2. org_status == "active"
3. tier present
4. Model-specific scope: `model:14b:chat` for 14B, `model:32b:chat-adapter` for 32B

## Verified Behaviors

```
SESSION-001: Login + /me                        → 200 ✓
SESSION-002: Logout                             → 200 ✓
SESSION-003: /me after logout                   → 401 ✓
SESSION-004: Chat after logout                  → 401 ✓
SESSION-005: Login disabled user                → 403 ✓
SESSION-006: Old token after disable            → 401 ✓
SESSION-008: Demoted admin old token → admin    → 401 ✓
```
