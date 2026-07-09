# CI/CD — GitHub Actions → K8s

**Версия:** 1.0 | **Дата:** 09.07.2026

---

## Pipeline

```
PR → CI (lint, validate) → Merge → CD (SSH → VPS2 → kubectl)
                    ↓
              Telegram-уведомление
```

### CI (`.github/workflows/ci.yml`)

Запускается на каждый PR и push в `main`:

| Job | Что проверяет |
|---|---|
| `lint-python` | ruff + pyflakes для `gateway/*.py` |
| `lint-shell` | ShellCheck для `scripts/*.sh` |
| `validate-k8s` | kubeconform для `k8s/**/*.yaml` |
| `lint-bash-scripts` | `bash -n` синтаксис |
| `test-deploy-dry-run` | Структура манифестов, импорты Python |

### CD (`.github/workflows/deploy.yml`)

Запускается на push в `main` (при изменении кода) или вручную (`workflow_dispatch`):

```
GitHub Actions → SSH (appleboy/ssh-action) → VPS2 → deploy.sh
```

**Компоненты деплоя:**

| Команда | Что деплоится |
|---|---|
| `deploy.sh all` | Всё: gateway + vllm + portal + hpa |
| `deploy.sh gateway` | Gateway ConfigMap + rollout restart |
| `deploy.sh vllm` | Drain → restart vLLM → undrain |
| `deploy.sh portal` | docker-compose up на VPS2 + VPS3 |
| `deploy.sh config` | ConfigMaps + HPA |
| `deploy.sh hpa` | Только HPA-манифесты |

## Настройка

### 1. GitHub Secrets

Добавить в Settings → Secrets and variables → Actions:

| Secret | Значение |
|---|---|
| `VPS2_HOST` | `130.17.1.90` |
| `VPS2_USER` | `root` |
| `VPS2_SSH_KEY` | Приватный ключ (`~/.ssh/id_ed25519`) |
| `TELEGRAM_BOT_TOKEN` | Токен бота для уведомлений |
| `TELEGRAM_CHAT_ID` | ID чата для уведомлений |

### 2. SSH-ключ на VPS2

```bash
# На VPS1:
cat ~/.ssh/id_ed25519.pub

# Добавить в /root/.ssh/authorized_keys на VPS2
```

### 3. Репозиторий на VPS2

```bash
ssh root@130.17.1.90
cd /root
git clone git@github.com:dedvmedved-dot/aither-project.git
cd aither-project
chmod +x scripts/deploy.sh scripts/health-check.sh
```

## Ручной деплой

```bash
# С VPS1:
ssh root@130.17.1.90 "cd /root/aither-project && git pull && bash scripts/deploy.sh all"

# Компонентный деплой:
ssh root@130.17.1.90 "cd /root/aither-project && bash scripts/deploy.sh gateway"
```

## Пропуск деплоя

Добавить `[skip-deploy]` в сообщение коммита — CD не запустится:

```bash
git commit -m "docs: update roadmap [skip-deploy]"
```

## Мониторинг деплоя

```bash
# Статус подов после деплоя
kubectl get pods -l app=gateway
kubectl rollout history deployment/gateway

# Откат (если деплой сломал)
kubectl rollout undo deployment/gateway
kubectl rollout undo deployment/vllm-qwen
```

## Telegram-уведомления

После каждого деплоя бот отправляет:

```
🚀 Deploy #42
Репо: dedvmedved-dot/aither-project
Ветка: main
Коммит: efda2e9
Автор: dedvmedved-dot
Статус: success
```
