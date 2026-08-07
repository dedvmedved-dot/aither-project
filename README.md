# Aither — AI Platform

**Платформа для работы с большими языковыми моделями через Web-интерфейс и OpenAI-совместимый API.**

---

## Текущий проект

| Параметр | Значение |
|----------|---------|
| **Активная ветка** | [`aither-v2`](aither-v2/) |
| **Application baseline** | `39a8946143e7a38ceff9faabad024225acbf202e` |
| **Documentation baseline** | `8b76669969a69b68dba5766eaf72d5b1b3f21d8b` |
| **Документация обновлена** | 2026-08-07 |
| **Environment** | HOME LAB / TEST |
| **Production acceptance** | NOT GRANTED |
| **External acceptance** | PENDING EXTERNAL CONNECTOR AUDIT |

---

## Текущие модели

| Модель | Model ID | Scope | Контекст |
|--------|----------|-------|----------|
| Qwen2.5-32B-Instruct-AWQ | `qwen2.5-32b-instruct` | `model:32b:chat` | 32K native; деградация ~34K |
| Qwen3-32B-AWQ | `qwen3-32b` | `model:qwen3:chat` | 32K + YaRN; деградация ~50K |

> Git configuration confirmed. Runtime deployment reported by Hermes (06–07.08.2026).

---

## Навигация

| Документ | Описание |
|----------|----------|
| [`aither-v2/README.md`](aither-v2/README.md) | **Основной технический README** — архитектура, модели, компоненты, API |
| [`aither-v2/docs/current-state/`](aither-v2/docs/current-state/) | Текущее состояние, история изменений, матрица, дефекты |
| [`aither-v2/docs/models/MODEL_CATALOG.md`](aither-v2/docs/models/MODEL_CATALOG.md) | Каталог моделей |
| [`aither-v2/docs/hermes-aither-connection.md`](aither-v2/docs/hermes-aither-connection.md) | Подключение Hermes Agent |
| [`aither-v2/reports/`](aither-v2/reports/) | Отчёты |

---

## Структура репозитория

```
aither-project/
├── README.md                    ← этот файл
├── aither-v2/                   ← основной проект
│   ├── README.md                ← технический README
│   ├── deploy/                  ← манифесты (vLLM, gateway, etc.)
│   ├── services/                ← код (portal, identity, BFF)
│   ├── docs/                    ← документация
│   └── reports/                 ← отчёты
├── 01-k8s-gpu-operator/         ← GPU Operator
├── 02-containerd-nvidia-runtime/ ← NVIDIA runtime
├── 03-vllm-14b-deploy/          ← исторический: vLLM 14B
├── docs/                        ← общая документация
│   ├── mvp-roadmap/             ← дорожная карта MVP
│   ├── evidence/                ← доказательства стадий
│   ├── project-control/         ← управление проектом
│   ├── repository/              ← управление репозиторием
│   └── user-package/            ← пакет пользователя
├── reports/                     ← отчёты
└── lab-journal.md               ← лабораторный журнал
```

---

## Подключение

**Тестовая зона (внутренняя сеть/VPN):**
```bash
curl http://10.129.13.78:30080/
```

**Портал (Internet):**
```bash
curl https://fb1.spb.ru:10443/
```

**Безопасный SSH:**
```bash
ssh <user>@<bastion>
# или с ProxyJump:
ssh -J <user>@<bastion> <user>@<target>
```

---

## Историческая архитектура

<details>
<summary>MVP Gates 0–5 (завершено) — VPS2 + 40.51</summary>

Предыдущая версия платформы: VPS2 (Portal BFF + PostgreSQL) → Cisco VPN → 40.51 YADRO VEGMAN (vLLM Qwen2.5-14B, Redis, PostgreSQL).

| Gate | Компонент | Статус |
|------|-----------|--------|
| 0 | NVIDIA 570 + Docker 28 | ✅ |
| 1 | K8s 1.33 single-node + Flannel | ✅ |
| 2 | GPU Operator + vLLM + Qwen2.5-14B | ✅ |
| 3 | PostgreSQL 16 + Redis 7 + API Gateway | ✅ |
| 4 | Portal BFF + Portal DB + nginx | ✅ |
| 5 | Аутентификация, организации, API-ключи | ✅ |

Подробнее: [`lab-journal.md`](lab-journal.md), [`bortovoy-zhurnal.md`](bortovoy-zhurnal.md)

</details>

---

## Безопасность

> ⚠️ В исторических файлах могут находиться примеры с паролями. **Не использовать в production.** Текущая документация не содержит credentials.
