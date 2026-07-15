# Changelog

## [1.2.0] — 10.07.2026

### Добавлено

- **chroma-proxy**: новый компонент (Deployment + Service + ConfigMap `chroma-proxy-script`)
- **hybrid_rag.py**: гибридный RAG (Wiki Graph + ChromaDB через прокси) в Gateway
- **k8s/chromadb/chroma-proxy.yaml**: полный манифест (ConfigMap с proxy.py, Deployment, Service)
- **PVC chromadb-data**: ReadWriteOnce, 20Gi, привязан к n7-gpu
- **Gateway**: env `CHROMA_PROXY_URL`, 13 модулей (добавлен `hybrid_rag.py`)
- `docs/02-deployment-guide.md`: шаг проверки RAG после деплоя

### Изменено

- **ChromaDB**: образ `chromadb/chroma:0.5.23` (НЕ latest — 0.6.3 REST API сломан)
- **ChromaDB**: namespace `default`, PVC RWO, nodeSelector на n7-gpu
- **Gateway**: комментарий о 13 модулях (было 11)
- **images.txt**: `chromadb/chroma:latest` → `chromadb/chroma:0.5.23`, примечание о версии
- **01-architecture.md**: добавлен chroma-proxy в диаграмму и таблицу компонентов, секция RAG-архитектуры
- **config.yaml.template**: добавлен `CHROMA_PROXY_URL`

### Архитектура RAG

```
Gateway (hybrid_rag.py)
  ├─ Wiki Graph (keyword, 8 стр.)
  └─ chroma-proxy :9000 → all-MiniLM-L6-v2 → ChromaDB :8000
```

Gateway НЕ содержит зависимостей chromadb/sentence-transformers — всё в прокси.

## [1.1.0] — 07.07.2026

### Изменено

- **Gateway**: переход на Docker-образ `ghcr.io/dedvmedved-dot/aither-project-gateway:latest`
  (python:3.12-slim, 11 модулей). ConfigMap для кода удалён, код в образе.
- **Gateway**: добавлены ConfigMap `gateway-wiki` и `delegation-public-key`
- **vLLM 14B**: TP=2, 2× GPU, добавлен LoRA-адаптер `astra-14b` (rank=8, 65 MB)
- **vLLM 14B**: удалён `--enforce-eager` (падение скорости 2.5×), результат 28 tok/s
- **vLLM 32B**: TP=2, 2× GPU, `--tensor-parallel-size 2`
- **vLLM**: стратегия деплоймента → `Recreate` (избегание дедлока GPU)
- **HPA**: добавлен Gateway HPA (min=1, max=3, метрики active requests + rps)
- **Namespace**: всё в `default` (соответствует живому кластеру)
- **K8s-манифесты**: полная синхронизация с живым деплойментом

### Конфигурация

- `configs/vllm/args.txt`: добавлены LoRA-аргументы, TP=2, примечание про `--enforce-eager`
- `offline/docker/images.txt`: обновлён список образов (удалён python:3.11-slim)
- `offline/pip/requirements.txt`: синхронизирован с `gateway/requirements.txt` (redis>=5.0)

### Документация

- `docs/diagrams/physical-architecture.svg`: белый фон (Material Design pastel) — для DOCX/печати

## [1.0.0] — 11.07.2026

### Добавлено

- Пакет офлайн-развёртывания для закрытого контура
- K8s-манифесты: Gateway, vLLM 14B, vLLM 32B, PostgreSQL, Redis, ChromaDB
- Ansible playbooks для полного цикла (ОС → GPU → K8s → vLLM → Портал)
- Скрипты эксплуатации: health-check, backup/restore, ротация ключей
- Приёмо-сдаточные тесты: smoke, API, security
- Документация: архитектура, деплой, админ, пользователь, безопасность
- Офлайн-зависимости: docker save/load, pip download, npm pack

### Компоненты платформы

- Портал (SPA + BFF) — веб-интерфейс, OAuth, чаты, биллинг
- Gateway — Rate Limiter, AI Security (DLP + Prompt Injection), биллинг
- vLLM 14B + 32B — инференс на 2× RTX 6000 (TP=2)
- PostgreSQL — биллинг, пользователи, организации
- Redis — Rate Limiter (sliding window)
- ChromaDB — векторная БД для RAG
- Prometheus + Grafana — мониторинг GPU, инференса, биллинга
