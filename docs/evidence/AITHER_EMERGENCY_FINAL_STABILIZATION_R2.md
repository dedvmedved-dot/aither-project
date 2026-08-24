# AITHER EMERGENCY FINAL STABILIZATION R2 — Evidence

TASK: AITHER-EMERGENCY-FINAL-STABILIZATION-R2
MODE: FORCE_MAJEURE_MANUAL_FINAL_STABILIZATION
EXECUTOR: HERMES
DATE: 2026-08-24

## 1. BASELINE_SHA

`c12673fe2c962606312b0a8ac7087ae5200b395c` — "emergency: restore Aither Portal production user path"

## 2. FINAL_SHA

Зафиксирован финальным audit-коммитом (см. `git log`, message `audit: finalize Aither emergency stabilization R2`).

## 3. OWNER browser evidence status O1–O5

Не предоставлены на момент формирования evidence → все `REQUIRED`.

- O1 LOGIN — REQUIRED
- O2 MODEL SELECTOR — REQUIRED
- O3 WEB CHAT BOTH MODELS — REQUIRED
- O4 DOCUMENTATION — REQUIRED
- O5 REFRESH/PERSISTENCE — REQUIRED

Правило: Hermes не подменяет browser evidence curl-тестами. Общий `PASS` не присваивается.

## 4. Current K8s readiness

- n7 Ready, n8 Ready.
- Все production pods 1/1 Ready: ai-platform, bff×2, identity, portal, portal-backend, portal-frontend, redis-rate-limit, siem, chromadb.
- Active inference Ready: `vllm-qwen3-32b-awq`, `vllm-qwen38-27b-fp8`.
- Нет CrashLoopBackOff / ImagePullBackOff / Pending production pods.

## 5. Current model IDs

`qwen3-32b`, `qwen3.8-27b` (ровно две активные).

## 6. External API statuses

- `GET /api/v1/models` → 200, ровно две модели.
- `POST /api/v1/chat/completions` qwen3-32b → 200, nonempty.
- `POST /api/v1/chat/completions` qwen3.8-27b → 200, nonempty.

## 7. Unknown model negative

`retired-test-model-xyz` → HTTP 404 `{"detail":"model_not_found: 'retired-test-model-xyz'"}`. Нет fallback.

## 8. Invalid session negative

`GET /api/v1/models` с `Bearer invalid-session-xyz` → HTTP 401 `{"detail":"Invalid token"}` (fail-closed через Identity). Нет прокси в model backend, нет 5xx.

## 9. Docs normal URL

`GET /docs/17_MODEL_USAGE_GUIDE.md` → 200, `Content-Type: text/plain; charset=utf-8`, `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`. Содержит `CB-WEBUI-03`, `qwen3-32b`, `qwen3.8-27b`; старый заголовок `Qwen2.5-32B и Qwen3-32B` отсутствует.

## 10. Docs cache-busted

`GET /docs/17_MODEL_USAGE_GUIDE.md?rev=<UTC>` → 200, тот же актуальный body.

## 11. Legacy state

- `aither-gateway` — replicas 0.
- `nginx-gateway-32b` — replicas 0.
- `ai-platform-test` (docker) — exited/stopped.

Production path не имеет consumers этих legacy components.

## 12. HOLD state

- `CURRENT_TASK.json`: task_id `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`.
- `agent_exec=false`, `source_write=false`, `runtime_write=false`, `kubernetes=false`, `deployment=false`.
- host `sync/commit/push=false`.
- Runner timer active; execution service fail-closed: `BLOCKED "host capability prohibits action: sync"` (не выполняет Hermes task).

## 13. Active executor state

Активный Hermes executor process отсутствует. H2 socket может оставаться LISTEN (не считается активным выполнением).

## 14. Changed files

Только evidence (нет source changes, P0 correction не требовался).

## 15. P0 correction required

NO.

## 16. Rollback details

Не применялся.

## 17. Backlog preserved

Да — не тронуты: governance runner repair, BLOCKED_* propagation, retry/suppression redesign, H2 observer redesign, aither-status.service, ts-collector.service, ai-platform-test permanent removal, legacy manifest deletion, RCA (controller-manager/scheduler/Flink), performance/benchmark/SLO/observability, D2/D3/E1/F1/F2, portal feature expansion, refactoring.

## 18. SECRETS_EXPOSED: NO
## 19. AI_CODEX_USED: NO
## 20. AUTOMATED_RUNNER_USED: NO
