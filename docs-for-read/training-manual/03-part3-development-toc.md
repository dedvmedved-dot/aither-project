# Часть III. Разработка и доработка

**Документ:** `03-part3-development.md` · 5 глав · ~95 стр. · 10 схем · 10 таблиц

> Как изменять, расширять и улучшать платформу: код, модели, автоматизация.

---

## Глава 14. Инструменты разработчика (18 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 14.1 | Git — система контроля версий | 5 | 1 | 1 | Что такое VCS. Git: распределённая модель. Основные понятия: репозиторий, коммит, ветка, merge, remote. Рабочий цикл: `clone` → `branch` → `add` → `commit` → `push` → `pull request` → `merge`. `.gitignore`: что исключать (`node_modules/`, `*.env`, `models/`). ✏️ Склонировать aither-project, создать ветку, сделать коммит |
| 14.2 | Среда разработки | 4 | — | 1 | VS Code: Remote-SSH (разработка прямо на сервере). Nano: консольный редактор (Ctrl+O, Ctrl+X). SSH-туннели: `ssh -L 8080:localhost:8080` для доступа к K8s-сервисам. `kubectl port-forward`: временный проброс. watch: автообновление вывода (`watch kubectl get pods`) |
| 14.3 | Python — ликбез для доработки Gateway | 5 | — | 1 | Синтаксис: переменные, функции, классы, декораторы. Типы данных: str, int, float, list, dict, set, tuple. Модули и импорты: `from gateway.billing import deduct_tokens`. `pip`, `venv`: виртуальное окружение. Типовые ошибки: `IndentationError`, `NameError`, `TypeError`, `ModuleNotFoundError`. Логирование: `logging.info()` vs `print()`. ✏️ Написать простой Flask-сервер |
| 14.4 | Node.js/TypeScript — ликбез для доработки портала | 4 | — | 1 | npm: `package.json`, `npm install`, `npm run build`. TypeScript: типы (string, number, interface, enum), компиляция (`tsc`). Express: `app.get()`, `app.post()`, `app.use()`, middleware. async/await: асинхронный код без callback hell. ✏️ Написать простой Express-роут |

**Схемы гл. 14:** (1) Git workflow: clone → branch → commit → push → PR → merge.  
**Таблицы гл. 14:** Команды Git, Команды VS Code, Типы данных Python, Коды ответа HTTP.

---

## Глава 15. Доработка Gateway (28 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 15.1 | Структура кода Gateway: карта модулей | 3 | 1 | 1 | 11 модулей: кто кого импортирует, граф зависимостей. `gateway.py` — главный: инициализация, создание FastAPI app (почему не Flask), lifespan (подключение к БД при старте). Маршруты: `/v1/models`, `/v1/chat/completions`, `/v1/embeddings`, `/health`, `/admin/*` |
| 15.2 | Добавление новой модели в каталог | 4 | 1 | 1 | Шаг 1: `catalog.yaml` — добавить модель (name, backend, model_path, max_tokens, tokens_per_ruble, tags). Шаг 2: `routing.py` — если нужен особый роутинг. Шаг 3: `kubectl create configmap gateway-catalog --from-file=catalog.yaml --dry-run=client -o yaml \| kubectl apply -f -`. Шаг 4: `kubectl rollout restart deploy/gateway`. ✏️ Добавить Qwen 2.5 Coder 14B |
| 15.3 | Изменение тарифов и лимитов | 3 | — | 1 | Где лежат: env `TOKEN_COST`, `RATE_LIMIT_RPM`, `RATE_LIMIT_TPM`. Как менять: `kubectl set env deploy/gateway TOKEN_COST=2` (мгновенно, без рестарта). Как проверять: `kubectl get deploy gateway -o yaml \| grep TOKEN_COST`. Rate Limiter: алгоритм в `admin.py`, Redis-ключи |
| 15.4 | Добавление DLP-правила | 5 | 1 | 1 | `dlp.py` — структура: список правил (pattern + description + action). Регэкспы для: паспорт РФ (`\d{4}\s?\d{6}`), ИНН (`\d{10}\|\d{12}`), СНИЛС (`\d{3}-\d{3}-\d{3}\s?\d{2}`). Действия: BLOCK, LOG, MASK (замена на `***`). ✏️ Добавить фильтр для номера банковской карты |
| 15.5 | Интеграция с SIEM | 4 | 1 | — | Что такое SIEM (Security Information and Event Management). Syslog: протокол, формат сообщений, RFC 5424. Отправка алертов: DLP-срабатывание → syslog → SIEM. Webhook: HTTP POST в систему мониторинга. ✏️ Настроить отправку алертов в syslog |
| 15.6 | Деплой изменений: от коммита до прода | 3 | — | 1 | Процесс: `git commit` → `git push` → `docker build` → `docker push` → `kubectl set image` → `kubectl rollout status`. Rollback: `kubectl rollout undo`. Проверка после деплоя: `curl /health`, `curl /v1/models`, дымовой тест |
| 15.7 | ✏️ Практикум: полный цикл доработки Gateway | 3 | — | — | Задача: добавить новую модель + изменить тариф + добавить DLP-правило → задеплоить → проверить |
| 15.8 | Отладка Gateway | 3 | 1 | — | `kubectl logs -f deploy/gateway`. `kubectl exec -it deploy/gateway -- python3 -c "..."`. PDB (Python Debugger): `import pdb; pdb.set_trace()`. Как включить DEBUG-логи: `LOG_LEVEL=DEBUG`. Типовые ошибки: `redis.exceptions.ConnectionError`, `psycopg2.OperationalError`, `KeyError: 'choices'` |

**Схемы гл. 15:** (1) Граф зависимостей модулей Gateway (11 узлов + внешние БД). (2) Добавление модели: flow от catalog.yaml до /v1/models. (3) DLP: запрос → цепочка фильтров → результат (pass/block/mask). (4) SIEM-интеграция: Gateway → syslog → SIEM. (5) Отладка: `kubectl logs` → `kubectl exec` → PDB.  
**Таблицы гл. 15:** Модули Gateway, DLP-правила, Переменные окружения, Команды деплоя.

---

## Глава 16. Доработка портала (22 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 16.1 | Структура кода портала | 3 | 1 | 1 | Карта: `server.ts` (роуты) → `policies.ts` (права) → `security.ts` (защита). Статика: `index.html`, `admin.html`. NPM-скрипты: `build`, `start`, `dev`. Зависимости: express, jsonwebtoken, cors, cookie-parser |
| 16.2 | Изменение фронтенда | 5 | 1 | 1 | CSS: где какие классы, как поменять тему. HTML: структура `index.html` (header, chat-container, message-list, input-area). JavaScript: SSE-клиент (EventSource), обработка `onmessage`, парсинг JSON, рендеринг Markdown. ✏️ Поменять цветовую схему на Astra Linux (синий/серый), добавить логотип |
| 16.3 | Добавление новой страницы | 4 | 1 | — | Шаг 1: `portal/static/my-page.html`. Шаг 2: роут в `server.ts` (`app.get('/my-page', ...)`). Шаг 3: ссылка в навигации. ✏️ Добавить страницу «Мои API-ключи» с таблицей ключей |
| 16.4 | Подключение OAuth-провайдера | 4 | — | 1 | Шаг 1: регистрация приложения в провайдере. Шаг 2: `server.ts` — passport-стратегия. Шаг 3: callback URL. Шаг 4: `policies.ts` — роль по умолчанию. ✏️ Добавить VK (ВКонтакте) |
| 16.5 | Безопасность фронтенда | 3 | — | 1 | XSS: sanitise HTML, `innerText` vs `innerHTML`. CSRF: SameSite cookies. CSP (Content-Security-Policy): заголовки, ограничение скриптов. Helmet: автоматические заголовки безопасности |
| 16.6 | ✏️ Практикум: полный цикл доработки портала | 3 | — | — | Задача: новая страница + новый OAuth + смена темы → `deploy.sh` → проверка в браузере |

**Схемы гл. 16:** (1) Карта роутов BFF (дерево /auth/*, /api/*, /admin/*). (2) index.html: структура DOM (аннотированная). (3) OAuth flow: пользователь → провайдер → callback → JWT.  
**Таблицы гл. 16:** Роуты BFF, CSS-классы, OAuth-провайдеры.

---

## Глава 17. Создание и обучение LoRA-адаптеров (16 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 17.1 | Теория LoRA — глубже | 4 | 1 | 1 | Математика (без формул): полные веса W (заморожены), LoRA: A×B (rank r << d). Почему rank=8 достаточно. Как применять: `output = Wx + (alpha/r) * BAx`. alpha=16: масштабирование. Целевые слои: q_proj, v_proj (attention). ✏️ «Ручной» расчёт числа параметров LoRA |
| 17.2 | Подготовка датасета | 4 | — | 1 | Формат: JSONL — `{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}`. Сколько нужно: 20-30 примеров (старт), 100+ (хорошо), 1000+ (отлично). Примеры: вопросы про Astra Linux, команды `apt`, конфигурация сети. ✏️ Подготовить датасет из 10 примеров |
| 17.3 | train_lora_14b.py — построчный разбор | 5 | 1 | 1 | Импорты: torch, transformers, peft (LoraConfig, get_peft_model), datasets, bitsandbytes. BitsAndBytesConfig: load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16. LoraConfig: r=8, lora_alpha=16, target_modules=["q_proj","v_proj"]. TrainingArguments: per_device_train_batch_size=1, gradient_accumulation_steps=4, num_train_epochs=3, learning_rate=2e-4. Trainer: train(), save_model(). Сохранение: `adapter_config.json` + `adapter_model.safetensors` |
| 17.4 | Запуск обучения в K8s | 3 | — | 1 | K8s Job vs Deployment. `fine-tuning/lora-job-14b.yaml` — построчно: image, command, resources (1 GPU, 32 GB RAM), volume (доступ к моделям и датасету). `kubectl logs -f job/lora-train-14b`. Время: ~10-30 минут на 100 примерах. Типовые ошибки: OOM (уменьшить batch size), CUDA out of memory (проверить 4-bit) |

**Схемы гл. 17:** (1) LoRA: полная матрица W + LoRA A×B. (2) Процесс QLoRA-обучения: датасет → токенизация → 4-bit модель → LoRA → сохранение.  
**Таблицы гл. 17:** Параметры LoRA, Этапы подготовки датасета, Ресурсы для обучения.

---

## Глава 18. CI/CD и автоматизация (16 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 18.1 | Что такое CI/CD | 2 | 1 | — | CI (Continuous Integration): автотесты при каждом коммите. CD (Continuous Delivery): автодеплой после тестов. GitHub Actions: `.github/workflows/`. Зачем: исключить человеческий фактор, ускорить цикл «написал → работает» |
| 18.2 | CI/CD для Gateway | 5 | 1 | 1 | `.github/workflows/deploy.yml` — построчный разбор: `on: push` → `jobs: build-and-deploy`. Шаг 1: checkout. Шаг 2: `docker build`. Шаг 3: `docker push` в ghcr.io. Шаг 4: `kubectl set image deploy/gateway gateway=ghcr.io/...:${{ github.sha }}`. Шаг 5: health-check (5 попыток). Шаг 6: rollback при провале. Шаг 7: Telegram-уведомление. GitHub Secrets: `VPS2_HOST`, `VPS2_SSH_KEY`, `TELEGRAM_BOT_TOKEN` |
| 18.3 | CI/CD для портала | 3 | — | 1 | `.github/workflows/deploy-portal.yml`: `npm ci` → `tsc` → `scp dist/ VPS2:/opt/aither/` → `ssh systemctl restart aither-bff`. Альтернатива: Docker-образ портала |
| 18.4 | Тестирование | 4 | — | 1 | Unit-тесты: pytest для Gateway (тест `deduct_tokens`), Jest для BFF (тест `/api/chat`). Интеграционные тесты: `curl` против живого Gateway. Нагрузочное тестирование: `hey -n 1000 -c 10`. ✏️ Написать unit-тест для `dlp.py` |
| 18.5 | ✏️ Практикум: настроить CI/CD | 2 | — | — | GitHub Secrets → push → автосборка → автодеплой → Telegram «✅ Deployed» |

**Схемы гл. 18:** (1) CI/CD pipeline: push → build → test → deploy → health-check. (2) GitHub Actions workflow: граф шагов.  
**Таблицы гл. 18:** GitHub Actions events, Секреты CI/CD, Инструменты тестирования.

---

*Конец Части III*
