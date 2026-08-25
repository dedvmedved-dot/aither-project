# AITHER PORTAL CHAT RENDER/STATE P0 R1 — Evidence

TASK: AITHER-PORTAL-CHAT-RENDER-STATE-P0-R1
MODE: FORCE_MAJEURE_MANUAL_P0_CORRECTION
EXECUTOR: HERMES
DATE: 2026-08-25

## 1. BASELINE_SHA / FINAL_SHA

- BASELINE: `665a3052f87dc67f87fbf2347ebf578c6adf33e3`
- FINAL: финальный corrective-коммит (message `fix: stabilize chat rendering and per-session continuation state`)

## 2. Changed paths

- `aither-v2/services/portal-frontend/app.js`
- `aither-v2/services/portal-frontend/k8s/aither-portal.yaml` (обновлён image digest)
- `docs/evidence/AITHER_PORTAL_CHAT_RENDER_STATE_P0_R1.md`

## 3. Root causes A–D

- A: Chat `formatMessage` использовал `formatMarkdown` (bold/italic/inline-code/`\n`→`<br>`), без таблиц; `\n`→`<br>` до KaTeX ломал multiline math (`$$<br>...<br>$$`).
- B: `finish_reason=length` внутри формулы разрезал `$$ E=mc` / `^2 $$` — два невалидных фрагмента.
- C: Continue был DOM-only (session не хранил `generation_status`/`finish_reason`/`needs_continue`/`answer_id`); `_switchChat` чистил DOM и восстанавливал только history.
- D: multi-chat race — после `await` код использовал глобальный `#chat-messages`; response одного чата мог мутировать DOM другого.

## 4. Old/new Chat renderer pipeline

- OLD: split ```code``` → highlightCode | `formatMarkdown(escHtml(...))` (bold/italic/inline-code/`\n`→`<br>`).
- NEW (`formatMessage`): protect fenced code → protect inline code → protect math (`$$…$$`/`\[…\]`/`\(…\)`/`$…$`, multiline-capable) → escape → tables → bold/italic → `\n`→`<br>` → restore inline code → restore code → restore math → DOM insert → KaTeX render.

## 5. Math protection strategy

Math fragments извлекаются в placeholders `\x00MB<n>\x00` ДО newline/table conversion, поэтому multiline `$$…$$` сохраняется цельным. Restore — HTML-escaped (safe DOM), KaTeX auto-render рендерит после insert. `preProcess` сохраняет `\_`→`_`; `ignoredTags` pre/code; `throwOnError=false`, `trust=false`.

## 6. Table rendering

`renderChatTable` — pipe-tables (`| h |` + `|---|` + rows) → `<table class="md-table">`, 4 столбца/строки поддерживаются. Inline code и math в ячейках сохраняются (placeholders).

## 7. Session generation schema

```javascript
session.generation = {
  status: 'idle'|'generating'|'needs_continue',
  request_id, answer_id, model, finish_reason
}
```

Persist в существующей `localStorage`-сериализации (`saveChatSessions`).

## 8. Backward migration

`loadChatSessions` + `ensureGeneration` — старые sessions без `generation` мигрируют к `idle`, history сохраняется.

## 9. Logical answer design

Assistant history item: `{ role:'assistant', content, model, answer_id, finish_reason }`. Continuation fragments дописываются к тому же `answer_id` (`content = content + '\n' + fragment`), затем весь logical answer re-render.

## 10. request_id / answer_id design

- `request_id` = уникальный ID каждого запроса (для stale-response detection).
- `answer_id` = ID логического ответа (переиспользуется между Continuation; очищается при `stop`).

## 11. Background response isolation

Response handler использует captured `sessionId` (`findSession(sessionId)`, проверка `request_id`), обновляет только эту session; DOM обновляется только при `currentSessionId === sessionId` (`reRenderSessionMessages`).

## 12. Continue persistence

`status=needs_continue` + `answer_id` сохраняются; `_switchChat`/`restoreChatMessages` восстанавливают warning + кнопку «Продолжить» через `reRenderSessionMessages`.

## 13. Refresh persistence

`generation` сериализуется; после refresh `needs_continue` восстанавливается (warning + Continue). `stop` → нет Continue.

## 14. Stale response protection

Если `g.request_id !== captured requestId` → response отбрасывается (не меняет history/DOM, не crash).

## 15. Clear/delete behavior

`clearChat` сбрасывает `generation` (idle) — outstanding request_id инвалидируется. Delete: `findSession` вернёт null → response отбрасывается.

## 16. Formula tests (browser — OWNER)

Qwen3-32B multiline formula (ε₀/ρ/φ/int) — code + math protection готовы; typesetting — OWNER.

## 17. Cross-boundary formula test

Логическое объединение фрагментов через `answer_id` — code ready; визуальная отрисовка merged formula — OWNER.

## 18. Table tests

`renderChatTable` + inline code + `$math$` в ячейках — code ready; браузерная отрисовка — OWNER.

## 19. S1–S8 matrix (browser — OWNER)

Код реализует captured-session + request_id isolation + reRender. Фактические switch-сценарии — OWNER.

## 20. Source validation

- `node --check app.js` → OK.
- `git diff --check` → OK.
- no CDN → OK.
- static: `.generation` (6), `request_id` (15), `answer_id` (10), `needs_continue` (7), `ensureGeneration`, `findSession(sessionId)`, `currentSessionId === sessionId`, `renderChatTable`, `reRenderSessionMessages`, `findAnswerItem`, multiline math regex — present.

## 21. Runtime image tag/digest

- tag: `10.129.13.78:5000/aither-portal:chat-render-state-r1`
- digest: `sha256:c749ff81186deb8e115a203654956756b27dfa763ca95273f8b780e23172fcdc`

## 22. Authoritative manifest

`aither-v2/services/portal-frontend/k8s/aither-portal.yaml` обновлён на новый digest.

## 23. Pod restart reproducibility

`kubectl delete pod` → новый pod Ready → KaTeX + app.js 200, без ручной копии.

## 24. Model regressions

models 200; qwen3-32b chat 200; qwen3.8-27b chat 200.

## 25. max_tokens unchanged

`DEFAULT_MAX_TOKENS=2048`, `HARD_MAX_TOKENS=4096`. Streaming/auto-continue не введены.

## 26. KaTeX durable delivery preserved

KaTeX из image (no hostPath), subPath ConfigMap подход сохранён.

## 27. HOLD preserved

`.agent/CURRENT_TASK.json` = `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`, `agent_exec=false`.

## 28. Backlog preserved

Да — не тронуты Qwen3.8 64K, streaming, auto-continue, server-side history, billing/tariffs/OAuth/RAG, observability, governance runner repair, performance/SLO.

## 29. Rollback

- Previous image digest: `417e0fd58050...` (docs-math-r2).
- ConfigMap backup: `/tmp/portal-config.orig2.yaml` (+ текущий извлечён в /tmp/portal-cm5).
- `kubectl set image` на прежний digest.

## 30. AI_CODEX_USED: NO
## 31. AUTOMATED_RUNNER_USED: NO
## 32. SECRETS_EXPOSED: NO
