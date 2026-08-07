# REPOSITORY KNOWN DEFECTS

**Baseline SHA:** `39a8946143e7a38ceff9faabad024225acbf202e`  
**Date:** 2026-08-07  
**Status:** DOCUMENTATION ONLY — NO FIXES IN THIS TASK

---

## REPO-DEFECT-APIKEY-WUI-001

| Field | Value |
|-------|-------|
| **ID** | REPO-DEFECT-APIKEY-WUI-001 |
| **Component** | `services/portal-frontend/app.js` |
| **Description** | Single-model API-key selection modal uses legacy option values (`qwen-14b`, `qwen-32b-base`) in `<option value>` attributes, while `_createToken()` handler expects `qwen2.5-32b-instruct` and `qwen3-32b` |
| **Evidence** | `git grep "value=\"qwen-14b\"" services/portal-frontend/app.js` — found in token modal. `git grep "value=\"qwen-32b-base\"" services/portal-frontend/app.js` — found in token modal |
| **Impact** | When user selects «Только Qwen2.5-32B» or «Только Qwen3-32B», the values passed to scope selection logic may not match expected model IDs |
| **Status** | OPEN |
| **Allowed action** | DOCUMENT ONLY — fix in separate task |

---

## REPO-DEFECT-FEEDBACK-DB-SCHEMA-001

| Field | Value |
|-------|-------|
| **ID** | REPO-DEFECT-FEEDBACK-DB-SCHEMA-001 |
| **Component** | `services/identity/app/main.py` |
| **Description** | Feedback INSERT now includes `file_name` and `file_content` columns, but the tracked CREATE TABLE statement (line 199) does not include these columns. The schema migration was done at runtime only. |
| **Evidence** | `git show 27c897a:services/identity/app/main.py` — CREATE TABLE has only 6 columns (id, user_id, username, topic, message, created_at). INSERT has 8 columns. |
| **Impact** | New deployment from Git source would fail on INSERT due to missing columns |
| **Status** | OPEN |
| **Allowed action** | DOCUMENT ONLY — fix in separate task |

---

## REPO-DEFECT-FEEDBACK-AUTH-001

| Field | Value |
|-------|-------|
| **ID** | REPO-DEFECT-FEEDBACK-AUTH-001 |
| **Component** | `services/identity/app/main.py` |
| **Description** | `POST /v1/identity/feedback` has no explicit authorization check. Anonymous submissions allowed. `GET /v1/identity/feedback` has no explicit auth/admin check. `GET /api/v1/feedback` (BFF) has admin check. |
| **Evidence** | `git grep -A5 "submit_feedback\|list_feedback" services/identity/app/main.py` — Identity endpoints lack auth |
| **Impact** | POST: anonymous submissions possible. GET /v1/identity/feedback: direct Identity access may expose feedback data without admin authorization. Portal BFF path (`/api/v1/feedback`) is admin-gated |
| **Status** | OPEN |
| **Allowed action** | DOCUMENT ONLY — fix in separate task |

---

## REPO-DEFECT-FEEDBACK-SIZE-001

| Field | Value |
|-------|-------|
| **ID** | REPO-DEFECT-FEEDBACK-SIZE-001 |
| **Component** | `services/identity/app/main.py` |
| **Description** | Portal-backend enforces 5 MiB attachment limit, but Identity service has no size check on `file_content` (base64). Oversized payloads pass through to SQLite. |
| **Evidence** | `git grep -i "size\|limit\|5.*mb\|max" services/identity/app/main.py` — no size limit found |
| **Impact** | Large file uploads could cause SQLite performance issues or DB bloat |
| **Status** | OPEN |
| **Allowed action** | DOCUMENT ONLY — fix in separate task |

---

## REPO-DEFECT-TOKENIZER-CONFIG-001

| Field | Value |
|-------|-------|
| **ID** | REPO-DEFECT-TOKENIZER-CONFIG-001 |
| **Component** | Model configuration (runtime) |
| **Description** | Commit `39a8946` message claims «tokenizer_config.json patched» but this file is not tracked in Git. The thinking-mode-off patch exists only at runtime on n8. |
| **Evidence** | `git show 39a8946 --name-only` — only `app.js` and `index.html` changed |
| **Impact** | If the model directory is recreated from HuggingFace, thinking mode returns to default ON |
| **Status** | OPEN |
| **Allowed action** | DOCUMENT ONLY — fix in separate task |

---

## REPO-DEFECT-README-OBSOLETE-001

| Field | Value |
|-------|-------|
| **ID** | REPO-DEFECT-README-OBSOLETE-001 |
| **Component** | `README.md` |
| **Description** | Root README still references `qwen-14b`, `qwen-32b-base`, `model:32b:chat-adapter`, completion adapter, and gateway requirement for 32B chat |
| **Evidence** | `git grep "qwen-14b\|qwen-32b-base\|chat-adapter" README.md` — 5 matches |
| **Impact** | Documents architecture that no longer exists |
| **Status** | FIXED in this task — README updated |

---

## REPO-DEFECT-HERMES-DOC-001

| Field | Value |
|-------|-------|
| **ID** | REPO-DEFECT-HERMES-DOC-001 |
| **Component** | `docs/hermes-aither-connection.md` |
| **Description** | Hermes connection guide references `qwen-14b` and `qwen-32b-base`, describes completion adapter requirement |
| **Evidence** | `git grep "qwen-14b\|qwen-32b-base" docs/hermes-aither-connection.md` — 5 matches |
| **Impact** | External users would attempt to use non-existent models |
| **Status** | FIXED in this task — document updated |

---

## Summary

| ID | Status |
|----|--------|
| REPO-DEFECT-APIKEY-WUI-001 | OPEN |
| REPO-DEFECT-FEEDBACK-DB-SCHEMA-001 | OPEN |
| REPO-DEFECT-FEEDBACK-AUTH-001 | OPEN — documentation updated |
| REPO-DEFECT-FEEDBACK-SIZE-001 | OPEN |
| REPO-DEFECT-FEEDBACK-LIST-AUTH-001 | OPEN |
| REPO-DEFECT-TOKENIZER-CONFIG-001 | OPEN |
| REPO-DEFECT-ROOT-README-CREDENTIAL-001 | CURRENT FILE FIXED |
| REPO-DEFECT-README-OBSOLETE-001 | FIXED |
| REPO-DEFECT-HERMES-DOC-001 | FIXED |

**TOTAL:** 9 | OPEN: 6 | FIXED/CURRENT FILE FIXED: 3 |
| REPO-DEFECT-FEEDBACK-AUTH-001 | UPDATED — split into POST/GET analysis |
| REPO-DEFECT-FEEDBACK-SIZE-001 | OPEN |
| REPO-DEFECT-FEEDBACK-LIST-AUTH-001 | OPEN |
| REPO-DEFECT-TOKENIZER-CONFIG-001 | OPEN |
| REPO-DEFECT-FEEDBACK-LIST-AUTH-001 | OPEN |
| REPO-DEFECT-ROOT-README-CREDENTIAL-001 | CURRENT FILE FIXED |
| REPO-DEFECT-README-OBSOLETE-001 | FIXED |
| REPO-DEFECT-HERMES-DOC-001 | FIXED |

## REPO-DEFECT-ROOT-README-CREDENTIAL-001

| Field | Value |
|-------|-------|
| **ID** | REPO-DEFECT-ROOT-README-CREDENTIAL-001 |
| **Component** | `README.md` (root) |
| **Description** | Root README contained `sshpass -p <password>` credential example in SSH instructions |
| **Status** | CURRENT FILE FIXED — example replaced with `ssh <user>@<bastion>` |
| **Historical exposure** | NOT ASSESSED BY THIS DOCUMENTATION-ONLY TASK |

---

## REPO-DEFECT-FEEDBACK-LIST-AUTH-001

| Field | Value |
|-------|-------|
| **ID** | REPO-DEFECT-FEEDBACK-LIST-AUTH-001 |
| **Component** | `services/identity/app/main.py` |
| **Description** | `GET /v1/identity/feedback` lacks explicit authentication and administrator authorization in tracked source |
| **Evidence** | `git grep -A5 "GET.*v1/identity/feedback" services/identity/app/main.py` — no auth/admin check |
| **Impact** | Direct Identity access may expose stored feedback metadata/message content outside BFF admin authorization |
| **Status** | OPEN |
| **Allowed action** | DOCUMENT ONLY — fix in separate authorized system task |
