# Aither Project

**Token‑as‑a‑Service** — платформа для продажи токенов к LLM через OpenAI‑совместимый API.

## Статус MVP — ✅ Gates 0–5 пройдены

| Gate | Компонент | Где | Статус |
|------|-----------|-----|--------|
| 0 | NVIDIA 570 + Docker 28 | 40.51 | ✅ |
| 1 | K8s 1.33 single‑node + Flannel 0.25.7 | 40.51 | ✅ |
| 2 | GPU Operator + vLLM + Qwen2.5‑14B (TP=2) | 40.51 | ✅ |
| 3 | PostgreSQL 16 + Redis 7 + API Gateway | 40.51, K8s | ✅ |
| 4 | Portal BFF + Portal DB + nginx | VPS2, Docker | ✅ |
| 5 | Аутентификация, организации, API‑ключи | VPS2 → 40.51 | ✅ |

## Архитектура

```
Клиент → http://130.17.1.90:80 (nginx) → Portal BFF :3000 → Portal DB :5432
                                                    ↓ (Cisco VPN tun1)
                                           10.129.13.78:30900 (gateway) → vLLM :8000
                                                                         → PostgreSQL 16
                                                                         → Redis 7
```

```
┌──────────────────────────────────────────────────────────────┐
│                         VPS2 (130.17.1.90)                   │
│  ┌─────────┐   ┌──────────────┐   ┌───────────────────────┐  │
│  │  nginx  │ → │ Portal BFF   │ → │ Portal DB (PostgreSQL)│  │
│  │  :80    │   │ Fastify :3000│   │ 127.0.0.1:5432        │  │
│  └─────────┘   └──────┬───────┘   └───────────────────────┘  │
│                       │ Cisco VPN tun1                        │
└───────────────────────┼──────────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────────┐
│           40.51 YADRO VEGMAN S320 (10.129.13.78)             │
│                       │                                       │
│  ┌────────────────────▼──────────────────────────────────┐   │
│  │            API Gateway (Python) :30900                 │   │
│  │            • Rate limiting (Redis)                     │   │
│  │            • Auth (JWT RS256 — TODO)                   │   │
│  │            • Proxy → vLLM                              │   │
│  └───┬──────────────────────┬────────────────────────────┘   │
│      │                      │                                 │
│  ┌───▼──────────┐   ┌───────▼──────────┐                     │
│  │  vLLM :8000  │   │  PostgreSQL 16   │                     │
│  │  TP=2, RTX×2 │   │  aither          │                     │
│  │  Qwen2.5-14B │   │  :5432           │                     │
│  └──────────────┘   └──────────────────┘                     │
│      ┌──────────────┐                                        │
│      │  Redis 7     │                                        │
│      │  :6379       │                                        │
│      └──────────────┘                                        │
└──────────────────────────────────────────────────────────────┘
```

## Оборудование

| Сервер | BMC | ОС | CPU | RAM | GPU | Диски |
|--------|-----|----|-----|-----|-----|-------|
| 40.51 | 10.129.40.51:9444 | Astra Linux 1.8 | 2× Xeon 6258R (56C/112T) | 754 GB | 2× RTX 6000 (24 GB) | 447 GB + 12× SAS SSD |
| 40.50 | 10.129.40.50:9443 | нет | 2× Xeon 6258R (56C/112T) | 768 GB | 2× RTX 6000 (24 GB) | RAID сбой |

## Подключение

**Портал (извне):**
```bash
curl http://130.17.1.90:80/health
```

**40.51 (ядро, через VPS2):**
```bash
ssh root@130.17.1.90 "sshpass -p root ssh root@10.129.13.78"
```

**Проверка vLLM:**
```bash
curl http://10.129.13.78:30900/v1/models  # с VPS2
```

## API портала (v0.3.0)

### Аутентификация
```bash
curl -X POST http://130.17.1.90:80/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"name":"sergey"}'
# → access_token (JWT, 24h)
```

### Организации
```bash
# Создать
curl -X POST http://130.17.1.90:80/api/v1/orgs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"MyOrg"}'

# Список
curl -H "Authorization: Bearer $TOKEN" \
  http://130.17.1.90:80/api/v1/orgs
```

### API-ключи
```bash
# Создать (только owner)
curl -X POST http://130.17.1.90:80/api/v1/orgs/$ORG_ID/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"default"}'

# Отозвать
curl -X DELETE http://130.17.1.90:80/api/v1/orgs/$ORG_ID/api-keys/$KEY_ID \
  -H "Authorization: Bearer $TOKEN"
```

## Модель

**Qwen2.5‑14B‑Instruct** — 28 GB, размещена на хосте 40.51 (`/data/models/`), загружается в vLLM через hostPath. Инференс: TP=2 на обеих RTX 6000.

## Структура репозитория

```
aither-project/
├── README.md               ← этот файл
├── lab-journal.md          ← лабораторный журнал (Gates 0–5, детально)
├── bortovoy-zhurnal.md     ← бортовой журнал (краткая хронология)
├── status.md               ← статус реализованного/нереализованного
├── hosts/                  ← инвентаризация хостов
├── manifests/              ← K8s-манифесты, IP-план
├── references/             ← ТР, аналитика, адаптация под single-node
├── diagrams/               ← схемы (Graphviz)
├── portal/                 ← код портала (BFF, nginx, docker-compose)
└── plan.md                 ← план работ
```

## Журналы

- [lab-journal.md](lab-journal.md) — детальный лабораторный журнал (команды, разбор, питфоллы)
- [bortovoy-zhurnal.md](bortovoy-zhurnal.md) — краткая хронология всех событий
- [status.md](status.md) — что сделано / что осталось
