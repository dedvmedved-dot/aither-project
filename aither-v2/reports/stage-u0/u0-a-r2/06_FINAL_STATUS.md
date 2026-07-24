# Final Status — Stage U0.A-R2

## Stage

Stage U0.A-R2 — Deterministic Inventory Regeneration & Evidence Reconciliation

## Status

AWAITING EXTERNAL AUDIT

## Baseline SHA

630885881c8e8994ab7f536df615ee52d5429de4

## Tooling Commit SHA

01f95d8e4865e74a07cb297550b8c905c554b470

## Generation Base SHA

01f95d8e4865e74a07cb297550b8c905c554b470

## Generated Inventory Commit SHA

e3c543a7f8390b8aad3c3fe1dce840ba7e88b2bb

## Tracked File Count

895

## Reconciliation

| Source | Count | Unique | Missing | Extra | Duplicates | Status |
|--------|------:|-------:|-------:|------:|-----------:|--------|
| git ls-files vs FILE_CATALOG.md | 895 / 895 | 895 / 895 | 0 | 0 | 0 | ✅ |
| git ls-files vs FILE_METADATA.csv | 895 / 895 | 895 / 895 | 0 | 0 | 0 | ✅ |
| git ls-files vs FILE_HASHES.txt | 895 / 895 | 895 / 895 | 0 | 0 | 0 | ✅ |

## Set Equality

All path sets equal: YES

## Determinism

First generation check-only: PASSED (exit 0)
Deterministic regeneration: VERIFIED

## Findings

| Finding | Previous Status | Current Status | Corrective Commit |
|---------|----------------|----------------|-------------------|
| U0A-CAT-001 | FAILED | CORRECTED / AWAITING EXTERNAL VERIFICATION | e3c543a |
| U0A-VAL-001 | FAILED | CORRECTED / AWAITING EXTERNAL VERIFICATION | e3c543a |
| U0AR1-VAL-001 | FAILED | CORRECTED / AWAITING EXTERNAL VERIFICATION | e3c543a |
| U0AR1-CAT-001 | FAILED | CORRECTED / AWAITING EXTERNAL VERIFICATION | e3c543a |
| U0AR1-CAT-002 | FAILED | CORRECTED / AWAITING EXTERNAL VERIFICATION | e3c543a |
| U0AR1-CAT-003 | FAILED | CORRECTED / AWAITING EXTERNAL VERIFICATION | e3c543a |
| U0AR1-VAL-002 | FAILED | CORRECTED / AWAITING EXTERNAL VERIFICATION | e3c543a |

## Final Declarations

```
Stage U0.A-R2:
AWAITING EXTERNAL AUDIT

Stage U1.1:
NOT STARTED / BLOCKED BY STAGE U0.A-R2

Internal Pilot:
NOT YET OPEN

Production v1.0:
NO-GO

PROD-READY-01:
OPEN
```
