# AITHER PORTAL CONTINUE RENDER + INSTANT USER P0 R1 — Evidence

TASK: AITHER-PORTAL-CONTINUE-RENDER-INSTANT-USER-P0-R1
MODE: FORCE_MAJEURE_MANUAL_P0_CORRECTION
EXECUTOR: HERMES
DATE: 2026-08-25

## Baseline / Final SHA
- BASELINE: `ebc8f5c6a202fc44d118ba6cea9c17acaa71e072`
- FINAL: финальный corrective-коммит (`fix: restore instant user bubble and continuation math rendering`)

## Changed paths
- `aither-v2/services/portal-frontend/app.js`
- `aither-v2/services/portal-frontend/k8s/aither-portal.yaml` (image digest)
- `docs/evidence/AITHER_PORTAL_CONTINUE_RENDER_INSTANT_USER_P0_R1.md`

## Root cause A — user question not visible immediately
`sendChatMessage` записывал user message в `session.history`, но рендерил только `⏳ Генерация ответа...` (DOM-append). User bubble появлялся только после `reRenderSessionMessages` при ответе.

## Fix A
После установки `generation.status='generating'` + push user message — вызывается единый state-driven `reRenderSessionMessages(session)` (если `currentSessionId===sessionId`). Рендерит user bubble + generation indicator из `history + generation` (single source of truth). Continuation не добавляет fake user bubble (инструкция не попадает в history).

## Root cause B — continuation render break
`formatMessage` сначала защищал fenced code, потом math. Fenced `latex`/`tex`/`math`/`katex` классифицировались как code → syntax-highlighted (белый/красный), KaTeX ломался.

## Fix B — math-fence normalization
До generic fenced-code extraction: ` ```latex/tex/math/katex ... ``` ` → display math (`$$...$$`), если уже есть `$$`/`\[` — без вложенных делимитеров. Generic code (`python`/`bash`/`json`/…) остаётся code.

## Old/new send UI flow
- OLD: push history → save → render ⏳ (user bubble отсутствовал до ответа).
- NEW: push history → set generation → save → `reRenderSessionMessages` (user bubble + ⏳ сразу).

## I1-I3, C1-C9 (код; browser — OWNER)
- I1 instant user bubble — код PASS (reRenderSessionMessages на send).
- I2 no duplication — PASS (history single source).
- I3 switch during generation — PASS (reRender по currentSessionId guard).
- C1 no fake continue bubble — PASS.
- C2-C5 latex/tex/math/katex → math, python → code — PASS (normalization).
- C6 cross-block math — PASS (logical merge + math protection).
- C7 table after continue — PASS (table renderer).
- C8 multiple continues — PASS (answer_id append).
- C9 switch during continue — PASS (session-safe).

## Both-model regressions
- models 200 (qwen3-32b + qwen3.8-27b).
- qwen3-32b chat 200.
- qwen3.8-27b chat 200.

## 64K unchanged
`vllm-qwen38-27b-fp8` `--max-model-len 65536`, pod Ready, no inference rollout.

## Timeouts unchanged
backend 600s / Portal nginx 630s / VPS2 nginx 630s.

## Portal image
- tag: `10.129.13.78:5000/aither-portal:continue-render-r1`
- digest: `sha256:ca1e71e1d4bd9cad73bdb50300c362e5978c3092c8a3b19c98e72f0fc2b4d4c2`

## Restart reproducibility
`kubectl delete pod` → Ready → app.js 200 + KaTeX 200, no hostPath.

## HOLD / backlog
HOLD preserved (`AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`). Backlog preserved (streaming, branching/editing, attachments, OCR, conversation graph — не тронуты).

## AI_CODEX_USED: NO
## AUTOMATED_RUNNER_USED: NO
## SECRETS_EXPOSED: NO
