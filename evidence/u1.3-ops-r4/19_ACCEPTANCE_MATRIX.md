# U1.3-OPS-R4 — Acceptance Matrix

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| R4-001 | Append-only Git history | PASS | commit-chain.txt |
| R4-002 | Current branch and remote match | PASS | logs/21-pre-final-git-state.log |
| R4-003 | No amend/force push | PASS | logs/21-pre-final-git-state.log |
| R4-004 | Raw wrapper captures non-zero exit | PASS | logs/06-,07- (wrapper verified) |
| R4-005 | Accepted baseline comparison | PASS | logs/02-accepted-baseline-comparison.log |
| R4-006 | Runtime artifact inventory | PASS | logs/03-runtime-artifacts.log |
| R4-007 | Credentials fingerprint distinctness | PASS | logs/04-credentials-fingerprints.log |
| R4-008 | Identity routing | PASS | logs/05-identity-routing.log |
| R4-009 | BETA01 role User | PASS | BFF login returns role="user" |
| R4-010 | BETA02 role User | PASS | BFF login returns role="user" |
| R4-011 | OWNER role Admin | PASS | BFF login returns role="admin" |
| R4-012 | User identity isolation | PASS | junit/track-a-full.xml (TestBETA02::test_isolation) |
| R4-013 | Targeted model_switch 4/4 | PASS | junit/targeted-model-switch-before.xml |
| R4-014 | Targeted Track A 10/10 | PASS | junit/targeted-track-a-before.xml |
| R4-015 | Probe static tests | PASS | 11_PROBE_IMPLEMENTATION_AUDIT (code review) |
| R4-016 | DNS preflight | PASS | logs/12-dns-preflight.log (20/20 both zones) |
| R4-017 | Probe count Internet | PASS | 240/240, availability-summary.json |
| R4-018 | Probe count Test Zone | PASS | 240/240, availability-summary.json |
| R4-019 | Probe interval accuracy | PASS | ~1s interval, availability-summary.json |
| R4-020 | Probe timestamp correctness | PASS | 2026-07-26, not 1970 |
| R4-021 | Zero non-200 Internet | PASS | 0 non-200 |
| R4-022 | Zero non-200 Test Zone | PASS | 0 non-200 |
| R4-023 | Zero connection failures | PASS | 0 connection_failure_count |
| R4-024 | Rollout restart | PASS | logs/14-rollout-restart.log |
| R4-025 | Full U1.3-WUI 28/28 | PASS | junit/u13-wui-full.xml |
| R4-026 | Full Track A 10/10 | PASS | junit/track-a-full.xml |
| R4-027 | TLS warnings zero | PASS | grep verified: 0 matches |
| R4-028 | Raw WUI log non-empty | PASS | logs/15-wui-full.log (4450 bytes) |
| R4-029 | Raw Track A log non-empty | PASS | logs/16-track-a-full.log (2219 bytes) |
| R4-030 | Fresh clone | PASS | logs/17-fresh-clone.log |
| R4-031 | Fresh clone WUI 28/28 | PASS | junit/u13-wui-fresh-clone.xml |
| R4-032 | Fresh clone Track A 10/10 | PASS | junit/track-a-fresh-clone.xml |
| R4-033 | Operations revalidation | PASS | logs/18-operations-revalidation.log |
| R4-034 | Secret scan | PASS | logs/19-secret-scan.log |
| R4-035 | Placeholder scan | PASS | logs/20-placeholder-scan.log (0 matches) |
| R4-036 | No active background jobs | PASS | jobs -l: empty |
| R4-037 | Final external Local/Remote match | PASS | logs/21-pre-final-git-state.log |
| R4-038 | Final external working tree clean | PASS | logs/21-pre-final-git-state.log |

All 38 requirements: PASS
