# 03-admin-guide.md — Руководство администратора

## Веб-панель администратора

**URL:** `https://<HOST>:10443/admin.html`

Веб-панель даёт графический доступ к Gateway Admin API (задача #39 дорожной карты). Доступ защищён общим ключом `ADMIN_KEY` (HS256), одинаковым для Gateway и BFF.

### Вкладки панели

| Вкладка | Endpoint API | Назначение |
|---|---|---|
| 🫀 **Health** | `GET /api/v1/admin/health` | Состояние всех компонентов: Redis, PostgreSQL, vLLM-бэкенды, Reaper |
| 🧠 **Модели** | `GET /api/v1/admin/models` | Каталог моделей: health-статус, drain/undrain, max_tokens |
| 📊 **Очереди** | `GET /api/v1/admin/queues` | RPM/TPM/daily по организациям в реальном времени |
| 🏢 **Организации** | `GET /api/v1/admin/orgs/{id}` | Баланс, резерв, запросы/токены за сегодня, лимиты |
| ⏱️ **Reaper** | `GET /api/v1/admin/reaper` | Статус Reservation Reaper: последний запуск, возвращено токенов |
| 🗺️ **Статус 5а** | — | Сводка всех 9 задач этапа 5а: что в панели, что во внешних системах |

### Действия администратора через веб-панель

**Слив модели из ротации (Drain):**
На вкладке «Модели» → кнопка 🚫 Drain. Запросы перестанут маршрутизироваться на модель. Состояние сохраняется в Redis (`admin:drained_models`).

**Возврат модели (Undrain):**
Кнопка ↩ Undrain. Модель возвращается в ротацию.

**Просмотр организации:**
Вкладка «Организации» → вставить UUID → показывает баланс, резерв, запросы/токены за сегодня, текущие RPM/TPM и лимиты тарифа.

### Внешние системы (из веб-панели — ссылки)

| Система | URL | Задача 5а |
|---|---|---|
| **Grafana** | `https://grafana.130.17.1.90.nip.io` | #40 TTFT-мониторинг |
| **SIEM (syslog)** | `10.129.13.78:514` (CEF) | #35 SIEM-интеграция |
| **Security Egress** | `/var/log/aither/egress.log` на n8 | #34 Security Gateway Egress |
| **LLM-Wiki (RAG)** | ChromaDB на n8, API через Gateway | #37 Гибридный RAG |
| **Vault** | Внешний HSM / Hashicorp Vault | #36 Vault-интеграция |

### Конфигурация админ-доступа

Ключ задаётся в `.env` BFF (VPS2) **и** в `ADMIN_KEY` env Gateway (K8s):
```bash
ADMIN_KEY=hs256-shared-secret-key-for-admin-api-2026
```

Без этого ключа веб-панель будет получать 401/403 от Gateway.

### Устройство прокси

```
Браузер → https://fb1.spb.ru:10443/admin.html (VPS1 nginx)
       → VPS2 nginx (:80) → статика /usr/share/nginx/html/admin.html
       → JS вызывает /api/v1/admin/* → VPS2 nginx → BFF (:3000)
       → BFF добавляет X-Admin-Key → VPS1 nginx → Gateway K8s (:30900)
```

---

## Управление платформой (CLI)

### Проверка состояния
```bash
bash scripts/health-check.sh
```

### Просмотр логов
```bash
kubectl logs -n aither deploy/gateway --tail=100 -f
kubectl logs -n aither deploy/vllm-qwen --tail=100 -f
```

### Перезапуск сервиса
```bash
kubectl rollout restart deploy/gateway -n aither
kubectl rollout restart deploy/vllm-qwen -n aither
```

### Резервное копирование
```bash
bash scripts/backup.sh
# → /backup/aither/YYYY-MM-DD_HHMM/
```

### Восстановление
```bash
bash scripts/restore.sh /backup/aither/2026-07-11_1200
```

### Ротация ключей
```bash
bash scripts/rotate-keys.sh <org_id>
```

### Сбор логов для диагностики
```bash
bash scripts/collect-logs.sh
# → /tmp/aither-logs-YYYYMMDD-HHMM/
```

## Управление пользователями

### Просмотр организаций
```sql
SELECT id, name, invite_code FROM organizations;
```

### Назначение администратора
```sql
UPDATE users SET role='admin' WHERE email='user@example.com';
```

### Просмотр использования
```sql
SELECT org_id, SUM(amount) as total_spent, COUNT(*) as requests
FROM billing_ledger
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY org_id ORDER BY total_spent DESC;
```

## Мониторинг

- **Grafana:** http://GRAFANA_HOST:30300 (admin/admin)
- **Prometheus:** http://PROMETHEUS_HOST:30909
- **Gateway метрики:** http://GATEWAY_HOST:30900/metrics

## Обновление моделей

1. Добавить модель в `configs/gateway/config.yaml.template`
2. Создать vLLM deployment в `k8s/`
3. `kubectl apply -f k8s/vllm-new/`
4. Обновить Gateway ConfigMap: `kubectl create configmap gateway-config --from-file=catalog.yaml -n aither --dry-run=client -o yaml | kubectl apply -f -`
5. `kubectl rollout restart deploy/gateway -n aither`
