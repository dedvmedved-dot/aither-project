# U1.3-OPS-R7-R5 — Gitleaks Rescan & Classification (Directions 12-13)

**Scan date:** 2026-07-27
**Target HEAD:** 1c6c341
**Previous scan HEAD:** c2fee84
**Gitleaks version:** 8.18.4
**Scans performed:** 5 (staged, current HEAD, evidence, diff, final HEAD)

## Scan Results

| Scan | Findings |
|---|---|
| Staged | 92 |
| Current HEAD | 182 |
| Evidence directory | 634 |
| Diff (base..HEAD) | 182 |
| Final HEAD | 182 |

## Classification

### Current HEAD (182 findings)

| Category | Count | Description |
|---|---|---|
| `false_positive_gitleaks_self_scan` | 156 | Gitleaks scanning its own output files |
| `historical_evidence_artifact` | 13 | Evidence/log files from prior stages |
| `test_fixture_false_positive` | 4 | Unit test fixtures with hardcoded test values |
| `historical_incident_log` | 0 | — |
| `pre_commit_hook_false_positive` | 1 | `.githooks/pre-commit` — test values |
| `historical_beta_report` | 4 | Beta reports with leaked test API keys |
| `config_template_placeholder` | 3 | Config templates/docs with placeholder values |
| `oauth_doc_reference` | 1 | OAuth doc with token reference |

### New findings from D14/D18 commits (1f1bbb3 → d283dec → 1c6c341)

| File | Findings |
|---|---|
| `aither-v2/services/bff/app.py` | **0** |
| `tests/e2e/test_u13_registration.py` | **0** |
| `docs/evidence/u1.3-ops-r7-r5/junit/registration-28.xml` | **0** |
| `docs/evidence/u1.3-ops-r7-r5/junit/track-a-full-wui-r7r5.xml` | **0** (sanitized) |
| `docs/evidence/u1.3-ops-r7-r5/execution-checklist.*` | **0** |

### Historical Leaks Requiring Revocation (BLOCKED — Direction 15)

The following files contain full API keys that should be revoked (Owner action required):

1. `aither-v2/reports/beta/ba02-api-key-isolation.md` — full `athr_` API key
2. `aither-v2/reports/beta/hermes-final.md` — full `athr_` API key
3. `aither-v2/reports/beta/openai-api-final.md` — API key reference

These are NOT introduced by R7-R5 work — they are historical beta report artifacts.

## Conclusion

- **New active secrets introduced:** 0
- **New credential disclosures:** 0
- **D14/D18 commits verified clean:** YES
- **All 182 findings classified:** YES
- **REMEDIATED (current R7-R5 scope):** YES
- **Historical leaks pending revocation:** 3 (Direction 15 — BLOCKED)
