# Snapshot: R7-R5-EMG-01-CHECKPOINT-01

**Emergency:** R7-R5-EMG-01-14B-N8-MIGRATION
**Captured:** 2026-07-27T12:36:10Z
**Status:** INTERMEDIATE EMERGENCY CHECKPOINT — NOT FINAL

This is a sanitized infrastructure snapshot captured during emergency operations.
It is NOT accepted as-built documentation.
Data requires external audit and subsequent reconciliation.

## Sanitization

- All Kubernetes Secret data removed
- ConfigMap data values excluded (keys only)
- Runtime IPs, PIDs, tokens, passwords, cookies removed
- Raw evidence stored separately in emergency journal

## Contents

| Directory | Description |
|---|---|
| `nodes/` | Node labels, GPU summary |
| `workloads/` | Sanitized deployments, pods summary |
| `networking/` | Sanitized services, endpoints |
| `storage/` | PVC index, model storage summary |
| `configuration/` | ConfigMap index, Secret references, BFF env names, nginx summary |
| `git/` | Commit chain, delta stat, changed files |
