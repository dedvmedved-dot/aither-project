# Руководство по эксплуатации платформы Aither AI

**Версия документа:** 1.0
**Дата:** 2026-07-26
**Пространство имён K8s:** `aither-inference`
**Язык:** Русский
**Целевая аудитория:** DevOps-инженеры, SRE, администраторы платформы

---

## Содержание

1. [Обзор системы](#1-обзор-системы)
2. [Компоненты архитектуры](#2-компоненты-архитектуры)
3. [Зоны доступа: Internet и Test Zone](#3-зоны-доступа-internet-и-test-zone)
4. [Ежедневные операции](#4-ежедневные-операции)
5. [Проверки работоспособности (Health Checks)](#5-проверки-работоспособности-health-checks)
6. [Мониторинг](#6-мониторинг)
7. [Логирование](#7-логирование)
8. [Реагирование на алерты](#8-реагирование-на-алерты)
9. [Типовые операционные задачи](#9-типовые-операционные-задачи)
10. [Окна обслуживания](#10-окна-обслуживания)
11. [Контакты эскалации](#11-контакты-эскалации)
12. [Приложения](#12-приложения)

---

## 1. Обзор системы

### 1.1. Назначение

Платформа Aither AI предоставляет API-доступ к большим языковым моделям (LLM) через единый Web-интерфейс (SPA) и OpenAI-совместимый Agent API. Платформа обслуживает две сетевые зоны:

- **Internet** — публичный доступ через HTTPS (`https://fb1.spb.ru:443`)
- **Test Zone** — внутренний доступ через K8s NodePort (`http://10.129.13.78:30080`)

### 1.2. Модели в инференсе

| Модель | Deployment | Узел | GPU | Режим | Max Tokens |
|--------|-----------|------|-----|-------|------------|
| Qwen2.5-14B-Instruct | `vllm-14b-instruct` | bootsman-k8s-clnt01-n8-gpu | 1× GPU | Chat Completions (диалог) | 2048 |
| Qwen2.5-32B-GPTQ | `vllm-32b-gptq` | bootsmam-k8s-clnt01-n7-gpu | 1× GPU | Text Completion (продолжение) | 4096 |

### 1.3. Узлы кластера

| Узел | Имя хоста | IP | Роль |
|------|----------|-----|------|
| n8 | bootsman-k8s-clnt01-n8-gpu | 10.129.13.78 | Control-plane + GPU-инференс (14B) |
| n7 | bootsmam-k8s-clnt01-n7-gpu | 10.129.13.77 | GPU-инференс (32B) |
| VPS2 | — | 130.17.1.90 | Обратный прокси (nginx) + BFF |

### 1.4. Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Фронтенд (SPA) | Vanilla JS + HTML5 + CSS3, nginx:stable-alpine |
| BFF (Backend-for-Frontend) | FastAPI (Python 3.11-slim) / Fastify 4.x (Node.js/TypeScript) |
| Identity-сервис | Python/FastAPI, SQLite |
| AI Platform (Core) | Python/FastAPI, SQLite |
| Инференс моделей | vLLM (OpenAI-совместимый API) |
| Обратный прокси (Internet) | nginx:1.27-alpine на VPS2 (Docker) |
| Rate limiting | Redis 7-alpine |
| База данных (Portal) | PostgreSQL 16 |
| Оркестрация | Kubernetes, namespace `aither-inference` |
| Контейнерный реестр | Локальный Docker Registry (`10.129.13.78:5000`) |

---

## 2. Компоненты архитектуры

### 2.1. Схема взаимодействия

```
Internet-клиент
    │
    ▼
VPS2 (130.17.1.90)
├── :443 → nginx (Docker: aither-failover-nginx)
│           ├── /         → K8s NodePort 10.129.13.78:30080 (Portal Frontend)
│           ├── /v1/*     → K8s NodePort 10.129.13.78:30902 (AI Platform)
│           ├── /api/*    → K8s NodePort 10.129.13.78:30080 (Portal Frontend → BFF)
│           └── /auth/*   → K8s NodePort 10.129.13.78:30080 (Portal Frontend → BFF)
├── :10443 → nginx (выделенный порт 32B)
│           ├── /v1/*     → K8s NodePort 10.129.13.78:30902 (AI Platform)
│           └── /*        → K8s NodePort 10.129.13.78:30080 (Portal Frontend)
├── :30901 → nginx (ChromaDB/RAG)
│           └── /*        → K8s ChromaDB 10.129.13.78:30901
└── :3000 → BFF (Fastify, Node.js)

Test Zone клиент
    │
    ▼
10.129.13.78:30080 (K8s NodePort)
    └── Pod aither-portal-frontend (nginx)
          ├── /api/*       → aither-portal-backend:8000 (K8s ClusterIP)
          ├── /v1/chat/*   → aither-ai-platform:8000 (K8s ClusterIP)
          ├── /health      → aither-portal-backend:8000
          └── /*           → SPA (статика, index.html)

K8s Cluster (aither-inference)
├── aither-portal-frontend (nginx, порт 80, NodePort 30080)
├── aither-portal-backend  (FastAPI/Fastify, порт 8000)
├── aither-bff             (FastAPI Python BFF, порт 8000)
├── aither-identity        (Identity-сервис, порт 8000)
├── aither-ai-platform     (AI Platform Core, порт 8000, NodePort 30902)
├── aither-redis-rate-limit (Redis, порт 6379)
├── nginx-gateway-32b      (nginx-шлюз для 32B, порт 8000)
│     └── → vllm-32b-gptq ClusterIP :8000 (n7)
└── vllm-14b-instruct      (vLLM 14B, порт 8000, n8)
```

### 2.2. VPS2 nginx (обратный прокси)

- **Контейнер:** `aither-failover-nginx` (Docker)
- **Режим сети:** `--network host`
- **Конфигурация:** `/root/nginx-failover.conf` (монтируется как `/etc/nginx/conf.d/default.conf`)
- **TLS:** Let's Encrypt, сертификаты в `/etc/nginx/ssl/`
- **Автообновление сертификатов:** certbot + deploy hook

**Проверка конфигурации:**
```bash
docker exec aither-failover-nginx nginx -t
```

**Перезагрузка (без даунтайма):**
```bash
docker exec aither-failover-nginx nginx -s reload
```

**⚠️ Питфол:** После редактирования `/root/nginx-failover.conf` через `patch`/`write_file` новый inode файла отличается от старого. Docker bind mount привязан к старому inode — контейнер видит старую версию. Требуется полный перезапуск контейнера:
```bash
docker stop aither-failover-nginx && docker rm aither-failover-nginx
docker run -d --name aither-failover-nginx \
  --network host --restart unless-stopped \
  -v /root/nginx-failover.conf:/etc/nginx/conf.d/default.conf:ro \
  -v /root/ssl-cert:/etc/nginx/ssl:ro \
  nginx:alpine
```

### 2.3. K8s-кластер на YADRO VEGMAN S320

Оборудование: серверы YADRO VEGMAN S320 с GPU NVIDIA RTX 6000 Ada.

| Компонент | Назначение |
|-----------|-----------|
| n8 (control-plane) | kube-apiserver, etcd, controller-manager, scheduler + GPU-инференс 14B |
| n7 (worker) | GPU-инференс 32B |
| Локальный Docker Registry | `10.129.13.78:5000` — хранение образов |

### 2.4. Деплойменты K8s (пространство имён `aither-inference`)

| Deployment | Образ | Порт | Назначение |
|-----------|-------|------|-----------|
| `aither-portal-frontend` | `nginx:stable-alpine` | 80 | Статика SPA + прокси на BFF |
| `aither-portal-backend` | `10.129.13.78:5000/aither-portal-backend:stage18a-82fe433` | 8000 | Portal BFF (FastAPI/Fastify) |
| `aither-bff` | `python:3.11-slim` | 8000 | BFF (FastAPI Python, rate limiting) |
| `aither-identity` | `10.129.13.78:5000/aither-identity:stage18a-82fe433` | 8000 | Identity-сервис (SQLite) |
| `aither-ai-platform` | `10.129.13.78:5000/aither-ai-platform:stage18a-82fe433` | 8000 | AI Platform Core (SQLite) |
| `vllm-14b-instruct` | `vllm/vllm-openai` | 8000 | Инференс Qwen2.5-14B-Instruct |
| `vllm-32b-gptq` | `vllm/vllm-openai` | 8000 | Инференс Qwen2.5-32B-GPTQ |
| `aither-redis-rate-limit` | `redis:7-alpine` | 6379 | Rate limiting (in-memory) |
| `nginx-gateway-32b` | `nginx:alpine` | 8000 | Шлюз для 32B-модели (completion) |

### 2.5. Сервисы K8s

| Service | Тип | ClusterIP/Порт | NodePort |
|---------|-----|----------------|----------|
| `aither-portal-frontend` | ClusterIP | Порт 80 | 30080 |
| `aither-portal-backend` | ClusterIP | Порт 8000 | — |
| `aither-bff` | ClusterIP | Порт 8000 | — |
| `aither-identity` | ClusterIP | Порт 8000 | — |
| `aither-ai-platform` | ClusterIP | Порт 8000 | 30902 |
| `vllm-14b-instruct` | ClusterIP | Порт 8000 | — |
| `vllm-32b-gptq` | ClusterIP (10.99.3.103) | Порт 8000 | — |
| `aither-redis-rate-limit` | ClusterIP | Порт 6379 | — |
| `nginx-gateway-32b` | ClusterIP | Порт 8000 | — |

### 2.6. BFF и Portal Backend

Платформа имеет два BFF-компонента:

**aither-portal-backend** (основной, FastAPI/Fastify):
- Порт: 8000 (внутри кластера)
- Образ: `10.129.13.78:5000/aither-portal-backend:stage18a-82fe433`
- Назначение: обслуживание Web UI, OAuth, API-ключи, проксирование в AI Platform

**aither-bff** (MVP BFF, FastAPI Python):
- Порт: 8000 (внутри кластера)
- Образ: `python:3.11-slim`
- Код из ConfigMap `aither-bff-config`
- Назначение: rate limiting, аутентификация, маршрутизация 14B/32B

### 2.7. vLLM — инференс моделей

**vllm-14b-instruct** (узел n8):
- Модель: `/data/models/Qwen2.5-14B-Instruct` (hostPath)
- Tensor Parallel Size: 1
- GPU Memory Utilization: 0.85
- Max Model Length: 2048
- Served Model Name: `qwen-14b`
- GPU: 1× (nvidia.com/gpu: 1)
- Память: 64 Gi
- Startup Probe: `/health`, до 60 попыток (5 мин на загрузку)

**vllm-32b-gptq** (узел n7):
- Модель: `/data/models/Qwen2.5-32B-GPTQ` (hostPath)
- Квантизация: GPTQ
- Tensor Parallel Size: 1
- GPU Memory Utilization: 0.95
- Max Model Length: 4096
- Served Model Name: `qwen-32b-base`
- GPU: 1× (nvidia.com/gpu: 1)
- Память: 48 Gi
- Startup Probe: `/health`, до 60 попыток (5 мин на загрузку)

### 2.8. nginx-gateway-32b

Специализированный nginx-шлюз для маршрутизации запросов к 32B-модели:

- Проксирует `/v1/completions` → `vllm-32b-gptq` ClusterIP (10.99.3.103:8000)
- Блокирует `/v1/chat/completions` → HTTP 422 (базовая модель не поддерживает диалог)
- `livenessProbe`: `/healthz` (локальный, не зависит от vLLM)
- `readinessProbe`: `/health` (проверяет доступность vLLM)
- dnsPolicy: `ClusterFirst`
- ConfigMap: `nginx-gateway-32b` (ключ: `nginx.conf`)

### 2.9. Redis (Rate Limiting)

- **Deployment:** `aither-redis-rate-limit`
- **Образ:** `redis:7-alpine`
- **Порт:** 6379
- **Хранение:** `emptyDir` (in-memory, не персистентное)
- **Probes:** `redis-cli ping`
- **Отказоустойчивость:** fail-open (при недоступности Redis запросы не блокируются)

### 2.10. PostgreSQL

- Развёрнут в K8s (порт 31113 на n8)
- База данных: `portal` (пользователь `portal`)
- Таблицы: `portal_users`, `portal_organizations`, `portal_org_members`, `portal_api_keys`, `chats`, `chat_messages`, `billing_accounts`, `payment_transactions`

---

## 3. Зоны доступа: Internet и Test Zone

### 3.1. Internet-зона

**URL:** `https://fb1.spb.ru:443/`

**Схема маршрутизации:**
```
Клиент (Интернет)
  → VPS2 nginx :443 (TLS-termination, Let's Encrypt)
    → /v1/*    → 10.129.13.78:30902 (AI Platform NodePort)
    → /api/*   → 10.129.13.78:30080 (Portal Frontend NodePort)
    → /auth/*  → 10.129.13.78:30080 (Portal Frontend NodePort)
    → /*       → 10.129.13.78:30080 (Portal Frontend NodePort)
```

**Дополнительные порты Internet-зоны:**

| Порт | Назначение |
|------|-----------|
| `:443` | Основной Web UI + API |
| `:10443` | Выделенный порт 32B |
| `:30901` | ChromaDB/RAG |

**Проверка доступности:**
```bash
curl -sk -o /dev/null -w "%{http_code}\n" https://fb1.spb.ru:443/
# Ожидается: 200

curl -sk -o /dev/null -w "%{http_code}\n" https://fb1.spb.ru:10443/
# Ожидается: 200
```

**Проверка TLS-сертификата:**
```bash
openssl s_client -connect fb1.spb.ru:443 -servername fb1.spb.ru </dev/null 2>/dev/null | openssl x509 -noout -dates
```

### 3.2. Test Zone

**URL:** `http://10.129.13.78:30080/`

**Схема доступа:**
```
Клиент (внутренняя сеть 10.129.13.0/24 или VPN)
  → 10.129.13.78:30080 (K8s NodePort)
    → Pod aither-portal-frontend (nginx :80)
      → /api/*          → aither-portal-backend:8000 (BFF)
      → /v1/chat/*      → aither-ai-platform:8000 (AI Platform)
      → /health         → aither-portal-backend:8000
      → /*              → SPA (index.html, статика)
```

**Проверка доступности:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://10.129.13.78:30080/
# Ожидается: 200
```

### 3.3. Доступ к кластеру

**Прямой SSH (с VPS2 через Cisco VPN):**
```bash
ssh -i /root/.ssh/id_ed25519_n7n8 -o StrictHostKeyChecking=no root@10.129.13.78 "kubectl get pods -A"
ssh -i /root/.ssh/id_ed25519_n7n8 -o StrictHostKeyChecking=no root@10.129.13.77 "hostname"
```

**Альтернативный доступ через bastion (если прямой SSH недоступен):**
```bash
docker exec vpn-cisco sshpass -p '<pass>' ssh -o StrictHostKeyChecking=no \
  svlkravchuk@10.129.11.21 \
  'sshpass -p root ssh -o StrictHostKeyChecking=no root@10.129.13.78 "<команда>"'
```

### 3.4. Автоопределение зоны

Фронтенд автоматически определяет зону по hostname:
- IP из диапазона `10.129.*` или `localhost` → **TEST ZONE**
- Все остальные → **INTERNET**

---

## 4. Ежедневные операции

### 4.1. Запуск всех компонентов

**Порядок запуска:**
1. Проверить статус кластера K8s
2. Убедиться, что Docker Registry доступен
3. Применить манифесты (если не применены)
4. Дождаться готовности всех подов
5. Запустить/проверить VPS2 nginx

```bash
# 1. Проверить кластер K8s
kubectl cluster-info
kubectl get nodes
# Ожидается: n7 и n8 в статусе Ready

# 2. Проверить реестр образов
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.78 \
  "curl -fsS http://localhost:5000/v2/_catalog"
# Ожидается: список репозиториев (aither-identity, aither-portal-backend, aither-ai-platform)

# 3. Применить манифесты инфраструктурных компонентов
kubectl apply -f /root/aither-project/aither-v2/manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml

# 4. Применить манифесты Identity и AI Platform
kubectl apply -f /root/aither-project/aither-v2/services/identity/k8s/identity.yaml
kubectl apply -f /root/aither-project/aither-v2/services/ai-platform/k8s/ai-platform.yaml

# 5. Применить манифест BFF
kubectl apply -f /root/aither-project/aither-v2/manifests/mvp-roadmap/05-bff/bff-mvp.yaml

# 6. Применить манифест Portal Backend и Frontend
kubectl apply -f /root/aither-project/aither-v2/services/portal-backend/k8s/portal-backend.yaml
kubectl apply -f /root/aither-project/aither-v2/services/portal-frontend/k8s/portal-frontend.yaml

# 7. Применить манифесты vLLM
kubectl apply -f /root/aither-project/aither-v2/03-vllm-14b-deploy/manifests/vllm-deployment.yaml

# 8. Применить манифест nginx-gateway-32b
kubectl apply -f /root/aither-project/aither-v2/manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml

# 9. Дождаться готовности всех деплойментов
for deploy in aither-portal-frontend aither-portal-backend aither-bff \
              aither-identity aither-ai-platform aither-redis-rate-limit \
              nginx-gateway-32b vllm-14b-instruct vllm-32b-gptq; do
  echo "Waiting for $deploy..."
  kubectl rollout status deploy/$deploy -n aither-inference --timeout=600s
done

# 10. Запустить/проверить VPS2 nginx
docker start aither-failover-nginx 2>/dev/null || \
  docker run -d --name aither-failover-nginx \
    --network host --restart unless-stopped \
    -v /root/nginx-failover.conf:/etc/nginx/conf.d/default.conf:ro \
    -v /root/ssl-cert:/etc/nginx/ssl:ro \
    nginx:alpine
```

**Ожидаемое время полного запуска:**
- Инфраструктурные поды (Redis, BFF, Portal): ~2-3 минуты
- vLLM 14B (n8): ~5 минут (загрузка модели)
- vLLM 32B (n7): ~5 минут (загрузка модели)
- **Итого:** ~10-12 минут

### 4.2. Проверка статуса всех компонентов

**Быстрая проверка (одна команда):**
```bash
kubectl get pods -n aither-inference -o wide
```

**Ожидаемый вывод:**
```
NAME                                      READY   STATUS    RESTARTS   AGE
aither-ai-platform-xxx                    1/1     Running   0          ...
aither-bff-xxx                            1/1     Running   0          ...
aither-identity-xxx                       1/1     Running   0          ...
aither-portal-backend-xxx                 1/1     Running   0          ...
aither-portal-frontend-xxx                1/1     Running   0          ...
aither-redis-rate-limit-xxx               1/1     Running   0          ...
nginx-gateway-32b-xxx                     1/1     Running   0          ...
vllm-14b-instruct-xxx                     1/1     Running   0          ...
vllm-32b-gptq-xxx                         1/1     Running   0          ...
```

**Детальная проверка:**
```bash
kubectl get deployments -n aither-inference
# Ожидается: все AVAILABLE = 1 (или 2 для nginx-gateway-32b)
```

### 4.3. Остановка компонентов

**Остановка K8s-компонентов (graceful — масштабирование до 0):**
```bash
# Портал (frontend + backend)
kubectl scale deploy/aither-portal-frontend -n aither-inference --replicas=0
kubectl scale deploy/aither-portal-backend -n aither-inference --replicas=0
kubectl scale deploy/aither-bff -n aither-inference --replicas=0

# Инфраструктура
kubectl scale deploy/aither-identity -n aither-inference --replicas=0
kubectl scale deploy/aither-ai-platform -n aither-inference --replicas=0
kubectl scale deploy/aither-redis-rate-limit -n aither-inference --replicas=0
kubectl scale deploy/nginx-gateway-32b -n aither-inference --replicas=0

# Модели (в последнюю очередь)
kubectl scale deploy/vllm-14b-instruct -n aither-inference --replicas=0
kubectl scale deploy/vllm-32b-gptq -n aither-inference --replicas=0

# Остановка VPS2 nginx
docker stop aither-failover-nginx
```

**Восстановление из scale 0:**
```bash
kubectl scale deploy/vllm-14b-instruct -n aither-inference --replicas=1
kubectl scale deploy/vllm-32b-gptq -n aither-inference --replicas=1
kubectl scale deploy/aither-redis-rate-limit -n aither-inference --replicas=1
kubectl scale deploy/aither-identity -n aither-inference --replicas=1
kubectl scale deploy/aither-ai-platform -n aither-inference --replicas=1
kubectl scale deploy/aither-bff -n aither-inference --replicas=1
kubectl scale deploy/aither-portal-backend -n aither-inference --replicas=1
kubectl scale deploy/aither-portal-frontend -n aither-inference --replicas=1
kubectl scale deploy/nginx-gateway-32b -n aither-inference --replicas=2
```

### 4.4. Перезапуск компонентов

**Перезапуск без даунтайма (rolling restart):**

```bash
# Перезапуск Portal Frontend
kubectl rollout restart deploy/aither-portal-frontend -n aither-inference
kubectl rollout status deploy/aither-portal-frontend -n aither-inference --timeout=120s

# Перезапуск Portal Backend (BFF)
kubectl rollout restart deploy/aither-portal-backend -n aither-inference
kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=120s

# Перезапуск BFF (Python)
kubectl rollout restart deploy/aither-bff -n aither-inference
kubectl rollout status deploy/aither-bff -n aither-inference --timeout=120s

# Перезапуск Identity
kubectl rollout restart deploy/aither-identity -n aither-inference
kubectl rollout status deploy/aither-identity -n aither-inference --timeout=60s

# Перезапуск AI Platform
kubectl rollout restart deploy/aither-ai-platform -n aither-inference
kubectl rollout status deploy/aither-ai-platform -n aither-inference --timeout=60s

# Перезапуск Redis
kubectl rollout restart deploy/aither-redis-rate-limit -n aither-inference
kubectl rollout status deploy/aither-redis-rate-limit -n aither-inference --timeout=60s

# Перезапуск nginx-gateway-32b
kubectl rollout restart deploy/nginx-gateway-32b -n aither-inference
kubectl rollout status deploy/nginx-gateway-32b -n aither-inference --timeout=60s
```

**Перезапуск vLLM (с даунтаймом ~5-10 минут):**
```bash
# vLLM 14B (загрузка модели ~5 мин)
kubectl rollout restart deploy/vllm-14b-instruct -n aither-inference
kubectl rollout status deploy/vllm-14b-instruct -n aither-inference --timeout=600s

# vLLM 32B (загрузка модели ~5 мин)
kubectl rollout restart deploy/vllm-32b-gptq -n aither-inference
kubectl rollout status deploy/vllm-32b-gptq -n aither-inference --timeout=600s
```

**Перезапуск проблемного пода (ручной):**
```bash
# Удалить конкретный под — ReplicaSet пересоздаст
kubectl delete pod -n aither-inference <имя-пода>
kubectl rollout status deploy/<имя-деплоймента> -n aither-inference --timeout=180s
```

**Перезагрузка VPS2 nginx (без даунтайма):**
```bash
docker exec aither-failover-nginx nginx -t && \
  docker exec aither-failover-nginx nginx -s reload
```

**Полный перезапуск VPS2 nginx (с кратким даунтаймом ~2 сек):**
```bash
docker stop aither-failover-nginx && docker rm aither-failover-nginx
docker run -d --name aither-failover-nginx \
  --network host --restart unless-stopped \
  -v /root/nginx-failover.conf:/etc/nginx/conf.d/default.conf:ro \
  -v /root/ssl-cert:/etc/nginx/ssl:ro \
  nginx:alpine
```

### 4.5. Перезапуск всего кластера (после отключения питания)

```bash
# 1. Убедиться, что узлы загружены и kubelet запущен
kubectl get nodes
# Если узлы NotReady — подождать 2-3 минуты

# 2. Проверить, что container runtime работает
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.78 "systemctl status containerd"
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.77 "systemctl status containerd"

# 3. Проверить состояние подов
kubectl get pods -n aither-inference

# 4. Если поды в состоянии Error/CrashLoopBackOff — перезапустить деплойменты
kubectl rollout restart deploy/vllm-14b-instruct -n aither-inference
kubectl rollout restart deploy/vllm-32b-gptq -n aither-inference

# 5. Дождаться загрузки моделей (самый долгий этап)
kubectl rollout status deploy/vllm-14b-instruct -n aither-inference --timeout=600s
kubectl rollout status deploy/vllm-32b-gptq -n aither-inference --timeout=600s

# 6. Запустить VPS2 nginx
docker start aither-failover-nginx

# 7. Финальная проверка
curl -s http://10.129.13.78:30080/health | python3 -m json.tool
curl -sk -o /dev/null -w "%{http_code}\n" https://fb1.spb.ru:443/
```

---

## 5. Проверки работоспособности (Health Checks)

### 5.1. Health-check эндпоинты

| Компонент | Эндпоинт | Доступ |
|-----------|----------|--------|
| Portal Frontend | `GET /` (nginx) | Internet / Test Zone |
| Portal Backend (BFF) | `GET /health` | Internet: `https://fb1.spb.ru:443/health`<br>Test Zone: `http://10.129.13.78:30080/health` |
| BFF (Python) | `GET /health` | K8s ClusterIP: `http://aither-bff:8000/health` |
| AI Platform | `GET /health` | `http://10.129.13.78:30902/health` |
| Identity | `GET /health` | `http://aither-identity:8000/health` |
| vLLM 14B | `GET /health` | `http://vllm-14b-instruct:8000/health` |
| vLLM 32B | `GET /health` | `http://10.99.3.103:8000/health` |
| nginx-gateway-32b | `GET /healthz` (локальный)<br>`GET /health` (vLLM) | `http://nginx-gateway-32b:8000/healthz` |
| Redis | `redis-cli ping` | K8s internal |
| PostgreSQL | `psql -U portal -d portal -c "SELECT 1"` | K8s internal |

### 5.2. Ожидаемые ответы

**Portal BFF (`GET /health`):**
```json
{
  "status": "ok",
  "service": "portal-bff",
  "database": "connected"
}
```

**BFF Python (`GET /health`):**
```json
{
  "status": "ok",
  "version": "0.4.0",
  "rate_limit": "enabled",
  "redis": "connected",
  "auth": "configured"
}
```

**AI Platform (`GET /health`):**
```json
{
  "status": "ok"
}
```

**vLLM (`GET /health`):**
```
(HTTP 200, тело может быть пустым или содержать status)
```

**nginx-gateway-32b (`GET /healthz`):**
```
ok
```

### 5.3. Быстрая проверка (одним скриптом)

```bash
#!/bin/bash
# quick-health.sh — комплексная проверка здоровья

echo "=== K8s Pods ==="
kubectl get pods -n aither-inference -o wide

echo ""
echo "=== Problem Pods ==="
kubectl get pods -n aither-inference --field-selector=status.phase!=Running | grep -v Completed

echo ""
echo "=== Portal Frontend ==="
echo -n "Internet (443): "; curl -sk -o /dev/null -w "%{http_code}\n" https://fb1.spb.ru:443/
echo -n "Test Zone (30080): "; curl -s -o /dev/null -w "%{http_code}\n" http://10.129.13.78:30080/

echo ""
echo "=== Portal BFF Health ==="
curl -s http://10.129.13.78:30080/health | python3 -m json.tool 2>/dev/null || echo "FAILED"

echo ""
echo "=== AI Platform Health ==="
curl -s http://10.129.13.78:30902/health | python3 -m json.tool 2>/dev/null || echo "FAILED"

echo ""
echo "=== vLLM Models ==="
curl -s http://10.129.13.78:30902/v1/models 2>/dev/null | python3 -c "import sys,json; [print(f'  {m[\"id\"]}') for m in json.load(sys.stdin).get('data',[])]" 2>/dev/null || echo "FAILED"

echo ""
echo "=== Resource Usage ==="
kubectl top pods -n aither-inference 2>/dev/null || echo "metrics-server not available"
kubectl top nodes 2>/dev/null || echo "metrics-server not available"

echo ""
echo "=== Recent Events ==="
kubectl get events -n aither-inference --sort-by='.lastTimestamp' | tail -10
```

### 5.4. Проверка K8s Health Probes

```bash
# Проверить состояние проб для конкретного деплоймента
kubectl describe pod -n aither-inference -l app=aither-portal-frontend | grep -A5 "Liveness\|Readiness"
kubectl describe pod -n aither-inference -l app=vllm | grep -A5 "Liveness\|Readiness\|Startup"
```

### 5.5. Проверка доступности моделей (через API)

```bash
# Список моделей через AI Platform
curl -s http://10.129.13.78:30902/v1/models | python3 -m json.tool

# Тестовый chat completion (14B)
curl -s -X POST http://10.129.13.78:30902/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${VLLM_API_KEY}" \
  -d '{
    "model": "qwen-14b",
    "messages": [{"role": "user", "content": "Тест связи"}],
    "max_tokens": 10
  }' | python3 -m json.tool

# Тестовый completion (32B, через nginx-gateway)
curl -s -X POST http://10.129.13.78:30902/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${VLLM_API_KEY}" \
  -d '{
    "model": "qwen-32b-base",
    "prompt": "Продолжи: столица России",
    "max_tokens": 10
  }' | python3 -m json.tool
```

### 5.6. K8s Probes (сводная таблица)

| Deployment | Liveness | Readiness | Startup |
|-----------|----------|-----------|---------|
| `aither-portal-frontend` | `GET /` (10+15s) | `GET /` (5+10s) | — |
| `aither-portal-backend` | `GET /health` (10+15s) | `GET /ready` (5+10s) | — |
| `aither-bff` | `GET /health` (30+30s) | `GET /health` (10+10s) | `GET /health` (30+5s×30) |
| `aither-identity` | `GET /health` (10+15s) | `GET /ready` (5+10s) | — |
| `aither-ai-platform` | `GET /health` (15+20s) | `GET /ready` (10+15s) | — |
| `aither-redis-rate-limit` | `redis-cli ping` (15+20s) | `redis-cli ping` (5+10s) | — |
| `nginx-gateway-32b` | `GET /healthz` (30s×3) | `GET /health` (5+10s×3) | `GET /healthz` (5+5s×30) |
| `vllm-14b-instruct` | `GET /health` (30s×3) | `GET /health` (5s×3) | `GET /health` (5s×60) |
| `vllm-32b-gptq` | `GET /health` (30s×3) | `GET /health` (5s×3) | `GET /health` (5s×60) |

---

## 6. Мониторинг

### 6.1. Prometheus

Сбор метрик через Prometheus. Конфигурация алерт-правил: `/root/aither-project/aither-v2/docs/stage17/prometheus/alert-rules.yaml`

### 6.2. Критические алерты

| Алерт | Условие | Порог | Действие |
|-------|---------|-------|----------|
| `ServiceDown` | `up{service=~"identity|portal-backend|ai-platform|nginx-gateway-32b"} == 0` | 1 мин | Проверить поды: `kubectl get pods -n aither-inference` |
| `ReadinessCheckFailed` | `probe_success == 0` | 30 сек | Проверить readiness probe: `kubectl describe pod` |
| `GatewayUnavailable` | `rate(gateway_requests_total{status="error"}[5m]) > 10` | 2 мин | Проверить Gateway: `kubectl logs deploy/nginx-gateway-32b` |

### 6.3. Предупреждения (warning)

| Алерт | Условие | Порог | Действие |
|-------|---------|-------|----------|
| `HighErrorRate` | HTTP 5xx > 5% | 5 мин | Проверить логи BFF и AI Platform |
| `HighLatency` | P95 latency > 5 сек | 5 мин | Проверить загрузку GPU и vLLM |
| `PVCLowSpace` | PVC заполнен > 85% | 5 мин | Очистить или расширить PVC |
| `HighMemoryUsage` | Память > 500 MB | 5 мин | Проверить `kubectl top pods` |

### 6.4. Grafana Dashboards

Дашборды Grafana (файлы в `/root/aither-project/aither-v2/docs/stage17/grafana/`):

| Дашборд | Файл | Назначение |
|---------|------|-----------|
| System Overview | `dashboard-system-overview.json` | Общее состояние системы |
| Gateway | `dashboard-gateway.json` | Метрики nginx-шлюза 32B |
| AI Platform | `dashboard-ai-platform.json` | Состояние vLLM-инференса |
| Identity | `dashboard-identity.json` | Аутентификация и сессии |
| Portal | `dashboard-portal.json` | Web UI и BFF |
| GPU Overview | `gpu-overview.json` | Утилизация GPU |
| vLLM Inference | `vllm-inference.json` | Метрики вывода моделей |

### 6.5. Быстрый ручной мониторинг

```bash
# Статус подов
kubectl get pods -n aither-inference --no-headers | wc -l
kubectl get pods -n aither-inference -o wide

# Использование ресурсов
kubectl top pods -n aither-inference
kubectl top nodes

# Статус GPU (на узлах)
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.78 "nvidia-smi"
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.77 "nvidia-smi"

# Метрики через API
curl -s http://10.129.13.78:30080/api/v1/status | python3 -m json.tool
```

### 6.6. Ключевые метрики для наблюдения

| Метрика | Значение | Тревога при |
|---------|----------|-------------|
| `gateway_ttft_seconds` | Time-to-first-token | P95 > 10s |
| `gateway_requests_total` | Всего запросов | — |
| `gateway_billing_errors_total` | Ошибки биллинга | > 0 за 5 мин |
| `gateway_active_requests` | Активные запросы | > max_concurrent |
| `node_memory_MemAvailable_bytes` | Свободная RAM | < 4 GB |
| `DCGM_FI_DEV_GPU_UTIL` | Утилизация GPU | > 95% sustained |

---

## 7. Логирование

### 7.1. Логи K8s-деплойментов

**Portal Frontend (nginx):**
```bash
kubectl logs -n aither-inference deploy/aither-portal-frontend --tail=100
kubectl logs -n aither-inference deploy/aither-portal-frontend --tail=100 -f
kubectl logs -n aither-inference deploy/aither-portal-frontend --since=1h
```

**Portal Backend (BFF FastAPI/Fastify):**
```bash
kubectl logs -n aither-inference deploy/aither-portal-backend --tail=100
kubectl logs -n aither-inference deploy/aither-portal-backend --timestamps
kubectl logs -n aither-inference deploy/aither-portal-backend -f
kubectl logs -n aither-inference deploy/aither-portal-backend --since=1h
```

**BFF (Python FastAPI):**
```bash
kubectl logs -n aither-inference deploy/aither-bff --tail=100
kubectl logs -n aither-inference deploy/aither-bff -f
kubectl logs -n aither-inference deploy/aither-bff --since=30m
```

**Identity:**
```bash
kubectl logs -n aither-inference deploy/aither-identity --tail=100
kubectl logs -n aither-inference deploy/aither-identity --since=1h
```

**AI Platform:**
```bash
kubectl logs -n aither-inference deploy/aither-ai-platform --tail=100
kubectl logs -n aither-inference deploy/aither-ai-platform -f
kubectl logs -n aither-inference deploy/aither-ai-platform --since=30m
```

**Redis:**
```bash
kubectl logs -n aither-inference deploy/aither-redis-rate-limit --tail=50
```

**nginx-gateway-32b:**
```bash
kubectl logs -n aither-inference deploy/nginx-gateway-32b --tail=100
kubectl logs -n aither-inference deploy/nginx-gateway-32b -f
```

**vLLM 14B:**
```bash
kubectl logs -n aither-inference deploy/vllm-14b-instruct --tail=100
kubectl logs -n aither-inference deploy/vllm-14b-instruct -f
kubectl logs -n aither-inference deploy/vllm-14b-instruct --since=1h
```

**vLLM 32B:**
```bash
kubectl logs -n aither-inference deploy/vllm-32b-gptq --tail=100
kubectl logs -n aither-inference deploy/vllm-32b-gptq -f
kubectl logs -n aither-inference deploy/vllm-32b-gptq --since=1h
```

### 7.2. Логи VPS2 nginx

```bash
# Логи Docker-контейнера
docker logs aither-failover-nginx --tail=100
docker logs aither-failover-nginx --tail=200 -f
docker logs aither-failover-nginx --since 1h

# Логи доступа (внутри контейнера)
docker exec aither-failover-nginx tail -100 /var/log/nginx/access.log
docker exec aither-failover-nginx tail -100 /var/log/nginx/error.log
```

### 7.3. Логи падений (CrashLoopBackOff)

```bash
# Логи ПРЕДЫДУЩЕГО экземпляра (причина падения)
kubectl logs -n aither-inference <имя-пода> --previous --tail=100

# События пода
kubectl describe pod -n aither-inference <имя-пода> | grep -A20 "Events"
```

### 7.4. Уровни логирования

**Portal Backend (BFF):**
```bash
# Временно повысить детализацию
kubectl set env deploy/aither-portal-backend -n aither-inference PORTAL_LOG_LEVEL=DEBUG
kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=60s

# Вернуть обычный уровень
kubectl set env deploy/aither-portal-backend -n aither-inference PORTAL_LOG_LEVEL=INFO
```

**AI Platform / Identity:**
```bash
kubectl set env deploy/aither-ai-platform -n aither-inference AI_PLATFORM_LOG_LEVEL=DEBUG
```

### 7.5. Алиасы для быстрого доступа к логам

Добавить в `~/.bashrc`:
```bash
alias klog-fe='kubectl logs -n aither-inference deploy/aither-portal-frontend --tail=100'
alias klog-be='kubectl logs -n aither-inference deploy/aither-portal-backend --tail=100'
alias klog-bff='kubectl logs -n aither-inference deploy/aither-bff --tail=100'
alias klog-id='kubectl logs -n aither-inference deploy/aither-identity --tail=100'
alias klog-ai='kubectl logs -n aither-inference deploy/aither-ai-platform --tail=100'
alias klog-gw='kubectl logs -n aither-inference deploy/nginx-gateway-32b --tail=100'
alias klog-v14='kubectl logs -n aither-inference deploy/vllm-14b-instruct --tail=100'
alias klog-v32='kubectl logs -n aither-inference deploy/vllm-32b-gptq --tail=100'
alias klog-redis='kubectl logs -n aither-inference deploy/aither-redis-rate-limit --tail=50'
```

---

## 8. Реагирование на алерты

### 8.1. ServiceDown (критический)

**Симптом:** Prometheus сообщает `up == 0` для сервиса более 1 минуты.

**Немедленные действия:**
```bash
# 1. Проверить поды проблемного сервиса
kubectl get pods -n aither-inference -l app=<имя-сервиса>

# 2. Проверить статус деплоймента
kubectl get deploy -n aither-inference <имя-деплоймента>

# 3. Посмотреть логи
kubectl logs -n aither-inference deploy/<имя-деплоймента> --tail=50

# 4. Проверить события
kubectl get events -n aither-inference --sort-by='.lastTimestamp' | tail -20

# 5. При необходимости — перезапустить
kubectl rollout restart deploy/<имя-деплоймента> -n aither-inference
kubectl rollout status deploy/<имя-деплоймента> -n aither-inference --timeout=300s
```

### 8.2. GatewayUnavailable (критический)

**Симптом:** Более 10 ошибок/сек от Gateway за 2 минуты.

**Немедленные действия:**
```bash
# 1. Проверить статус nginx-gateway-32b
kubectl get pods -n aither-inference -l app=nginx-gateway

# 2. Проверить логи шлюза
kubectl logs -n aither-inference deploy/nginx-gateway-32b --tail=100

# 3. Проверить доступность vLLM 32B (upstream)
kubectl get pods -n aither-inference -l model=qwen-32b-gptq
kubectl logs -n aither-inference deploy/vllm-32b-gptq --tail=50

# 4. Проверить health vLLM
curl -s http://10.99.3.103:8000/health

# 5. При необходимости — перезапустить Gateway
kubectl rollout restart deploy/nginx-gateway-32b -n aither-inference
kubectl rollout status deploy/nginx-gateway-32b -n aither-inference --timeout=120s
```

### 8.3. HighErrorRate (warning)

**Симптом:** HTTP 5xx > 5% за 5 минут.

**Действия:**
```bash
# 1. Проверить логи BFF и AI Platform на ошибки
kubectl logs -n aither-inference deploy/aither-portal-backend --tail=200 | grep -i error
kubectl logs -n aither-inference deploy/aither-ai-platform --tail=200 | grep -i error

# 2. Проверить логи nginx на VPS2
docker logs aither-failover-nginx --tail=100 | grep -E " 50[0-9] "

# 3. Проверить доступность VPN-туннеля до K8s
ping -c 3 10.129.13.78

# 4. Проверить состояние моделей
curl -s http://10.129.13.78:30902/v1/models | python3 -m json.tool
```

### 8.4. HighLatency (warning)

**Симптом:** P95 latency > 5 сек.

**Действия:**
```bash
# 1. Проверить загрузку GPU
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.78 "nvidia-smi"
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.77 "nvidia-smi"

# 2. Проверить использование CPU/RAM подами
kubectl top pods -n aither-inference

# 3. Проверить, не перегружена ли очередь vLLM
kubectl logs -n aither-inference deploy/vllm-14b-instruct --tail=50 | grep -i "queue\|wait\|timeout"

# 4. Проверить сетевые задержки через VPN
ping -c 10 10.129.13.78
```

### 8.5. PVCLowSpace (warning)

**Действия:**
```bash
# Проверить использование PVC
kubectl get pvc -n aither-inference
kubectl describe pvc -n aither-inference <имя-pvc>

# Очистка старых данных при необходимости
kubectl exec -n aither-inference deploy/aither-ai-platform -- df -h /data
```

### 8.6. Аварийный сценарий: полная недоступность Internet-зоны

**Если `https://fb1.spb.ru:443` не отвечает:**

```bash
# 1. Проверить VPS2
ping -c 3 130.17.1.90

# 2. Проверить Docker на VPS2
ssh root@130.17.1.90 "docker ps | grep aither-failover-nginx"

# 3. Проверить VPN-туннель (Cisco)
ssh root@130.17.1.90 "ip addr show tun0 | grep 'inet '"

# 4. Проверить доступность K8s NodePort с VPS2
ssh root@130.17.1.90 "curl -s -o /dev/null -w '%{http_code}' http://10.129.13.78:30080/"

# 5. Если VPS2 недоступен — использовать Test Zone напрямую
# Доступ: http://10.129.13.78:30080/
```

---

## 9. Типовые операционные задачи

### 9.1. Обновление ConfigMap и перезапуск пода

```bash
# 1. Взять текущий ConfigMap (бэкап)
kubectl get configmap <имя-cm> -n aither-inference -o yaml > /tmp/cm-backup.yaml

# 2. Обновить ConfigMap из файла
kubectl apply -f <путь-к-манифесту>

# 3. Или обновить конкретный ключ
kubectl create configmap <имя-cm> -n aither-inference \
  --from-file=<ключ>=<файл> \
  --dry-run=client -o yaml | kubectl apply -f -

# 4. Перезапустить поды для применения
kubectl rollout restart deploy/<имя-деплоймента> -n aither-inference
kubectl rollout status deploy/<имя-деплоймента> -n aither-inference --timeout=120s
```

**Пример: обновление nginx-gateway-32b ConfigMap:**
```bash
# ВАЖНО: ключ в ConfigMap должен совпадать с subPath в Deployment!
kubectl create configmap nginx-gateway-32b -n aither-inference \
  --from-file=nginx.conf=<путь-к-nginx.conf> \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deploy/nginx-gateway-32b -n aither-inference
kubectl rollout status deploy/nginx-gateway-32b -n aither-inference --timeout=120s
```

**⚠️ Питфол:** Несовпадение ключа ConfigMap и `subPath` в Deployment → под в CrashLoopBackOff. Проверить:
```bash
kubectl get deploy nginx-gateway-32b -n aither-inference -o jsonpath='{.spec.template.spec.containers[0].volumeMounts[?(@.name=="config")].subPath}'
kubectl get configmap nginx-gateway-32b -n aither-inference -o jsonpath='{.data}' | python3 -c "import sys,json; print(list(json.load(sys.stdin).keys()))"
# Ключи должны совпадать!
```

### 9.2. Принудительный перезапуск пода

```bash
# Способ 1: удалить под (ReplicaSet пересоздаст)
kubectl delete pod -n aither-inference <имя-пода>

# Способ 2: rollout restart (предпочтительный)
kubectl rollout restart deploy/<имя-деплоймента> -n aither-inference
kubectl rollout status deploy/<имя-деплоймента> -n aither-inference --timeout=180s

# Способ 3: аннотация для принудительного пересоздания (без изменения конфигурации)
kubectl patch deploy/<имя-деплоймента> -n aither-inference \
  -p '{"spec":{"template":{"metadata":{"annotations":{"restartedAt":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}}}}}'
```

### 9.3. Deployment Rollout

```bash
# Просмотр истории деплоймента
kubectl rollout history deploy/<имя-деплоймента> -n aither-inference

# Просмотр деталей конкретной ревизии
kubectl rollout history deploy/<имя-деплоймента> -n aither-inference --revision=<N>

# Откат к предыдущей версии
kubectl rollout undo deploy/<имя-деплоймента> -n aither-inference
kubectl rollout status deploy/<имя-деплоймента> -n aither-inference --timeout=120s

# Откат к конкретной ревизии
kubectl rollout undo deploy/<имя-деплоймента> -n aither-inference --to-revision=<N>

# Приостановить rollout
kubectl rollout pause deploy/<имя-деплоймента> -n aither-inference

# Возобновить rollout
kubectl rollout resume deploy/<имя-деплоймента> -n aither-inference
```

### 9.4. Обновление образа деплоймента

```bash
# 1. Собрать и запушить новый образ
cd /root/aither-project/portal
TAG="aither-portal-backend:stage18a-$(date +%Y%m%d-%H%M)"
docker build -t 10.129.13.78:5000/$TAG .
docker push 10.129.13.78:5000/$TAG

# 2. Обновить образ в Deployment
kubectl set image deploy/aither-portal-backend -n aither-inference \
  portal-backend=10.129.13.78:5000/$TAG

# 3. Дождаться готовности
kubectl rollout status deploy/aither-portal-backend -n aither-inference --timeout=180s

# 4. Проверить
curl -s http://10.129.13.78:30080/health | python3 -m json.tool
```

### 9.5. Диагностика CrashLoopBackOff

```bash
# 1. Получить логи падения
POD=$(kubectl get pods -n aither-inference -l app=<метка> -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n aither-inference $POD --previous --tail=100

# 2. Проверить события
kubectl describe pod -n aither-inference $POD | grep -A30 "Events"

# 3. Проверить образ
kubectl get pod -n aither-inference $POD -o jsonpath='{.spec.containers[0].image}'

# 4. Проверить ресурсы
kubectl describe pod -n aither-inference $POD | grep -A10 "Requests\|Limits"

# 5. Принудительно пересоздать
kubectl delete pod -n aither-inference $POD
```

### 9.6. Диагностика ImagePullBackOff

```bash
# 1. Проверить событие
kubectl describe pod -n aither-inference <имя-пода> | grep -A5 "Events"

# 2. Проверить доступность реестра
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.78 \
  "curl -fsS http://localhost:5000/v2/_catalog"

# 3. Проверить наличие образа в реестре
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.78 \
  "curl -fsS http://localhost:5000/v2/<имя-репозитория>/tags/list"

# 4. Проверить доступность реестра с проблемного узла
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.77 \
  "curl -fsS http://10.129.13.78:5000/v2/_catalog"
```

### 9.7. Прямая передача образа между узлами (air-gapped)

Если worker-узел (n7) не может скачать образ через интернет:

```bash
# На n8 (где образ уже есть):
ctr -n k8s.io image export /tmp/<образ>.tar docker.io/<образ>:<тег>
scp /tmp/<образ>.tar root@10.129.13.77:/tmp/

# На n7:
ctr -n k8s.io image import /tmp/<образ>.tar
```

### 9.8. Проверка состояния GPU

```bash
# На n8
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.78 "nvidia-smi"

# На n7
ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.77 "nvidia-smi"

# Проверить GPU-ресурсы в K8s
kubectl describe nodes | grep -A5 "nvidia.com/gpu"
```

### 9.9. Управление секретами

```bash
# Просмотр существующих секретов
kubectl get secrets -n aither-inference

# Создание/обновление секрета из файла
kubectl create secret generic <имя> -n aither-inference \
  --from-file=<ключ>=<файл> \
  --dry-run=client -o yaml | kubectl apply -f -

# Обновление секрета из литерала
kubectl create secret generic <имя> -n aither-inference \
  --from-literal=<ключ>=<значение> \
  --dry-run=client -o yaml | kubectl apply -f -

# ⚠️ После изменения секрета — перезапустить поды
kubectl rollout restart deploy/<имя-деплоймента> -n aither-inference
```

### 9.10. Проверка переменных окружения деплоймента

```bash
kubectl get deploy <имя-деплоймента> -n aither-inference -o yaml | grep -A1 "name:\|value:"
```

---

## 10. Окна обслуживания

### 10.1. Плановое обслуживание

**Рекомендуемое время:** ночные часы МСК (02:00–05:00) или выходные дни.

**Типовые операции обслуживания:**

| Операция | Ожидаемый даунтайм | Частота |
|----------|-------------------|---------|
| Перезапуск BFF/Portal | ~10 сек (rolling) | По необходимости |
| Перезапуск vLLM | ~5-10 мин (перезагрузка модели) | При обновлении модели |
| Обновление ConfigMap | ~10 сек (rolling restart) | По необходимости |
| Обновление образов | ~30-60 сек (rolling) | Еженедельно |
| Обновление TLS-сертификатов | 0 сек (авто) | Каждые 60 дней |
| Резервное копирование БД | 0 сек | Ежедневно |
| Перезагрузка узла K8s | ~5-10 мин (перезагрузка моделей) | Ежемесячно |

### 10.2. Процедура перед окном обслуживания

```bash
# 1. Создать резервную копию
BACKUP_DIR="/root/backups/pre-maint-$(date +%Y%m%d-%H%M)"
mkdir -p "$BACKUP_DIR"

# Бэкап БД AI Platform (SQLite)
POD=$(kubectl get pods -n aither-inference -l app=aither-ai-platform -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n aither-inference "$POD" -- python3 -c "
import sqlite3; conn = sqlite3.connect('/data/ai-platform.db')
conn.backup(open('/tmp/backup.db', 'wb'))
"
kubectl cp "aither-inference/$POD:/tmp/backup.db" "$BACKUP_DIR/ai-platform.db"

# Бэкап БД Identity (SQLite)
POD=$(kubectl get pods -n aither-inference -l app=aither-identity -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n aither-inference "$POD" -- python3 -c "
import sqlite3; conn = sqlite3.connect('/data/identity.db')
conn.backup(open('/tmp/backup.db', 'wb'))
"
kubectl cp "aither-inference/$POD:/tmp/backup.db" "$BACKUP_DIR/identity.db"

# Бэкап nginx-конфигурации VPS2
cp /root/nginx-failover.conf "$BACKUP_DIR/nginx-failover.conf"

# Бэкап репозитория
cd /root/aither-project && git bundle create "$BACKUP_DIR/aither-project.bundle" --all

# 2. Проверить текущее состояние
kubectl get pods -n aither-inference -o wide
curl -s http://10.129.13.78:30080/health | python3 -m json.tool

# 3. Уведомить пользователей (если применимо)
echo "Платформа Aither: плановое обслуживание $(date). Ожидаемая продолжительность: ..."
```

### 10.3. Процедура после окна обслуживания

```bash
# 1. Проверить состояние всех подов
kubectl get pods -n aither-inference -o wide
kubectl get deployments -n aither-inference

# 2. Проверить health всех сервисов
curl -s http://10.129.13.78:30080/health | python3 -m json.tool
curl -s http://10.129.13.78:30902/health | python3 -m json.tool

# 3. Проверить доступность Internet-зоны
curl -sk -o /dev/null -w "%{http_code}\n" https://fb1.spb.ru:443/

# 4. Проверить доступность Test Zone
curl -s -o /dev/null -w "%{http_code}\n" http://10.129.13.78:30080/

# 5. Проверить список моделей
curl -s http://10.129.13.78:30902/v1/models | python3 -m json.tool

# 6. Выполнить дымовой тест
curl -s -X POST http://10.129.13.78:30902/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${VLLM_API_KEY}" \
  -d '{"model":"qwen-14b","messages":[{"role":"user","content":"OK"}],"max_tokens":5}' \
  | python3 -c "import sys,json; print('PASS' if 'choices' in json.load(sys.stdin) else 'FAIL')"
```

### 10.4. Обновление моделей (с даунтаймом ~5-10 мин)

```bash
# 1. Оповестить пользователей
# 2. Дождаться завершения активных запросов (мониторинг Grafana)
# 3. Обновить модель на узле
# 4. Перезапустить vLLM Deployment
kubectl rollout restart deploy/vllm-14b-instruct -n aither-inference
kubectl rollout status deploy/vllm-14b-instruct -n aither-inference --timeout=600s

# 5. Проверить загрузку модели
kubectl logs -n aither-inference deploy/vllm-14b-instruct --tail=20
# Ожидается: "Uvicorn running on http://0.0.0.0:8000"

# 6. Проверить health модели
curl -s http://10.129.13.78:30902/v1/models | python3 -m json.tool
```

---

## 11. Контакты эскалации

При возникновении инцидентов, которые невозможно решить по данному руководству, обращаться по следующей цепочке эскалации:

| Уровень | Роль | Контакт | Зона ответственности |
|---------|------|---------|---------------------|
| **L1** | DevOps / SRE | Сергей Кравчук (tg: @sergey_kravchuk) | Инфраструктура K8s, VPS, сеть, мониторинг |
| **L2** | GPU-инфраструктура | n8 (10.129.13.78) / n7 (10.129.13.77) | GPU-узлы, драйверы NVIDIA, vLLM |
| **L2** | VPS2 | 130.17.1.90 | nginx, BFF, TLS-сертификаты, VPN |
| **L3** | Резервный портал | VPS3 (89.127.217.88) | Аварийный портал при недоступности VPS2 |
| **L3** | База данных | PostgreSQL K8s (n8) | Целостность и доступность БД |

### 11.1. Матрица эскалации по типу инцидента

| Тип инцидента | Первичный контакт | Эскалация при недоступности |
|--------------|-------------------|---------------------------|
| Портал не открывается (Internet) | VPS2 (130.17.1.90) | VPS3 (89.127.217.88) |
| Модель не отвечает | GPU-узел (n8/n7) | DevOps (Сергей Кравчук) |
| База данных недоступна | PostgreSQL K8s (n8) | DevOps (Сергей Кравчук) |
| Проблемы с сетью/VPN | VPS2 (Cisco VPN) | DevOps (Сергей Кравчук) |
| TLS-сертификат истёк | VPS2 (Let's Encrypt) | DevOps (Сергей Кравчук) |

### 11.2. Аварийные каналы связи

- **Telegram:** @sergey_kravchuk
- **VPS2 SSH:** `ssh root@130.17.1.90`
- **K8s control-plane SSH:** `ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.78`
- **K8s worker SSH:** `ssh -i /root/.ssh/id_ed25519_n7n8 root@10.129.13.77`

---

## 12. Приложения

### Приложение A. Карта деплойментов и команд

| Deployment | Просмотр логов | Health Check | Перезапуск |
|-----------|---------------|-------------|-----------|
| `aither-portal-frontend` | `kubectl logs -n aither-inference deploy/aither-portal-frontend --tail=100` | `curl -s http://10.129.13.78:30080/` | `kubectl rollout restart deploy/aither-portal-frontend -n aither-inference` |
| `aither-portal-backend` | `kubectl logs -n aither-inference deploy/aither-portal-backend --tail=100` | `curl -s http://10.129.13.78:30080/health` | `kubectl rollout restart deploy/aither-portal-backend -n aither-inference` |
| `aither-bff` | `kubectl logs -n aither-inference deploy/aither-bff --tail=100` | `curl -s http://aither-bff:8000/health` | `kubectl rollout restart deploy/aither-bff -n aither-inference` |
| `aither-identity` | `kubectl logs -n aither-inference deploy/aither-identity --tail=100` | `curl -s http://aither-identity:8000/health` | `kubectl rollout restart deploy/aither-identity -n aither-inference` |
| `aither-ai-platform` | `kubectl logs -n aither-inference deploy/aither-ai-platform --tail=100` | `curl -s http://10.129.13.78:30902/health` | `kubectl rollout restart deploy/aither-ai-platform -n aither-inference` |
| `vllm-14b-instruct` | `kubectl logs -n aither-inference deploy/vllm-14b-instruct --tail=100` | `curl -s http://vllm-14b-instruct:8000/health` | `kubectl rollout restart deploy/vllm-14b-instruct -n aither-inference` |
| `vllm-32b-gptq` | `kubectl logs -n aither-inference deploy/vllm-32b-gptq --tail=100` | `curl -s http://10.99.3.103:8000/health` | `kubectl rollout restart deploy/vllm-32b-gptq -n aither-inference` |
| `aither-redis-rate-limit` | `kubectl logs -n aither-inference deploy/aither-redis-rate-limit --tail=50` | `kubectl exec deploy/aither-redis-rate-limit -n aither-inference -- redis-cli ping` | `kubectl rollout restart deploy/aither-redis-rate-limit -n aither-inference` |
| `nginx-gateway-32b` | `kubectl logs -n aither-inference deploy/nginx-gateway-32b --tail=100` | `curl -s http://nginx-gateway-32b:8000/healthz` | `kubectl rollout restart deploy/nginx-gateway-32b -n aither-inference` |

### Приложение B. Шпаргалка команд kubectl

```bash
# Статус всех подов
kubectl get pods -n aither-inference -o wide

# Статус всех деплойментов
kubectl get deployments -n aither-inference

# Статус всех сервисов
kubectl get services -n aither-inference

# Статус всех ConfigMap
kubectl get configmaps -n aither-inference

# Статус всех Secrets
kubectl get secrets -n aither-inference

# Просмотр логов пода (последние 200 строк)
kubectl logs -n aither-inference <pod-name> --tail=200

# Просмотр логов с фильтрацией по времени
kubectl logs -n aither-inference <pod-name> --since=1h

# Просмотр логов деплоймента
kubectl logs -n aither-inference deploy/<deployment-name> --tail=100

# Интерактивный shell в поде
kubectl exec -n aither-inference -it <pod-name> -- /bin/sh

# Выполнение команды в поде
kubectl exec -n aither-inference <pod-name> -- <команда>

# Описание пода (события, ресурсы, probes)
kubectl describe pod -n aither-inference <pod-name>

# Просмотр ресурсов
kubectl top pods -n aither-inference
kubectl top nodes

# Масштабирование
kubectl scale deploy/<deployment-name> -n aither-inference --replicas=3

# Просмотр YAML деплоймента
kubectl get deploy/<deployment-name> -n aither-inference -o yaml

# Редактирование деплоймента
kubectl edit deploy/<deployment-name> -n aither-inference

# Просмотр событий
kubectl get events -n aither-inference --sort-by='.lastTimestamp'

# Удаление пода
kubectl delete pod -n aither-inference <pod-name>
```

### Приложение C. План аварийного восстановления

1. **VPS2 недоступен** → использовать Test Zone напрямую: `http://10.129.13.78:30080/`
2. **n8 (control-plane) недоступен** → невозможно управлять кластером; приоритетное восстановление n8
3. **n7 (vLLM 32B) недоступен** → AI Platform автоматически маршрутизирует запросы 32B через completion; 14B остаётся доступным
4. **Полная потеря БД** → восстановление из ежедневного бэкапа (раздел 10.2)
5. **VPN-туннель (Cisco) нестабилен** → проверить контейнер `vpn-cisco` на VPS2: `docker logs vpn-cisco --tail=50`

### Приложение D. Связанные документы

- [WUI Operations Guide](../admin-guide/WUI_OPERATIONS_GUIDE.md) — Руководство администратора Web UI
- [Production Runbook](../production-runbook.md) — Production Runbook
- [API Reference](../api-reference.md) — Справочник API
- [Security Audit](../security-audit-2026-07-11.md) — Аудит безопасности
- [VPS3 Failover](../vps3-failover.md) — Отказоустойчивость VPS3
- [Gateway Management API](../gateway-management-api.md) — API управления шлюзом
- [Model Catalog](../model-catalog.md) — Каталог моделей

---

**Конец документа.**
