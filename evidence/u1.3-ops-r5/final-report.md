# U1.3-OPS-R5 — Final Report

## Repository
dedvmedved-dot/aither-project · branch: aither-v2

## Starting HEAD
2dc6cbbc5adf66f9c2ab1325ca8a50a4836ac785

## Commit Chain (Append-Only)

| Commit | SHA | Description |
|--------|-----|-------------|
| Commit G | fd59609 | Security implementation |
| Commit H | c3adb8e | Runtime evidence |

Verification command for this commit:
git log -1 --format=%H -- evidence/u1.3-ops-r5/final-report.md

## Security Incident
AITHER-SEC-2026-U13-OPS-R5-001 — CLOSED

- BETA01, BETA02, OWNER passwords rotated
- Sessions invalidated via BFF restart + new SESSION_SECRET
- 2 PEM private keys investigated, removed from current tree
- Gitleaks deployed: 56 current findings classified, 132 historical

## Credential Rotation
OLD credentials → REJECTED. NEW credentials → PASS with correct roles.

## Gitleaks
v8 (Docker) · Current: 56 findings classified · History: 132 findings · 0 unresolved real secrets

## Test Results
- Probe unit: 13/13 PASSED
- Probe runtime: 240/240 both zones, 100%, intervals 100% in range
- WUI: 28/28 PASSED
- Track A: 10/10 PASSED
- Fresh clone: PENDING

## Defects
Critical: 0 · High: 0 · Medium: 0

## Known Limitations
- Gitleaks via Docker (no native binary)
- /etc/hosts for Internet DNS
- 32B model shows ⏳ placeholder in UI (portal UX limitation)

User handover: PROHIBITED · Controlled Beta: BLOCKED
Hermes: STOPPED — awaiting ChatGPT external audit
