# Приложения и Лабораторный практикум

**Документ:** `04-appendices-labs.md` · ~95 стр. · 6 схем · 5 таблиц · 14 ЛР

---

## Приложение A. Глоссарий (10 стр.)

Алфавитный указатель всех терминов с переводом, расшифровкой и ссылкой на главу где explained.

Формат: **Термин** (EN: English) — определение. [→ Гл. X]

Ожидаемый объём: ~200 терминов.

---

## Приложение B. Шпаргалка по командам (6 стр.)

| Инструмент | Команды |
|---|---|
| **kubectl** | `get pods/nodes/services/deployments/hpa`, `describe`, `logs`, `exec -it`, `apply -f`, `delete`, `rollout restart/undo/status`, `set image`, `create secret/configmap`, `port-forward`, `top`, `cordon/uncordon/drain` |
| **docker** | `build -t`, `run -d -p -v --name`, `ps`, `logs -f`, `exec -it`, `stop/start/restart`, `rm/rmi`, `save/load`, `tag`, `push/pull` |
| **systemctl** | `start/stop/restart`, `status`, `enable/disable`, `daemon-reload`, `list-units` |
| **journalctl** | `-u <unit>`, `-f`, `-p 3`, `--since "..."`, `--no-pager`, `-o short-iso` |
| **git** | `clone`, `status`, `add`, `commit -m`, `push`, `pull`, `log --oneline`, `branch`, `checkout`, `merge` |
| **curl** | `-X POST`, `-H "..."`, `-d '{...}'`, `-v`, `-s -o /dev/null -w "%{http_code}"` |
| **ssh** | `-L <local>:<remote>` (туннель), `-i <key>`, `-o StrictHostKeyChecking=no` |

---

## Приложение C. Типовые неисправности (10 стр.)

Каждый кейс: симптом → диагностика → причина → решение → профилактика.

| # | Кейс | Стр. |
|---|---|---|
| C.1 | Pod CrashLoopBackOff | 1 |
| C.2 | Pod OOMKilled | 1 |
| C.3 | ImagePullBackOff / ErrImagePull | 1 |
| C.4 | CreateContainerConfigError | 1 |
| C.5 | GPU не видна (`nvidia.com/gpu=0`) | 1 |
| C.6 | 502 Bad Gateway (BFF → Gateway) | 1 |
| C.7 | 429 Too Many Requests (Rate Limit) | 0.5 |
| C.8 | vLLM: CUDA out of memory | 1 |
| C.9 | PostgreSQL: connection refused | 0.5 |
| C.10 | Redis: NOAUTH / connection refused | 0.5 |
| C.11 | `toLocaleString` is undefined (фронтенд) | 0.5 |
| C.12 | WireGuard: handshake failed | 0.5 |
| C.13 | Сертификат TLS просрочен | 0.5 |

---

## Приложение D. Список портов и сервисов (3 стр.)

| Порт | Сервис | Узел | Протокол | Описание |
|---|---|---|---|---|
| 10443 | nginx (HTTPS) | VPS1 | TCP+TLS | Входная точка |
| 30900 | nginx → Gateway NP | VPS1→n7 | TCP | Прокси в K8s |
| 80 | nginx (портал) | VPS2 | TCP | Статика |
| 3000 | BFF (Node.js) | VPS2 | TCP | API портала |
| 5432 | PostgreSQL (Portal) | VPS2 | TCP | БД портала |
| 8080 | Gateway (ClusterIP) | K8s | TCP | API Gateway |
| 32293 | vLLM 14B (NodePort) | n8 | TCP | Инференс 14B |
| 32294 | vLLM 32B (NodePort) | n7 | TCP | Инференс 32B |
| 8000 | vLLM (ClusterIP) | K8s | TCP | Внутренний |
| 30300 | Grafana (NodePort) | n7 | TCP | Дашборды |
| 6379 | Redis | K8s (n8) | TCP | Rate Limiter |
| 31113 | PostgreSQL (Gateway) | K8s (n8) | TCP | Биллинг |
| 8000 | ChromaDB | K8s (n8) | TCP | RAG |
| 9443 | BMC n7 | n7 | TCP | Управление |
| 19443 | socat BMC n7 | VPS2 | TCP | Проброс |
| 51820 | WireGuard | VPS1, VPS2 | UDP | Туннель |

---

## Приложение E. Полная схема потоков данных (8 стр., 4 схемы)

1. **Поток чат-запроса:** Браузер → :10443 → nginx VPS1 → VPS2 :3000 (BFF) → VPS1 :30900 → Gateway → vLLM → ответ → ... → браузер (стриминг SSE)
2. **Поток биллинга:** Gateway → Redis (проверка лимита) → vLLM (инференс) → Gateway (парсинг usage) → PostgreSQL (`UPDATE balance`)
3. **Поток OAuth-авторизации:** Браузер → BFF → Провайдер (GitHub/Google/Яндекс) → callback → BFF → JWT → cookie
4. **Поток деплоя:** Git push → GitHub Actions → docker build → docker push → kubectl set image → health check → Telegram

Каждая схема — на отдельной странице, с пояснениями.

---

## Приложение F. Карта репозитория (5 стр.)

Полное дерево файлов с аннотациями: что за файл, зачем нужен, где используется.

---

## Приложение G. Быстрый старт — памятка (2 стр.)

1 страница = 1 ламинированный лист. 10 шагов от нуля до работающей системы:
1. Установить Astra Linux (Kickstart)
2. Настроить сеть
3. `make offline-load`
4. `make deploy`
5–10. Проверки

---

## Приложение H. Чек-лист приёмо-сдаточных испытаний (4 стр.)

Формальная таблица: пункт → методика проверки → ожидаемый результат → фактический → подпись.

---

# Лабораторный практикум (14 работ, ~46 стр., ~40 часов)

Каждая ЛР: цель, исходные данные, порядок выполнения, контрольные вопросы, форма отчёта.

| # | Лабораторная работа | Стр. | Часы | Главы |
|---|---|---|---|---|
| ЛР 1 | Linux: командная строка, файлы, процессы, права | 3 | 2 | 1.2, 1.5 |
| ЛР 2 | Установка Astra Linux через Kickstart на ВМ | 3 | 3 | 8.2 |
| ЛР 3 | Docker: Dockerfile, сборка, запуск, Compose | 4 | 3 | 2.2–2.4 |
| ЛР 4 | Kubernetes: мини-кластер из 2 узлов (kubeadm) | 4 | 4 | 3.2–3.5, 9.1–9.4 |
| ЛР 5 | Деплой vLLM 14B: манифест, проверка, первый запрос | 3 | 2 | 5.4, 10.3 |
| ЛР 6 | Деплой Gateway: сборка образа, ConfigMap, Secret, проверка биллинга | 4 | 3 | 11.1–11.5 |
| ЛР 7 | Деплой портала: VPS2, nginx, BFF, PostgreSQL, сквозной тест | 4 | 3 | 13.1–13.3 |
| ЛР 8 | Развёртывание в закрытом контуре: полный цикл air-gap | 5 | 4 | 12.1–12.7 |
| ЛР 9 | Мониторинг: Grafana-дашборды, логи, алерты | 3 | 2 | 13.1–13.3 |
| ЛР 10 | Инцидент: поиск и устранение неисправности | 3 | 2 | Прил. C |
| ЛР 11 | Резервное копирование и восстановление | 2 | 2 | 13.4 |
| ЛР 12 | Доработка Gateway: новая модель + тариф + DLP + деплой | 3 | 3 | 15.2–15.6 |
| ЛР 13 | Доработка портала: новая страница + OAuth + тема | 3 | 3 | 16.2–16.4 |
| ЛР 14 | LoRA: подготовка датасета, обучение, подключение к vLLM | 3 | 3 | 17.2–17.4 |
| **Итого** | | **~47** | **~39** | |

---

*Конец Приложений и Лабораторного практикума*
