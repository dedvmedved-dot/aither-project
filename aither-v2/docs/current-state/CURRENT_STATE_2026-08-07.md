# CURRENT STATE — Aither Platform

**Document ID:** R7-R5-REPOSITORY-CLEANUP-01-CS  
**Baseline SHA:** `39a8946143e7a38ceff9faabad024225acbf202e`  
**Date:** 2026-08-07

---

## 1. Scope

Документирует текущее состояние проекта Aither на основе Git-репозитория (commit `39a8946`) и отчётов Hermes от 06–07.08.2026. Не описывает работающую систему. Разделяет Git-confirmed facts и runtime-reported claims.

---

## 2. Git Baseline

```
Repository: dedvmedved-dot/aither-project
Branch: aither-v2
HEAD: 39a8946143e7a38ceff9faabad024225acbf202e
Status: clean
```

---

## 3. Commit History (relevant)

```
39a8946 feat(wui): markdown rendering + model descriptions + feedback file upload
95723c6 fix: default scopes for new users — model:32b:chat instead of chat-adapter
27c897a feat: feedback form with file attachments + identity update
8ba71ac feat: Qwen3-32B-AWQ — замена 14B на n8, 64K YaRN, новый WUI
407cbe7 feat(vllm): switch to native vLLM AWQ endpoint for qwen2.5-32b
```

---

## 4. Current Documented Architecture

```
Портал (WUI) → BFF (Portal Backend)
                  ├── Qwen2.5-32B → vllm-32b-instruct-awq (n7)
                  └── Qwen3-32B  → vllm-qwen3-32b-awq  (n8)
```

Обе модели: Instruct, chat/completions, tool calling. Completion adapter удалён. Gateway для 32B chat не требуется.

---

## 5. Qwen2.5-32B-Instruct-AWQ

| Parameter | Value |
|-----------|-------|
| Model ID | `qwen2.5-32b-instruct` |
| Manifest | `deploy/vllm-32b-instruct-awq.yaml` |
| Node | n7 |
| GPU | 2×RTX 6000, TP=2 |
| Quantization | AWQ 4-bit |
| Context (configured) | 65536 |
| Context (observed) | PASS 30K, FAIL 34K |
| Scope | `model:32b:chat` |

---

## 6. Qwen3-32B-AWQ

| Parameter | Value |
|-----------|-------|
| Model ID | `qwen3-32b` |
| Manifest | `deploy/vllm-qwen3-32b-awq.yaml` |
| Node | n8 |
| GPU | 2×RTX 6000, TP=2 |
| Quantization | AWQ 4-bit |
| Context (configured) | 65536 (with VLLM_ALLOW_LONG_MAX_MODEL_LEN) |
| Context extension | YaRN — REPORTED RUNTIME |
| Context (observed) | PASS 40K, FAIL 50K |
| Scope | `model:qwen3:chat` |
| Thinking | Disabled via `chat_template_kwargs` in Portal; tokenizer patch at runtime |

---

## 7. Model Contract

| Display | Model ID | Scope |
|---------|----------|-------|
| Qwen2.5-32B-Instruct-AWQ | `qwen2.5-32b-instruct` | `model:32b:chat` |
| Qwen3-32B-AWQ | `qwen3-32b` | `model:qwen3:chat` |

---

## 8. Portal Backend

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/chat` | Chat completions → routes to vLLM based on model ID |
| `POST /api/v1/auth/login` | JWT-based login |
| `POST /api/v1/auth/register` | Email verification registration |
| `POST /api/v1/feedback` | Feedback with optional file attachment (multipart, 5 MiB limit) |
| `GET /api/v1/feedback` | List feedback (admin only) |
| `*/api/v1/api-keys` | API key CRUD |

---

## 9. Portal Frontend (WUI)

| Feature | Status |
|---------|--------|
| Model selector: Qwen2.5-32B / Qwen3-32B | ✅ |
| Model descriptions | ✅ |
| `formatMarkdown()`: bold, italic, code, lists, headers | ✅ |
| Code blocks: frames + copy button + 20-language highlighting | ✅ |
| Feedback form: file attachment | ✅ |

---

## 10. Identity Scopes

Default scopes for new users (all registration paths):
```
model:32b:chat,model:qwen3:chat,rag:query
```

Admin bootstrap:
```
model:32b:chat,model:qwen3:chat,rag:query,rag:ingest
```

45 existing users migrated at runtime (REPORTED RUNTIME, not in Git).

---

## 11. API Keys

API keys are created via Portal WUI. Key format: `athr_...`. Scope selection in WUI modal has known defect (REPO-DEFECT-APIKEY-WUI-001).

---

## 12. Feedback Attachments

| Component | Implementation |
|-----------|---------------|
| WUI | FormData + file input |
| Portal Backend | multipart/form-data, UploadFile, 5 MiB check |
| Identity | `FeedbackRequest.file_name`, `file_content` (base64) |
| DB schema | `file_name`, `file_content` columns (added at runtime) |

---

## 13. Hermes Integration

| Provider | Model | Port | Config |
|----------|-------|------|--------|
| `aither-32b` | `qwen2.5-32b-instruct` | 9999 | max_tokens: 16000, compression: false |
| `aither-qwen3-32b` | `qwen3-32b` | 9998 | max_tokens: 16000, compression: false |

Alternative: Portal API at `https://fb1.spb.ru:10443/v1` with `athr_` key.

---

## 14. Long-Context Observations

**Qwen2.5-32B:**
- Устойчивый результат до 30K
- Деградация на 34K (потеря инструкций, `!!!!!!`)

**Qwen3-32B:**
- Устойчивый результат до 40K
- Деградация на 50K (`!!!!!!`)
- Оценочная граница: между 40K и 50K

---

## 15. Performance Observations

| Test | Qwen2.5 | Qwen3 |
|------|---------|-------|
| Развёрнутая биография | ~26 сек, 705 токенов | ~105 сек, 1590 токенов |
| Относительная скорость | 1× | ~4× медленнее |

> Reported observation. NOT a formal benchmark.

---

## 16. Git-Confirmed Facts

- Deployment manifests for both models exist in `deploy/`
- Portal Backend contains routing branches for Qwen2.5 and Qwen3. Qwen2.5 uses UPSTREAM_32B_URL. Qwen3 currently uses UPSTREAM_14B_URL (configuration slot previously used for 14B). Effective runtime values: REPORTED RUNTIME / NOT VERIFIED BY THIS REPOSITORY-ONLY TASK
- Feedback endpoint accepts multipart with 5 MiB limit
- Identity service FeedbackRequest includes file fields
- Default registration scopes include both model scopes
- WUI has updated model selector and markdown rendering

---

## 17. Runtime-Reported Facts

- 45 users migrated to new scopes (runtime DB operation)
- tokenizer_config.json patched for thinking off (runtime file change)
- 7 portal docs updated in runtime ConfigMap
- YaRN extension active for Qwen3
- Both models working via Hermes

---

## 18. Repository Inconsistencies

- Feedback DB CREATE TABLE doesn't include `file_name`/`file_content` columns
- API-key WUI modal uses legacy model option values
- Commit `39a8946` message overstates scope (claims tokenizer/DB/Identity changes not in diff)
- Gateway catalog ConfigMap (runtime) still references `qwen-14b` and `qwen-32b-base`

---

## 19. Known Defects

See [REPOSITORY_KNOWN_DEFECTS.md](REPOSITORY_KNOWN_DEFECTS.md):
- REPO-DEFECT-APIKEY-WUI-001 — OPEN
- REPO-DEFECT-FEEDBACK-DB-SCHEMA-001 — OPEN
- REPO-DEFECT-FEEDBACK-AUTH-001 — OPEN
- REPO-DEFECT-FEEDBACK-SIZE-001 — OPEN
- REPO-DEFECT-FEEDBACK-LIST-AUTH-001 — OPEN
- REPO-DEFECT-TOKENIZER-CONFIG-001 — OPEN
- REPO-DEFECT-ROOT-README-CREDENTIAL-001 — CURRENT FILE FIXED
- REPO-DEFECT-README-OBSOLETE-001 — FIXED
- REPO-DEFECT-HERMES-DOC-001 — FIXED

---

## 20. Open Security Observations

> This task performs no remediation.

- Feedback endpoint: anonymous submissions allowed
- Feedback list via Portal BFF (`/api/v1/feedback`): admin-only. Feedback list via Identity directly (`/v1/identity/feedback`): no explicit auth check in tracked source
- API keys stored in Identity DB; key exposure only at creation
- Hermes provider config requires VLLM_API_KEY — documented as placeholder only
- Previously opened security incidents remain OPEN unless separate verified closure exists
