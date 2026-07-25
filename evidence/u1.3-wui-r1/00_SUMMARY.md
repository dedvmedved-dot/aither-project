# U1.3-WUI-R1 — SUMMARY

## Audit Resolution

**Rejected commit:** 14136d7f7ce7309b590370dda539164d18d2a8d6
**Findings:**
1. ❌ 5 failed U1.3-WUI tests (model selection)
2. ❌ 2 failed Agent Page UI tests (renderAgentPage undefined)
3. ❌ Fresh-clone absent
4. ❌ Acceptance Matrix contradicted JUnit evidence
5. ❌ TLS warning in test output

**Corrected in R1:**
1. ✅ Added missing renderAgentPage() function
2. ✅ Model selection values verified correct; failures were from stale ConfigMap
3. ✅ Fresh-clone validation: 28/28 PASSED
4. ✅ Acceptance Matrix rebuilt with exact test IDs and evidence paths
5. ✅ All TLS checks enforced; zero TLS warnings

## Test Results

| Suite | Passed | Failed | Errors | Skipped |
|-------|--------|--------|--------|---------|
| U1.3-WUI (original) | 28 | 0 | 0 | 0 |
| U1.3-WUI (fresh clone) | 28 | 0 | 0 | 0 |
| Track A regression | 10 | 0 | 0 | 0 |

## Deployment

| Artifact | SHA-256 |
|----------|---------|
| portal/static/index.html (source) | edc1ee8dde1745bcdf8f00dbdc6051074f1b530046c723b04f4fb46952f91f20 |
| Internet Zone (https://fb1.spb.ru:443) | edc1ee8d...f91f20 |
| Test Zone (http://10.129.13.78:30080) | edc1ee8d...f91f20 |
