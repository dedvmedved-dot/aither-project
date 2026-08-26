# AITHER BFF TOOL-CALLING CONTRACT R1 — Evidence

- TASK ID: `AITHER-BFF-TOOL-CALLING-CONTRACT-R1`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `e074a733662d59e873a736d975374acec268fa4b`
- FINAL SHA: `<sha>`
- PARENT SHA: `e074a733662d59e873a736d975374acec268fa4b`
- BRANCH: `aither-v2`

## 1. Changed paths
- `aither-v2/services/portal-backend/app/main.py`
- `aither-v2/services/portal-backend/k8s/portal-backend.yaml` (image digest)
- `docs/evidence/AITHER_BFF_TOOL_CALLING_CONTRACT_R1.md`

## 2. Root defect
Portal Backend `_chat_via_api_key()` (main.py ~стр.947) не пересылал upstream `tools`, `tool_choice`, `parallel_tool_calls`; `external_chat()` (~стр.1025) пересылал `tools`, но отбрасывал `tool_choice`. Из-за этого публичный endpoint `https://fb1.spb.ru/v1/chat/completions` (→ `/api/v1/chat` → `_chat_via_api_key`) передавал в vLLM запрос без tools → модель выдавала текст, `tool_calls == []`.

## 3. Patch summary
В обеих API-key функциях добавлено прозрачное извлечение и проброс (без семантической модификации):
```python
tools = ...get("tools")
tool_choice = ...get("tool_choice")
parallel_tool_calls = ...get("parallel_tool_calls")
...
if tools is not None: req_body["tools"] = tools
if tool_choice is not None: req_body["tool_choice"] = tool_choice
if parallel_tool_calls is not None: req_body["parallel_tool_calls"] = parallel_tool_calls
```
Response path НЕ изменён (raw body прокидывается, tool_calls не пересобираются).

## 4. Request contract (после фикса)
- `_chat_via_api_key`: tools → YES, tool_choice → YES, parallel_tool_calls → YES.
- `external_chat`: tools → YES (было), tool_choice → YES (добавлено), parallel_tool_calls → YES.

## 5. Image / deployment
- Pre image: `sha256:0759874777dc5a058aadf7d7555b828fb9120f857da0db4ddf130c961cbfa18d`.
- Post image: `sha256:fdea72be4ed76800bc758c2c0eb1fc68bbff25ca2f21d76dbfdafe3a3bf11258`.
- Controlled rollout только portal-backend (set image). Pod `aither-portal-backend-bdc9bbd4b-tfspt`, Ready 1/1, /health 200, /ready 200, restartCount 0.

## 6. Public E2E results (qwen3-32b, fb1.spb.ru/v1/chat/completions)
- basic chat: PASS
- system prompt: PASS
- streaming: PASS
- invalid model: PASS (404)
- invalid auth: PASS (401)
- AUTO structured tool_calls: PASS (`get_host_status` / `{"host":"proxmox-test"}`)
- FORCED structured tool_calls: PASS
- REQUIRED structured tool_calls: PASS
- no-tool-needed: PASS (нет ложного tool call, обычный ответ)
- multiple-tool selection: 20/20
- tool argument JSON: 20/20
- multi-turn tool loop: 20/20
- streaming tool call: PASS (tool_calls в stream)
- 100 sequential requests: PASS (unexpected 5xx = 0)

## 7. Immutability gates
- Qwen3-32B: NO CHANGED (pod `vllm-qwen3-32b-awq-86cb6c9845-n2xpg`, 16d, restarts 0).
- Qwen3.8: NO CHANGED (pod `vllm-qwen38-27b-fp8-66594db7fc-pqp9f`, restarts 0).
- nginx: NO CHANGED.
- Identity: NO CHANGED.
- .agent: NO CHANGED.

## 8. Stability / safety
- portal-backend restarts: 0 (кроме планового rollout).
- qwen3-32b restarts: 0. CUDA OOM: 0. unexpected 5xx: 0.
- Git/runtime reconciliation: PASS (manifest digest == live pod image == imageID `fdea72be4e…`).

## 9. Temp credential
Новый API key в этой задаче НЕ создавался — переиспользован ephemeral test key (scope `model:qwen3:chat`, авто-expire +1 day). TEMP_KEY_CLEANUP: NOT_CREATED. Секрет в evidence не сохранён.

## 10. Compliance
- AI_CODEX_USED: NO
- AUTOMATED_RUNNER_USED: NO
- SECRETS_EXPOSED: NO
- WORKTREE: CLEAN
