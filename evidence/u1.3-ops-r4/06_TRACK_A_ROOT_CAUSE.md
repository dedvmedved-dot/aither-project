# U1.3-OPS-R4 — Track A Root Cause

## Symptom
Track A regression suite: `4 passed / 6 failed` in R2/R3.
All failures: `expect(page.locator("#nav-role-badge")).to_have_text("User")` — portal shows "Admin" for BETA01/BETA02.

## Reproduction
1. Login as BETA01 (username="admin") → portal role badge shows "Admin"
2. Test asserts role="User" → FAIL
3. Same for BETA02 → FAIL (both use "admin" credentials)
4. OWNER login also uses "admin" → role badge shows "Admin" (correct for OWNER)

## Baseline
- Accepted WUI baseline: commit `171f78ddcec2c40dc8a5b630ccb5e8b2b31d5ddf`
- Track A test blob SHA at baseline: `090e8374767c98565ffbde4e5d6711ebd4bbd0ef`
- Track A test blob SHA at HEAD: `090e8374767c98565ffbde4e5d6711ebd4bbd0ef`
- **Tests are IDENTICAL** — no code change

## Root Cause Investigation

### Credential Analysis
`.env.r3` file contained identical values for all 6 variables:
- E2E_BETA01_USERNAME = "admin"
- E2E_BETA01_PASSWORD = "admin"
- E2E_BETA02_USERNAME = "admin"
- E2E_BETA02_PASSWORD = "admin"
- E2E_OWNER_USERNAME = "admin"
- E2E_OWNER_PASSWORD = "admin"

All SHA256 fingerprints: `8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918`

### Portal Role Logic
`portal/static/index.html` line 632:
```javascript
currentUser = res.data.user || { username: username, role: 'admin' };
```

BFF login response did NOT include `user` object → portal always defaulted to `role: 'admin'`.
Same code at accepted baseline → role was ALWAYS 'admin'.

### BFF Authentication
BFF (`bff-mvp.yaml`) had single-user admin auth:
- One ADMIN_USERNAME + ADMIN_PASSWORD_HASH
- Login only accepted matching admin credentials
- No multi-user/role support

## Confirmed Root Cause: TWO issues

### Issue 1: Same credentials for all users
All three accounts (BETA01, BETA02, OWNER) used identical "admin"/"admin" credentials.
No identity distinction possible.

### Issue 2: BFF single-user, portal hardcodes Admin role
BFF lacked multi-user support. Portal always defaulted to role="admin" since BFF
didn't return `user` object in login response.

## Selected Fixes

### Fix 1: BFF multi-user auth with roles
- Added `BETA_USERS` env var (format: `username:password_hash,...`)
- BFF login: admin check → role "admin"; beta users check → role "user"
- BFF `auth_req()`: session check returns admin/user role
- BFF `/api/v1/auth/login`: returns `user: {username, role}` in response
- BFF `/api/v1/auth/me`: includes role field
- BFF deployment: added BETA_USERS env from secret

### Fix 2: Distinct E2E credentials
Updated `tests/e2e/.env.r3`:
- BETA01: beta01 / Beta01Pass!
- BETA02: beta02 / Beta02Pass!
- OWNER: admin / admin

### Fix 3: Portal role from BFF response
Portal already supported `res.data.user` when present. No code change needed — BFF now returns it.

## Rejected Hypotheses
- "Identity service routing broken" → FALSE: Identity runs but BFF has inline auth
- "Portal needs code change" → FALSE: Portal already handles `res.data.user`
- "Architectural limitation" → FALSE: Adding beta user support is regression restoration

## Affected Files
- `aither-v2/manifests/mvp-roadmap/05-bff/bff-mvp.yaml` — BFF code + deployment env
- `aither-v2/manifests/mvp-roadmap/07-auth-api/bff-auth-secret.example.yaml` — secret template
- `tests/e2e/.env.r3` — NOT committed (credentials)
- k8s Secret `aither-bff-auth` — updated with BETA_USERS

## Validation
- BETA01 login → role "user" confirmed
- BETA02 login → role "user" confirmed
- OWNER login → role "admin" confirmed
- BETA01 API key isolation from BETA02 confirmed
- Targeted Track A: 10/10 PASSED
- Full Track A suite: 10/10 PASSED
