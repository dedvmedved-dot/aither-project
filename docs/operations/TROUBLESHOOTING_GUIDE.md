# Aither AI Platform — Руководство по устранению неисправностей

**Версия:** OPS-01-R1  
**Дата:** 26 июля 2026  
**Назначение:** Диагностика и устранение типовых эксплуатационных проблем  
**Namespace:** `aither-inference`

---

## 1. Быстрая диагностика

```bash
# Проверка статуса всех подов
kubectl get pods -n aither-inference -o wide

# Проверка статуса всех деплойментов
kubectl get deployments -n aither-inference

# Проверка последних событий
kubectl get events -n aither-inference --sort-by='.lastTimestamp' | tail -20
```

---

## 2. Проблемы с доступностью портала

### 2.1. Портал не открывается (HTTP 502/503/504)

**Internet Zone (https://fb1.spb.ru:443):**
```bash
# 1. Проверить VPS2 nginx
ssh vps2 'systemctl status nginx'
ssh vps2 'nginx -t'

# 2. Проверить pod aither-portal-frontend
kubectl get pods -n aither-inference -l app=aither-portal-frontend
kubectl logs -n aither-inference deployment/aither-portal-frontend --tail=50

# 3. Проверить BFF
kubectl logs -n aither-inference deployment/aither-bff --tail=50 | grep -i error

# 4. Проверить ConfigMap актуальность
kubectl get configmap aither-portal-frontend-config -n aither-inference -o yaml | head -20
```

**Test Zone (http://10.129.13.78:30080):**
```bash
kubectl get pods -n aither-inference -l app=aither-portal
kubectl logs -n aither-inference deployment/aither-portal --tail=50
```

### 2.2. Портал показывает ошибку входа

```bash
# Проверить identity service
kubectl logs -n aither-inference deployment/aither-identity --tail=50 | grep -i error

# Проверить BFF auth
kubectl logs -n aither-inference deployment/aither-bff --tail=50 | grep -i "auth\|login\|401\|403"

# Проверить Secret
kubectl get secret aither-bff-auth -n aither-inference -o yaml | grep -c "ADMIN_USERNAME\|SESSION_SECRET"
```

---

## 3. Проблемы с моделями

### 3.1. Модель не отвечает (HTTP 503/504)

```bash
# Проверить vLLM поды
kubectl get pods -n aither-inference -l 'app in (vllm-14b-instruct,vllm-32b-gptq)'

# Проверить использование GPU
kubectl exec -n aither-inference deployment/vllm-14b-instruct -- nvidia-smi 2>/dev/null || \
  kubectl logs -n aither-inference deployment/vllm-14b-instruct --tail=20

# Проверить nginx gateway
kubectl logs -n aither-inference deployment/nginx-gateway-32b --tail=20 | grep -i error

# Проверить AI Platform
kubectl logs -n aither-inference deployment/aither-ai-platform --tail=20 | grep -i error
```

### 3.2. Модель возвращает пустой ответ

```bash
# Проверить загрузку модели
kubectl logs -n aither-inference deployment/vllm-14b-instruct | grep -i "loading\|ready\|model"

# Проверить доступность через API
curl -s http://10.129.13.78:30080/api/v1/models
```

---

## 4. Проблемы с API-ключами

### 4.1. Ключ не создаётся

```bash
# Проверить BFF токены
kubectl logs -n aither-inference deployment/aither-bff --tail=50 | grep -i "token\|key"

# Проверить Redis (key service)
kubectl get pods -n aither-inference -l app=aither-redis-rate-limit
kubectl exec -n aither-inference deployment/aither-redis-rate-limit -- redis-cli ping
```

### 4.2. Ключ возвращает 401

```bash
# Проверить формат ключа (athr_...)
# Проверить срок действия
# Проверить статус отзыва через Web UI
```

---

## 5. Проблемы с производительностью

### 5.1. Высокая задержка ответа

```bash
# Проверить загрузку GPU
kubectl exec -n aither-inference deployment/vllm-14b-instruct -- nvidia-smi

# Проверить использование CPU/памяти подами
kubectl top pods -n aither-inference

# Проверить rate limiting
kubectl logs -n aither-inference deployment/aither-redis-rate-limit --tail=20
```

### 5.2. Ошибки rate limit (HTTP 429)

```bash
# Проверить конфигурацию rate limit в BFF
kubectl get configmap aither-bff-config -n aither-inference -o yaml

# Проверить Redis
kubectl exec -n aither-inference deployment/aither-redis-rate-limit -- redis-cli INFO stats
```

---

## 6. Проблемы с деплойментом

### 6.1. Pod в CrashLoopBackOff

```bash
POD=<pod-name>
kubectl describe pod $POD -n aither-inference | grep -A10 "Events:"
kubectl logs $POD -n aither-inference --previous
```

### 6.2. Деплоймент не обновляется (stuck rollout)

```bash
kubectl rollout status deployment/<name> -n aither-inference --timeout=120s
kubectl describe deployment/<name> -n aither-inference | grep -A5 "Conditions:"
```

---

## 7. Диагностическая информация для escalation

При обращении в поддержку подготовьте:

```bash
# Снимок состояния кластера
kubectl get all -n aither-inference > cluster-state.txt

# Логи проблемного компонента (последние 200 строк)
kubectl logs -n aither-inference deployment/<component> --tail=200 > logs.txt

# Описание проблемного пода
kubectl describe pod <pod-name> -n aither-inference > pod-describe.txt
```

---

## 8. Справочник HTTP-кодов

| Код | Значение | Действие |
|-----|----------|----------|
| 200 | OK | Штатная работа |
| 401 | Не авторизован | Проверить API-ключ / сессию |
| 403 | Доступ запрещён | Проверить scope ключа |
| 404 | Не найдено | Проверить URL / ID модели |
| 429 | Rate limit | Подождать, проверить лимиты |
| 500 | Внутренняя ошибка | Проверить логи BFF / AI Platform |
| 502 | Ошибка шлюза | Проверить VPS2 nginx → K8s связь |
| 503 | Сервис недоступен | Проверить поды, перезапустить |
| 504 | Таймаут | Модель не успела ответить, увеличить timeout |
