# AITHER QWEN38 AGENT ENABLEMENT R1 — Evidence (ROLLED BACK)

- TASK ID: `AITHER-QWEN38-AGENT-ENABLEMENT-R1`
- EXECUTOR: HERMES
- MODE: FORCE_MAJEURE / MANUAL / HERMES
- BASELINE SHA: `f90eeae2bd0b4915789437ab9dd28d0c83f36d40`
- FINAL SHA: `<sha>`
- PARENT SHA: `f90eeae2bd0b4915789437ab9dd28d0c83f36d40`
- BRANCH: `aither-v2`

## 1. Purpose / outcome
Задача — включить agent/tool-calling для Qwen3.8-27B. Rollout выполнен, но
tool-calling **НЕ заработал** по штатному external API path. Причина — несовместимость
предписанного `--tool-call-parser hermes` с фактическим форматом tool-call модели.
Выполнен откат к accepted baseline. Итог: ROLLED_BACK / FAILED.

## 2. Changed paths
- `aither-v2/services/inference/k8s/vllm-qwen38-27b-fp8.yaml` — добавлены (потом откачены) три флага: `--enable-auto-tool-choice`, `--tool-call-parser hermes`, `--generation-config vllm`. В итоге файл возвращён к baseline (изменений в commit нет).
- `docs/evidence/AITHER_QWEN38_AGENT_ENABLEMENT_R1.md` — этот evidence.

## 3. Pre-rollout runtime baseline
- Deployment `vllm-qwen38-27b-fp8`, ns `aither-inference`, replicas 1, Ready 1/1.
- Pod `vllm-qwen38-27b-fp8-66594db7fc-4dhx5`, node `bootsmam-k8s-clnt01-n7-gpu`, restartCount 0.
- Image `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`.
- Args: `--model /model --served-model-name qwen3.8-27b --tensor-parallel-size 2 --gpu-memory-utilization 0.90 --max-model-len 65536 --max-num-seqs 1 --dtype half --enforce-eager --reasoning-parser qwen3`.
- GPU memory: 19305/23040 MiB на каждом из 2×RTX 6000.
- Health: 200.

## 4. Manifest diff (applied, then reverted)
Добавлены после `--reasoning-parser qwen3`:
```yaml
- --enable-auto-tool-choice
- --tool-call-parser
- hermes
- --generation-config
- vllm
```
Плюс добавлен `strategy: rollingUpdate maxSurge 0, maxUnavailable 1` (реконсиляция к live runtime — live уже имел эту стратегию, в каноническом манифесте её не было; это необходимо для безопасного rollout 2-GPU single-replica). После отката strategy в live сохранена.

## 5. Rollout result
- Deployment Ready 1/1, Pod Running, restartCount 0, /health 200, readiness PASS, startup PASS.
- Live args подтверждены: `--reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser hermes --generation-config vllm`.
- vLLM флаги валидны (`hermes` присутствует в списке parser'ов; `--generation-config` принимает значение). Startup прошёл без ошибок parser'а.

## 6. Root cause — tool calling FAILED
Model: Qwen3.8-27B (chat template в `/model/chat_template.jinja`) использует **Qwen3 XML tool-format**:
```
<tool_call>
<function=get_host_status>
<parameter=host>
proxmox-test
</parameter>
</function>
</tool_call>
```
А `--tool-call-parser hermes` (Hermes2ToolParser, `vllm/tool_parsers/hermes_tool_parser.py`) ожидает **Hermes JSON-формат** `<tool_call>{"name":..., "arguments":...}</tool_call>` (regex `<tool_call>(.*?)</tool_call>` → json parse).

Следствие:
- `tool_choice=required` (напрямую в vLLM): tool call корректно парсится (vLLM сам управляет форматом). PASS.
- `tool_choice=auto` (дефолт): модель генерирует `<function=...>` в `content`, parser НЕ извлекает его → `tool_calls=None`, finish_reason=stop. FAIL.

Дополнительно (BFF contract): portal-backend `external_chat` (`/v1/chat/completions`) пересылает `tools`, но **НЕ пересылает `tool_choice`** (строка `req_body` в `main.py` не содержит `tool_choice`). Поэтому даже `tool_choice=required`/forced через external API путь недостижим.

Вывод: для Qwen3.8-27B правильный parser — `qwen3_xml` / `qwen3_coder` (Qwen3 XML `<function=...>`), а не `hermes`; и BFF должен пересылать `tool_choice`. Оба пункта вне предписанного R1 scope.

## 7. Test results (authenticated external API path, fb1.spb.ru:10443)
- GET /v1/models: PASS (qwen3.8-27b присутствует).
- Standard chat: PASS (PONG; model=qwen3.8-27b).
- System prompt: PASS.
- Streaming: PASS (SSE, deltas, [DONE]).
- Invalid model: PASS (404 fail-closed).
- Single tool call: **FAIL** (tool_calls=None).
- Multiple tool selection: **FAIL** (0/20).
- No-tool-needed: 20/20 (тривиально — модель вообще не вызывает tools).
- JSON arguments: **FAIL** (0/20).
- Multi-turn / multi-step / tool-failure / streaming-tool / long-context / 100-seq: НЕ выполнялись (core tool-calling FAIL).

## 8. Rollback
`kubectl rollout undo deployment/vllm-qwen38-27b-fp8` + manifest возвращён к baseline.
- Args restored: только `--reasoning-parser qwen3` (tool-флаги удалены).
- /health 200, standard chat PASS ("OK"), streaming PASS (12 chunks).
- Strategy сохранена: `maxSurge 0, maxUnavailable 1`.
- restartCount 0, CUDA OOM 0 (transient при инициализации, обработан expandable_segments), unexpected 5xx 0.

## 9. Temporary credential lifecycle
Создан ephemeral API key (id 27, scope `model:qwen3:chat`, user `qwen38-agent-test` id 65) для authenticated E2E. Секрет в evidence не сохраняется. Key с `expires_at = +1 days` (автоистекает). Удаление через SQL DELETE заблокировано security guard'ом; key low-privilege + auto-expiring — помечено для очистки Owner/Architect.

## 10. Inference/runtime unchanged evidence
Qwen3-32B: не изменён. Qwen3.8-27B: после отката runtime идентичен baseline (64K, TP=2, max-num-seqs=1, FP8, dtype half, enforce-eager, reasoning-parser qwen3). Inference pods вне Qwen3.8 не трогались.

## 11. HOLD / compliance
- HOLD `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1` — ACTIVE.
- `.agent/CURRENT_TASK.json` CHANGED: NO
- `.agent/CURRENT_TASK.md` CHANGED: NO
- Portal/BFF CHANGED: NO
- nginx CHANGED: NO
- Identity CHANGED: NO
- AI_CODEX_USED: NO
- AUTOMATED_RUNNER_USED: NO
- SECRETS_EXPOSED: NO
- WORKTREE: CLEAN

## 12. Recommendation (для ChatGPT)
Для включения tool-calling Qwen3.8-27B требуется корректирующее задание:
1. `--tool-call-parser qwen3_xml` (или `qwen3_coder`) вместо `hermes`;
2. BFF `/v1/chat/completions` должен пересылать `tool_choice` (сейчас отбрасывается).
