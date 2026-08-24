# Aither — Документация для участников Closed Beta

**Версия:** CB-WEBUI-03
**Дата:** 24 августа 2026
**Статус:** Closed Beta

---

## Содержание комплекта

| № | Документ | Описание | Кому |
|---|---|---|---|
| 01 | [WELCOME](01_WELCOME.md) | Приветствие, цели тестирования, что ожидается | Всем |
| 02 | [QUICK START](02_QUICK_START.md) | Быстрый старт за 5 минут через Web UI | Всем |
| 03 | [USER GUIDE](03_USER_GUIDE.md) | Полное руководство пользователя (Web UI + API) | Всем |
| 04 | [API GUIDE](04_API_GUIDE.md) | Описание API с примерами curl, Python, PowerShell | Разработчикам |
| 05 | [TEST ASSIGNMENT](05_TEST_ASSIGNMENT.md) | Обязательные тестовые задания (Web UI) | Всем |
| 06 | [BUG REPORT TEMPLATE](06_BUG_REPORT_TEMPLATE.md) | Форма сообщения об ошибке | Всем |
| 07 | [FEEDBACK FORM](07_USER_FEEDBACK_FORM.md) | Форма обратной связи | Всем |
| 08 | [FAQ](08_FAQ.md) | Часто задаваемые вопросы (35+) | Всем |
| 09 | [SECURITY RULES](09_SECURITY_RULES.md) | Правила безопасности | Всем |
| 10 | [KNOWN LIMITATIONS](10_KNOWN_LIMITATIONS.md) | Известные ограничения | Всем |
| 11 | [ACCEPTANCE CHECKLIST](11_ACCEPTANCE_CHECKLIST.md) | Чек-лист участника | Всем |
| 12 | [OWNER HANDOVER](12_OWNER_HANDOVER.md) | Инструкция для владельца проекта | Owner |
| 13 | [WEB UI GUIDE](13_WEB_UI_GUIDE.md) | Полное руководство по Web UI | Всем |
| 14 | [API KEY USER GUIDE](14_API_KEY_USER_GUIDE.md) | Создание, использование и отзыв API-ключей через Web UI | Всем |
| 15 | [DUAL ZONE ACCESS GUIDE](15_DUAL_ZONE_ACCESS_GUIDE.md) | Доступ через Internet и Test Zone | Всем |
| 16 | [AI AGENT CONNECTION PRIMER](16_AI_AGENT_CONNECTION_PRIMER.md) | Подключение AI-агентов через токены | Разработчикам |
| 17 | [MODEL USAGE GUIDE](17_MODEL_USAGE_GUIDE.md) | Работа с моделями — активный каталог, выбор модели, API-ключи | Всем |

---

## 🌐 Web UI — основной интерфейс

**Aither теперь имеет Web UI!** Это основной способ взаимодействия с системой:

| Зона | URL | Доступ |
|---|---|---|
| **Internet** | `https://fb1.spb.ru:10443/` | Открытый (HTTPS, доверенный сертификат Let's Encrypt) |
| **Test Zone** | `http://10.129.13.78:30080/` | Внутренняя сеть / VPN |

Через Web UI вы можете:
- 💬 Вести чат с моделями (qwen3-32b и qwen3.8-27b)
- 🔑 Создавать и управлять API-ключами (префикс `aither_`)
- 🤖 Подключать AI-агентов через токены
- 📊 Видеть статус системы и моделей

**API также доступен** для разработчиков и автоматизации — см. [API GUIDE](04_API_GUIDE.md).

---

## PDF-версии

| PDF | Содержание |
|---|---|
| `pdf/aither-full-guide.pdf` | Полное руководство (все документы) |
| `pdf/aither-quick-start.pdf` | Только Quick Start |
| `pdf/aither-test-assignment.pdf` | Только Test Assignment |

---

## Как использовать

1. Начните с **[01_WELCOME](01_WELCOME.md)** — поймите, зачем вы здесь
2. Откройте **[Web UI](https://fb1.spb.ru:10443/)** — основной интерфейс
3. Выполните **[02_QUICK_START](02_QUICK_START.md)** — первый диалог за 5 минут
4. Изучите **[13_WEB_UI_GUIDE](13_WEB_UI_GUIDE.md)** — полные возможности Web UI
5. Выполните **[05_TEST_ASSIGNMENT](05_TEST_ASSIGNMENT.md)** — обязательные задания
6. Заполните **[07_FEEDBACK_FORM](07_USER_FEEDBACK_FORM.md)** — обратная связь
7. При ошибках — **[06_BUG_REPORT_TEMPLATE](06_BUG_REPORT_TEMPLATE.md)**

---

## Контакты

- **Поддержка:** через установленный канал связи с владельцем проекта
- **Срочные проблемы:** немедленно сообщать владельцу проекта
- **API-ключ утерян/скомпрометирован:** отозвать в Web UI, запросить новый через владельца

---

## Версия документов

| Версия | Дата | Изменения |
|---|---|---|
| 1.0 | 25.07.2026 | Первоначальный выпуск для Closed Beta |
| 1.1 | 25.07.2026 | CB-WEBUI-03: Web UI как основной интерфейс, новые документы 13–16, переход на `aither_`-ключи, сертификат Let's Encrypt |
| 1.2 | 24.08.2026 | Актуализация модельного каталога (`qwen3-32b`, `qwen3.8-27b`), API-ключей `aither_`, URL портала, всех документов под текущий production contract |
