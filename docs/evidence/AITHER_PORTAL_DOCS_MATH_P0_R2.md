# AITHER PORTAL DOCS/MATH P0 R2 — Evidence

TASK: AITHER-PORTAL-DOCS-MATH-P0-R2
MODE: FORCE_MAJEURE_MANUAL_P0_CORRECTION
EXECUTOR: HERMES
DATE: 2026-08-25

## 1. BASELINE_SHA / FINAL_SHA

- BASELINE: `27fe900cb6f2d25b1c09a9e9e13f141e946dd4db`
- FINAL: финальный corrective-коммит (message `fix: make Portal math deployment durable and repair anchors`)

## 2. Changed paths

- `aither-v2/services/portal-frontend/Dockerfile`
- `aither-v2/services/portal-frontend/app.js`
- `aither-v2/services/portal-frontend/k8s/aither-portal.yaml` (новый authoritative manifest)
- `docs/user-package/04_API_GUIDE.md` (TOC anchor fix)
- `docs/user-package/14_API_KEY_USER_GUIDE.md` (corruption fix)
- `docs/user-package/16_AI_AGENT_CONNECTION_PRIMER.md` (corruption fix)
- `docs/user-package/17_MODEL_USAGE_GUIDE.md` (corruption fix)
- `docs/evidence/AITHER_PORTAL_DOCS_MATH_P0_R2.md`

## 3. Active serving chain

```
https://fb1.spb.ru:10443 (VPS2 nginx aither-failover-nginx)
  → 10.129.13.78:30080 (NodePort svc aither-portal, selector app=aither-portal)
  → Deployment aither-portal (namespace aither-inference)
  → pod (nginx: custom image aither-portal:docs-math-r2)
  → nginx (config из ConfigMap aither-portal-config)
  → index/app/vendor (app files из ConfigMap subPath; vendor/katex из image filesystem)
```

## 4. Active deployment name

`aither-portal` (namespace `aither-inference`). Не путать с secondary `aither-portal-frontend`.

## 5. Old KaTeX delivery method

Ручной hostPath `/data/aither/portal-vendor` (n7/n8) + volume mount `vendor:/usr/share/nginx/html/vendor`.

## 6. New KaTeX delivery method

KaTeX vendor запечён в immutable Portal image (`COPY vendor/katex/ /usr/share/nginx/html/vendor/katex/`). Никакого hostPath, никакого runtime fetch/CDN.

## 7. Dockerfile change

Добавлена строка: `COPY vendor/katex/ /usr/share/nginx/html/vendor/katex/` (KaTeX 0.16.11 pinned, no CDN).

## 8. Image tag/digest

- tag: `10.129.13.78:5000/aither-portal:docs-math-r2`
- digest: `sha256:417e0fd58050ce98fe59b8c586b8d4fb8d8506c7f756f5145046be74ace075c3`

## 9. Authoritative manifest path

`aither-v2/services/portal-frontend/k8s/aither-portal.yaml` (новый, отражает активный aither-portal: image digest, ConfigMap mounts, docs mount, subPath для app files, без hostPath).

## 10. Proof no hostPath dependency

- Deployment volumes после фикса: `config`, `www`, `docs` (vendor hostPath удалён).
- KaTeX assets отдаются из image filesystem (`/usr/share/nginx/html/vendor/katex/`), сохранённого subPath-монтированием (ConfigMap не перекрывает каталог vendor/).
- Поле `hostPath` отсутствует в authoritative manifest.

## 11. Pod restart reproducibility

`kubectl delete pod <aither-portal>` → новый pod Ready → KaTeX assets снова 200 (без ручной копии на node). Повторено дважды (до и после финального деплоя).

## 12. Asset HTTP checks

- `/vendor/katex/katex.min.css` → 200 (23335 B)
- `/vendor/katex/katex.min.js` → 200 (275414 B)
- `/vendor/katex/contrib/auto-render.min.js` → 200 (3481 B)
- `/vendor/katex/fonts/KaTeX_Main-Regular.woff2` → 200 (26272 B)
- Content-Length > 0, no 404, no CDN.

## 13. Anchor root cause

Renderer создавал `<h2>Заголовок</h2>` без `id`; `#section` некуда скроллить. Дополнительно: R1-эндпоинт-замена была жадной и превратила `/api/v1/models` → `/api/api/v1/models` в 3 документах, что сломало slug заголовков.

## 14. Slug algorithm

`slugifyHeading`: trim → lowercase → удалить всё кроме Unicode letters/digits/space/dash → spaces→`-` → collapse `-+`→`-` → trim leading/trailing dash. Duplicates → `-2`, `-3`. Anchor resolution нормализует `--`→`-` и trim, поэтому `#рекомендуемый-способ--web-ui` резолвится в `id="рекомендуемый-способ-web-ui"`.

## 15. A1–A5 results

- A1 «Быстрый старт» → `#быстрый-старт` — PASS (код; scroll — OWNER)
- A2 «API Guide» → `#api-guide` — PASS (код)
- A3 duplicate headings → уникальные id (`-2`, `-3`) — PASS (код)
- A4 missing anchor → controlled no-op, no crash — PASS (код)
- A5 anchor in long modal → scrollIntoView внутри `.wiki-doc-body`, без page navigation — PASS (код; фактический scroll — OWNER)

## 16. Link audit counts

- TOTAL_MARKDOWN_LINKS = 208
- LOCAL_LINKS = 93
- EXTERNAL_LINKS = 115
- BROKEN_LOCAL_LINKS = 0
- ANCHOR_LINKS_TOTAL = 114
- ANCHOR_LINKS_RESOLVABLE = 114
- ANCHOR_LINKS_BROKEN = 0

## 17. Math regression

Не изменялось. KaTeX 0.16.11, delimiters `$$/$/\(/\[`, throwOnError=false, trust=false, ignoredTags pre/code, underscore normalization. Assets отдаются из image. Browser typesetting — OWNER (финальный gate).

## 18. Portal regression

- models API → 200
- qwen3-32b chat → 200
- qwen3.8-27b chat → 200
- docs 00/14/16/17 → 200
- max_tokens policy / Continue — не тронуты

## 19. R1 evidence correction note

`DOC_PACKAGE_FILES_AUDITED = 18`, `DOC_PACKAGE_FILES_MODIFIED_IN_R1 = 17`, `UNCHANGED_BUT_AUDITED = 07_USER_FEEDBACK_FORM.md` (подтверждено `git show 27fe900 --name-only`).

## 20. HOLD preserved

`.agent/CURRENT_TASK.json` = `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`, `agent_exec=false`, `source_write=false`, `runtime_write=false`, `kubernetes=false`, `deployment=false`, host sync/commit/push=false. Automated runner не запускался.

## 21. Backlog preserved

Да — не тронуты: max-model-len tuning, server-side chat history, billing, tariffs, OAuth, chat race, RAG redesign, streaming, governance runner repair, observability/SLO, legacy cleanup, RCA. Token-counter UX оставлен в backlog.

## 22. Changed paths

См. пункт 2.

## 23. Rollback readiness

- Previous deployment YAML: `/tmp/aither-portal.orig.yaml`
- Previous image: `nginx:stable-alpine` (stock) / previous custom digest `09e76d8af6c9...`
- ConfigMap backups: `/tmp/portal-config.orig2.yaml`, `/tmp/portal-docs.orig2.yaml`
- Rollback: `kubectl set image` на прежний image; восстановить hostPath mount при необходимости.

## 24. AI_CODEX_USED: NO
## 25. AUTOMATED_RUNNER_USED: NO
## 26. SECRETS_EXPOSED: NO
