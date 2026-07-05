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

### Реализовано (Gates 0–4)

| Gate | Компонент | Где | Статус |
|------|-----------|-----|--------|
| 0 | NVIDIA 570 + Docker | 40.51 | ✅ |
| 1 | K8s single-node + Flannel 0.25.7 | 40.51 | ✅ |
| 2 | GPU Operator + vLLM + Qwen2.5-14B (TP=2) | 40.51 | ✅ |
| 3 | PostgreSQL 16 + Redis 7 + API Gateway | 40.51, K8s | ✅ |
| 4 | Portal BFF + Portal DB + nginx | VPS2 | ✅ |

### Не реализовано

| Функция | Приоритет | Где требуется |
|---------|-----------|---------------|
| OAuth/OIDC (вход через GitHub/Google) | P0 | VPS2 |
| Регистрация + создание организации | P0 | VPS2 |
| Управление API-ключами (создание/ротация/блокировка) | P0 | VPS2 → 40.51 |
| Billing Service (reserve → settle → refund) | P0 | 40.51 |
| Usage Collector (подсчёт токенов) | P0 | 40.51 |
| Rate Limiter (per-key, per-org) | P1 | 40.51 |
| Пополнение баланса (платёжный шлюз) | P1 | 40.51 |
| Delegation Token (не хардкод) | P1 | VPS2 → 40.51 |
| mTLS между Portal BFF и Core | P2 | VPS2 ↔ 40.51 |
| React SPA (фронтенд) | P1 | VPS2 |
| Email-уведомления (SMTP) | P2 | VPS2 |
| Аналитика потребления (графики, CSV) | P2 | VPS2 |
| Админ-панель | P3 | 40.51 |
| Восстановление 40.50 (второй узел K8s) | P3 | 40.50 |

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

`dedvmedved-dot/aither-project` — 8 коммитов, ветка main
