# REPOSITORY STATE MATRIX

**Baseline SHA:** `39a8946143e7a38ceff9faabad024225acbf202e`  
**Date:** 2026-08-07

| Claim | Git evidence | Hermes report | Classification |
|-------|-------------|---------------|----------------|
| Qwen2.5-32B-Instruct-AWQ manifest/configuration | `deploy/vllm-32b-instruct-awq.yaml` (commit `407cbe7`) | ✅ Confirmed | GIT CONFIRMED (config); runtime deployment: REPORTED RUNTIME |
| Qwen3-32B-AWQ manifest/configuration | `deploy/vllm-qwen3-32b-awq.yaml` (commit `8ba71ac`) | ✅ Confirmed | GIT CONFIRMED (config); runtime deployment: REPORTED RUNTIME |
| 14B model removed | `vllm-14b-instruct` scaled to 0 (not in Git; runtime state) | ✅ Reported | REPORTED RUNTIME |
| Qwen3 max-model-len=65536 | `deploy/vllm-qwen3-32b-awq.yaml` args | ✅ Confirmed | GIT CONFIRMED |
| VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 | `deploy/vllm-qwen3-32b-awq.yaml` env | ✅ Confirmed | GIT CONFIRMED |
| YaRN enabled for Qwen3 | NOT in tracked files | ✅ «32K + YaRN 64K» | REPORTED RUNTIME |
| Qwen3 thinking disabled in Portal | `services/portal-backend/app/main.py` — `chat_template_kwargs` | ✅ Confirmed | GIT CONFIRMED |
| tokenizer_config.json patched (thinking off) | NOT in tracked files | ✅ Reported in `39a8946` msg | REPORTED RUNTIME |
| WUI model selector: Qwen2.5 + Qwen3 | `services/portal-frontend/index.html` (commit `39a8946`) | ✅ Confirmed | GIT CONFIRMED |
| WUI formatMarkdown() | `services/portal-frontend/app.js` (commit `39a8946`) | ✅ Confirmed | GIT CONFIRMED |
| WUI model descriptions | `services/portal-frontend/app.js` — `updateModelInfo` | ✅ Confirmed | GIT CONFIRMED |
| Feedback file attachment (WUI) | `services/portal-frontend/app.js` — FormData + file input (commit `39a8946`) | ✅ Confirmed | GIT CONFIRMED |
| Feedback multipart (Portal Backend) | `services/portal-backend/app/main.py` — UploadFile (commit `27c897a`) | ✅ Confirmed | GIT CONFIRMED |
| Feedback file fields (Identity) | `services/identity/app/main.py` — FeedbackRequest (commit `27c897a`) | ✅ Confirmed | GIT CONFIRMED |
| Feedback 5 MiB limit | `services/portal-backend/app/main.py` — size check | ✅ Confirmed | GIT CONFIRMED |
| python-multipart dependency | `requirements.lock`, `requirements.txt` (commit `27c897a`) | ✅ Confirmed | GIT CONFIRMED |
| 45 users migrated in DB | NOT in tracked files | ✅ Reported in `95723c6` msg | REPORTED RUNTIME |
| New user default scopes: model:32b:chat + model:qwen3:chat | `services/identity/app/main.py` (commit `95723c6`) | ✅ Confirmed | GIT CONFIRMED |
| model:14b:chat removed from defaults | `services/identity/app/main.py` (commit `95723c6`) | ✅ Confirmed | GIT CONFIRMED |
| API-key modal uses correct model values | `services/portal-frontend/app.js` — legacy values found | ⚠️ Inconsistent | CONTRADICTED BY GIT |
| Hermes Qwen2.5-32B works | NOT in tracked files | ✅ Reported | REPORTED RUNTIME |
| Hermes Qwen3-32B works | NOT in tracked files | ✅ Reported | REPORTED RUNTIME |
| Qwen2.5: 30K PASS, 34K FAIL | NOT in tracked files | ✅ Test data | REPORTED RUNTIME |
| Qwen3: 40K PASS, 50K FAIL | NOT in tracked files | ✅ Test data | REPORTED RUNTIME |
| Qwen3 ~4× slower than Qwen2.5 | NOT in tracked files | ✅ Test data | REPORTED RUNTIME |
| Hermes max_tokens=16000 required | NOT in tracked files | ✅ Config advice | REPORTED RUNTIME |
| compression.enabled=false required | NOT in tracked files | ✅ Config advice | REPORTED RUNTIME |
| All 7 portal docs updated | NOT in tracked files (docs in runtime ConfigMap) | ✅ Reported in `39a8946` msg | REPORTED RUNTIME |
| Gateway catalog still shows old models | NOT in tracked files | — | REPORTED RUNTIME |

## Summary

| Classification | Count |
|----------------|-------|
| GIT CONFIRMED | 16 |
| REPORTED RUNTIME | 10 |
| CONTRADICTED BY GIT | 1 |
| **Total claims** | **31** |
