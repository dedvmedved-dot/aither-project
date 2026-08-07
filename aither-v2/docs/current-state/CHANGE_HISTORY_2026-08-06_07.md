# CHANGE HISTORY — Qwen2.5/Qwen3 Migration (06–07.08.2026)

**Document ID:** R7-R5-REPOSITORY-CLEANUP-01-CH  
**Baseline SHA:** `39a8946143e7a38ceff9faabad024225acbf202e`  
**Date:** 2026-08-07

---

## Commit Chronology

| Commit | Message | Files changed | Git-confirmed changes | Runtime claims | Current relevance |
|--------|---------|---------------|----------------------|----------------|-------------------|
| `407cbe7` | feat(vllm): switch to native vLLM AWQ endpoint | `deploy/vllm-32b-instruct-awq.yaml`, `services/portal-backend/app/main.py` | Qwen2.5-32B-Instruct-AWQ deployment; native `/v1/chat/completions`; `model:32b:chat` scope; remove completion adapter | — | ACTIVE — current 32B deployment |
| `8ba71ac` | feat: Qwen3-32B-AWQ | `deploy/vllm-qwen3-32b-awq.yaml`, `services/portal-backend/app/main.py` | Qwen3-32B-AWQ manifest (TP=2, max-model-len=65536); `qwen3-32b` allowlist; `enable_thinking=false`; `model:qwen3:chat` scope | «64K YaRN» — runtime claim, config not in tracked files | ACTIVE — current Qwen3 deployment |
| `27c897a` | feat: feedback form with file attachments | `services/identity/app/main.py`, `services/portal-backend/app/main.py`, `requirements.lock`, `requirements.txt` | FeedbackRequest with file_name/file_content; multipart endpoint; UploadFile; 5 MiB check; python-multipart dep | — | ACTIVE — feedback with attachments |
| `95723c6` | fix: default scopes for new users | `services/identity/app/main.py` | Default registration scopes: `model:32b:chat,model:qwen3:chat,rag:query` for email + OAuth + bootstrap admin | «DB: migrate all 45 existing users» — RUNTIME CLAIM; «WUI: auto-reject old model names» — NOT IN DIFF | ACTIVE — new users get correct scopes |
| `39a8946` | feat(wui): markdown rendering + descriptions | `services/portal-frontend/app.js`, `services/portal-frontend/index.html` | Model selector (Qwen2.5/Qwen3); formatMarkdown(); FormData feedback; model descriptions; default model change | «tokenizer_config.json patched» — NOT IN DIFF; «DB users scopes changed» — NOT IN DIFF; «Identity changed» — NOT IN DIFF; «all 7 docs updated» — NOT IN DIFF | ACTIVE — current WUI |

---

## Git-Confirmed Architecture Changes

### 407cbe7 — Qwen2.5-32B Native Chat
- New file: `deploy/vllm-32b-instruct-awq.yaml` (144 lines)
- Modified: `services/portal-backend/app/main.py` (129 lines changed)
- Removed: handwritten completion adapter (~92 lines)
- Changed: `model:32b:chat-adapter` → `model:32b:chat`
- Changed: UPSTREAM_32B_URL → `vllm-32b-instruct-awq`

### 8ba71ac — Qwen3-32B
- New file: `deploy/vllm-qwen3-32b-awq.yaml` (142 lines)
- Modified: `services/portal-backend/app/main.py` (34 lines changed)
- Added: `qwen3-32b` to ALLOWED_MODELS
- Added: `model:qwen3:chat` scope check
- Added: `chat_template_kwargs: {enable_thinking: false}` for Qwen3
- Added: Qwen3 upstream routing → `UPSTREAM_14B_URL`

### 27c897a — Feedback Attachments
- Modified: `services/identity/app/main.py` — FeedbackRequest + file fields
- Modified: `services/portal-backend/app/main.py` — multipart endpoint
- Modified: `requirements.lock`, `requirements.txt` — python-multipart

### 95723c6 — Registration Scopes
- Modified: `services/identity/app/main.py` (3 lines)
- Changed 3 registration flows: email, OAuth, bootstrap → `model:32b:chat,model:qwen3:chat,rag:query`
- Removed: `model:14b:chat`, `model:32b:chat-adapter`, `model:32b:completion`

### 39a8946 — WUI Refresh
- Modified: `services/portal-frontend/app.js` (49 lines changed)
- Modified: `services/portal-frontend/index.html` (14 lines changed)
- Changed: model names throughout (`qwen-14b` → `qwen2.5-32b-instruct`, `qwen-32b-base` → `qwen3-32b`)
- Added: `formatMarkdown()` function
- Changed: `formatMessage` to apply markdown to text segments
- Changed: `updateModelInfo` with detailed descriptions
- Changed: feedback form to use FormData with file input

---

## Runtime-Only Claims (NOT in Git)

| Claim | Source | Commit message that references it |
|-------|--------|----------------------------------|
| 45 users migrated in DB | Hermes report | `95723c6` |
| tokenizer_config.json patched (thinking off) | Hermes report | `39a8946` |
| All 7 portal docs updated | Hermes report | `39a8946` |
| WUI auto-rejects old model names | Hermes report | `95723c6` |
| YaRN 64K runtime state | Hermes report | `8ba71ac` |
| Identity DB schema migration (feedback file columns) | Hermes report | `27c897a` |

---

## Classification of Old Model References

`git grep` results for `qwen-14b`, `qwen-32b-base`, `model:32b:chat-adapter`, `model:32b:completion`:

| File | Type | Action |
|------|------|--------|
| `03-vllm-14b-deploy/docs/*` (13 files) | HISTORICAL DOC | Mark as historical, do not rewrite |
| `03-vllm-14b-deploy/manifests/*` (4 files) | HISTORICAL MANIFEST | Mark as historical |
| `README.md` (2 refs) | CURRENT DOC | Updated in this task |
| `docs/hermes-aither-connection.md` (5 refs) | CURRENT DOC | Updated in this task |
| `docs/evidence/*` (3 files) | EVIDENCE | Mark as historical |
| `docs/user-package/17_MODEL_USAGE_GUIDE.md` | CURRENT DOC | Already updated in CB-WEBUI-02 |
| `services/portal-frontend/app.js` | SOURCE CODE | Register as defect (API-key values) |
| `services/portal-frontend/index.html` | SOURCE CODE | Register as defect (admin buttons) |
