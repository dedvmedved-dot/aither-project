# Aither Platform — офлайн-пакет развёртывания

**Версия:** 1.0.0  
**Дата:** 11.07.2026  
**Назначение:** Развёртывание платформы Aither в изолированном контуре без доступа в Интернет

---

## Что это

Самодостаточный пакет для развёртывания AI-платформы Aither на bare-metal серверах
с GPU (NVIDIA RTX 6000/8000) под управлением Astra Linux SE 1.8.

Включает всё необходимое: Kubernetes-манифесты, Docker-образы, Python-зависимости,
NPM-пакет портала, скрипты эксплуатации, документацию и приёмо-сдаточные тесты.

## Состав пакета

```
offline-deploy/
├── README.md                   ← этот файл
├── VERSION                     ← версия пакета
├── Makefile                    ← make deploy / make test / make docs
├── CHANGELOG.md                ← история версий
│
├── docs/                       ← документация
│   ├── 01-architecture.md      ← архитектура платформы
│   ├── 02-deployment-guide.md  ← пошаговое развёртывание
│   ├── 03-admin-guide.md       ← руководство администратора
│   ├── 04-user-guide.md        ← руководство пользователя
│   ├── 05-security-model.md    ← модель угроз и меры защиты
│   ├── 06-troubleshooting.md   ← типовые проблемы
│   ├── 07-api-reference.md     ← OpenAPI + примеры запросов
│   └── 08-upgrade-guide.md     ← процедура обновления
│
├── playbooks/                  ← Ansible playbooks
│   ├── ansible.cfg
│   ├── inventory.yml.template
│   ├── site.yml                ← главный playbook
│   ├── 01-prerequisites.yml    ← подготовка ОС
│   ├── 02-gpu-setup.yml        ← NVIDIA + containerd
│   ├── 03-k8s-deploy.yml       ← Kubernetes
│   ├── 04-storage.yml          ← хранилище
│   ├── 05-vllm-deploy.yml      ← vLLM с моделями
│   ├── 06-gateway-deploy.yml   ← Gateway + Redis + PostgreSQL
│   ├── 07-portal-deploy.yml    ← Портал + ChromaDB
│   ├── 08-monitoring-deploy.yml ← Prometheus + Grafana
│   └── 09-post-deploy.yml      ← проверки, seed-данные
│
├── k8s/                        ← Kubernetes-манифесты
│   ├── namespace.yaml
│   ├── gateway/                ← deployment, service, configmap
│   ├── vllm-14b/               ← deployment, service
│   ├── vllm-32b/               ← deployment, service
│   ├── postgres/               ← deployment, service, init-schema
│   ├── redis/                  ← deployment, service
│   ├── chromadb/               ← deployment, service
│   └── monitoring/             ← prometheus, grafana, dashboards
│
├── offline/                    ← офлайн-зависимости
│   ├── README.md               ← инструкция по переносу
│   ├── docker/                 ← save.sh, load.sh, images.tar.gz
│   ├── pip/                    ← requirements.txt, download.sh, install.sh
│   ├── npm/                    ← portal-offline.tgz, install.sh
│   ├── models/                 ← transfer.sh, model-list.txt
│   └── checksums.sha256        ← контрольные суммы
│
├── scripts/                    ← скрипты эксплуатации
│   ├── health-check.sh         ← проверка всех компонентов
│   ├── backup.sh               ← резервное копирование
│   ├── restore.sh              ← восстановление из бэкапа
│   ├── rotate-keys.sh          ← ротация API-ключей
│   ├── seed-data.sql           ← начальные данные
│   ├── create-admin.sh         ← создание администратора
│   └── collect-logs.sh         ← сбор логов
│
├── configs/                    ← эталонные конфигурации
│   ├── nginx/nginx.conf
│   ├── bff/.env.template
│   ├── gateway/config.yaml.template
│   └── vllm/args.txt
│
└── tests/                      ← приёмо-сдаточные тесты
    ├── 01-smoke.sh
    ├── 02-api.sh
    ├── 03-security.sh
    ├── 04-load.sh
    └── expected/               ← ожидаемые результаты
```

## Быстрый старт

### 1. Подготовка носителя

```bash
# На машине с интернетом
cd offline-deploy/
make bundle    # собирает все офлайн-зависимости в один архив
```

### 2. Перенос в закрытый контур

Скопируйте каталог `offline-deploy/` на флеш-носитель → целевая машина.

### 3. Загрузка зависимостей

```bash
cd offline-deploy/
make offline-load    # загружает Docker-образы, pip-пакеты, npm-пакет
```

### 4. Развёртывание

```bash
make deploy    # ansible-playbook site.yml
```

### 5. Проверка

```bash
make test      # приёмо-сдаточные тесты
```

## Системные требования

### Минимальные

| Компонент | Требование |
|---|---|
| ОС | Astra Linux SE 1.8 (Смоленск) |
| CPU | 28 ядер (допустимо 16) |
| RAM | 128 GB (допустимо 64 GB) |
| GPU | 2× NVIDIA RTX 6000/8000 |
| Диск | 500 GB SSD (модели ~200 GB) |
| Сеть | 10 Gbps между узлами |

### Рекомендованные (для 32B модели)

| Компонент | Требование |
|---|---|
| CPU | 56 потоков (2× Xeon) |
| RAM | 256 GB |
| GPU | 2× NVIDIA RTX 6000 (48 GB каждая) |
| Диск | 1 TB NVMe |

## Что внутри

### Модели

| Модель | Размер | GPU | Назначение |
|---|---|---|---|
| Qwen 2.5 14B Instruct | ~28 GB | 1× RTX 6000 | Чат, код, простые задачи |
| Qwen 2.5 32B Instruct GPTQ | ~20 GB | 1× RTX 6000 | Анализ, сложные задачи |
| nomic-embed-text | ~274 MB | CPU | Эмбеддинги для RAG |

### Сервисы

| Сервис | Порт | Описание |
|---|---|---|
| Портал (SPA) | 80 | Веб-интерфейс |
| BFF (Node.js) | 3000 | API, авторизация |
| Gateway (Python) | 30900 | Rate Limit, биллинг, безопасность |
| vLLM 14B | 32293 | Инференс 14B |
| vLLM 32B | 32294 | Инференс 32B |
| PostgreSQL | 31113 | Биллинг, пользователи |
| Redis | 6379 | Rate Limiter |
| ChromaDB | 8000 | Векторная БД |
| Grafana | 30300 | Дашборды |
| Prometheus | 30909 | Метрики |

## Лицензия и ограничения

Пакет предназначен для использования внутри организации.
Распространение третьим лицам — по согласованию с разработчиками.
