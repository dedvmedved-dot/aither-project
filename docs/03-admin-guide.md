# Aither Platform — Руководство администратора

**Дата:** 07.07.2026
**Версия:** v2.0

---

## Оглавление

1. [Обзор системы](#1-обзор-системы)
2. [Развёртывание с нуля](#2-развёртывание-с-нуля)
3. [Админ-панель (11 вкладок)](#3-админ-панель-11-вкладок)
4. [CLI-команды](#4-cli-команды)
5. [Бэкап и восстановление](#5-бэкап-и-восстановление)
6. [Мониторинг (Grafana + Prometheus)](#6-мониторинг-grafana--prometheus)
7. [RAG-администрирование](#7-rag-администрирование)
8. [vLLM-управление](#8-vllm-управление)
9. [Безопасность](#9-безопасность)
10. [Сеть и связность](#10-сеть-и-связность)
11. [CI/CD pipeline](#11-cicd-pipeline)
12. [Устранение неполадок](#12-устранение-неполадок)
13. [Аварийные процедуры](#13-аварийные-процедуры)
14. [Схема БД](#14-схема-бд)

---

## 1. Обзор системы

### Физическая топология

```
VPS1 (170.168.91.95)  ── nginx :10443, Hermes, K8s follower
  │ WireGuard 10.100.0.0/24
VPS2 (130.17.1.90)     ── Портал (BFF :3000, nginx :80), PostgreSQL, WireGuard
  │ VPN
  ├─ Cisco815 (V1) ── 10.129.11.0/24
  └─ HuaweiHP (V2) ── VLAN 308, 10.129.13.0/24
       ├─ n8-gpu (40.51) ── control-plane, Gateway, PG, Redis, vLLM 14B
       └─ n7-gpu (40.50) ── worker, vLLM 32B, Coder-14B, ChromaDB, Prometheus

VPS3 (89.127.217.88)   ── Резервный портал + Hermes
```

### Компоненты и их расположение

| Компонент | Хост | Порт | Технология |
|---|---|---|---|
| nginx (входная точка) | VPS1 | 10443 | nginx, HTTPS |
| BFF (бэкенд портала) | VPS2 | 3000 | Node.js/Fastify, systemd |
| nginx (статика) | VPS2 | 80 | Docker |
| PostgreSQL (портал) | VPS2 | 5432 | Docker, 16-alpine |
| Gateway | n8 (K8s) | 30900 | Python/FastAPI, 15 модулей |
| PostgreSQL (биллинг) | n8 (K8s) | 5432 | 16 |
| Redis (rate limit) | n8 (K8s) | 6379 | 7-alpine |
| vLLM 14B | n8 (K8s) | 32293 | Qwen2.5-14B, TP=2 |
| vLLM 32B | n7 (K8s) | 32294 | Qwen2.5-32B, TP=2, GPTQ |
| vLLM Coder-14B | n7 (K8s) | — | Qwen2.5-Coder-14B |
| chroma-proxy | n7 (K8s) | 9000 | Python, all-MiniLM-L6-v2 |
| ChromaDB | n7 (K8s) | 8000 | 0.5.23, in-memory (⚠️) |
| Prometheus | n8 (K8s) | 30909 | — |
| Grafana | n8 (K8s) | 30300 | fb1.spb.ru:10443/grafana/ |
| BFF (резерв) | VPS3 | 3000 | systemd |

### URL для доступа

| Ресурс | URL |
|---|---|
| Портал | `https://fb1.spb.ru:10443` |
| Админ-панель | `https://fb1.spb.ru:10443/admin.html` |
| API Gateway | `https://fb1.spb.ru:10443/v1/chat/completions` |
| Grafana | `https://fb1.spb.ru:10443/grafana/` |
| Swagger/OpenAPI | `https://fb1.spb.ru:10443/v1/openapi.json` |

---

## 2. Развёртывание с нуля

### Предварительные требования

- **VPS1:** Ubuntu 22.04+, nginx, Hermes Agent, WireGuard
- **VPS2:** Ubuntu 22.04+, Docker, Node.js 20+, WireGuard
- **n8-gpu (40.51):** Astra Linux 1.8, NVIDIA driver 570, 2×RTX6000
- **n7-gpu (40.50):** Astra Linux 1.8, NVIDIA driver 570, 2×RTX6000

### Порядок развёртывания

#### Шаг 1: WireGuard VPS1 ↔ VPS2

```bash
# VPS1
ip link add wg0 type wireguard
ip addr add 10.100.0.1/24 dev wg0
wg set wg0 private-key /etc/wireguard/private.key \
  peer <VPS2_PUBKEY> allowed-ips 10.100.0.2/32 endpoint 130.17.1.90:51820
ip link set wg0 up

# VPS2
ip link add wg0 type wireguard
ip addr add 10.100.0.2/24 dev wg0
wg set wg0 private-key /etc/wireguard/private.key \
  peer <VPS1_PUBKEY> allowed-ips 10.100.0.1/32 endpoint 170.168.91.95:51820
ip link set wg0 up
```

#### Шаг 2: K8s на GPU-узлах

```bash
# n8 (control-plane)
kubeadm init --pod-network-cidr=10.244.0.0/16
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/gpu-operator/main/deploy/v24.6.0/nvidia-operator.yaml

# n7 (worker)
kubeadm join <n8-ip>:6443 --token <token> --discovery-token-ca-cert-hash <hash>
kubectl label node bootsman-k8s-clnt01-n7-gpu node-role.kubernetes.io/worker=
```

#### Шаг 3: Портал на VPS2

```bash
cd /root/aither-project/portal
npm install && npm run build

# Создать .env
cat > .env << 'EOF'
PORT=3000
PGHOST=127.0.0.1
PGPORT=5432
PGUSER=portal
PGPASSWORD=portal
PGDATABASE=portal
JWT_SECRET=<random 64 chars>
CORE_API=http://<vps1-ip>:30900
ADMIN_KEY=<random 32 chars>
# OAuth ключи
GITHUB_CLIENT_ID=...
GOOGLE_CLIENT_ID=...
YANDEX_CLIENT_ID=...
EOF

# Запуск
cp configs/vps2/aither-bff.service /etc/systemd/system/
systemctl enable aither-bff --now
```

#### Шаг 4: Gateway и инфраструктура K8s

```bash
kubectl apply -f k8s/postgres/deployment.yaml
kubectl apply -f k8s/redis/deployment.yaml
kubectl apply -f k8s/gateway/deployment.yaml
kubectl apply -f k8s/gateway/service.yaml
kubectl apply -f k8s/vllm-14b/deployment.yaml
kubectl apply -f k8s/vllm-32b/deployment.yaml
kubectl apply -f k8s/chroma-proxy.yaml
kubectl apply -f k8s/hpa/
kubectl apply -f k8s/monitoring/
```

#### Шаг 5: Миграции БД

```bash
# На VPS2
docker exec aither-portal-portal-db-1 psql -U portal -d portal \
  -f /root/aither-project/db/migrations/007_subscription_tiers.sql
```

#### Шаг 6: RAG-инициализация

```bash
kubectl exec deploy/chroma-proxy -- python3 /chroma/ingest_textbook.py
```

#### Шаг 7: Проверка

```bash
curl https://fb1.spb.ru:10443/api/v1/status
# {"version":"0.5.0","orgs":6,"users":5}
```

---

## 3. Админ-панель (11 вкладок)

URL: `https://fb1.spb.ru:10443/admin.html`
Аутентификация: JWT-токен администратора (cookie) или `X-Admin-Key`.

| # | Вкладка | Данные от | Назначение |
|---|---|---|---|
| 1 | 🫀 **Health** | Gateway | Статус всех компонентов |
| 2 | 🧠 **Модели** | Gateway | Каталог vLLM-моделей, Drain/Undrain |
| 3 | 📊 **Очереди** | Gateway | Rate limits по организациям |
| 4 | ⏱️ **Reaper** | Gateway | Авто-возврат резервирований (>5 мин) |
| 5 | 🏢 **Организации** | BFF | CRUD: список, детали, каскадное удаление |
| 6 | 👥 **Пользователи** | BFF | CRUD: список, роли, организации, удаление |
| 7 | 🔑 **API-ключи** | BFF | Просмотр, отзыв |
| 8 | 💰 **Токены** | Gateway | Начисление/списание токенов |
| 9 | ⚙️ **Тарифы** | BFF | 4 тарифа (Free/Standard/VIP/Enterprise), смена |
| 10 | 🔧 **Настройки** | BFF | LDAP-конфигурация (9 полей) |
| 11 | 🗺️ **Статус 5а** | Статическая | Дорожная карта этапа 5а |

### Управление организациями

**Просмотр:** 🏢 → таблица (имя, баланс, тариф, участники, ключи)
**Детали:** 👁 → карточка + список участников
**Удаление:** 🗑 → каскадное (участники → ключи → биллинг → платежи → политики → организация)

### Управление пользователями

**Просмотр:** 👥 → таблица (имя, email, OAuth-провайдер, кол-во orgs)
**Организации:** 🏢 → список orgs пользователя (роль, тариф)
**Роли:** выпадающий список → owner / billing_admin / developer / viewer
**Удаление:** 🗑 → исключение из orgs + удаление (чаты сохраняются)

### Управление тарифами

| Тариф | RPM | TPM | Daily | Цена | RAG | Модели |
|---|---|---|---|---|---|---|
| Free | 10 | 10K | 100 | 0 ₽ | ❌ | 14B |
| Standard | 60 | 100K | 5K | 5 000 ₽ | ❌ | 14B, 32B |
| VIP | 300 | 500K | 50K | 15 000 ₽ | ✅ | Все |
| Enterprise | 1000 | 2M | 200K | 50 000 ₽ | ✅ | Все + кастом |

### Настройка LDAP (9 полей)

| Поле | Пример |
|---|---|
| LDAP-сервер | `ldap://freeipa.example.com:389` |
| Базовый DN | `dc=example,dc=com` |
| Сервисная учётка (DN) | `uid=svc,cn=users,cn=accounts,...` |
| Пароль учётки | `••••••••` |
| User Base | `cn=users,cn=accounts,...` |
| Group Base | `cn=groups,cn=accounts,...` |
| Атрибут логина | `uid` |
| Атрибут почты | `mail` |
| Атрибут имени | `displayName` |

После сохранения — **перезапустить BFF**: `systemctl restart aither-bff`.

Ролевое сопоставление (группы LDAP → роли портала):
- `aither-admins` → owner
- `aither-billing` → billing_admin
- `aither-developers` → developer

---

## 4. CLI-команды

### BFF (VPS2, systemd)

```bash
systemctl status aither-bff          # статус
systemctl restart aither-bff         # перезапуск (после смены LDAP/конфигов)
systemctl stop aither-bff            # остановка
journalctl -u aither-bff -f          # логи в реальном времени
journalctl -u aither-bff --since "1 hour ago"  # логи за час
```

### Nginx (VPS2, Docker)

```bash
docker ps | grep nginx               # статус контейнера
docker restart portal-portal-nginx-1 # перезапуск (после смены статики)
docker logs portal-portal-nginx-1    # логи
docker exec portal-portal-nginx-1 nginx -s reload  # перезагрузка конфига
```

### PostgreSQL (VPS2, Docker)

```bash
docker exec aither-portal-portal-db-1 psql -U portal -d portal  # консоль
docker exec aither-portal-portal-db-1 pg_dump -U portal portal > backup.sql  # дамп
```

### Gateway (K8s)

```bash
kubectl get pods -n aither -l app=gateway            # список подов
kubectl logs -n aither deploy/gateway --tail=100     # последние 100 строк
kubectl logs -n aither deploy/gateway -f             # стриминг логов
kubectl rollout restart -n aither deploy/gateway     # перезапуск
kubectl rollout status -n aither deploy/gateway      # статус деплоя
kubectl rollout undo -n aither deploy/gateway        # откат
kubectl describe -n aither deploy/gateway            # детали деплоймента
```

### vLLM (K8s)

```bash
kubectl get pods -n aither -l app=vllm               # все vLLM-поды
kubectl logs -n aither deploy/vllm-qwen --tail=50    # 14B
kubectl logs -n aither deploy/vllm-qwen32b --tail=50 # 32B
kubectl exec -n aither deploy/vllm-qwen -- nvidia-smi  # GPU-статус на n8
kubectl exec -n aither deploy/vllm-qwen32b -- nvidia-smi # GPU-статус на n7
```

### GPU-узлы (n8, n7)

```bash
ssh root@10.129.13.78 "nvidia-smi"                   # n8 GPU-статус
ssh root@10.129.13.77 "nvidia-smi"                   # n7 GPU-статус
ssh root@10.129.13.78 "kubectl get nodes"            # статус узлов K8s
ssh root@10.129.13.78 "kubectl top nodes"            # загрузка узлов
ssh root@10.129.13.78 "kubectl top pods -n aither"   # загрузка подов
```

### WireGuard

```bash
wg show wg0                          # статус туннеля VPS1↔VPS2
ping 10.100.0.2                      # проверка связности
```

---

## 5. Бэкап и восстановление

### Бэкап БД портала (VPS2)

```bash
#!/bin/bash
BACKUP_DIR=/root/backups
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M)
docker exec aither-portal-portal-db-1 pg_dump -U portal portal | gzip > $BACKUP_DIR/portal_$DATE.sql.gz
# Ротация: хранить 7 последних
ls -t $BACKUP_DIR/portal_*.sql.gz | tail -n +8 | xargs rm -f
```

### Бэкап БД биллинга (K8s)

```bash
kubectl exec -n aither deploy/postgres -- pg_dump -U aither aither | gzip > $BACKUP_DIR/billing_$DATE.sql.gz
```

### Бэкап конфигурации

```bash
cd /root/aither-project
tar czf $BACKUP_DIR/aither-configs_$DATE.tar.gz \
  configs/ portal/.env portal/secrets.env \
  k8s/ gateway/catalog.yaml
git push  # всегда актуально в репо
```

### Бэкап ChromaDB

⚠️ ChromaDB в in-memory режиме — данные теряются при рестарте. После восстановления необходим инжест:

```bash
kubectl exec -n aither deploy/chroma-proxy -- python3 /chroma/ingest_textbook.py
```

### Восстановление БД портала

```bash
gunzip -c $BACKUP_DIR/portal_20260707_1200.sql.gz | \
  docker exec -i aither-portal-portal-db-1 psql -U portal -d portal
systemctl restart aither-bff
```

### Полное восстановление после сбоя VPS2

```bash
# 1. Восстановить БД
gunzip -c $BACKUP_DIR/portal_LATEST.sql.gz | docker exec -i aither-portal-portal-db-1 psql -U portal -d portal

# 2. Восстановить конфиги
cd /root/aither-project && git pull
cp configs/vps2/aither-bff.service /etc/systemd/system/

# 3. Запустить
systemctl daemon-reload
systemctl start aither-bff
docker restart portal-portal-nginx-1

# 4. Проверить
curl https://fb1.spb.ru:10443/api/v1/status
```

---

## 6. Мониторинг (Grafana + Prometheus)

### Доступ

```
URL: https://fb1.spb.ru:10443/grafana/
Логин: admin
Пароль: admin
```

### Дашборды

| Дашборд | Что показывает | Ключевые метрики |
|---|---|---|
| **Aither GPU** | Температура, utilisation, память, throttle | GPU util > 90% — нагрузка |
| **vLLM Inference** | Запросы/сек, токены/сек, KV cache hit rate | Cache hit < 80% — перезапуск vLLM |
| **Aither Billing** | Списания по моделям, балансы организаций | Резкий рост списаний — проверка |
| **Infrastructure** | Latency по эндпоинтам, ошибки 4xx/5xx | 5xx > 1% — инцидент |

### Prometheus-метрики Gateway

```
# Все метрики
curl http://10.129.13.78:30900/metrics

# Ключевые:
aither_requests_total{model="qwen2.5-14b"}
aither_request_duration_seconds{quantile="0.99"}
aither_ttft_seconds{model="qwen2.5-14b"}
aither_rate_limit_hits_total{org_id="..."}
aither_dlp_blocks_total{type="credit_card"}
```

### Alert-правила (рекомендуемые)

```yaml
# GPU temperature > 85°C — warning
# vLLM pod not ready > 5 min — critical
# Gateway 5xx rate > 5% — critical
# BFF down > 2 min — critical
# Disk > 90% — warning
```

---

## 7. RAG-администрирование

### Статус RAG

```bash
# Проверка ChromaDB
kubectl exec -n aither deploy/chroma-proxy -- curl -s http://localhost:8000/api/v1/collections

# Проверка chroma-proxy
curl http://10.129.13.77:9000/health

# Проверка гибридного RAG через Gateway
curl -X POST https://fb1.spb.ru:10443/v1/rag/hybrid-query \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"query": "лабораторные работы", "top_k": 5, "wiki_radius": 1}'
```

### Инжест учебника (после рестарта ChromaDB)

```bash
kubectl exec -n aither deploy/chroma-proxy -- python3 /chroma/ingest_textbook.py
```

⚠️ **Важно:** chroma-proxy использует in-memory ChromaDB — данные теряются при каждом рестарте пода. После перезапуска **обязательно** повторить инжест.

### Wiki Graph (LLM-Wiki)

```bash
# Проверка страниц Wiki
kubectl get configmap -n aither gateway-wiki -o jsonpath='{.data}' | jq 'keys'

# Обновление Wiki (после правки .md-файлов)
kubectl create configmap gateway-wiki --from-file=wiki/entities/ --from-file=wiki/concepts/ \
  -n aither --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart -n aither deploy/gateway
```

### Добавление новых документов в RAG

```bash
# 1. Положить .md/.txt файл в chroma-proxy
kubectl cp document.md aither/$(kubectl get pod -n aither -l app=chroma-proxy -o name | head -1):/chroma/

# 2. Запустить инжест
kubectl exec -n aither deploy/chroma-proxy -- python3 -c "
from ingest_textbook import ingest_file
ingest_file('/chroma/document.md', collection='documents')
"
```

---

## 8. vLLM-управление

### Статус моделей

```bash
# Все vLLM-поды
kubectl get pods -n aither -l app=vllm -o wide

# Детали конкретного пода
kubectl describe -n aither pod/vllm-qwen-<hash>

# Логи (поиск ошибок загрузки модели)
kubectl logs -n aither deploy/vllm-qwen | grep -i error
```

### Drain/Undrain модели

```bash
# Drain (исключить из ротации)
kubectl exec -n aither deploy/gateway -- curl -X POST http://localhost:8080/admin/models/qwen2.5-14b/drain

# Undrain (вернуть в ротацию)
kubectl exec -n aither deploy/gateway -- curl -X POST http://localhost:8080/admin/models/qwen2.5-14b/undrain

# Статус всех моделей
kubectl exec -n aither deploy/gateway -- curl http://localhost:8080/admin/models
```

### Смена модели (добавление новой)

```bash
# 1. Загрузить модель в /mnt/models/
scp model-files root@10.129.13.77:/mnt/models/

# 2. Создать deployment.yaml
# 3. Применить
kubectl apply -f k8s/vllm-NEW/deployment.yaml

# 4. Добавить в catalog.yaml
# 5. Обновить ConfigMap
kubectl create configmap gateway-catalog --from-file=gateway/catalog.yaml \
  -n aither --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart -n aither deploy/gateway
```

### GPU-диагностика

```bash
# На узле
ssh root@10.129.13.78
nvidia-smi
nvidia-smi -q -d TEMPERATURE,MEMORY,UTILIZATION

# Через K8s
kubectl describe node bootsman-k8s-clnt01-n8-gpu | grep nvidia
kubectl get pods -n gpu-operator
```

---

## 9. Безопасность

### Ротация JWT-секрета

```bash
# 1. Сгенерировать новый
NEW_SECRET=$(openssl rand -hex 32)

# 2. Обновить на VPS2
sed -i "s/JWT_SECRET=.*/JWT_SECRET=$NEW_SECRET/" /root/aither-project/portal/.env

# 3. Перезапустить
systemctl restart aither-bff
```

### Ротация API-ключей

Через админ-панель: 🔑 API-ключи → 🚫 Отозвать.

### Отзыв всех ключей организации

```sql
-- Подключиться к БД портала
docker exec -it aither-portal-portal-db-1 psql -U portal -d portal

-- Отозвать ключи организации
UPDATE portal_api_keys SET status='revoked'
WHERE org_id = '<org-uuid>' AND status='active';
```

### DLP-аудит

```bash
# Статистика блокировок DLP
kubectl exec -n aither deploy/gateway -- curl http://localhost:8080/admin/security/stats

# Последние инциденты
kubectl exec -n aither deploy/postgres -- psql -U aither -d aither \
  -c "SELECT * FROM security_events ORDER BY created_at DESC LIMIT 20;"
```

### Блокировка организации

```bash
# Через админ-панель: 🏢 → выбрать org → Заблокировать
# Или через API:
curl -X POST https://fb1.spb.ru:10443/api/v1/admin/orgs/<id>/block \
  -H "X-Admin-Key: $ADMIN_KEY"
```

---

## 10. Сеть и связность

### Проверка связности

```bash
# VPS1 → VPS2 (WireGuard)
ping 10.100.0.2

# VPS2 → n8
ssh root@10.129.13.78 "hostname"

# VPS2 → n7
ssh root@10.129.13.77 "hostname"

# DNS в K8s
kubectl exec -n aither deploy/gateway -- nslookup kubernetes.default
```

### WireGuard

```bash
# Статус
wg show wg0

# Перезапуск (если туннель упал)
wg-quick down wg0 && wg-quick up wg0
```

### Диагностика сети

```bash
# Трассировка до n8
traceroute 10.129.13.78

# Проверка портов
nc -zv 10.129.13.78 30900  # Gateway
nc -zv 10.129.13.77 32294  # vLLM 32B
nc -zv 10.100.0.2 3000     # BFF
```

---

## 11. CI/CD pipeline

### Процесс деплоя

```
git push main (gateway/**) →
  GitHub Actions → docker build → push ghcr.io →
  kubectl set image → rollout status →
  health-check (5 попыток) →
  rollback (при провале) →
  Telegram-уведомление
```

### Ручной деплой Gateway

```bash
cd /root/aither-project/gateway
docker build -t ghcr.io/dedvmedved-dot/aither-project-gateway:latest .
docker push ghcr.io/dedvmedved-dot/aither-project-gateway:latest
kubectl set image -n aither deploy/gateway gateway=ghcr.io/dedvmedved-dot/aither-project-gateway:latest
kubectl rollout status -n aither deploy/gateway
```

### Ручной деплой портала

```bash
cd /root/aither-project/portal
npm run build
rsync -avz dist/ root@130.17.1.90:/root/aither-project/portal/dist/
rsync -avz static/ root@130.17.1.90:/root/aither-project/portal/static/
ssh root@130.17.1.90 "systemctl restart aither-bff"
```

### Статус CI/CD

```bash
# Последний запуск workflow
gh run list --repo dedvmedved-dot/aither-project --limit 5
gh run view --repo dedvmedved-dot/aither-project <run-id>
```

---

## 12. Устранение неполадок

### Портал недоступен (502/504)

```bash
# 1. Проверить BFF
systemctl status aither-bff
journalctl -u aither-bff --since "5 min ago"

# 2. Проверить nginx VPS2
docker ps | grep nginx
docker logs portal-portal-nginx-1 --tail 20

# 3. Проверить nginx VPS1
ssh root@170.168.91.95 "systemctl status nginx"

# 4. Перезапустить цепочку
systemctl restart aither-bff && docker restart portal-portal-nginx-1
```

### Gateway недоступен

```bash
# 1. Проверить под
kubectl get pods -n aither -l app=gateway

# 2. Логи
kubectl logs -n aither deploy/gateway --tail=50

# 3. Если CrashLoopBackOff
kubectl describe -n aither pod/<gateway-pod>
kubectl logs -n aither <gateway-pod> --previous

# 4. Перезапуск
kubectl rollout restart -n aither deploy/gateway
```

### vLLM не стартует

```bash
# 1. Проверить GPU
kubectl exec -n aither deploy/vllm-qwen -- nvidia-smi 2>&1

# 2. Проверить модель на диске
kubectl exec -n aither deploy/vllm-qwen -- ls /mnt/models/

# 3. Проверить OOM
kubectl describe -n aither pod/<vllm-pod> | grep -A5 "State:"

# 4. Решение: перезапуск с очисткой GPU-памяти
kubectl delete pod -n aither -l app=vllm
```

### ChromaDB пустая (0 коллекций)

```bash
kubectl exec -n aither deploy/chroma-proxy -- python3 /chroma/ingest_textbook.py
```

### etcd без кворума

```bash
# Проверить
ssh root@10.129.13.78 "kubectl get pods -n kube-system -l component=etcd"

# Если только n8:
ssh root@170.168.91.95 "systemctl restart kubelet"  # VPS1 как follower
```

### Таблица проблем

| Симптом | Вероятная причина | Решение |
|---|---|---|
| 502 Bad Gateway | BFF упал | `systemctl restart aither-bff` |
| 504 Gateway Timeout | Gateway не отвечает | `kubectl rollout restart deploy/gateway` |
| OAuth не работает | Redirect URI mismatch | Проверить `.env` → перезапустить BFF |
| RAG возвращает пусто | ChromaDB пустая | Инжест учебника |
| vLLM CrashLoopBackOff | OOM / модель повреждена | Проверить `nvidia-smi`, логи |
| Rate limit на всё | Redis упал | `kubectl rollout restart deploy/redis` |
| Admin panel 403 | Нет прав админа | Проверить JWT-токен, роль пользователя |

---

## 13. Аварийные процедуры

### Полное падение VPS2

```bash
# 1. Проверить жив ли хост
ping 130.17.1.90
ssh root@130.17.1.90 "uptime"

# 2. Если нет — переключить на VPS3
ssh root@89.127.217.88
systemctl start aither-bff
# Обновить nginx VPS1: направить на VPS3
ssh root@170.168.91.95
sed -i 's/130.17.1.90/89.127.217.88/' /etc/nginx/sites-enabled/aither-failover
systemctl reload nginx
```

### Полное падение n8 (control-plane)

```bash
# Проверить
ssh root@10.129.13.78 "uptime"

# K8s — если n8 мёртв, etcd без кворума
# Восстановить из бэкапа etcd:
ssh root@10.129.13.78
etcdctl snapshot restore /backups/etcd-snapshot.db \
  --data-dir /var/lib/etcd-restore
systemctl restart kubelet
```

### Утечка API-ключа

```bash
# 1. Найти ключ
docker exec aither-portal-portal-db-1 psql -U portal -d portal \
  -c "SELECT id, name, prefix FROM portal_api_keys WHERE status='active';"

# 2. Отозвать
docker exec aither-portal-portal-db-1 psql -U portal -d portal \
  -c "UPDATE portal_api_keys SET status='revoked' WHERE id='<key-id>';"

# 3. Выпустить новый (пользователь делает сам через портал)
```

---

## 14. Схема БД

### PostgreSQL портала (VPS2)

```
portal_users
  id, display_name, email, oauth_provider, oauth_id, created_at

portal_organizations
  id, name, tier, created_at, owner_id → portal_users

portal_org_members
  org_id → portal_organizations, user_id → portal_users, role

portal_api_keys
  id, org_id → portal_organizations, name, prefix, key_hash, status, created_at

portal_settings
  key, value  (LDAP-конфигурация: 9 ключей)

portal_chats
  id, org_id → portal_organizations, title, created_at

portal_messages
  id, chat_id → portal_chats, role, content, tokens_used, created_at

subscription_tiers
  id, name, rpm_limit, tpm_limit, daily_limit, price, rag_enabled, allowed_models
```

### PostgreSQL биллинга (K8s)

```
billing_accounts
  org_id, balance, reserved, tier

billing_transactions
  id, org_id, type (reserve/settle/refund), model, tokens, timestamp

security_events
  id, org_id, event_type (dlp_credit_card/prompt_injection/...), 
  request_hash, created_at
```

### Redis (K8s)

```
org:{id}:tokens           — баланс токенов
org:{id}:rpm:{window}     — счётчик RPM (sliding window)
org:{id}:tpm:{window}     — счётчик TPM
reservation:{id}          — активная резервация
```

---

*Документ создан на основе реальной конфигурации платформы Aither, состояние на 07.07.2026.*
