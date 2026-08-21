# AITHER-MVP-SOURCE-RUNTIME-RECONCILE-D1-R1

## Цель
Закрыть только drift D1 из `SOURCE_RUNTIME_DRIFT_AUDIT_R1`: вернуть рабочую конфигурацию внешнего API routing из live `aither-portal-config/nginx.conf` в GitHub Source of Truth и синхронизировать вторичный `aither-portal-frontend-config/nginx.conf` с этим каноническим файлом.

## Жёсткие ограничения
- Не исправлять D2/D3 в этой задаче.
- Не менять Service selectors, Deployments BFF, model deployments, Identity, billing, users, DB, secrets, CNI, control-plane, observability, backups.
- Не читать значения Kubernetes Secrets.
- Не создавать API keys/credentials.
- Не выполнять прямые Git write operations: add/commit/push/pull/reset/clean/checkout/switch/merge/rebase/tag/ref mutation. Host runner выполняет commit/push.
- Не изменять `.agent/*`.
- Не менять `/root/.hermes`.
- Не использовать `safe.directory=*`, generic sudo, recursive chown/chmod.
- Изменённые repo-файлы перед завершением должны иметь uid/gid 1000:1000.

## Разрешённые repo-пути
1. `aither-v2/services/portal-frontend/nginx.conf`
2. `docs/evidence/SOURCE_RUNTIME_RECONCILE_D1_R1.md`

## Разрешённые runtime-объекты
Только namespace `aither-inference`:
- ConfigMap `aither-portal-config` — READ ONLY, кроме случая, если во время проверки обнаружено, что он уже отличается от зафиксированного working D1 runtime; любые изменения здесь допускаются только для возврата к проверенному working content.
- ConfigMap `aither-portal-frontend-config` — разрешено обновить только key `nginx.conf` до канонического content.
- Deployment `aither-portal-frontend` — допускается controlled rollout/restart только если нужен reload nginx после ConfigMap update.
- Deployment `aither-portal` — не рестартовать, если `aither-portal-config` не изменялся.

## Порядок выполнения
1. INSPECT
   - Проверить clean worktree, task baseline/HEAD, ownership.
   - Read-only получить live `aither-portal-config` key `nginx.conf` и вычислить sha256.
   - Read-only получить `aither-portal-frontend-config` key `nginx.conf` и sha256.
   - Вычислить sha256 source `aither-v2/services/portal-frontend/nginx.conf`.
   - Подтвердить наличие в live primary config точных external API routes:
     - `location = /api/v1/models`
     - `location = /api/v1/chat/completions`
2. SOURCE OF TRUTH RECONCILIATION
   - Обновить `aither-v2/services/portal-frontend/nginx.conf` так, чтобы он представлял полный проверенный working nginx content из live primary `aither-portal-config/nginx.conf`, без сокращений и без ручного удаления существующих working route blocks.
   - После записи source sha256 должен совпасть с live primary config sha256 (нормализовать только финальный newline, если это единственное отличие; факт нормализации явно записать в evidence).
3. SECONDARY RUNTIME RECONCILIATION
   - Если `aither-portal-frontend-config/nginx.conf` отличается от нового canonical source, обновить только этот key до canonical content.
   - Не изменять `index.html`, `app.js`, `styles.css` и любые другие keys.
   - При необходимости выполнить controlled rollout `aither-portal-frontend`; дождаться Ready.
4. VALIDATE
   - Source nginx hash == live `aither-portal-config/nginx.conf` hash.
   - Source nginx hash == live `aither-portal-frontend-config/nginx.conf` hash после reconciliation.
   - Подтвердить, что оба external API route blocks присутствуют в source и обоих ConfigMaps.
   - Проверить `aither-portal` и `aither-portal-frontend` Ready.
   - Test Zone `GET http://10.129.13.78:30080/health` -> 200.
   - Test Zone `POST http://10.129.13.78:30080/api/v1/chat/completions` без Authorization -> 401/403, не 404/5xx.
   - Internet path `GET https://fb1.spb.ru:10443/health` -> 200, если endpoint доступен из среды; недоступность внешней сети сама по себе не является FAIL, но должна быть зафиксирована.
   - Не использовать реальный API key и не повторять model inference.
5. EVIDENCE
   - Создать `docs/evidence/SOURCE_RUNTIME_RECONCILE_D1_R1.md`.
   - Зафиксировать before/after hashes, точные изменённые runtime objects/keys, rollout status, HTTP status checks, ownership и `git status`.
   - Не включать secret values, bearer tokens, credentials, full environment dumps.
6. OWNERSHIP
   - Оба изменённых repo-path должны быть uid/gid 1000:1000.
   - Никакого recursive chown/chmod.
7. STOP
   - После evidence и проверок остановиться. D2/D3 не трогать.

## PASS
PASS только если одновременно:
- canonical source содержит полный working primary nginx configuration;
- source hash совпадает с primary live nginx hash;
- secondary frontend ConfigMap nginx hash совпадает с canonical source;
- external API route blocks присутствуют во всех трёх копиях;
- portal health остаётся 200;
- unauthenticated chat route отвечает 401/403, а не 404/5xx;
- никаких изменений вне разрешённых runtime objects и repo paths;
- D2/D3 не затронуты;
- secrets не читались и не выводились;
- Hermes не выполнял Git writes;
- ownership gate PASS.

Иначе BLOCKED с точной причиной и без расширения scope.
