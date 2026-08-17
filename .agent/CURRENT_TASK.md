# TASK: AITHER-MVP-OPS-RC1-R1

## Goal
Close the operational RC1 blockers that can be completed autonomously: D1 Alertmanager/Telegram alerting, D2 NTP monitoring, D3 PostgreSQL+Redis backup/restore, #30 multi-tenant isolation, and C3 Kubernetes cluster hygiene.

## Baseline
- Branch: `aither-v2`
- Baseline SHA: `b454764cf9ff8fafba973fd897a4084b3a27725b`
- Roadmap reconciliation: ACCEPTED.
- H0-H8 autonomous handoff: ACCEPTED.

## Critical behavior requirements
1. Work only inside the authorized OPS-RC1 scope. Do not start SEC-RC1, INFRA-RC1, BIZ-RC1, RC1 release/tagging, hardware expansion, model replacement, billing production activation, or Owner-only browser/email flows.
2. Inspect current source and live runtime before changing anything. Reuse canonical manifests/components; do not create duplicate monitoring, backup, or isolation stacks when an existing implementation can be corrected.
3. Do not print, copy, rotate, expose, or commit secret values. Existing Kubernetes Secret references may be reused by name only. If Telegram delivery requires an unavailable secret/value, implement and validate everything possible and report the delivery step as BLOCKED rather than exposing credentials.
4. Do not change model identities or model placement. Current model contract remains `qwen2.5-32b-instruct` and `qwen3-32b`.
5. Runtime claims require runtime evidence. Source-only presence is not PASS.
6. Preserve running production services. Use reversible changes and bounded tests. Do not intentionally disrupt healthy model/portal/identity services.
7. Keep the worktree clean at finish. Commit only authorized paths. No unrelated refactors.

## Workstream A — D1 Alertmanager + Telegram alerts
- Determine the current Prometheus/Grafana/Alertmanager state from repo and runtime.
- Ensure Prometheus actually loads the intended alert rules (`rule_files`/equivalent must be effective, not merely mounted).
- Deploy or correct Alertmanager using the existing observability architecture.
- Required alert coverage at minimum: GPU temperature threshold, GPU memory pressure, pod/container restart anomaly, and one safe synthetic/test alert path.
- Configure Telegram notification through existing secret references if available. Never print token/chat secret values.
- Runtime evidence: Prometheus rule load succeeds, Alertmanager healthy/ready, routing configuration accepted, synthetic alert reaches Alertmanager. Telegram end delivery must be evidenced if credentials are available; otherwise classify only that subcheck BLOCKED and report exact non-secret reason.

## Workstream B — D2 NTP monitoring
- Verify time synchronization mechanism on relevant Kubernetes nodes without installing packages.
- Add/correct Prometheus monitoring/alerting for material clock offset using metrics actually available in this environment; do not hard-code a nonexistent metric.
- If `node_timex_offset_seconds` is available, use it with the roadmap threshold semantics; otherwise implement an equivalent evidence-backed signal and document the mapping.
- Runtime evidence must show current synchronization/offset state for N7 and N8 (or explain any inaccessible node explicitly) and prove the alert rule is loaded.

## Workstream C — D3 PostgreSQL + Redis backup and restore
- Inspect existing persistence/backup implementation first.
- Implement automated scheduled PostgreSQL and Redis backups using existing Kubernetes storage conventions.
- Backups must have bounded retention or a documented retention mechanism, failure visibility, and no secret values in manifests/logs.
- Perform a non-destructive restore validation into temporary/test targets. Do not overwrite production data.
- Prove PostgreSQL restored data is readable and Redis restored data is readable, then remove temporary restore resources if safe.
- Record commands/results and backup artifact metadata without embedding credentials or sensitive payloads.

## Workstream D — #30 Multi-tenant isolation
- Audit existing NetworkPolicies and any ResourceQuota/LimitRange controls.
- Complete missing isolation controls using the current namespace/tenant architecture rather than inventing a parallel tenancy model.
- At minimum prove: intended allow path works, prohibited cross-tenant path is denied, quotas/limits are enforced for the scoped tenant namespace(s), and existing platform traffic required for normal operation remains functional.
- Do not weaken security policies to make tests pass.

## Workstream E — C3 cluster hygiene
- Inspect pods/events/jobs for stale Failed/Evicted/Completed artifacts and abnormal restart accumulation.
- Remove only objectively stale disposable workload artifacts; never delete healthy running application/model pods merely to obtain a clean output.
- Re-check cluster state after cleanup and document remaining non-healthy objects with reasons.
- Do not reopen the previously accepted Qwen3 GPU admission incident unless a genuinely new symptom is present.

## Repository drift to handle only when directly required by OPS-RC1
- Observability labels/config may still contain retired generic model naming. Where touched for operational correctness, align labels with the current model contract without changing model deployments.
- Do not conduct a broad repository renaming campaign in this task.

## Required evidence and report
Create/update evidence under authorized `docs/` or existing evidence convention and update `ROADMAP-RECOVERY.md` only for items actually proven by this task.

The final evidence must state separately for D1, D2, D3, #30 and C3:
- source/config change summary;
- runtime validation performed;
- PASS / PARTIAL / BLOCKED;
- exact non-secret blocker for anything not PASS;
- rollback/reversibility note;
- `SECRET_VALUES_PRINTED: NO`;
- `SECRETS_EXPOSED: NO`.

## Acceptance
Overall PASS requires all autonomously achievable checks to pass and no unreported regression. A single Owner-only Telegram credential/delivery dependency may be reported as PARTIAL/BLOCKED without fabricating success; all other work must continue independently.

Do not declare Architect acceptance. Commit/push authorized changes and publish `EXECUTION_RESULT.json`, then STOP.
