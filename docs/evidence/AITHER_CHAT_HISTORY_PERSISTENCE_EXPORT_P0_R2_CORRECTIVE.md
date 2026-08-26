# AITHER CHAT HISTORY PERSISTENCE + EXPORT P0 R2 (CORRECTIVE) — Evidence

- TASK ID: `AITHER-CHAT-HISTORY-PERSISTENCE-EXPORT-P0-R2-CORRECTIVE`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `00b7e249031834dc1b4e8662481ed680fa1b9623`
- FINAL SHA: `<sha>`
- PARENT SHA: `00b7e249031834dc1b4e8662481ed680fa1b9623`
- BRANCH: `aither-v2`

## 1. Changed paths (все в рамках GIT SCOPE)
- `aither-v2/services/portal-backend/app/main.py`
- `aither-v2/services/portal-backend/k8s/portal-backend.yaml`
- `aither-v2/services/portal-frontend/app.js`
- `aither-v2/services/portal-frontend/index.html` (cache-bust `app.js?v=chat-persist-r2`)
- `aither-v2/services/portal-frontend/k8s/aither-portal.yaml`
- `docs/evidence/AITHER_CHAT_HISTORY_PERSISTENCE_EXPORT_P0_R2_CORRECTIVE.md`

`.agent/CURRENT_TASK.json` / `.agent/CURRENT_TASK.md` — НЕ изменены. Inference-манифесты — НЕ изменены.

## 2. Root causes (исправленные дефекты R1)
1. `POST /chats` принимал browser `id` + `INSERT OR REPLACE` (browser выбирал canonical ID).
2. Frontend создавал `uid()` и слал `PUT /chats/{uid}` → 404, без реального `POST` (серверный chat не создавался).
3. `parent_id = NULL` у всех узлов.
4. FK без `ON DELETE CASCADE`; DELETE conversation оставлял/ломал орфанов.
5. Отсутствие реальной R1→R2 миграции (`CREATE TABLE IF NOT EXISTS` не мигрирует).
6. Обычный индекс `(user_id, legacy_client_id)` без UNIQUE.
7. Frontend `chatSessions.slice(0,30)` + полная история в localStorage.
8. Fire-and-forget persistence (нет server-ack перед inference, нет await после).

## 3. Implementation summary
- **BLOCKER 1 (server-generated ID)**: `POST /chats` всегда `str(uuid.uuid4())`; `body.id` → HTTP 400 «chat id is server-generated»; обычный `INSERT` (без `INSERT OR REPLACE`); `legacy_client_id` — отдельное поле; идемпотентность по `(user_id, legacy_client_id)`.
- **BLOCKER 2 (frontend реально создаёт chat)**: `_doServerPersist` без `server_id` → `POST /chats` → сохраняет `session.server_id` → далее `PUT /chats/{server_id}`.
- **BLOCKER 3 (linear parent_id)**: PUT + import вставляют цепочку (root NULL, далее → prev). Миграция перестраивает цепочку существующих R1-бесед через `LAG(id) OVER (PARTITION BY conversation_id ORDER BY sequence_no)`.
- **BLOCKER 4 (FK cascade)**: `conversation_id` и `parent_id` → `ON DELETE CASCADE`.
- **BLOCKER 5 (реальная миграция)**: `PRAGMA user_version` (0→2), rebuild-таблиц в одной транзакции, idempotent, restart-safe, fail-closed (integrity/fk проверка после).
- **BLOCKER 6 (legacy UNIQUE)**: partial unique index `(user_id, legacy_client_id) WHERE legacy_client_id IS NOT NULL`; duplicate pre-check → `BLOCKED_LEGACY_DUPLICATES` при дублях.
- **BLOCKER 7 (server = SoT)**: удалён `slice(0,30)`; localStorage хранит только `aither_current_chat`; полная история — только server-side.
- **BLOCKER 8 (durable write ordering)**: pre-inference `await` + abort при ошибке; post-inference/continue `await`; delete server-confirm → UI.
- **BLOCKER 9 (canonical manifest)**: PV/PVC/5Gi/RWO/Retain/hostPath/nodeAffinity/nodeSelector/volume/volumeMount/CHAT_DB_PATH/securityContext/digest — в Git.

## 4. Schema before / after
- BEFORE (R1): `user_version=0`; FK без CASCADE; обычный `idx_conv_legacy`.
- AFTER (R2): `user_version=2`; `ON DELETE CASCADE` (conversation_id, parent_id); `idx_conv_legacy_unique` (partial UNIQUE).

## 5. DB backup evidence
- Path: `/root/aither-chat-db-backup-r2/chat_history.db`
- Size: 32768 bytes
- SHA256: `6b746a958c8e3330681e90c3c7a1c9b0971ff12ff037541799bee2ca9986182f`

## 6. Migration evidence (row counts / hashes)
- Pre-migration: conversations=0, message_nodes=2 (осиротевшие синтетические `test-synth-1`), foreign_key_check=2, integrity=ok.
- Post-migration: conversations=0, message_nodes=0 (орфаны удалены — родительской беседы нет), foreign_key_check=пусто, integrity=ok, user_version=2.
- Реальные данные не терялись/не дублировались (0 валидных строк). Хеш данных не раскрывает содержимое (0 строк).

## 7. Parent chain verification
`PRAGMA foreign_key_list(message_nodes)` → `on_delete=CASCADE` для `conversation_id` и `parent_id`.
Тест на 4 сообщения: root `parent_id IS NULL`, каждый `seq>1` → `parent_id = id(seq-1)`, циклов нет, все родители в одной беседе. PASS.
Миграционный rebuild цепочки (LAG) проверен на синтетической R1-схеме: seq1=NULL, seq2→n0, seq3→n1, seq4→n2. PASS.

## 8. Cascade verification
DELETE conversation → 2xx, conversation absent, message_nodes=0, orphan=0; после pod restart → GET 404; после login → absent. PASS.

## 9. UNIQUE legacy verification
`idx_conv_legacy_unique` (partial UNIQUE). Duplicate pre-check: при дублях → `BLOCKED_LEGACY_DUPLICATES`. Reimport: imported=0/skipped=N. PASS.

## 10. Server-generated ID verification
`POST /chats` → server UUID. `body.id` → 400. Takeover-тест (user B с `id=chat_A`) → 400, chat A не изменён. PASS.

## 11. >30 chats verification (35 chats)
Создано 35 chats + сообщения. После backend pod restart: server_count=35, missing=0; content сохранён. После logout/login: 35, missing=0. PASS.

## 12. Cross-user isolation
GET/PUT/DELETE чужого id → 404 (read/write/delete denied). Export — только свои. PASS.

## 13. Delete verification
См. §8 (cascade). После restart — 404. PASS.

## 14. Pod restart persistence
Synthetic chat → restart → exact restore (RESTART-QUESTION-1/RESTART-ANSWER-1 + parent chain + metadata). readiness PASS. PASS.

## 15. Export verification
GET `/chats/export` → 200 ZIP: `00_INDEX.md` + один `.md` на беседу (35 MD = 35 бесед). Markdown raw (формулы `$E=mc^2$`, таблицы, fenced code, Unicode). Filename sanitization. Deleted excluded. PASS.

## 16. Git/runtime reconciliation
PV/PVC/storage path/reclaim/access/capacity/node affinity/backend node placement/volume/volumeMount/CHAT_DB_PATH/backend digest/frontend digest/securityContext/readiness — сверены live vs Git. PASS.

## 17. Exact image digests
- Backend: `10.129.13.78:5000/aither-portal-backend@sha256:0759874777dc5a058aadf7d7555b828fb9120f857da0db4ddf130c961cbfa18d`
- Frontend: `10.129.13.78:5000/aither-portal@sha256:14c5808079327b217facc300b3adb08adb87368f95afbfd968a8e692e84b93f3`

## 18. Inference/runtime unchanged
Qwen3-32B: не изменён. Qwen3.8-27B: не изменён (max-model-len=65536, max-num-seqs, gpu-mem, FP8 E4M3, Marlin, FP16 compute, KV FP16, enforce-eager, timeout chain). Inference pods НЕ перезапускались: `vllm-qwen3-32b-awq` (16d), `vllm-qwen38-27b-fp8` (24h). Model catalog: `qwen3-32b`, `qwen3.8-27b` (200).

## 19. HOLD / compliance
- HOLD `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1` — ACTIVE, не изменён.
- `.agent/CURRENT_TASK.json` CHANGED: NO
- `.agent/CURRENT_TASK.md` CHANGED: NO
- AI_CODEX_USED: NO
- AUTOMATED_RUNNER_USED: NO
- SECRETS_EXPOSED: NO
- WORKTREE: CLEAN
