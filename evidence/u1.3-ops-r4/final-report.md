# U1.3-OPS-R4 — Final Report

## Repository
dedvmedved-dot/aither-project

## Branch
aither-v2

## Starting HEAD
0419be6deab62352581a729d4242609efe768622

## Commit Chain (Append-Only)

| Commit | SHA | Description |
|--------|-----|-------------|
| Baseline | 0419be6deab62352581a729d4242609efe768622 | U1.3-OPS-R3 (rejected) |
| Commit D | b8d592cfee5b7ddb2fd8ce5f70075422b5d66239 | Implementation |
| Commit E | 9f570fc35d6f41265170a8583c7b594a1c84ccfc | Runtime evidence |

Verification command for this commit:
git log -1 --format=%H -- evidence/u1.3-ops-r4/final-report.md

## History Rewrite Status
NO amend, NO force push, NO history rewriting.

## Working Tree
CLEAN

## Model Switch Root Cause
Playwright strict-mode: `.chat-msg.assistant` resolves to 2 elements after two chat messages. Test assertion `to_be_visible()` requires exactly 1 match.

## Model Switch Correction
Added `.last` to locator: `expect(page.locator(".chat-msg.assistant").last).to_be_visible()`.
12 conditions for test modification met.

## Track A Root Cause
Two issues:
1. `.env.r3`: all 6 credential variables identical (all "admin"/"admin")
2. BFF single-user admin: no multi-user/role support, portal defaulted to role="admin"

## Track A Correction
1. BFF: Added BETA_USERS support with role differentiation (admin → "admin", beta → "user")
2. BFF login response: returns `user: {username, role}`
3. `.env.r3`: distinct credentials (beta01/Beta01Pass!, beta02/Beta02Pass!, admin/admin)

## Credential Fingerprint Audit
- BETA01_USERNAME distinct from BETA02_USERNAME: YES
- BETA01_USERNAME distinct from OWNER_USERNAME: YES
- BETA02_USERNAME distinct from OWNER_USERNAME: YES

## Identity Routing
- BETA01 role: User ✓
- BETA02 role: User ✓
- OWNER role: Admin ✓
- Isolation: PASS

## Test Results

| Suite | Result |
|-------|--------|
| Targeted model_switch | 4 passed / 0 failed |
| Targeted Track A | 10 passed / 0 failed |
| Full U1.3-WUI | 28 passed / 0 failed |
| Full Track A | 10 passed / 0 failed |
| Fresh-clone U1.3-WUI | 28 passed / 0 failed |
| Fresh-clone Track A | 10 passed / 0 failed |

## Availability Probe

| Metric | Internet | Test Zone |
|--------|----------|-----------|
| Probes | 240 | 240 |
| HTTP 200 | 240 | 240 |
| Failures | 0 | 0 |
| DNS/TLS/Timeout/Conn | 0/0/0/0 | 0/0/0/0 |
| Availability | 100% | 100% |
| Timestamp valid | YES (2026) | YES (2026) |
| Interval accuracy | ~1s | ~1s |

## Rollout Restart
PASS — Zero-downtime confirmed

## TLS Verification
0 warnings

## Secret Scan
gitleaks: NOT AVAILABLE · fallback grep: EXECUTED · 0 new real secrets

## Placeholder Scan
0 matches in new evidence

## Defects
- Critical: 0
- High: 0
- Medium: 0

## Known Limitations
- gitleaks not installed (fallback grep used)
- /etc/hosts required for Internet DNS on this test machine
- No isolated shutdown test environment

## User Handover
PROHIBITED

## Controlled Beta
BLOCKED

## Hermes Status
STOPPED — awaiting ChatGPT external audit
