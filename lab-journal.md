
## 10.07.2026 14:00 — #28 HPA (автомасштабирование) + #29 CI/CD (Docker-образ Gateway)

### Контекст
После дорожной карты выяснилось: #13 (YooKassa), #15 (Parsec), #27 (Production) отложены на конец.
В приоритете #28 и #29.

### #28 HPA — Диагноз и исправление

**Проблема:** vLLM HPA показывали `<unknown>` для CPU/memory. Причина — поды запрашивали только GPU (`nvidia.com/gpu: 2`), без CPU/memory resource requests.

**Исправлено:**

| Деплоймент | Было | Стало |
|---|---|---|
| `vllm-qwen` (14B) | requests: GPU only | requests: cpu=4, mem=32Gi; limits: cpu=16, mem=64Gi |
| `vllm-qwen32b` (32B) | requests: GPU only | requests: cpu=4, mem=32Gi; limits: cpu=16, mem=64Gi |

**Попутно:** стратегия деплоя `Recreate` вместо `RollingUpdate` — иначе новый под не может стартовать (GPU заняты старым).

**Результат HPA:**
```
gateway-hpa    CPU 1%/70%,  Mem 26%/80%   min=1, max=3  ✅
vllm-14b-hpa   CPU 44%/80%, Mem 2%/85%    min=1, max=1  ✅ (исправлен)
vllm-32b-hpa   CPU 36%/80%, Mem 3%/85%    min=1, max=1  ✅ (исправлен)
```

**Ограничение:** `maxReplicas=1` — на каждом узле ровно 2 GPU, масштабирование включится при добавлении узлов.

**Эталонные манифесты** экспортированы в `k8s/vllm-14b/` и `k8s/vllm-32b/` (deployment.yaml + service.yaml).

### #29 CI/CD — Docker-образ Gateway

**Было:** Gateway = `python:3.12-slim` + 14 файлов через ConfigMap + `pip install` при старте.

**Стало:**

| Компонент | Файл |
|---|---|
| Dockerfile | `gateway/Dockerfile` — `python:3.12-slim`, COPY всех .py, pip install, HEALTHCHECK |
| Зависимости | `gateway/requirements.txt` — redis, pyjwt, psycopg2-binary, pyyaml |
| K8s-деплоймент | `k8s/gateway/deployment.yaml` — образ `ghcr.io/dedvmedved-dot/aither-project-gateway:latest` |
| CI/CD workflow | `.github/workflows/deploy.yml` — сборка + push в ghcr.io + kubectl set image + health-check + rollback |

**Пайплайн:**
```
Push в main (gateway/**) →
  changes (paths-filter) →
  build-gateway (Docker build + push в ghcr.io) →
  deploy (kubectl set image + rollout status) →
  health-check (5 попыток curl /health) →
  rollback (kubectl rollout undo при провале) →
  Telegram-уведомление
```

**Тестовая сборка** на VPS1: образ собирается (52 MB), импорты работают (redis, pyjwt, psycopg2, pyyaml, все 11 модулей gateway).

### ⚠️ Не сделано (отложено до финала проекта)

| # | Что | Почему отложено |
|---|---|---|
| 1 | GitHub Actions secrets (VPS2_HOST, etc.) | Без них деплой-степ падает, но сборка образа работает. Текущий ConfigMap-деплой функционирует. |
| 2 | Сделать ghcr.io пакет публичным | K8s не может пулить приватный пакет без imagePullSecrets. Нужно после первой успешной сборки в Actions. |
| 3 | Применить `k8s/gateway/deployment.yaml` | Переключит Gateway с ConfigMap на Docker-образ. Без образа в ghcr.io под не стартует. |

**Когда делать:** в конце проекта, одним блоком: дёрнуть workflow → сделать пакет публичным → `kubectl apply -f k8s/gateway/deployment.yaml`.

### Коммиты
```
722c827 feat(hpa): resource requests для vLLM + Recreate-стратегия + эталонные манифесты
5f617c5 feat(ci-cd): Docker-образ Gateway + health-check + rollback
e32a528 fix(ci-cd): make ghcr.io package public + trigger on push
93acce3 ci: trigger deploy workflow
```
