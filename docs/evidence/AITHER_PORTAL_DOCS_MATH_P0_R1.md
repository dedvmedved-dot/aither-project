# AITHER PORTAL DOCS & MATH P0 R1 — Evidence

TASK: AITHER-PORTAL-DOCS-MATH-P0-R1
MODE: FORCE_MAJEURE_MANUAL_P0_CORRECTION
EXECUTOR: HERMES
DATE: 2026-08-24

## 1. BASELINE_SHA / FINAL_SHA

- BASELINE: `f5aa54b673de91c28c67fc4bd28063a827bed7f3`
- FINAL: финальный corrective-коммит (message `fix: repair Portal docs navigation and render math`)

## 2. Changed paths

- `aither-v2/services/portal-frontend/app.js`
- `aither-v2/services/portal-frontend/index.html`
- `aither-v2/services/portal-frontend/vendor/katex/**` (новые, 64 файла)
- `docs/user-package/00..17_*.md` (18 файлов)
- `docs/evidence/AITHER_PORTAL_DOCS_MATH_P0_R1.md`

## 3. Docs inventory

18 файлов в `docs/user-package/` (00_INDEX … 17_MODEL_USAGE_GUIDE). Все синхронизированы с production contract.

## 4. Card catalog before/after

- before: 9 hard-coded карточек в `index.html`, расходились с canonical docs.
- after: `DOC_CATALOG` (18 записей: file/title/icon/desc/category) в `app.js`; `renderDocCards()` рендерит их в `#docs-grid` (категории: Основное / Разработчикам / Тестирование); каждая карточка открывает `showDoc('/docs/<file>')`.

## 5. Markdown link root cause

`renderMarkdown()` делал `<a href="$2" target="_blank">`, поэтому `[FAQ](08_FAQ.md)` разрешался как `/08_FAQ.md` (404) вместо `/docs/08_FAQ.md`.

## 6. Link routing implementation

`renderMarkdown()` теперь: http(s)/mailto → external (`noopener noreferrer`); `#anchor` → in-modal anchor; локальный `.md` → `<a class="md-doc-link" data-doc-path="...">`; глобальный `document` click-listener ловит `.md-doc-link` и вызывает `showDoc('/docs/' + normalizeDocPath(...))`. `normalizeDocPath` — allowlist (`^[\w-]+\.md$`), запрет `..` и `\` (path traversal).

## 7. Link audit counts

- TOTAL_MARKDOWN_LINKS = 208
- LOCAL_LINKS = 93
- EXTERNAL_LINKS = 115
- BROKEN_LOCAL_LINKS = 0 (все локальные ссылки ведут на существующие файлы; маршрутизация исправлена renderer-фиксом)

## 8. Stale reference audit counts

До: `athr_` в 12 файлах, `qwen-14b`/`qwen-32b-base` в 9 файлах, `:443` в 13 файлах, `CB-WEBUI-01/02` в 9 файлах.

После: `CURRENT_STALE_REFERENCES = 0`. Осталось только `Qwen2.5`/`qwen2.5` в `17_MODEL_USAGE_GUIDE.md` — явно HISTORICAL (помечено «больше не является активной моделью»).

## 9. 00_INDEX before/after

- before: дата 25.07.2026, версия CB-WEBUI-01.
- after: дата 24.08.2026, версия CB-WEBUI-03, active models qwen3-32b/qwen3.8-27b, `aither_`, URL :10443/:30080, changelog v1.2.

## 10. KaTeX version/source/license

KaTeX **0.16.11** (pinned), из npm (`katex@0.16.11`). Включены: `katex.min.css`, `katex.min.js`, `contrib/auto-render.min.js`, 60 font-файлов (woff2/woff/ttf), `LICENSE` (MIT).

## 11. Proof local runtime assets / no CDN

- Канонический путь: `aither-v2/services/portal-frontend/vendor/katex/`.
- `grep -RniE 'cdn.jsdelivr|unpkg|cdnjs|katex.*https://'` → пусто (нет внешней runtime-зависимости).
- Деплой: hostPath `/data/aither/portal-vendor` (n7 и n8) → mount `/usr/share/nginx/html/vendor`.
- Runtime HTTP: `vendor/katex/katex.min.css|.js`, `contrib/auto-render.min.js`, `fonts/KaTeX_Main-Regular.woff2` → 200.

## 12. Math delimiter policy

`$$...$$` (display), `\[...\]` (display), `$...$` (inline), `\(...\)` (inline). `ignoredTags: ['script','noscript','style','textarea','pre','code']`. `throwOnError=false`, `trust=false`.

## 13. Underscore normalization

`preProcess: math => math.replace(/\\_/g, '_')` — только внутри math-выражения (не global, не в code blocks). `T\_0 → T_0`, `T\_{\infty} → T_{\infty}`.

## 14. M1–M8 (browser typesetting — OWNER)

Реализация и доставка assets проверены на уровне кода/HTTP. Фактическое typesetting в браузере — OWNER browser verification:

- M1 `$$...$$` display — OWNER
- M2 escaped form `T\_0 = T\_{\infty}\left(...\right)` — OWNER
- M3 inline `$M=2.5$` — OWNER
- M4 `\(...\)` / `\[...\]` — OWNER
- M5 code isolation (fenced code не рендерится) — OWNER
- M6 malformed TeX failsafe — OWNER
- M7 formula в continuation — OWNER
- M8 restored chat после refresh — OWNER

## 15. D1–D7

- D1 cards — code ready (DOC_CATALOG+renderDocCards); браузерная отрисовка — OWNER.
- D2 00_INDEX current — PASS (HTTP 200, aither_, qwen3).
- D3 chained internal links — renderer fix ready; клик-через — OWNER.
- D4 anchors — `#anchor` ссылки остаются in-modal; OWNER.
- D5 docs 14/16/17 current — PASS (200, `aither_`, нет retired).
- D6 BROKEN_LOCAL_LINKS_AFTER = 0 — PASS.
- D7 CURRENT_STALE_REFERENCES_AFTER = 0 — PASS.

## 16. Regression

- models API → 200
- qwen3-32b chat → 200
- qwen3.8-27b chat → 200
- DEFAULT_MAX_TOKENS (2048/4096) и finish_reason/Continue — не тронуты (изменения не касались backend/main.py).

## 17. Runtime delivery

- ConfigMap `aither-portal-config`: обновлены `app.js` + `index.html`.
- ConfigMap `aither-portal-docs`: пересоздан (18 файлов).
- Deployment `aither-portal`: добавлен hostPath `vendor` mount; rollout successful.
- KaTeX vendor скопирован на n7 и n8 (`/data/aither/portal-vendor`).

## 18. Rollback

- Original ConfigMaps: `/tmp/portal-config.orig2.yaml`, `/tmp/portal-docs.orig2.yaml`.
- hostPath mount: удалить volume/volumeMount из deployment (patch).
- KaTeX vendor: удалить `/data/aither/portal-vendor` на узлах.
- Git: один коммит, без force-push.

## 19. HOLD/BACKLOG preserved

- `.agent/CURRENT_TASK.json` = `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`, `agent_exec=false`.
- Backlog не тронут (max-model-len, server-side history, billing, tariffs, OAuth, chat race, RAG redesign, streaming, governance runner repair, etc.). Token-counter UX оставлен в backlog (только зафиксировано).

## 20. AI_CODEX_USED: NO
## 21. AUTOMATED_RUNNER_USED: NO
## 22. SECRETS_EXPOSED: NO
