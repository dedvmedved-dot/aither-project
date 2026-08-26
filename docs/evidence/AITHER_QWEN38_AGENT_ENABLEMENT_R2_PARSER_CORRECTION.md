# AITHER QWEN38 AGENT ENABLEMENT R2 (PARSER CORRECTION) — Evidence

- TASK ID: `AITHER-QWEN38-AGENT-ENABLEMENT-R2-PARSER-CORRECTION`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `0331bdabb3c7b10b9e47bea52b538ed390142915`
- FINAL SHA: `<sha>`
- PARENT SHA: `0331bdabb3c7b10b9e47bea52b538ed390142915`
- BRANCH: `aither-v2`

## 1. Changed paths
- `aither-v2/services/inference/k8s/vllm-qwen38-27b-fp8.yaml`
- `docs/evidence/AITHER_QWEN38_AGENT_ENABLEMENT_R2_PARSER_CORRECTION.md`

## 2. Parser discovery (runtime, vLLM 0.27.1)
- Runtime vLLM version: `0.27.1`.
- Total registered tool parsers: 45.
- `qwen3_xml` available: YES. `qwen3_coder` available: YES. `hermes` available: YES.
- Примечание: `qwen3_xml` и `qwen3_coder` — алиасы одного `Qwen3EngineToolParser` (structural_tag_model=qwen_3_coder, adapter Qwen3ParserToolAdapter).

## 3. Chat template compatibility
- Path: `/model/tokenizer_config.json` (chat_template, 8952 chars).
- SHA256: `c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`.
- Format: `<tool_call><function=NAME><parameter=ARG>VALUE</parameter></function></tool_call>` (Qwen3 XML), НЕ Hermes JSON.
- `hermes` (R1) несовместим; `qwen3_xml`/`qwen3_coder` совместимы с `<function=...>`.

## 4. Candidate results (A/B)
- Candidate A: `qwen3_xml` → CORE RAW GATE PASS (basic/auto/forced/required/no-tool, parser errors 0). SELECTED.
- Candidate B: `qwen3_coder` → NOT RUN (A прошёл полностью).

## 5. Final args (candidate A)
```
--model /model --served-model-name qwen3.8-27b --tensor-parallel-size 2 --host 0.0.0.0 --port 8000
--gpu-memory-utilization 0.90 --max-model-len 65536 --max-num-seqs 1 --dtype half --enforce-eager
--reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_xml --generation-config vllm
```
Плюс `strategy: maxSurge 0, maxUnavailable 1` (реконсиляция к live; было отсутствующим в манифесте).

## 6. Pre/post pod/image
- Pre pod: `vllm-qwen38-27b-fp8-66594db7fc-pqp9f` (baseline, no tool flags).
- Post pod: `vllm-qwen38-27b-fp8-57b74959dd-7477b` (candidate A), Ready 1/1, restartCount 0, /health 200.
- Image (неизменен): `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`.

## 7. RAW tests (direct vLLM)
- basic chat: PASS. system prompt: PASS. streaming: PASS.
- AUTO structured tool_calls: PASS (`get_host_status` / `{"host":"proxmox-test"}`).
- FORCED structured tool_calls: PASS. REQUIRED structured tool_calls: PASS.
- NO-TOOL: PASS. Parser errors: 0.

## 8. PUBLIC tests (fb1.spb.ru/v1/chat/completions, qwen3.8-27b)
- basic chat: PASS. system prompt: PASS. streaming: PASS. invalid model: PASS (404). invalid auth: PASS (401).
- AUTO structured tool_calls: PASS. FORCED: PASS. REQUIRED: PASS. NO-TOOL: PASS.
- multiple-tool selection: 20/20. tool argument JSON: 20/20.
- multi-turn tool loop: 20/20. multi-step tool loop: 10/10. tool failure handling: 10/10.
- streaming tool call: PASS.
- long-context + tool: 8K PASS, 32K PASS, 48K PASS, 60K PASS.
- 100 sequential requests: PASS (unexpected 5xx = 0).

## 9. Stability / performance observation
- Qwen3.8 restarts: 0. CUDA OOM: 0. unexpected 5xx: 0.
- GPU memory: 19307 MiB ×2 (без изменений). Approx decode ~9.1 tok/s (без изменений).
- Performance tuning НЕ выполнялся (enforce-eager, max-num-seqs=1, dtype half сохранены).

## 10. Temp credential lifecycle
- Использован ephemeral API key (id 27, scope `model:qwen3:chat`).
- Revoke через штатный Identity API: `DELETE /v1/identity/api-keys/27` (owner JWT) → 200 "Key revoked". Post-revoke `/v1/models` со старым ключом → 401. TEMP_KEY_CLEANUP: PASS (не SQL DELETE).
- Секрет в evidence не сохранён.

## 11. Git/runtime reconciliation
- Git manifest args == live Deployment args == `/proc/1/cmdline` (все содержат `--tool-call-parser qwen3_xml`, `--enable-auto-tool-choice`, `--generation-config vllm`, `--reasoning-parser qwen3`). PASS.
- Image digest manifest == live == imageID. PASS.

## 12. Immutability gates
- Qwen3-32B: NO CHANGED. Portal BFF: NO CHANGED. nginx: NO CHANGED. Identity: NO CHANGED (только revoke key). Gateway: NO. Frontend: NO. `.agent/*`: NO.
- AI_CODEX_USED: NO. AUTOMATED_RUNNER_USED: NO. SECRETS_EXPOSED: NO.
