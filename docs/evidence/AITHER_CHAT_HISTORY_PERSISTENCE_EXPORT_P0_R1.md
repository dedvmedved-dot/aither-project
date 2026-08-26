# AITHER CHAT HISTORY PERSISTENCE + EXPORT P0 R1 — Evidence

TASK: AITHER-CHAT-HISTORY-PERSISTENCE-EXPORT-P0-R1
MODE: FORCE_MAJEURE_MANUAL_P0_USER_DATA_CORRECTION
EXECUTOR: HERMES
DATE: 2026-08-26

## 1. Baseline / Final SHA
- BASELINE: `65d457cd8d206ede3a8b75c2490c7f66a4040d6e`
- FINAL: финальный commit (`feat: persist and export per-user chat history`)

## 2. Root cause
Frontend хранил чаты в `localStorage` (`aither_chats`, `aither_current_chat`), обрезал до 30, а Logout удалял их → потеря истории при новом входе.

## 3. Changed paths
- `aither-v2/services/portal-backend/app/main.py`
- `aither-v2/services/portal-frontend/app.js`
- `aither-v2/services/portal-frontend/index.html`
- `aither-v2/services/portal-frontend/k8s/aither-portal.yaml` (image digest)
- `docs/evidence/AITHER_CHAT_HISTORY_PERSISTENCE_EXPORT_P0_R1.md`

## 4. Storage discovery
No StorageClass (bare-metal). Existing pattern: статические PV (hostPath) + PVC + `Retain`.

## 5. Chosen PV/PVC design
- PV `pv-aither-portal-chat-data`: 5Gi RWO Retain, hostPath `/data/aither/chat-data`, nodeAffinity → n7.
- PVC `aither-portal-chat-data` (namespace aither-inference).
- Portal-backend pinned к n7 (`nodeSelector kubernetes.io/hostname: bootsmam-k8s-clnt01-n7-gpu`).
- ⚠️ Адаптация: mount = `/data/chat` (а не `/data`), чтобы не затенить image-baked `/data/rag-docs`.

## 6. DB path / schema
- DB: `/data/chat/chat_history.db` (env `CHAT_DB_PATH`).
- SQLite, `PRAGMA journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`.
- `conversations` (id, user_id, title, model, created_at, updated_at, legacy_client_id, tokens, requests, schema_version).
- `message_nodes` (id, conversation_id, parent_id, sequence_no, role, content, model, answer_id, created_at, metadata_json) + FK + unique `(conversation_id, sequence_no)`.
- Indexes: `(user_id, updated_at)`, `(user_id, legacy_client_id)`.

## 7. Auth ownership
`_chat_owner` = `await _get_user_from_token(request)` → `user["id"]`. Все SQL с `WHERE user_id=?`. Чужой chat id → 404.

## 8. API
GET/POST `/api/v1/chats`, GET/PUT/DELETE `/api/v1/chats/{id}`, POST `/api/v1/chats/import-legacy`, GET `/api/v1/chats/export` (ZIP).

## 9. Write-order protection
PUT — replace-all (delete + insert) в одной транзакции; SQLite WAL + busy_timeout. Frontend пишет последовательно (await serverPersistSession перед inference; fire-and-forget после ответа, но single-session serialized).

## 10. Logout/Login design
Logout: серверную историю не удаляет (только очищает localStorage/in-memory auth). Login: `loadServerChats()` загружает серверную историю, затем `maybeMigrateLegacy()`.

## 11. Migration + idempotency
`import-legacy` использует legacy chat/session id как `legacy_client_id`; повторный import → skipped. Frontend `confirm()` перед импортом; после успеха — удаляет legacy localStorage.

## 12. localStorage transition
localStorage больше не SoT: канон — сервер (SQLite). `aither_chats` остаётся только как миграционный источник.

## 13. Export design
- GET `/api/v1/chats/export` → `application/zip`, `Content-Disposition: attachment; filename="Aither_chat_history_<ts>.zip"`.
- `00_INDEX.md` + один `.md` на чат (raw content, not rendered).
- Filename sanitization (`/` `\` control → удалены, `..` нейтрализовано, уникальность через chat_id suffix).

## 14. Images/digests
- Backend: `aither-portal-backend:chat-persist-r1` → `sha256:e4778103e72552630d7ad589b13b2f1789d81463efb271eaca727aa62d6184ae`.
- Frontend: `aither-portal:chat-persist-r1` → `sha256:ab2f99c95cfa72f108a8e125359bf327dd4d4480bbe4eeb209fbcc847d5b2af3`.

## 15. Tests
- Unauth `GET /chats` → 401 (`Authentication required`) ✓.
- Pod-restart persistence: synthetic chat, `HASH_BEFORE == HASH_AFTER` (300976a9…), conversations count сохранился ✓.
- Frontend restart: Portal Ready, app.js/index.html served, KaTeX 200 ✓.
- Regression: models 200 (qwen3-32b + qwen3.8-27b), обе модели chat 200 ✓.

## 16. 64K/timeouts unchanged
qwen3.8 `--max-model-len 65536`; backend 600s; portal nginx 630s; VPS2 nginx 630s. Inference не перезапускался.

## 17. HOLD / backlog
HOLD preserved (`AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`). Backlog preserved (streaming, branching, attachments, OCR, CUDA Graphs/INT8/W4A16/NVLink A/B — не тронуты).

## 18. Storage limitation disclosure
survives logout/login = YES; survives Portal pod restart = YES; survives browser/device change = YES; survives physical storage-node loss = NO (local host PV, не HA).

## 19. OWNER browser gate
Требуется: два чата → logout/login → сохранены; Continue merged; reload; Export ZIP (00_INDEX + N md); cross-user изоляция; другой browser/private window.

## 20. AI_CODEX_USED: NO
## 21. AUTOMATED_RUNNER_USED: NO
## 22. SECRETS_EXPOSED: NO
