# TASK: AITHER-MVP-OPS-RC1-R2

## Goal
Correct the R1 exact-path allowlist defect and complete the same bounded OPS-RC1 closure scope: D1 Alertmanager/Telegram alerting, D2 NTP/time-sync monitoring, D3 PostgreSQL+Redis backup/restore, #30 multi-tenant isolation, and C3 Kubernetes cluster hygiene.

## Baseline
- Branch: `aither-v2`
- Baseline SHA: `63ad4ef91221aa32cfa3d1be6cdc770787a0a9a4`
- R1 result: `BLOCKED / NOT ACCEPTED` because directory-prefix allowlist entries were interpreted as exact filenames.
- R2 is corrective execution of the same OPS-RC1 scope. It is not authorization to reopen unrelated work.

## Critical behavior requirements
1. GitHub is Source of Truth. Read this file and `.agent/CURRENT_TASK.json` before any implementation.
2. Work only on the exact paths authorized below. The runner treats `allowed_paths` as exact filenames, not directory prefixes.
3. If another repository path becomes necessary, STOP and return BLOCKED with the exact non-secret reason. Do not improvise, create a nearby file, or expand scope.
4. Inspect source and live runtime before changing anything. Reuse the existing architecture; do not create duplicate monitoring, backup, tenancy, Telegram, scheduler, runner, or bridge stacks.
5. Do not modify `.agent/*`, scheduler, host runner, H2 bridge, Telegram gateway, `/root/.hermes`, model placement, model identities, billing production activation, or Owner-only flows.
6. Model contract remains `qwen2.5-32b-instruct` / `model:qwen2.5:chat` and `qwen3-32b` / `model:qwen3:chat`. Legacy `model:32b:chat` is compatibility-only.
7. Do not reopen the previously accepted Qwen3 GPU admission incident unless a genuinely new runtime symptom is observed.
8. Never print, copy, rotate, expose, or commit secret values. Existing Secret references may be used by name only. `secret_access=false` remains binding.
9. Runtime claims require runtime evidence. Manifest existence alone is not PASS.
10. Preserve healthy running services. Use bounded, reversible validation and non-destructive restore tests.
11. Temporary runtime/evidence artifacts that are not exact allowed repository paths must not remain in the worktree. Clean them before finish. Persist final evidence only in `docs/operations/OPS_RC1_R2_EVIDENCE.md`.
12. Finish with a clean worktree. Commit/push only authorized implementation paths; runner owns `.agent/EXECUTION_RESULT.json`.

## Exact authorized repository paths
- `manifests/observability/prometheus.yaml`
- `manifests/observability/alertmanager.yaml`
- `manifests/observability/node-exporter.yaml`
- `manifests/observability/kube-state-metrics.yaml`
- `manifests/postgres.yaml`
- `manifests/redis.yaml`
- `manifests/backups.yaml`
- `manifests/quotas.yaml`
- `manifests/network-policies.yaml`
- `docs/operations/MONITORING_GUIDE.md`
- `docs/operations/BACKUP_RESTORE_GUIDE.md`
- `docs/operations/OPERATIONS_GUIDE.md`
- `docs/operations/OPS_RC1_R2_EVIDENCE.md`
- `ROADMAP-RECOVERY.md`

Do not modify any repository file not listed above.

## Workstream A — D1 Alertmanager + Telegram alerts
- Inspect current Prometheus/Grafana runtime and source first.
- Ensure Prometheus actually loads intended alert rules; prove active rule loading in runtime.
- Deploy/correct Alertmanager within existing observability architecture and prove healthy/ready state and accepted routing configuration.
- Minimum alert coverage: GPU temperature, GPU memory pressure, pod/container restart anomaly, and a safe synthetic alert path.
- Prove a synthetic alert reaches Alertmanager.
- Use only existing secret references for Telegram if already available without reading/printing secret values. If end-delivery cannot be proven without unavailable Owner credentials, mark only Telegram end-delivery PARTIAL/BLOCKED and continue all other work.

## Workstream B — D2 NTP/time synchronization monitoring
- Verify the actual time-sync mechanism on relevant Kubernetes nodes without package installation.
- Determine the metric actually available in this environment; do not invent a metric.
- Prefer `node_timex_offset_seconds` only if runtime confirms it exists; otherwise use an evidence-backed equivalent signal and document the mapping.
- Provide runtime evidence for N7 and N8 synchronization/offset state (or exact non-secret accessibility blocker) and prove the corresponding Prometheus rule is loaded.

## Workstream C — D3 PostgreSQL + Redis backup/restore
- Inspect existing persistence and backup behavior first.
- Implement scheduled PostgreSQL and Redis backups using existing storage conventions.
- Require bounded retention/cleanup and visible failure behavior.
- Do not embed credentials or sensitive payloads in manifests/evidence.
- Perform non-destructive restore validation into temporary/test targets only; never overwrite production data.
- Prove restored PostgreSQL data is readable and restored Redis data is readable.
- Remove temporary restore resources when validation completes safely.

## Workstream D — #30 Multi-tenant isolation
- Audit current namespaces, NetworkPolicies, ResourceQuota and LimitRange state.
- Complete isolation using current tenancy architecture; do not invent a parallel tenancy model.
- Runtime proof must include: intended allowed path succeeds; prohibited cross-tenant path is denied; quota/limits enforcement is demonstrated; platform traffic required for normal operation remains functional.
- Do not weaken isolation to make tests pass.

## Workstream E — C3 Kubernetes cluster hygiene
- Inspect pods, jobs, events and restart state for stale Failed/Evicted/Completed artifacts.
- Remove only objectively stale/disposable workload artifacts.
- Never delete or restart healthy production application/model pods merely for cleaner output.
- Re-check cluster state and document any remaining non-healthy objects and their reasons.

## Evidence contract
Write a single final repository evidence report to `docs/operations/OPS_RC1_R2_EVIDENCE.md`.

For each of D1, D2, D3, #30 and C3 include:
- source/config change summary;
- exact runtime validation performed;
- relevant non-secret command/result excerpts or structured summaries;
- PASS / PARTIAL / BLOCKED;
- exact blocker for anything not PASS;
- regression/health check;
- rollback/reversibility note.

The report must explicitly state:
- `SECRET_VALUES_PRINTED: NO`
- `SECRETS_EXPOSED: NO`
- `OWNER_ACTION_REQUIRED: YES/NO` with reason if YES.

Update `ROADMAP-RECOVERY.md` only for items actually proven by runtime evidence in this task.

## Acceptance
Overall PASS requires every autonomously achievable OPS-RC1 gate to pass without unreported regression. Telegram end-delivery may remain PARTIAL/BLOCKED only when it genuinely depends on unavailable external/Owner credentials; do not fabricate delivery.

Do not declare Architect acceptance. Hermes may inspect -> implement -> test -> fix -> retest within this bounded task, then commit/push authorized changes through the governed runner, publish the machine-readable result, and STOP.
