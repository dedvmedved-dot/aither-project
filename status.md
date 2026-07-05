# Статус проекта Aither — 05.07.2026

## Подключение

**Портал (проверка извне):**
```bash
curl http://130.17.1.90:80/health
curl http://130.17.1.90:80/api/v1/status
```

**VPS2 (130.17.1.90):**
```bash
ssh root@130.17.1.90
```

**40.51 — ядро (10.129.13.78):**
```bash
ssh root@130.17.1.90 "sshpass -p root ssh root@10.129.13.78"
```

**Проверка ядра с VPS2:**
```bash
curl http://10.129.13.78:30900/health
curl http://10.129.13.78:30900/v1/models
```

**Проверка K8s на 40.51:**
```bash
kubectl get pods -A
kubectl get svc -A
```

---

## Функционал: что реализовано / что нет

### Реализовано (Gates 0–10)

| Gate | Компонент | Где | Статус |
|------|-----------|-----|--------|
| 0 | NVIDIA 570 + Docker | 40.51 | ✅ |
| 1 | K8s single-node + Flannel 0.25.7 | 40.51 | ✅ |
| 2 | GPU Operator + vLLM + Qwen2.5-14B (TP=2) | 40.51 | ✅ |
| 3 | PostgreSQL 16 + Redis 7 + API Gateway | 40.51, K8s | ✅ |
| 4 | Portal BFF + Portal DB + nginx | VPS2 | ✅ |
| 5 | Dev-аутентификация + JWT | VPS2 | ✅ |
| 6 | Организации + участники | VPS2 | ✅ |
| 7 | API-ключи (ak-...) + ротация | VPS2 | ✅ |
| 8 | Billing (reserve→settle→refund) + Usage | 40.51 | ✅ |
| 9 | Портал SPA (дашборд, организации) | VPS2 | ✅ |
| 10 | Чат-портал (SSE streaming, история, share) | VPS2 | ✅ |

### Доработки чата (05.07.2026)

- ✅ Лейаут DeepSeek-style (3 независимые зоны)
- ✅ Удаление чатов
- ✅ Подсветка синтаксиса (python/bash/js/sql) — встроенная
- ✅ Авто-# для русских строк в коде
- ✅ Сохранение chatId в localStorage (не плодит пустые чаты)
- ✅ Изоляция чатов по user_id

### Не реализовано

| Функция | Приоритет | Где |
|---------|-----------|-----|
| Rate Limiter (per-key, per-org) | P1 | 40.51 |
| Пополнение баланса (платёжный шлюз) | P1 | 40.51 |
| mTLS между Portal BFF и Core | P2 | VPS2 ↔ 40.51 |
| Email-уведомления (SMTP) | P2 | VPS2 |
| Аналитика потребления (графики, CSV) | P2 | VPS2 |
| Админ-панель | P3 | 40.51 |
| Восстановление 40.50 (второй узел K8s) | P3 | 40.50 |
| Доп. модели (Saiga, Qwen Coder 14B, Qwen 32B GPTQ) | P1 | 40.51 |

---

## Архитектура

```
Клиент → http://130.17.1.90:80 (nginx) → Portal BFF :3000 → Portal DB :5432
                                                    ↓ (Cisco VPN tun1)
                                           10.129.13.78:30900 (gateway) → vLLM :8000
                                                                         → PostgreSQL
                                                                         → Redis
```

## Репозиторий

`dedvmedved-dot/aither-project` — 73 коммита, ветка main
