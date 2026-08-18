# OPS-RC1 R2 — Evidence Report

**Task:** `AITHER-MVP-OPS-RC1-R2`
**Mode:** OPS_RC1 (corrective execution of R1 — exact-path allowlist defect)
**Branch:** `aither-v2`
**Baseline SHA:** `63ad4ef91221aa32cfa3d1be6cdc770787a0a9a4`
**Executor:** Hermes (HERMES-INTEGRATION)
**Date:** 2026-08-18

> R1 was `BLOCKED / NOT ACCEPTED` because the runner treated directory-prefix
> `allowed_paths` entries as exact filenames. R1 had already performed the runtime
> deployment (monitoring stack, backup CronJobs, ResourceQuota/LimitRange,
> NetworkPolicies — all `~9h` old at R2 start) but could not commit the manifests.
> R2 reconciles the source manifests with the live runtime and re-collects runtime
> evidence. No unrelated scope was reopened.

---

## Evidence contract flags

| Flag | Value |
|------|-------|
| `SECRET_VALUES_PRINTED` | NO |
| `SECRETS_EXPOSED` | NO |
| `OWNER_ACTION_REQUIRED` | YES — (1) Telegram bot_token/chat_id for D1 end-delivery; (2) NetworkPolicy-capable CNI decision for #30 enforcement |

---

## Workstream A — D1: Alertmanager + Telegram alerts

### Source/config change summary
- `manifests/observability/prometheus.yaml` — reconciled: `prometheus-config`
  (alerting → `alertmanager.monitoring.svc:9093`, `rule_files` → `/etc/prometheus/rules/*.rules`,
  scrape jobs for dcgm-exporter / node-exporter / kube-state-metrics / vllm), `prometheus-rules`
  (4 rule groups), Deployment (serviceAccount `prometheus`, emptyDir TSDB), Service (NodePort 30909).
- `manifests/observability/alertmanager.yaml` — NEW: `alertmanager-config`
  (route → `default` receiver, group_wait 30s, group_interval 30s, repeat_interval 4h),
  Deployment (v0.27.0), Service (9093).
- `manifests/observability/kube-state-metrics.yaml` — NEW: ServiceAccount, ClusterRole,
  ClusterRoleBinding, Deployment, Service (source of `kube_pod_container_status_restarts_total`).

### Runtime validation (exact)
- Prometheus Deployment `1/1` Running; Alertmanager Deployment `1/1` Running;
  kube-state-metrics `1/1` Running; node-exporter DaemonSet `2/2` (both nodes).
- Prometheus active alertmanager: `http://alertmanager.monitoring.svc:9093/api/v2/alerts`
  (`activeAlertmanagers: 1`, `droppedAlertmanagers: []`).
- All Prometheus scrape targets `health=up`:
  `dcgm-exporter`, `kube-state-metrics`, `node-exporter` (x2: 10.129.13.77, 10.129.13.78),
  `vllm` (vllm-32b-instruct-awq, vllm-qwen3-32b-awq).
- Rules loaded via `GET /api/v1/rules`: 4 groups —
  `gpu` [GPUHighTemperature, GPUMemoryPressure], `node` [ClockOffsetHigh],
  `kubernetes` [PodRestartAnomaly], `test` [SyntheticTestAlert].
- Alertmanager `/-/healthy` → `OK`; `/-/ready` → `OK`; `GET /api/v2/status` → version 0.27.0,
  config `original` includes `route.receiver: default`.
- Synthetic alert path proven: `SyntheticTestAlert` present in Alertmanager
  `GET /api/v2/alerts` with `status.state=active` (i.e. Prometheus → Alertmanager delivery works).
- Real alert also delivered: `PodRestartAnomaly` `active` in Alertmanager
  (source: `flink-taskmanager` container restarting in `aiops` namespace — a genuine
  cross-tenant restart signal correctly captured by the rule).
- GPU coverage: `GPUHighTemperature` not firing (healthy), `GPUMemoryPressure` `pending`
  (framebuffer below threshold) — both rules loaded and evaluating.

### Status
- **PASS** for Alertmanager deployment, config acceptance, rule loading, and the
  Prometheus → Alertmanager synthetic-alert path.
- **PARTIAL** for Telegram end-delivery — **BLOCKED**: no Telegram bot_token/chat_id
  Secret exists in the cluster (verified by name-only secret enumeration across all
  namespaces). `alertmanager-config` carries only a documented placeholder comment, no
  credential values. End-delivery requires OWNER-provided credentials.

### Regression / reversibility
- Monitoring pods healthy after validation; Prometheus `/-/ready` → `Ready`.
- Manifests are declarative; rollback = `kubectl apply` of the previous revision
  (all components stateless, TSDB on emptyDir).

---

## Workstream B — D2: NTP / time-sync monitoring

### Source/config change summary
- `manifests/observability/node-exporter.yaml` — NEW: DaemonSet with `--collector.timex`
  (exposes `node_timex_*`), hostNetwork/hostPID, `/proc` `/sys` `/` hostPath mounts,
  headless Service (9100).
- `manifests/observability/prometheus.yaml` — `ClockOffsetHigh` rule
  (`abs(node_timex_offset_seconds) > 5` for 5m) in the `node` rule group.

### Runtime validation (exact)
- Time-sync mechanism (no package install): `chronyd` **active** on both nodes
  (`systemd-timesyncd` inactive); `timedatectl` → `System clock synchronized: yes`,
  `NTP service: active`.
- N7 (`chronyc tracking`): Reference ID `596DFB16` (ntp2.vniiftri.ru), Stratum 2,
  System time `0.000141144 s` fast, RMS offset `0.000044143 s`.
- N8 (`chronyc tracking`): Reference ID `A29FC801` (time.cloudflare.com), Stratum 4,
  System time `0.000010708 s` fast, RMS offset `0.000088575 s`.
- `node_timex_offset_seconds` confirmed to exist on both nodes via node-exporter metrics:
  N7 `0`, N8 `0` (well within the 5s threshold → alert not firing, healthy).
- `ClockOffsetHigh` rule confirmed loaded (Prometheus `GET /api/v1/rules`).

### Status
- **PASS**. `node_timex_offset_seconds` is the runtime-confirmed metric and maps
  1:1 to the `ClockOffsetHigh` rule; both N7 and N8 offset states are healthy.

### Metric-mapping note (honest caveat)
- `node_timex_sync_status` reads `1` on N7 and `0` on N8, while `chronyc tracking` on N8
  reports a synchronized clock (offset ~1.1e-5 s). This is a known chrony↔`adjtimex`
  status-bit discrepancy; the **offset** metric (`node_timex_offset_seconds`) is the
  canonical drift signal used by the rule, and it is ~0 on both nodes.

### Regression / reversibility
- node-exporter DaemonSet unaffected; rule is passive. Rollback = re-apply prior DaemonSet.

---

## Workstream C — D3: PostgreSQL + Redis backup/restore

### Source/config change summary
- `manifests/backups.yaml` — NEW: PVC `aither-backup` (10Gi) + PV `pv-aither-backup`
  (hostPath `/data/aither-backup`, reclaimPolicy Retain), CronJob `postgres-backup`
  (`0 2 * * *`, `pg_dump -Fc`, 7-day `find -mtime +7 -delete` retention), CronJob
  `redis-backup` (`0 2 * * *`, `redis-cli --rdb`, 7-day retention).
- Credentials referenced by Secret **name only** (`aither-gateway-postgres`:
  `PG_USER`/`PG_PASSWORD`/`PG_DB`); no credential values embedded.
- Backup targets the **actual live persistence**: PostgreSQL `postgres.aiops.svc`
  (aiops namespace) and Redis `aither-redis-rate-limit.aither-inference.svc`.
- Retention/cleanup: `find /backup -name '*.dump' -mtime +7 -delete` (PG) and
  `find /backup -name '*.rdb' -mtime +7 -delete` (Redis); visible failure behavior via
  `backoffLimit: 2` + `failedJobsHistoryLimit: 3`.

### Runtime validation (exact)
- CronJobs scheduled, `suspend: false`; last run `2026-08-18T02:00:00Z`, both
  `lastSuccessfulTime` populated (jobs `Complete`, exit 0).
- Backup storage verified: `/data/aither-backup/` contains
  `aither-pg-20260818_020000.dump` (34 220 B) and `aither-redis-20260818_020000.rdb` (179 834 B).
- **PostgreSQL restore (non-destructive, temp pod `pg-restore-test`):**
  - `pg_restore --list` → `Format: CUSTOM`, `Compression: gzip`, `TOC Entries: 85`,
    `Dumped from database version: 16.14`, dbname `aither`.
  - Full `pg_restore --no-owner --no-privileges` into a fresh temp instance → exit 0;
    13 tables restored (`billing_accounts`, `billing_idempotency`, `billing_ledger`,
    `billing_reservations`, `gateway_audit_events`, `gateway_idempotency`,
    `model_drain_state`, `portal_api_keys`, `rag_collections`, `rag_documents`,
    `schema_migrations`, `subscription_tiers`, `usage_records`).
  - Data readability proven: `subscription_tiers=2`, `portal_api_keys=3`,
    `billing_accounts=3`, `schema_migrations=1`; sample `SELECT * FROM subscription_tiers`
    returned rows (`free`, `standard`). `portal_api_keys.api_key` values were **not** read.
- **Redis restore (non-destructive, temp pod `redis-restore-test`):**
  - `redis-check-rdb` → `Checksum OK`, `RDB looks OK!`, 418 keys, 7 expires.
  - Fresh Redis loaded RDB: `keys loaded: 418`; `dbsize` → `418`; sample keys readable
    (`aither-auth:invite:*`, `aither-auth:token:user:*`, `aither-auth:user:*`).
- Temporary restore resources (`pg-restore-test`, `redis-restore-test`, and the
  `tenancy-test` namespace from #30) removed; verified no temp resources remain.

### Status
- **PASS**. Scheduled backups run, retention/failure behavior configured, and both
  PostgreSQL and Redis dumps restored and read in isolated temporary targets without
  touching production data.

### Regression / reversibility
- Production PostgreSQL (aiops) and Redis (aither-inference) untouched (restore was into
  temp emptyDir-backed instances). Rollback = delete CronJobs/PVC via `kubectl delete -f`.

---

## Workstream D — #30: Multi-tenant isolation

### Source/config change summary
- `manifests/quotas.yaml` — NEW: ResourceQuota `aither-quota` (pods 60, requests.cpu 30,
  requests.memory 140Gi, limits.cpu 60, limits.memory 200Gi, PVCs 20) + LimitRange
  `aither-limits` (Container min/max + defaults 500m/512Mi, defaultRequest 100m/128Mi).
- `manifests/network-policies.yaml` — NEW: `vllm-ingress` (allow vllm:8000 from
  `aither.io/vllm-client=true` namespaces), `aither-gateway` (ingress from aither-bff;
  egress to vllm/redis/postgres/vault/dns), `aither-siem` (gateway→SIEM), `vault`
  (vault ingress from aither-inference + monitoring).

### Runtime validation (exact)
- **Quota/LimitRange — ENFORCED (PASS):**
  - `aither-quota` active, `used` tracked: `pods 16/60`, `requests.cpu 17700m/30`,
    `requests.memory 100800Mi/140Gi`, `limits.cpu 39600m/60`, `limits.memory 137600Mi/200Gi`.
  - LimitRange defaulting proven: a probe pod created with **no** resource spec was
    defaulted to `limits {cpu:500m, memory:512Mi}` / `requests {cpu:100m, memory:128Mi}`;
    quota `pods` count moved 16 → 17 → 16 after cleanup (active enforcement).
- **NetworkPolicy — DECLARED BUT NOT ENFORCED (PARTIAL/BLOCKED):**
  - CNI is plain flannel (`ghcr.io/flannel-io/flannel:v0.28.7`, `--ip-masq
    --kube-subnet-mgr`); no Calico/Cilium/kube-router/canal present.
  - Prohibited-path test (temp namespace `tenancy-test` **without** the
    `aither.io/vllm-client=true` label): `wget http://vllm-32b-instruct-awq.aither-inference.svc:8000/metrics`
    → **succeeded** (HTTP 200 metrics, `EXIT=0`). The cross-tenant path is **not denied**.
  - Corroboration: Prometheus (monitoring namespace, unlabeled) scrapes vllm `health=up`.
- **Platform traffic functional (PASS):** aither-inference production deployments healthy
  (portal, bff 2/2, identity, ai-platform, redis-rate-limit, vllm-32b-instruct-awq,
  vllm-qwen3-32b-awq all ready).

### Status
- **PARTIAL.** ResourceQuota + LimitRange enforcement is proven. NetworkPolicy objects are
  applied to the API server but are **not enforced** because flannel has no NetworkPolicy
  engine; the prohibited cross-tenant path is demonstrably **not** blocked.
- **Exact blocker:** NetworkPolicy enforcement requires installing/configuring a
  NetworkPolicy-capable CNI (Calico/Cilium/Canal) — a cluster-wide networking change that
  is outside this executor's authority and `package_install=false` scope, and which risks
  production traffic. This is **OWNER_ACTION_REQUIRED** (decide CNI migration). Isolation
  was not weakened to make the test pass; the honest non-enforcement finding is reported.

### Regression / reversibility
- Quota/LimitRange are API-server enforced and non-disruptive. NetworkPolicies are
  declarative; adding an enforcement CNI later will activate them without manifest changes.

---

## Workstream E — C3: Kubernetes cluster hygiene

### Runtime validation (exact)
- `kubectl get pods -A --field-selector status.phase!=Running,status.phase!=Succeeded`
  → **no resources** (no Failed/Evicted pods).
- Completed pods: `postgres-backup-29783640-*`, `redis-backup-29783640-*` (CronJob history,
  retained by design via `successfulJobsHistoryLimit: 3`); `nvidia-cuda-validator-*`
  (gpu-operator-managed validator).
- Jobs: only the two `Complete` backup jobs — no stale/orphaned Jobs.
- **No objectively stale/disposable artifacts require removal.** Cluster is clean.

### Remaining non-healthy objects (documented, NOT removed)
- `aither-gateway` (0/2 ready, readiness probe HTTP 503 ×106k over 11d) — pre-existing
  broken gateway; repair is out of scope for this task.
- `nginx-gateway-32b` (0/2 ready) — legacy gateway for the scale-to-0 32B-GPTQ model.
- `flink-taskmanager-*` (aiops namespace) — crash-looping AIOps workload (separate system,
  out of scope; it is also the live source of the correctly-firing `PodRestartAnomaly` alert).
- `vllm-14b-instruct`, `vllm-32b-gptq`, `aither-bff-gateway-canary` — intentionally scaled to 0.
- No healthy production application/model pod was deleted or restarted.

### Status
- **PASS** (no stale artifacts to remove); remaining non-healthy objects are documented
  with reasons (out of scope / intentional).

### Regression / reversibility
- No mutations performed; nothing to roll back.

---

## Summary

| Workstream | Result |
|-----------|--------|
| D1 Alertmanager + Telegram | **PASS** (alerting path); Telegram end-delivery **BLOCKED** (no Owner creds) |
| D2 NTP monitoring | **PASS** |
| D3 PostgreSQL + Redis backup/restore | **PASS** |
| #30 Multi-tenant isolation | **PARTIAL** (quota/limits enforced; NetworkPolicy not enforced — flannel CNI) |
| C3 Cluster hygiene | **PASS** |

**Overall:** All autonomously achievable OPS-RC1 gates pass. Two items depend on Owner action:
1. Telegram bot_token/chat_id for D1 end-delivery.
2. NetworkPolicy-capable CNI decision for #30 enforcement.

`SECRET_VALUES_PRINTED: NO`
`SECRETS_EXPOSED: NO`
`OWNER_ACTION_REQUIRED: YES` — (1) Telegram credentials; (2) CNI migration decision for NetworkPolicy enforcement.
