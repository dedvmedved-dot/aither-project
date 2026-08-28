# AITHER PORTAL CHAT HISTORY PERSISTENCE REGRESSION RECOVERY R1 — Evidence

- TASK: `AITHER-PORTAL-CHAT-HISTORY-PERSISTENCE-REGRESSION-RECOVERY-R1`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `3d3457e19accb03f25779398311df7c156203907`
- PARENT SHA: `3d3457e19accb03f25779398311df7c156203907`
- BRANCH: `aither-v2`
- FINAL SHA: `<after-commit>`

---

## 1. Reproduction before fix (Phase A)

Using a sanctioned fresh test account (`persist_r1_*`, created via Identity register API —
internal secret, service API, NOT a direct SQL write), exercised the normal Portal/public API
path:

- Login → create chat with unique marker `PERSIST-R1-<ts>-hermes` → list (marker present).
- Logout → login again (same account) → list.

Result: **server-side persistence WORKS** across logout/login (`SERVER_PERSISTS_ACROSS_RELOGIN: True`).
The data is NOT deleted and IS re-fetchable with a fresh token.

Conclusion: the reported "history disappears" is **not** a backend deletion — it is a
**frontend re-hydration gap** on session-restore paths.

## 2. Root cause (proven by code + git forensics + DB inspection)

- R1/R2 moved chat history to server-side SQLite (server = sole source of truth) and removed
  full history from `localStorage` (`aither_chats` no longer holds the chat list).
- The re-hydration function `loadServerChats()` is wired **only** into the username/password
  login handler (`handleLogin`, app.js line ~932).
- All other session-establishment paths — **OAuth callback** (init), **LDAP login**, and
  **page-load session restore** — funnel through `checkSession()`, which fetches `/auth/me`
  (user info) but **never calls `loadServerChats()`**.
- Therefore OAuth/LDAP users and any page reload with a stored token render an empty chat list
  (`loadChatSessions()` reads only the now-empty localStorage), so history "disappears" across
  logout/login and hard refresh — while conversations remain intact in the backend DB.

Git forensics: `loadServerChats` was introduced only in `00b7e24` (R1); `-S loadServerChats`
and `-G loadServerChats` show no later commit ever wired it into `checkSession`.

## 3. Regression layer / store / ownership

- REGRESSION LAYER: **PORTAL** (frontend session-restore hydration).
- AUTHORITATIVE STORE: SQLite `/data/chat/chat_history.db` (PVC `aither-portal-chat-data`, PV
  hostPath `/data/aither/chat-data`), `PRAGMA user_version=2`, tables `conversations` +
  `message_nodes`.
- STABLE OWNER KEY: `user_id` = Identity `users.id` (stable integer DB id), enforced with
  `WHERE user_id=?` on every chat query. `_chat_owner()` = `int(user.get("id") or user.get("uid") or 0)`.
- DATA LOSS: **NO** (5 pre-existing conversations, 90 message_nodes intact in DB — read-only
  inspection confirmed).

## 4. Historical R1/R2 forensics

- Reviewed `AITHER_CHAT_HISTORY_PERSISTENCE_EXPORT_P0_R1.md` and
  `AITHER_CHAT_HISTORY_PERSISTENCE_EXPORT_P0_R2_CORRECTIVE.md` (read-only).
- R1 root cause: frontend stored chats in localStorage, truncated to 30, logout deleted them.
  R1 introduced server-side SQLite (`/api/v1/chats`) + `loadServerChats()` on login.
- R2 corrective: 9 blockers (server-generated id, real POST, parent_id chain, FK cascade,
  migration, legacy UNIQUE, server=SoT, durable write ordering, canonical manifest).
- Neither R1 nor R2 wired `loadServerChats()` into the OAuth/LDAP/page-load `checkSession()`
  path — the gap is inherited from R1's original wiring, not a later regression commit.
- BLIND CHERRY-PICK: **NO** (fresh minimal fix, not a cherry-pick of historical commits).

## 5. Fix (minimal, root-cause)

`aither-v2/services/portal-frontend/app.js` — in `checkSession()`, after successful `/auth/me`,
add server re-hydration:

```js
loadServerChats().then(maybeMigrateLegacy);
```

This covers every session-restore path (page load, OAuth callback, LDAP) that funnels through
`checkSession()`. Username/password login is unaffected (it already calls `loadServerChats()`
directly and does not call `checkSession()`).

`aither-v2/services/portal-frontend/index.html` — cache-bust `app.js?v=chat-persist-r2b` →
`app.js?v=chat-persist-r3`.

Backend `main.py` NOT modified. Identity NOT modified. Inference/routing NOT modified.

Deployed via both ConfigMaps (`aither-portal-config` + `aither-portal-frontend-config`, all 4
keys) using delete+create (apply silently failed — pitfall), then `rollout restart` of both
`aither-portal` and `aither-portal-frontend`. Verified served app.js contains the fix
(`node --check` on served content = valid).

## 6. Regression test matrix (API level; browser automation unavailable — documented)

Test accounts (fresh, sanctioned): A=`persist_a_140927` (id 68), B=`persist_b_140927` (id 69).
Chat under test: `1c5b9e38-e49f-4fe3-a70d-5fdff0437152`.

| Test | Result |
|---|---|
| P1 same-session create+append (>=3 msgs) | PASS (HTTP 200, PUT status=updated, 3 messages) |
| P2 hard refresh (fresh-session list) | PASS (server-side list contains marker) |
| P3 logout/login same account #1 | PASS |
| P4 logout/login same account #2 | PASS |
| P5 new/clean session same account | PASS (fresh token → GET /chats returns history) |
| P6 account B cannot list A chat | PASS (B list empty of A marker) |
| P6 account B direct fetch of A chat | PASS (HTTP 404) |
| P7 return to A | PASS (HTTP 200, 3 messages intact) |
| P8 service restart persistence | PASS (portal-backend restart, chat + 3 msgs intact) |
| P9 explicit delete | PASS (DELETE 200) |
| P9 delete persists after relogin | PASS (HTTP 404 after relogin) |
| P9 other chat intact after delete | PASS |
| P10 pre-existing history preserved | PASS (3 messages intact after all operations) |

## 7. Chat non-regression

- CHAT CREATE: PASS (P1). CHAT MESSAGE APPEND: PASS (P1 PUT, 3 messages).
- Normal model response: PASS (`/api/v1/chat` → "ПРИВЕТ", HTTP 200).
- CHAT STREAM: the portal chat path is non-streaming (`stream: False` hardcoded in
  `chat_completions`, unchanged by this fix) — response delivered correctly.
- AGENT-DEEP ROUTING CHANGED: NO. AGENT-FAST ROUTING CHANGED: NO.
  (`AGENT_MODEL_ALIASES` map untouched; `main.py` diff = 0 lines.)
- QWEN3.8 CHANGED: NO. QWEN3-32B CHANGED: NO. IDENTITY CHANGED: NO.

## 8. Security gates

- Account isolation: PASS (B list empty of A, B direct fetch of A = 404).
- Conversation ID alone cannot bypass ownership: PASS (all chat queries `WHERE id=? AND user_id=?`).
- Logout revokes auth capability: logout proxies to Identity `/v1/identity/logout` (token revoked).
- No token/password/cookie/secret in this evidence.
- DIRECT DB WRITES: NO (read-only DB inspection only; test users created via Identity register API).
- No privilege escalation.

## 9. Compliance

- HISTORICAL DATA RECOVERY POSSIBLE: NO (no data loss occurred in this regression — data intact).
- SECRETS EXPOSED: NO. AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO.
- `.agent/CURRENT_TASK.json` CHANGED: NO. `.agent/CURRENT_TASK.md` CHANGED: NO.
