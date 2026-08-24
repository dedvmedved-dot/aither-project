# AITHER PORTAL ANSWER COMPLETENESS P0 R1 — Evidence

TASK: AITHER-PORTAL-ANSWER-COMPLETENESS-P0-R1
MODE: FORCE_MAJEURE_MANUAL_P0_CORRECTION
EXECUTOR: HERMES
DATE: 2026-08-24

## 1. BASELINE_SHA

`4b87897ad419306233f4140d5d32b4e5933485f3` — "audit: finalize Aither emergency stabilization R2"

## 2. FINAL_SHA

Зафиксирован финальным corrective-коммитом (см. `git log`, message `fix: prevent Portal answer truncation and sync API docs`).

## 3. Root cause

Browser Chat использовал `max_tokens=512` в двух местах:
- frontend `app.js`: `maxTokens = parseInt($('chat-max-tokens')?.value) || 512` (поле отсутствует → всегда 512);
- backend `main.py` `/api/v1/chat` (session path): `max_tokens = body_json.get("max_tokens", 512)`.

Следствие: генерация обрывалась на 512 токенах (`finish_reason=length`), frontend не анализировал `finish_reason` и показывал усечённый ответ как завершённый. Внешний API-key path имел `2048`, поэтому curl-тесты проходили, а browser UX — нет.

## 4. Frontend before/after output budget

- before: `|| 512`
- after: `DEFAULT_MAX_TOKENS = 2048`, `HARD_MAX_TOKENS = 4096`, `if (maxTokens > HARD_MAX_TOKENS) maxTokens = HARD_MAX_TOKENS;`

## 5. Backend before/after output budget

- before: `/api/v1/chat` session `512`; API-key paths `2048`.
- after: все три пути используют `_resolve_max_tokens(value)` → default `2048`.

## 6. Hard max policy

`_resolve_max_tokens`: `None` → 2048; `> 4096` → clamp 4096; bool/не-int → 400; `<= 0` → 400.

Runtime-подтверждено: `max_tokens=100000` → 200 (clamp); `0` → 400 «positive integer»; `-1` → 400; `"abc"` → 400 «must be an integer».

## 7. Timeout chain before/after

- backend → vLLM: 120s → **300s** (3 chat-пути; RAG 14B оставлен без изменений).
- portal nginx `location /api/`: без таймаута (60s default) → **330s** read/send.
- external reverse proxy (VPS2): `/api/` и `/` (:10443) без таймаута → **330s**; `/v1/chat/completions` 300s → **330s**.

## 8. finish_reason behavior

Frontend анализирует `choices[0].finish_reason`:
- `stop` → обычный завершённый ответ;
- `length` → сообщение «⚠️ Ответ достиг установленного лимита.» + кнопка «Продолжить».

## 9. Continue behavior

Кнопка «Продолжить» → `continueAnswer(model)`: history = текущая session.history.slice(-20) + `{role:'user', content:'Продолжи ответ с места остановки. Не повторяй уже написанное.'}`; та же модель; `max_tokens=2048`; continuation добавляется как следующий assistant-сегмент; при повторном `length` — снова кнопка.

## 10. Test results T1–T15

- T1 model catalog — PASS (ровно qwen3-32b, qwen3.8-27b)
- T2 short answer — PASS (200, finish_reason=stop)
- T3/T4 long answer (browser UI) — REQUIRED (OWNER browser verification)
- T5 Continue (browser UI) — REQUIRED (OWNER browser verification)
- T6 backend default — PASS (без max_tokens: 945 completion tokens, finish_reason=stop)
- T7 hard max — PASS (100000 → 200, clamp)
- T8 invalid max_tokens — PASS (0/-1/abc → 400)
- T9 external API regression — PASS (models 200; обе модели chat 200 nonempty)
- T10 unknown model — PASS (404 model_not_found)
- T11 timeouts — PASS (timeout chain 300s/330s/330s; long response без 504)
- T12 docs 14 — PASS (200; aither_ 8×; qwen3-32b/qwen3.8-27b; athr_=0; qwen-14b=0; qwen-32b-base=0)
- T13 docs 16 — PASS (200; aither_ 7×; обе модели; athr_=0; retired=0)
- T14 runtime readiness — PASS (все pods 1/1 Ready, новые portal/portal-backend после rollout)
- T15 HOLD preserved — PASS (CURRENT_TASK.json = AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1; agent_exec/source_write/runtime_write=false)

## 11. Docs 14 before/after

- before: `athr_` (7×), `qwen-14b`, `qwen-32b-base`.
- after: `aither_`, `qwen3-32b`, `qwen3.8-27b`, scope `model:qwen3:chat`; retired отсутствуют.

## 12. Docs 16 before/after

- before: `athr_` (11×), `OPENAI_API_KEY="athr_..."`, `qwen-14b`/`qwen-32b-base`, примеры Codex как executor.
- after: `OPENAI_API_KEY="aither_..."`, только `qwen3-32b`/`qwen3.8-27b`, универсальный OpenAI-compatible формат; Codex не представлен как внутренний executor.

## 13. Runtime image/config changes

- backend image: `aither-portal-backend:p0-answer-completeness-r1` (digest `554c1e6bf9bd...`).
- ConfigMap `aither-portal-config`: обновлены `app.js` и `nginx.conf`.
- ConfigMap `aither-portal-docs`: обновлены 14/16 (пересоздан из git).
- external proxy `/root/nginx-failover.conf`: обновлён (reload прошёл, `nginx -t` ok).

## 14. Rollout / readiness

`kubectl rollout restart deploy/aither-portal` и `aither-portal-backend` — оба successfully rolled out; все production pods 1/1 Ready; новых CrashLoopBackOff нет.

## 15. External API regression

Нет регрессии: models 200, qwen3-32b chat 200, qwen3.8-27b chat 200.

## 16. Changed paths

- `aither-v2/services/portal-backend/app/main.py`
- `aither-v2/services/portal-frontend/app.js`
- `aither-v2/services/portal-frontend/nginx.conf`
- `aither-v2/services/portal-frontend/nginx-failover-vps2.conf`
- `docs/user-package/14_API_KEY_USER_GUIDE.md`
- `docs/user-package/16_AI_AGENT_CONNECTION_PRIMER.md`
- `docs/evidence/AITHER_PORTAL_ANSWER_COMPLETENESS_P0_R1.md` (этот файл)

## 17. Rollback readiness

- Original ConfigMaps сохранены: `/tmp/portal-config.orig.yaml`, `/tmp/portal-docs.orig.yaml`.
- External proxy: previous conf можно восстановить из git `HEAD~1`.
- Backend image: предыдущий digest `1078f0a8...` (tag `hotfix-r1`) доступен в registry — `kubectl set image` обратно.
- Git: один коммит, без force-push.

## 18. Backlog preserved

Да — не тронуты: server-side chat history, billing UI, tariffs, OAuth redirect, chat switching race, RAG redesign, streaming, governance runner repair, BLOCKED_* propagation, H2 redesign, performance/benchmark/SLO/observability, legacy manifest deletion, RCA.

## 19. HOLD preserved

`.agent/CURRENT_TASK.json` остаётся `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`; automated runner не запускался.

## 20. AI_CODEX_USED: NO
## 21. AUTOMATED_RUNNER_USED: NO
## 22. SECRETS_EXPOSED: NO
