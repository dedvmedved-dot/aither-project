# CB-WEBUI-01 — Матрица приёмочных критериев

## Легенда

| Символ | Значение |
|--------|----------|
| ✅ | Пройдено — полностью соответствует критерию |

---

## Функциональные критерии

| ID | Критерий | Ожидаемый результат | Статус | Примечание |
|----|----------|---------------------|--------|------------|
| F-01 | Доступ к Web UI через Интернет | Страница входа загружается по `https://fb1.spb.ru:443/` | ✅ | SSL валиден |
| F-02 | Доступ к Web UI в тестовой зоне | Страница входа загружается по `http://10.129.13.78:30080/` | ✅ | NodePort |
| F-03 | Аутентификация через BFF | Успешный вход с валидными учётными данными | ✅ | Сессионная cookie |
| F-04 | Отказ при неверных учётных данных | Сообщение об ошибке, доступ не предоставлен | ✅ | Без утечки информации |
| F-05 | Выход из системы | Очистка сессии, редирект на страницу входа | ✅ | Токен и localStorage очищены |
| F-06 | Чат с qwen-14b | Диалоговый ответ на русском языке | ✅ | Chat completions |
| F-07 | Чат с qwen-32b-base | Продолжение текста на русском языке | ✅ | Completion |
| F-08 | Переключение модели | Dropdown меняет модель, обновляется подсказка | ✅ | Зелёный/жёлтый индикатор |
| F-09 | Автоопределение зоны (Интернет) | Бейдж «INTERNET» при fb1.spb.ru | ✅ | zone-internet |
| F-10 | Автоопределение зоны (Тестовая) | Бейдж «TEST ZONE» при 10.129.13.78 | ✅ | zone-test |
| F-11 | Русская локализация | Весь интерфейс на русском языке | ✅ | Все метки, ошибки, подсказки |
| F-12 | Копирование ответа | Кнопка копирует текст в буфер обмена | ✅ | Clipboard API |
| F-13 | Панель управления | Карточки: аккаунт, система, модели, действия | ✅ | Данные загружаются |
| F-14 | Страница профиля | ID, username, роль, зона | ✅ | Данные отображаются |
| F-15 | Страница статуса | Статус, версия, Redis, Rate Limit, Auth, Зона | ✅ | Данные загружаются |
| F-16 | Очистка истории чата | Сброс chatHistory, системное приветствие | ✅ | Кнопка «Очистить» |
| F-17 | Многооборотный диалог (14B) | Контекст до 20 сообщений | ✅ | chatHistory.slice(-20) |
| F-18 | Создание API-ключа | Модальное окно, выбор моделей, получение ключа | ✅ | Фронтенд: форма + POST /api/v1/tokens |
| F-19 | Отзыв API-ключа | Подтверждение → DELETE /api/v1/tokens/{id} | ✅ | Кнопка «Отозвать» |
| F-20 | Просмотр API-ключей | Таблица с названием, префиксом, датой, статусом | ✅ | Фронтенд реализован: GET /api/v1/tokens, таблица, обработка ошибок |
| F-21 | API key one-time secret | Полный secret показан один раз, после F5 скрыт | ✅ | R3: test_beta01_full (step 7-12), test_r3_identities.py |\n| F-22 | API key list after refresh | Ключ остаётся в списке после F5 | ✅ | R3: test_beta01_full (step 13), GET /api/v1/tokens |\n| F-23 | Key test для 14B | API test: /models + /chat с 14B ключом | ✅ | R3: test_beta01_full (step 14-15), direct API call |\n| F-24 | Key test для 32B | API test: /chat с 32B ключом | ✅ | R3: test_beta01_full (step 16-17), direct API call |\n| F-25 | Revoked key denied | Отозванный ключ возвращает 401/403 | ✅ | R3: test_beta01_full (step 24-25), HTTP assertion |\n| F-26 | BETA-USER-01 isolation | Видит только свои ключи | ✅ | R3: test_beta01_full — own tokens only via BFF owner field |\n| F-27 | BETA-USER-02 isolation | Не видит ключи BETA-USER-01 | ✅ | R3: test_beta02_isolation — foreign token 403/404 |\n| F-28 | Owner RBAC | Owner не видит чужие секреты, ограничен политикой | ✅ | R3: test_owner_rbac — no athr_ secrets in DOM |\n| F-29 | Agent key from Web UI | Ключ с назначением Agent создан через браузер | ✅ | R3: test_beta01_full (step 20-21), test_agent_api |\n| F-30 | Internet full browser cycle | BETA-USER-01 Internet (Chromium + Firefox) | ✅ | R3: test_r3_identities.py::TestBETA01 + R2: 4/4 PASS |\n| F-31 | Test Zone full browser cycle | BETA-USER-01 Test Zone (Chromium + Firefox) | ✅ | R3: test_r3_identities.py::TestBETA01 + R2: 4/4 PASS |

---

## Нефункциональные критерии

| ID | Критерий | Ожидаемый результат | Статус | Примечание |
|----|----------|---------------------|--------|------------|
| N-01 | Время загрузки страницы | < 3 секунд | ✅ | Статический контент через nginx (~30 KB) |
| N-02 | Время ответа 14B | < 10 секунд | ✅ | ~4 секунды |
| N-03 | Время ответа 32B | < 15 секунд | ✅ | ~5 секунд |
| N-04 | Доступность | Web UI доступен в обеих зонах | ✅ | K8s + nginx обеспечивают |
| N-05 | Совместимость с браузерами | Chromium + Firefox | ✅ | Протестировано: Chromium + Firefox — полный E2E в обоих браузерах |
| N-06 | Размер страницы | < 500 KB (без кеша) | ✅ | Статика: ~30 KB |
| N-07 | Количество HTTP-запросов | < 10 на загрузку страницы | ✅ | 3 запроса (HTML, CSS, JS) |

---

## Критерии безопасности

| ID | Критерий | Ожидаемый результат | Статус | Примечание |
|----|----------|---------------------|--------|------------|
| S-01 | HTTPS для Интернет-зоны | SSL/TLS на портах 443, 10443 | ✅ | Сертификат на VPS2 |
| S-02 | Защита от XSS | Пользовательский ввод экранируется | ✅ | Функция escHtml() |
| S-03 | CSRF-защита | same-origin credentials | ✅ | credentials: 'same-origin' |
| S-04 | Безопасное хранение токена | localStorage + сессионная cookie | ✅ | Токен не в URL |
| S-05 | Безопасный выход | Очистка всех сессионных данных | ✅ | Токен, user, история |
| S-06 | Защита страниц без входа | Скрытие защищённых страниц | ✅ | display:none + checkSession |
| S-07 | Обработка ошибок без утечки | Без деталей системы в сообщениях | ✅ | Пользовательские сообщения |

---

## Критерии развёртывания

| ID | Критерий | Ожидаемый результат | Статус | Примечание |
|----|----------|---------------------|--------|------------|
| D-01 | K8s ConfigMap обновлён | aither-portal-frontend-config обновлён | ✅ | kubectl apply |
| D-02 | Deployment перезапущен | Pod с новой конфигурацией | ✅ | kubectl rollout restart |
| D-03 | Nginx на VPS2 обновлён | /root/nginx-failover.conf применён | ✅ | nginx -s reload |
| D-04 | Маршрутизация `/` → k8s | Прокси работает | ✅ | http://10.129.13.78:30080 |
| D-05 | Маршрутизация `/api/` → BFF | Прокси работает | ✅ | Аутентификация и API |
| D-06 | Маршрутизация `/v1/` → AI Platform | Прокси работает | ✅ | upstream ai_platform |
| D-07 | Порт 10443 (32B) | Доступен | ✅ | Выделенный порт |

---

## Итоговая статистика

### По категориям

| Категория | Всего | Пройдено | Частично | Не пройдено |
|-----------|-------|----------|----------|-------------|
| Функциональные (F) | 31 | 31 | 0 | 0 |
| Нефункциональные (N) | 7 | 7 | 0 | 0 |
| Безопасность (S) | 7 | 7 | 0 | 0 |
| Развёртывание (D) | 7 | 7 | 0 | 0 |
| **Всего** | **52** | **52** | **0** | **0** |

### Процент прохождения

```
Пройдено полностью:  52/52 = 100%
Частично:              0/52 =   0%
Не пройдено:           0/52 =   0%
```

## Заключение приёмочной комиссии

CB-WEBUI-01 **принимается** без оговорок. Все 52 приёмочных критерия пройдены полностью.

**Решение:** ПРИНЯТО ✅
**Дата приёмки:** 2026-07-25
**Подпись:** DevOps-команда Aither

---

## TRACK-A-R3.1 — Reproducibility Verification (2026-07-25)

TRACK-A-R3.1 verification chain:

Implementation commit:
`1ed95001ffa817fb5c774a2ed5ebf58d810be759`

Tested commit:
`1ed95001ffa817fb5c774a2ed5ebf58d810be759`

Evidence commit:
`bb224c4b01a8602252f9b154dd9b650715259cc6`

Final documentation commit:
`<set at next push>`

Test source SHA-256:
`963f6df157c4ffb265d83f82a2978bca1e7f45217bf5c1dcfbdc165fa62e85e1`

Test source unchanged between tested and evidence commits: YES

| Run | Tests | Result | Exit Code | JUnit XML |
|-----|-------|--------|-----------|-----------|
| Individual BETA01 | 4/4 | ✅ PASS | 0 | beta01.xml |
| Individual BETA02 | 2/2 | ✅ PASS | 0 | beta02.xml |
| Individual OWNER01 | 2/2 | ✅ PASS | 0 | owner.xml |
| Individual Agent | 2/2 | ✅ PASS | 0 | agent.xml |
| Full Run 1 | 10/10 | ✅ PASS | 0 | full-r3-run-1.xml |
| Full Run 2 | 10/10 | ✅ PASS | 0 | full-r3-run-2.xml |
| Fresh Clone | 10/10 | ✅ PASS | 0 | fresh-clone-r3.xml |
| **Combined** | **40/40** | ✅ | **0** | |

| Verification | Result |
|--------------|--------|
| closeModal in test | 0 references |
| Test file hash match (working-tree vs HEAD) | YES |
| Working tree CLEAN | YES |
| Git local/remote match | YES |
| No admin substitution | YES |
| Internet 32B stability (10/10) | ✅ |
| Security evidence (7/7) | ✅ |

### Test Sources (F-21—F-31)

All F-21 through F-31 criteria verified by `tests/e2e/test_r3_identities.py`:
- `TestBETA01::test_full_scenario[zone-browser]` — 4 parametrized tests
- `TestBETA02::test_isolation[zone]` — 2 parametrized tests
- `TestOWNER01::test_rbac[zone]` — 2 parametrized tests
- `TestAgent::test_agent_api[zone]` — 2 parametrized tests

Evidence: `evidence/track-a-r3.1/` (full inventory in 00_SUMMARY.md)
