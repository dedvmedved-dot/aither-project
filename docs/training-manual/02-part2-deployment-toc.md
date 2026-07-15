# Часть II. Практическое развёртывание

**Документ:** `02-part2-deployment.md` · 6 глав · ~140 стр. · 18 схем · 20 таблиц

> Пошаговый деплой всей системы: от голого железа до production.
> Каждая команда объяснена. Каждый манифест разобран построчно.

---

## Глава 8. Подготовка серверов и установка ОС (18 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 8.1 | Обзор инфраструктуры Aither | 3 | 1 | 1 | 5 узлов: VPS1, VPS2, Cisco815, n8, n7. Роли каждого. IP-адреса, порты, туннели. Схема физических подключений. Таблица: узел, IP, доступы (SSH, BMC, K8s) |
| 8.2 | Установка Astra Linux SE 1.8 через Kickstart | 6 | 1 | 1 | BMC: загрузка ISO, консоль. Kickstart-файл: `ks-node01.cfg` построчно (network, disk, packages, %post). Параметр `parsec=0`: отключение мандатного контроля доступа — почему необходимо. Разметка диска: `/boot` (1 GB), `/` (100 GB), `/data` (остальное). ✏️ Установить Astra на ВМ |
| 8.3 | Базовая настройка ОС | 5 | — | 1 | Сеть: `/etc/network/interfaces` или `nmcli`. hostname: `/etc/hostname`. DNS: `/etc/resolv.conf`. SSH: `sshd_config` (Port, PermitRootLogin, PubkeyAuthentication). Брандмауэр: `iptables`/`nftables` — минимальный набор правил. Часовой пояс, локаль, раскладка. `apt update && apt upgrade` (осторожно в закрытом контуре) |
| 8.4 | Установка драйверов NVIDIA | 4 | 1 | — | `lspci | grep NVIDIA` — видит ли GPU. Установка: `nvidia-driver`, `nvidia-cuda-toolkit`. `nvidia-smi`: разбор вывода (GPU, VRAM, температура, процессы). `nvidia-persistenced`. NVIDIA Container Toolkit: `nvidia-ctk`, `containerd` config |
| 8.5 | ✏️ Практикум: голый сервер → готовая ОС | 2 | — | — | Полный цикл: BMC → ISO → Kickstart → сеть → SSH → nvidia-smi |

**Схемы гл. 8:** (1) Физическая схема всех 5 узлов с IP/портами/туннелями. (2) Kickstart: структура файла. (3) nvidia-smi: аннотированный скриншот.  
**Таблицы гл. 8:** Узлы и доступы, Разделы диска, Команды настройки сети.

---

## Глава 9. Развёртывание Kubernetes (22 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 9.1 | containerd: установка и настройка | 4 | 1 | 1 | Установка: `apt install containerd`. Конфиг: `/etc/containerd/config.toml` → `SystemdCgroup = true`. nvidia-runtime: секция `[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]`. Проверка: `crictl pull`, `crictl run` |
| 9.2 | kubeadm init: control-plane | 5 | 1 | 1 | Установка: kubeadm, kubelet, kubectl. `kubeadm init`: `--pod-network-cidr=10.244.0.0/16`, `--apiserver-advertise-address`. Вывод команды: токен, хэш, `kubeadm join` — разбор. `mkdir ~/.kube && cp /etc/kubernetes/admin.conf`. Проверка: `kubectl get nodes` (должен быть NotReady) |
| 9.3 | Flannel: overlay-сеть | 3 | 1 | — | `kubectl apply -f kube-flannel.yml`. Что внутри манифеста: DaemonSet, ConfigMap с `net-conf.json`. Как работает VXLAN-инкапсуляция. Проверка: `kubectl get nodes` → Ready, `kubectl get pods -n kube-flannel` |
| 9.4 | kubeadm join: worker node | 2 | — | — | На n7: `kubeadm join 10.129.13.78:6443 --token ... --discovery-token-ca-cert-hash ...`. Проверка: `kubectl get nodes` → 2 узла Ready |
| 9.5 | GPU Operator | 4 | 1 | 1 | NVIDIA GPU Operator: что ставит (driver, toolkit, device-plugin, dcgm). Helm chart → `kubectl apply`. `runtimeClassName: nvidia`. Проверка: `kubectl describe node | grep nvidia.com/gpu` |
| 9.6 | Системные компоненты | 2 | — | 1 | Metrics Server: `kubectl top nodes/pods`. cert-manager: автоматические сертификаты. Prometheus Adapter: кастомные метрики для HPA. `kubectl get pods -n kube-system` — все должны быть Running |
| 9.7 | ✏️ Практикум: K8s с нуля | 2 | — | — | containerd → kubeadm init → Flannel → kubeadm join → GPU Operator → `kubectl get nodes` (2 Ready) |

**Схемы гл. 9:** (1) containerd: архитектура (CRI → containerd → runc). (2) kubeadm init: временная диаграмма. (3) Flannel VXLAN: инкапсуляция пакета. (4) GPU Operator: компоненты.  
**Таблицы гл. 9:** Команды kubeadm, Системные поды kube-system, Параметры containerd.

---

## Глава 10. Развёртывание vLLM и моделей (25 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 10.1 | Подготовка моделей | 5 | 1 | 1 | Hugging Face: что это, модель vs репозиторий. `huggingface-cli download Qwen/Qwen2.5-14B-Instruct --local-dir /data/models/...`. Структура каталога: `config.json`, `tokenizer.json`, `model-00001-of-00004.safetensors`. Размеры: 14B ~28 GB, 32B-GPTQ ~20 GB. Перенос в закрытый контур: внешний диск → `rsync` → `/mnt/models/` |
| 10.2 | PVC и StorageClass для моделей | 4 | 1 | 1 | Local Path Provisioner: hostPath для моделей. PVC: `models-32b-pvc`. Почему не общий NFS: производительность (NVMe vs сеть). manifest: `PersistentVolumeClaim`, 100Gi, `storageClassName: local-path` |
| 10.3 | Деплой vLLM 14B | 6 | 1 | 1 | `k8s/vllm-14b/deployment.yaml` — полный построчный разбор: apiVersion, kind, metadata, spec (replicas=1, strategy=Recreate, nodeSelector, runtimeClassName=nvidia, containers[0]: image, command, args, env, resources (requests=4 CPU/32Gi RAM/2 GPU, limits=16 CPU/64Gi RAM/2 GPU), ports, volumeMounts). Service: ClusterIP :8000 + NodePort :32293. Проверка: `kubectl logs`, `curl :8000/health`, `curl :8000/v1/models`. ✏️ Первый запрос «Привет, мир» |
| 10.4 | Деплой vLLM 32B (GPTQ) | 5 | 1 | 1 | `k8s/vllm-32b/deployment.yaml` — построчно. Отличия от 14B: `--model /models`, `--served-model-name qwen2.5-32b`, `--dtype auto`, `--quantization gptq`. PVC `models-32b-pvc`. `HUGGING_FACE_HUB_TOKEN` (нужен для gated-моделей). Проверка: `curl :8000/v1/chat/completions`. Сравнение производительности: 14B (28 tok/s) vs 32B (35 tok/s) — почему 32B быстрее (квантизация) |
| 10.5 | Подключение LoRA-адаптера | 3 | — | 1 | Файлы адаптера: `adapter_config.json` (rank=8, alpha=16), `adapter_model.safetensors` (65 MB). Копирование: `/data/models/lora-qwen14b-astra/`. `--enable-lora --lora-modules astra-14b=/models/lora-qwen14b-astra/`. Проверка: `curl` с `model: "astra-14b"`. ✏️ Вопрос про Astra Linux с LoRA и без |
| 10.6 | HPA для vLLM | 2 | — | 1 | `k8s/hpa/hpa.yaml`: scaleTargetRef, min=1, max=1 (GPU ограничение). Метрики: CPU, память. Почему maxReplicas=1: нет свободных GPU. Как включить масштабирование при добавлении GPU-узлов |

**Схемы гл. 10:** (1) Структура каталога модели HuggingFace. (2) PVC → hostPath → /data/models. (3) vLLM 14B deployment: аннотированная схема пода. (4) vLLM 32B deployment: отличия (GPTQ, PVC).  
**Таблицы гл. 10:** Модели (размер, GPU, скорость), Параметры vLLM 14B vs 32B, Параметры LoRA.

---

## Глава 11. Развёртывание Gateway (25 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 11.1 | Сборка Docker-образа Gateway | 5 | 1 | 1 | `gateway/Dockerfile` — построчный разбор: `FROM python:3.12-slim`, `WORKDIR`, `COPY requirements.txt`, `pip install`, `COPY gateway/ .`, `RUN mkdir /app/wiki`, `HEALTHCHECK`, `CMD`. `docker build -t ghcr.io/dedvmedved-dot/aither-project-gateway:latest .`. Слои: кэширование pip. ✏️ Собрать образ, `docker run` локально |
| 11.2 | Push в registry и деплой в K8s | 5 | 1 | 1 | `docker push ghcr.io/...`. Альтернатива для закрытого контура: `docker save` → `docker load` в локальный registry (`registry:2` на :5000). Secret `pg-url`: `kubectl create secret generic pg-url --from-literal=url=postgresql://...`. `kubectl apply -f k8s/gateway/deployment.yaml`. Проверка: `kubectl get pods`, `curl :8080/health` |
| 11.3 | ConfigMap и Secret — детально | 4 | — | 1 | `gateway-catalog`: `catalog.yaml` (2 модели). `gateway-wiki`: wiki/index.md, llm-wiki.md. `delegation-public-key`: delegation/public.pem. Как создавать: `kubectl create configmap gateway-catalog --from-file=catalog.yaml`. Как обновлять: `kubectl create ... --dry-run=client -o yaml | kubectl apply -f -` |
| 11.4 | Переменные окружения — каждая с объяснением | 4 | — | 1 | `VLLM_URL`, `VLLM_32B_URL`, `CATALOG_PATH`, `REDIS_URL`, `RATE_LIMIT_RPM=300`, `RATE_LIMIT_TPM=100000`, `PORT=8080`, `TOKEN_COST=1`, `CHROMA_URL`, `WIKI_ROOT`, `PG_URL` (secretKeyRef), `ADMIN_KEY`. Почему каждое значение именно такое |
| 11.5 | Rate Limiter и биллинг — проверка | 3 | 1 | — | Проверка RPM: 301-й запрос → 429 Too Many Requests. Проверка TPM: запрос с большим контекстом → 429. Проверка биллинга: `curl` с API-ключом → `tokens_used` списываются. `SELECT * FROM billing_accounts` |
| 11.6 | HPA Gateway | 2 | — | 1 | `k8s/hpa/gateway-hpa.yaml`: min=1, max=3, метрики `gateway_active_requests` и `gateway_requests_per_second`. behavior: scaleDown (5 min стабилизация), scaleUp (мгновенно). Проверка: `kubectl get hpa`, нагрузочный тест |
| 11.7 | ✏️ Практикум: Gateway от сборки до прода | 2 | — | — | `docker build` → `docker push` → `kubectl apply` → `curl /health` → `curl /v1/chat/completions` |

**Схемы гл. 11:** (1) Dockerfile: слои (аннотированные). (2) Gateway в K8s: Pod (образ, volumeMounts, env) + Service + HPA. (3) Rate Limiter: Redis sliding window.  
**Таблицы гл. 11:** Переменные окружения Gateway, ConfigMap-ы, Docker-команды.

---

## Глава 12. Развёртывание в закрытом контуре — air-gap (38 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 12.1 | Пакет offline-deploy — обзор | 4 | 1 | 1 | Структура пакета: что в каждой папке и зачем. Makefile: `make bundle`, `make offline-load`, `make deploy`, `make test`, `make verify`. VERSION: как обновляется. CHANGELOG: как ведётся |
| 12.2 | Сборка офлайн-пакета (на машине с интернетом) | 6 | 1 | 1 | `offline/docker/save.sh` — построчно: `docker pull`, `docker save -o images.tar.gz`. `offline/pip/download.sh` — построчно: `pip download -d packages/ -r requirements.txt`. `offline/npm/install.sh` — `npm pack`. `offline/models/transfer.sh` — `huggingface-cli download`. checksums.sha256: генерация, проверка, зачем |
| 12.3 | Перенос на носитель → целевая машина | 4 | 1 | 1 | Носители: флешка, внешний HDD, оптический диск (ГОСТ). `rsync -av --progress`. Проверка контрольных сумм: `sha256sum -c checksums.sha256`. Модели отдельно: ~50 GB, внешний диск |
| 12.4 | Загрузка зависимостей | 5 | — | 1 | `offline/docker/load.sh` — построчно: `docker load -i images.tar.gz`, `docker tag`, `docker push localhost:5000/...`. `offline/pip/install.sh` — `pip install --no-index --find-links=packages/`. `offline/npm/install.sh` — `npm install portal-offline.tgz` |
| 12.5 | Ansible playbooks — мастер-класс | 12 | 2 | 2 | **playbooks/ansible.cfg** и **inventory.yml.template**. **site.yml**: оркестрация всех 9 playbook-ов. **01-prerequisites.yml**: `apt`, пользователи, `sshd_config`, брандмауэр. **02-gpu-setup.yml**: NVIDIA driver, `nvidia-smi`, toolkit. **03-k8s-deploy.yml**: containerd → kubeadm init → Flannel → kubeadm join. **04-storage.yml**: Local Path, PVC. **05-vllm-deploy.yml**: деплой 14B + 32B, прогрев (первый запрос). **06-gateway-deploy.yml**: сборка образа, деплой, PostgreSQL, Redis, ChromaDB. **07-portal-deploy.yml**: nginx, BFF, Portal DB. **08-monitoring-deploy.yml**: Prometheus, Grafana, DCGM. **09-post-deploy.yml**: seed-данные, smoke-тесты. Каждый playbook — построчный разбор задач |
| 12.6 | Приёмо-сдаточные тесты | 5 | 1 | 1 | **01-smoke.sh** — построчно: проверка `kubectl get pods` (все Running), `curl :8080/health`, `curl :8000/health`. **02-api.sh** — построчно: `/v1/models`, `/v1/chat/completions`, rate limit, биллинг. **03-security.sh** — построчно: DLP-фильтр, prompt injection, JWT без подписи. **04-load.sh** — нагрузочное тестирование (Apache Bench, `hey`) |
| 12.7 | Чек-лист развёртывания | 2 | — | 1 | Пошаговый список: от «вставить флешку» до «пользователь залогинился и отправил запрос». Каждый пункт с ожидаемым результатом |

**Схемы гл. 12:** (1) Пакет offline-deploy: структура (дерево). (2) Процесс сборки: интернет-машина → флешка → air-gap. (3) Ansible site.yml: граф зависимостей playbook-ов. (4) Приёмо-сдаточные тесты: блок-схема проверок. (5) Air-gap деплой: полная карта (носители, команды, проверки).  
**Таблицы гл. 12:** Состав пакета, Размеры компонентов, Команды Makefile, Порядок playbook-ов, Критерии приёмки.

---

## Глава 13. Мониторинг и эксплуатация (18 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 13.1 | Что мониторим и зачем | 3 | — | 1 | Метрики: GPU (температура, загрузка, VRAM, throttle). vLLM: requests/sec, latency (p50/p95/p99), tokens/sec. Gateway: RPM, TPM, queue depth. Биллинг: балансы, списания. Инфраструктура: CPU, RAM, диск, сеть |
| 13.2 | Prometheus + Grafana — настройка | 5 | 1 | 1 | Prometheus: `prometheus.yml` (scrape_configs). ServiceMonitor для K8s-сервисов. DCGM: метрики NVIDIA (`DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_MEM_COPY_UTIL`). Grafana: дашборды — GPU Overview, Gateway Dashboard, vLLM Performance. Импорт JSON-дашбордов |
| 13.3 | Логи: где и как читать | 4 | — | 1 | journalctl: `-u <service>`, `-p 3` (ERROR), `--since "1 hour ago"`, `-f` (follow), `--no-pager`. kubectl logs: `-f`, `--tail=100`, `--previous` (предыдущий контейнер). Агрегация: `kubectl logs -l app=vllm-qwen --all-containers`. Типовые ошибки: OOMKilled (увеличить memory limit), CrashLoopBackOff (неправильная команда/порт занят), ImagePullBackOff (нет образа / нет интернета), CreateContainerConfigError (ошибка в ConfigMap/Secret) |
| 13.4 | Резервное копирование | 3 | 1 | — | `scripts/backup.sh` — построчно: `pg_dump -U aither -h ... aither > backup.sql`, `tar czf configs-backup.tar.gz configs/`, Git push. `scripts/restore.sh` — построчно: создание БД, `psql < backup.sql`. Модели: `rsync /mnt/models/ /backup/models/`. Расписание: cron daily |
| 13.5 | Ротация ключей и сертификатов | 2 | — | 1 | `scripts/rotate-keys.sh` — построчно: генерация новых JWT-ключей, обновление Secret, `kubectl rollout restart deploy/gateway`. Сертификаты TLS: cert-manager автоматически, ручной режим — `openssl` |
| 13.6 | ✏️ Практикум: инцидент | 2 | — | — | Симуляция: «пользователи жалуются — модель не отвечает». Поиск причины: Grafana (GPU=0%, под CrashLoopBackOff) → kubectl logs → ошибка в args → fix → проверка |

**Схемы гл. 13:** (1) Мониторинг: что и откуда собирается. (2) Резервное копирование: схема потоков данных.  
**Таблицы гл. 13:** Метрики мониторинга, Типовые ошибки K8s, Команды journalctl/kubectl logs.

---

*Конец Части II*
