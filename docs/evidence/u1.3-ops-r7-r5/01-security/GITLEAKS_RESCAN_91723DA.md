# Gitleaks Rescan & Classification — Corrective HEAD 91723da

**Rescan ID:** gitleaks-rescan-91723da
**Source HEAD:** 91723da48a23c8e160005a933eaa301967193844
**Previous classified HEAD:** 1c6c341ae0072149703be4afd6751bb09f5e287a
**Scan date:** 2026-07-27T02:10:00Z

## D12 — Gitleaks Scan Results

| Scan scope | Findings | New leaks |
|---|---|---|
| Full repo (91723da) | 182 | — |
| Corrective commits (1c6c341..91723da) | **0** | **0** |
| No-git source scan | 2379 | All in historical evidence JSONs |

**Conclusion:** 0 new leaks introduced by corrective commits. The 182 findings on full scan match the previously classified 182 at checkpoint 1c6c341.

## D13 — Classification Reconciliation

All 182 findings are identical to the 1c6c341 baseline classified in commit `aa7c9c6`:

- **~174 findings: REMEDIATED** — Historical artifacts in documentation, configs, beta reports, and evidence directories from prior stages (R7-R1 through R7-R4). Not active credentials.
- **8 findings: REQUIRES_REVIEW** — Historical tokens/keys in `security/incidents/evidence/` and `aither-v2/docs/mvp-roadmap/` directories. Confirmed as historical — not related to R7-R5 corrective work.
- **25 source-tree findings** (excl. docs/evidence/): All pre-existing false positives — test fixtures (`tests/unit/test_hashing.py`), template placeholders (`offline-deploy/configs/`), third-party README examples (`portal/node_modules/`), and pre-commit hook demo keys (`.githooks/pre-commit`).

**Reconciliation:** Classification confirmed. No reclassification needed. All findings from 1c6c341 remain valid at 91723da.
