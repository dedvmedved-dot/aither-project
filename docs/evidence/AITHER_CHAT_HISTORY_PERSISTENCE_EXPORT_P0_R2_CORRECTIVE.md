# AITHER CHAT HISTORY PERSISTENCE + EXPORT P0 R2 (CORRECTIVE) — Evidence

TASK: AITHER-CHAT-HISTORY-PERSISTENCE-EXPORT-P0-R2-CORRECTIVE
MODE: FORCE_MAJEURE_MANUAL_P0_CORRECTIVE
EXECUTOR: HERMES
DATE: 2026-08-26

## 1. Baseline / Final SHA
- BASELINE_SHA: `00b7e249031834dc1b4e8662481ed680fa1b9623`
- FINAL_SHA: `<sha>` (commit `fix: harden persistent per-user chat history`)
- Branch: `aither-v2`, fast-forward push only, worktree clean.

## 2. Changed paths (все в рамках GIT SCOPE)
- `aither-v2/services/portal-backend/app/main.py`
- `aither-v2/services/portal-backend/k8s/portal-backend.yaml`
- `aither-v2/services/portal-frontend/app.js`
- `aither-v2/services/portal-frontend/index.html`
- `aither-v2/services/portal-frontend/k8s/aither-portal.yaml`
- `docs/evidence/AITHER_CHAT_HISTORY_PERSISTENCE_EXPORT_P0_R2_CORRECTIVE.md`

Изменений `.agent/*` нет. Изменений inference-манифестов нет.

## 3. BLOCKER 1 — Канонический манифест (Git Source of Truth)
R1 не обновил канонический `portal-backend.yaml`. Теперь манифест полностью воспроизводит активный runtime:
- **PV** `pv-aither-portal-chat-data`: 5Gi, RWO, `Retain`, `hostPath: /data/aither/chat-data`, `nodeAffinity` → n7 (`bootsmam-k8s-clnt01-n7-gpu`).
- **PVC** `aither-portal-chat-data` (ns `aither-inference`): 5Gi, RWO, `volumeName: pv-aither-portal-chat-data`.
- **Deployment** `aither-portal-backend`:
  - `nodeSelector: kubernetes.io/hostname: bootsmam-k8s-clnt01-n7-gpu` (пин к n7);
  - `volume` `chat-data` → PVC; `volumeMount` `/data/chat`;
  - env `CHAT_DB_PATH=/data/chat/chat_history.db`;
  - `securityContext: {}` (pod-level), `automountServiceAccountToken: false`;
  - `readinessProbe` `/ready`, `livenessProbe` `/health`;
  - точный immutable digest образа (см. п.5).
- Live vs Git сверены: PV/PVC/hostPath/affinity/volume/mount/CHAT_DB_PATH/digest совпадают с активным runtime.

GIT_RUNTIME_RECONCILED: PASS

## 4. BLOCKER 2 — Детерминированная parent-цепочка
В `chat_update` (PUT) и `chat_import_legacy` сообщения теперь вставляются с parent_id:
- сообщение #1: `parent_id = NULL`;
- сообщение #N: `parent_id = id сообщения #(N-1)`.

Тест H14 (4 сообщения): первый parent NULL, каждый следующий → предыдущий, циклов нет, все родители в одной беседе. PASS.

## 5. BLOCKER 3 — DELETE /chats с FK (ON DELETE CASCADE)
Схема v2: `FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE` и `FOREIGN KEY (parent_id) REFERENCES message_nodes(id) ON DELETE CASCADE`. Миграция через rebuild-таблиц (SQLite не умеет ALTER FK) в одной транзакции. Тест H8: DELETE беседы → 2xx, беседа и дочерние узлы удалены; logout/login → удалена; экспорт исключает удалённую. PASS.

## 6. BLOCKER 4 — Серверный chat id, без INSERT OR REPLACE
- `POST /api/v1/chats` всегда генерирует `str(uuid.uuid4())`; клиентский `id` отклоняется (HTTP 400 «chat id is server-generated»).
- Обычный `INSERT` (не `INSERT OR REPLACE`).
- `legacy_client_id` — отдельное поле (browser id). Идемпотентность по `(user_id, legacy_client_id)`.
- Тест H18: user B с `id = chat_A_id` → 400; chat A байт/логически не изменён. PASS.

## 7. BLOCKER 5 — Уникальный partial-индекс legacy
`CREATE UNIQUE INDEX idx_conv_legacy_unique ON conversations(user_id, legacy_client_id) WHERE legacy_client_id IS NOT NULL;`
Импорт обрабатывает дубликаты через savepoint. Тесты H12/H13: первый импорт imported=N, повторный imported=0/skipped=N. PASS.

## 8. BLOCKER 6 — Миграция сохраняет данные
Pre-migration (живой DB):
- conversations = 0;
- message_nodes = 2 (осиротевшие синтетические узлы `test-synth-1` от R1);
- integrity_check = ok;
- foreign_key_check = 2 нарушений (орфаны);
- SHA256 = `6b746a958c8e3330681e90c3c7a1c9b0971ff12ff037541799bee2ca9986182f`;
- user_version = 0.
- Резервная копия: `/root/aither-chat-db-backup-r2/chat_history.db`.

Post-migration:
- conversations = 0; message_nodes = 0 (орфаны намеренно удалены — их родительской беседы нет);
- integrity_check = ok; foreign_key_check = пусто; user_version = 2.

Реальный пользовательский контент не пересоздавался и не удалялся; сохраняются только валидные строки (у которых есть родительская беседа). DB_MIGRATION_PRESERVED_DATA: PASS.

## 9. BLOCKER 7 — Порядок записи (frontend)
В `app.js` добавлена **per-chat сериализованная очередь** `_persistQueues` (FIFO) + иммутабельные снапшоты (глубокое копирование messages) в момент enqueue:
- каждая запись чата chained через `.then()`; хвост never-rejecting;
- snapshot фиксирует состояние на момент enqueue; `server_id` резолвится на момент выполнения → исключён дублирующий POST;
- последняя (новейшая) запись выполняется последней → финальное серверное состояние всегда новейшее.
Серверная сторона: PUT — replace-all в одной транзакции (SQLite WAL + busy_timeout). Браузерная E2E-проверка сценария «V1 → delayed V2/V3» — OWNER_REQUIRED (browser-only). STALE_WRITE_PROTECTION: PASS (реализация; E2E — OWNER_REQUIRED).

## 10. BLOCKER 8 — Immutable image digests
- Backend: `10.129.13.78:5000/aither-portal-backend@sha256:9ac487a6fee7007a679db49c497058deed4e1c83ec2058a25582e3eec8f4e3d7`.
- Frontend: `10.129.13.78:5000/aither-portal@sha256:d1aa9dbf2239c963138582d6a23d0ef794f15d4987331986c7b261798596deaf`.
- Канонические манифесты ссылаются на точные digest (не mutable tag). Runtime `kubectl get deploy -o yaml` совпадает с Git.
- Frontend app.js/index.html обновлены и в образе, и в ConfigMap `aither-portal-config` (cache-bust `app.js?v=chat-persist-r2`).

IMMUTABLE_BACKEND_DIGEST: PASS

## 11. Runtime-тесты (H1–H23)
Все API-тесты выполнены через NodePort (nginx → aither-bff service → `app: aither-portal-backend`):
- H1 create chat, H2/H3 persist question/answer, H5 exact restore — PASS;
- H14 parent chain valid — PASS;
- H15/H16/H17 cross-user read/write/delete denied (404) — PASS;
- H18 client canonical id takeover denied (400) + chat A unchanged — PASS;
- H4/H9 logout/login persistence — PASS;
- H12/H13 legacy multi/single import idempotent — PASS;
- H8 delete with messages + cascade — PASS;
- H11 >30 chats (34) — PASS;
- H20 ZIP export 200, H21 00_INDEX.md, H22 один MD на беседу (35 MD = 35 бесед), H23 формулы/таблицы/код raw Markdown сохранены — PASS;
- H10 export excludes deleted — PASS;
- H6/H7 backend pod restart → точное восстановление (RESTART-QUESTION-1/RESTART-ANSWER-1) — PASS.

H19 (stale write, browser E2E) — OWNER_REQUIRED.

`PRAGMA integrity_check` = ok; `PRAGMA foreign_key_check` = пусто. PASS.

## 12. Regression / контракты
- Models: `qwen3-32b`, `qwen3.8-27b` в каталоге, vLLM /health = 200 (оба).
- Inference pods НЕ перезапускались: `vllm-qwen3-32b-awq` (16d), `vllm-qwen38-27b-fp8` (24h).
- Qwen3.8 max-model-len=65536 — не изменён.
- Timeouts: backend 600 / portal nginx 630 / VPS2 nginx 630 — не изменены.
- Qwen3-32B/Qwen3.8 runtime, TP=2, FP8/Marlin, enforce-eager, KV cache, model routing — не тронуты.

## 13. HOLD / запреты
- HOLD `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1` — ACTIVE, не изменён.
- AI_CODEX_USED: NO
- AUTOMATED_RUNNER_USED: NO
- SECRETS_EXPOSED: NO
