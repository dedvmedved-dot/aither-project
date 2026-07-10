# Приложения и Лабораторный практикум

**Документ 4 из 5.** ~95 стр. · 6 схем · 5 таблиц · 14 ЛР

---

# Приложение A. Глоссарий

Алфавитный указатель терминов с переводом, расшифровкой и ссылкой на главу.

| Термин | EN | Определение | Гл. |
|---|---|---|---|
| **Air-gap** | — | Физическая изоляция сети от Интернета | 7 |
| **API** | Application Programming Interface | Набор правил для взаимодействия программ | 4 |
| **Backpropagation** | — | Обратное распространение ошибки при обучении нейросети | 4 |
| **BFF** | Backend For Frontend | Сервер-посредник между браузером и API | 6 |
| **bf16** | Brain Floating Point 16 | 16-битный формат чисел для ИИ | 4 |
| **BMC** | Baseboard Management Controller | Контроллер удалённого управления сервером | 1, 8 |
| **BPE** | Byte-Pair Encoding | Алгоритм токенизации: разбиение текста на подслова | 4 |
| **Canary-токен** | — | Секретная строка в промпте для обнаружения утечек | 7 |
| **CD** | Continuous Delivery | Автоматический деплой после успешных тестов | 18 |
| **cert-manager** | — | Автоматический выпуск TLS-сертификатов в K8s | 9 |
| **cgroup** | Control Group | Механизм ядра Linux для ограничения ресурсов | 2 |
| **CI** | Continuous Integration | Автоматический запуск тестов при коммите | 18 |
| **CIDR** | Classless Inter-Domain Routing | Нотация IP-адресов: `10.0.0.0/24` | 1 |
| **CNI** | Container Network Interface | Плагин сети для Kubernetes | 9 |
| **containerd** | — | Среда выполнения контейнеров | 2, 9 |
| **Continuous Batching** | — | Пакетная обработка запросов в vLLM | 5 |
| **CORS** | Cross-Origin Resource Sharing | Механизм разрешения междоменных запросов | 6 |
| **CPU** | Central Processing Unit | Центральный процессор | 1 |
| **CRI** | Container Runtime Interface | Интерфейс между K8s и средой выполнения | 9 |
| **CSRF** | Cross-Site Request Forgery | Атака с подделкой межсайтового запроса | 7, 16 |
| **CSP** | Content-Security-Policy | Заголовок, ограничивающий источники скриптов | 16 |
| **CUDA** | Compute Unified Device Architecture | Платформа параллельных вычислений NVIDIA | 1 |
| **DaemonSet** | — | Контроллер K8s: по одному поду на каждом узле | 9 |
| **DCGM** | Data Center GPU Manager | Мониторинг GPU от NVIDIA | 13 |
| **Decode** | — | Фаза инференса: генерация по одному токену | 5 |
| **Deployment** | — | Контроллер K8s: управляет подами | 3 |
| **DLP** | Data Loss Prevention | Защита от утечек конфиденциальных данных | 7, 15 |
| **DNS** | Domain Name System | Система преобразования имён в IP-адреса | 1 |
| **Docker Compose** | — | Инструмент для запуска нескольких контейнеров | 2 |
| **Dockerfile** | — | Инструкция по сборке Docker-образа | 2 |
| **DOT** | — | Язык описания графов (Graphviz) | все |
| **etcd** | /etc + distributed | Распределённое хранилище состояния K8s | 3 |
| **FastAPI** | — | Python-фреймворк для создания API | 15 |
| **Flannel** | — | CNI-плагин для overlay-сети в K8s | 3, 9 |
| **fp16** | Half Precision (16-bit float) | 16-битный формат с плавающей точкой | 4 |
| **GPTQ** | Post-Training Quantization | Метод квантизации моделей до 4 бит | 4 |
| **GPU** | Graphics Processing Unit | Графический процессор / видеокарта | 1 |
| **Helm** | — | Пакетный менеджер для Kubernetes | 9 |
| **hostPath** | — | Тип тома K8s: папка на хосте | 3, 10 |
| **HPA** | Horizontal Pod Autoscaler | Автоматическое масштабирование подов | 3, 11 |
| **HTTP** | HyperText Transfer Protocol | Протокол передачи гипертекста | 1 |
| **HTTPS** | HTTP Secure | HTTP + шифрование TLS | 1 |
| **IOMMU** | Input-Output Memory Management Unit | Изоляция устройств PCIe для проброса GPU | 2 |
| **IPMI** | Intelligent Platform Management Interface | Интерфейс управления сервером (BMC) | 8 |
| **JWT** | JSON Web Token | Токен аутентификации: header.payload.signature | 6, 7 |
| **K8s** | Kubernetes | Оркестратор контейнеров | 3 |
| **Kickstart** | — | Файл автоматической установки ОС | 8 |
| **KVM** | Kernel-based Virtual Machine | Гипервизор, встроенный в ядро Linux | 2 |
| **KV-кэш** | Key-Value cache | Кэш состояний внимания для ускорения генерации | 5 |
| **LLM** | Large Language Model | Большая языковая модель | 4 |
| **LoRA** | Low-Rank Adaptation | Метод дообучения с малым числом параметров | 4, 17 |
| **ML** | Machine Learning | Машинное обучение | 4 |
| **Namespace** | — | Пространство имён: изоляция ресурсов в K8s и Linux | 2, 3 |
| **NodePort** | — | Тип Service K8s: порт на каждом узле (30000-32767) | 3 |
| **NVMe** | Non-Volatile Memory Express | Протокол доступа к быстрым SSD | 1 |
| **OAuth 2.0** | Open Authorization | Протокол делегирования доступа | 6, 16 |
| **OOM** | Out Of Memory | Нехватка памяти → процесс убит | 13 |
| **PagedAttention** | — | Алгоритм управления KV-кэшем в vLLM | 5 |
| **Parsec** | — | Модуль мандатного контроля доступа в Astra Linux | 8 |
| **PCIe** | Peripheral Component Interconnect Express | Шина подключения устройств | 2 |
| **Prefill** | — | Фаза инференса: обработка входного текста | 5 |
| **Prompt Injection** | — | Атака: внедрение инструкций в промпт модели | 7 |
| **PVC** | PersistentVolumeClaim | Запрос на постоянное хранилище в K8s | 3, 10 |
| **QEMU** | Quick EMUlator | Эмулятор устройств для виртуализации | 2 |
| **QLoRA** | Quantized LoRA | LoRA + 4-битная загружаемая модель | 4, 17 |
| **RAM** | Random Access Memory | Оперативная память | 1 |
| **Registry** | — | Хранилище Docker-образов | 2 |
| **RPM** | Requests Per Minute | Лимит запросов в минуту | 7, 11 |
| **runc** | — | Низкоуровневая среда выполнения контейнеров | 2 |
| **SAS** | Serial Attached SCSI | Серверный интерфейс подключения дисков | 1 |
| **SCP** | Secure Copy Protocol | Копирование файлов по SSH | 6 |
| **SIEM** | Security Information and Event Management | Система анализа событий безопасности | 15 |
| **SPA** | Single-Page Application | Одностраничное веб-приложение | 6 |
| **SSE** | Server-Sent Events | Потоковая передача данных от сервера к клиенту | 4, 6 |
| **SSL/TLS** | Secure Sockets Layer / Transport Layer Security | Протоколы шифрования сетевого трафика | 1, 7 |
| **systemd** | — | Система инициализации и управления службами в Linux | 1 |
| **Tensor Parallelism** | — | Разрезание модели на несколько GPU | 5 |
| **TPM** | Tokens Per Minute | Лимит токенов в минуту | 7, 11 |
| **UUID** | Universally Unique Identifier | Уникальный 128-битный идентификатор | 6 |
| **venv** | Virtual Environment | Изолированное окружение Python | 14 |
| **VLAN** | Virtual Local Area Network | Виртуальная локальная сеть (изоляция на L2) | 1, 7 |
| **vLLM** | Very Large Language Model | Движок инференса языковых моделей | 5 |
| **VPN** | Virtual Private Network | Виртуальная частная сеть (шифрованный туннель) | 1 |
| **VRAM** | Video RAM | Видеопамять графического процессора | 1 |
| **VXLAN** | Virtual Extensible LAN | Протокол инкапсуляции для overlay-сетей | 3, 9 |
| **WireGuard** | — | Современный VPN-протокол, встроенный в ядро | 1, 7 |
| **XSS** | Cross-Site Scripting | Атака с внедрением скрипта на страницу | 7, 16 |
| **YAML** | YAML Ain't Markup Language | Формат конфигурационных файлов | 3 |

---

# Приложение B. Шпаргалка по командам

## kubectl

```bash
# Просмотр
kubectl get pods -o wide
kubectl get pods -w                      # следить
kubectl get nodes
kubectl get svc,deploy,hpa
kubectl get events --sort-by=.metadata.creationTimestamp

# Информация
kubectl describe pod <name>
kubectl describe node <name>

# Логи
kubectl logs <pod>
kubectl logs -f <pod>                    # follow
kubectl logs --tail=100 <pod>
kubectl logs --previous <pod>            # предыдущий контейнер
kubectl logs -l app=gateway --all-containers

# Выполнение
kubectl exec -it <pod> -- bash
kubectl exec <pod> -- <command>

# Управление
kubectl apply -f file.yaml
kubectl delete -f file.yaml
kubectl delete pod <name>                # перезапустится через Deployment

# Обновление
kubectl set image deploy/<name> container=image:tag
kubectl set env deploy/<name> KEY=VALUE
kubectl rollout restart deploy/<name>
kubectl rollout status deploy/<name>
kubectl rollout undo deploy/<name>
kubectl rollout history deploy/<name>

# Масштабирование
kubectl scale --replicas=N deploy/<name>

# Порты
kubectl port-forward svc/<name> local:remote
kubectl port-forward pod/<name> local:remote

# Секреты и конфиги
kubectl create secret generic <name> --from-literal=key=value
kubectl create configmap <name> --from-file=key=file
kubectl get secret <name> -o jsonpath='{.data.key}' | base64 -d

# Метрики
kubectl top nodes
kubectl top pods
```

## Docker

```bash
docker build -t name:tag -f Dockerfile .
docker run -d -p host:container --name name --restart always -e KEY=val image
docker ps / docker ps -a
docker logs -f name
docker exec -it name bash
docker stop/start/restart name
docker rm/rmi name
docker save -o file.tar image
docker load -i file.tar
docker tag src dst
docker push/pull image
docker compose up -d / down / logs
```

## systemd / journalctl

```bash
systemctl start/stop/restart <unit>
systemctl status <unit>
systemctl enable/disable <unit>
systemctl daemon-reload
journalctl -u <unit> -f --no-pager
journalctl -u <unit> -p 3 --since "1 hour ago"
journalctl --since "2026-07-07" --until "2026-07-08"
```

## Git

```bash
git clone url
git status / git diff
git add file / git add -A
git commit -m "msg"
git push / git pull
git log --oneline
git checkout -b branch
git checkout main
git merge branch
git stash / git stash pop
```

## curl

```bash
curl -sf URL                              # тихий режим, показать ошибку
curl -X POST URL -H "Content-Type: application/json" -d '{"key":"val"}'
curl -H "Authorization: Bearer TOKEN" URL
curl -s -o /dev/null -w "%{http_code}\n" URL  # только код ответа
```

## SSH

```bash
ssh user@host
ssh -i key.pem user@host
ssh -L local_port:remote_host:remote_port user@host   # туннель
scp file user@host:/path/
rsync -av --progress source/ user@host:/dest/
```

---

# Приложение C. Типовые неисправности

## C.1. Pod CrashLoopBackOff

**Симптом:** `kubectl get pods` → `STATUS: CrashLoopBackOff`

**Диагностика:**
```bash
kubectl describe pod <name>              # события в конце
kubectl logs <name> --previous           # логи предыдущего контейнера
```

**Причины и решения:**
- Ошибка в `command` или `args` → исправить манифест
- Порт уже занят → сменить порт
- Файл ConfigMap не найден → проверить имя и ключ
- Приложение падает с ошибкой → читать логи, исправить код

---

## C.2. Pod OOMKilled

**Симптом:** `kubectl describe pod` → `State: Terminated, Reason: OOMKilled`

**Причина:** превышен `limits.memory`.

**Решение:** увеличить `limits.memory` в манифесте.
```yaml
resources:
  limits:
    memory: "512Mi"   # было "256Mi"
```

---

## C.3. ImagePullBackOff / ErrImagePull

**Симптом:** `kubectl get pods` → `STATUS: ImagePullBackOff`

**Причины:**
- Опечатка в имени образа
- Registry недоступен (нет интернета в закрытом контуре)
- Образ не запушен в registry

**Диагностика:**
```bash
kubectl describe pod <name> | grep -A5 Events
docker pull <image>                    # проверить вручную
```

**Решение:** проверить имя, `docker push`, или использовать `imagePullPolicy: IfNotPresent`.

---

## C.4. CreateContainerConfigError

**Симптом:** под не стартует, ошибка конфигурации.

**Причины:**
- ConfigMap или Secret, на который ссылается под, не существует
- Ошибка в синтаксисе команды `command`

**Решение:** проверить имена ConfigMap/Secret в `volumes` и `volumeMounts`.

---

## C.5. GPU не видна

**Симптом:** `kubectl describe node | grep nvidia` → `nvidia.com/gpu: 0`

**Причины:**
- Драйверы NVIDIA не установлены (`nvidia-smi` → ошибка)
- `nvidia-container-toolkit` не настроен
- `runtimeClassName: nvidia` не указан в манифесте пода

**Решение:**
```bash
nvidia-smi                              # видит ли драйвер карты?
systemctl status nvidia-persistenced    # запущен ли?
# Проверить секцию [runtimes.nvidia] в /etc/containerd/config.toml
```

---

## C.6. 502 Bad Gateway

**Симптом:** браузер показывает 502, BFF не может достучаться до Gateway.

**Диагностика:**
```bash
curl http://VPS1_IP:30900/health       # Gateway жив?
ssh VPS2 curl http://VPS1_IP:30900/health  # VPS2 видит VPS1?
```

**Причины:** WireGuard не поднят, порт закрыт, Gateway упал.

---

## C.7. 429 Too Many Requests

**Симптом:** `HTTP 429` после нескольких запросов.

**Причина:** превышен Rate Limit (RPM или TPM).

**Решение:** ждать (счётчик сбрасывается каждую минуту) или увеличить лимиты:
```bash
kubectl set env deploy/gateway RATE_LIMIT_RPM=500
```

---

## C.8. vLLM: CUDA out of memory

**Симптом:** `kubectl logs vllm-...` → `torch.cuda.OutOfMemoryError`

**Причины:**
- `--gpu-memory-utilization` слишком высокий
- `--max-model-len` слишком большой (KV-кэш съедает память)

**Решение:** уменьшить `--gpu-memory-utilization 0.90` → `0.85`.

---

## C.9. PostgreSQL: connection refused

**Симптом:** Gateway лог → `psycopg2.OperationalError: connection refused`

**Диагностика:**
```bash
kubectl get pods | grep postgres        # под запущен?
kubectl exec deploy/postgres -- psql -U aither -c "SELECT 1"  # БД жива?
```

**Решение:** перезапустить PostgreSQL, проверить Secret `pg-url`.

---

## C.10. Redis: NOAUTH / connection refused

**Симптом:** Gateway лог → `redis.exceptions.ConnectionError`

**Решение:** проверить, что Redis под Running, и `REDIS_URL=redis` (без пароля).

---

## C.11. `toLocaleString` is undefined (фронтенд)

**Симптом:** в админ-панели при нажатии «+Начислить» — белый экран, консоль: `TypeError: d.new_balance is undefined`.

**Причина:** Gateway вернул `{"error": "org not found"}`, фронтенд не проверил `d.error`.

**Решение:** добавить проверку `if (!d.error)` перед отображением.

---

## C.12. WireGuard: handshake failed

**Симптом:** `wg show` → `latest handshake: never`

**Причины:** ключи не совпадают, порт 51820 UDP закрыт.

**Решение:** проверить публичные ключи в конфиге, открыть порт 51820 UDP.

---

## C.13. Сертификат TLS просрочен

**Симптом:** браузер показывает «Ваше соединение не защищено».

**Диагностика:**
```bash
openssl s_client -connect fb1.spb.ru:10443 </dev/null 2>/dev/null | \
  openssl x509 -noout -dates
```

**Решение:** обновить сертификат Let's Encrypt (`certbot renew`) или проверить cert-manager в K8s.

---

# Приложение D. Список портов и сервисов

| Порт | Сервис | Узел | Протокол | Описание |
|---|---|---|---|---|
| 10443 | nginx | VPS1 | TCP+TLS | Единственная входная точка (HTTPS) |
| 30900 | nginx → Gateway | VPS1→K8s | TCP | Прокси в K8s NodePort |
| 80 | nginx | VPS2 | TCP | Статика портала |
| 3000 | BFF | VPS2 | TCP | Node.js API |
| 5432 | PostgreSQL Portal | VPS2 | TCP | БД портала |
| 8080 | Gateway | K8s (ClusterIP) | TCP | API Gateway |
| 30900 | Gateway | K8s (NodePort) | TCP | Внешний доступ к Gateway |
| 8000 | vLLM 14B | K8s (ClusterIP) | TCP | Инференс 14B |
| 32293 | vLLM 14B | n8 (NodePort) | TCP | Внешний доступ к 14B |
| 8000 | vLLM 32B | K8s (ClusterIP) | TCP | Инференс 32B |
| 32294 | vLLM 32B | n7 (NodePort) | TCP | Внешний доступ к 32B |
| 8000 | ChromaDB | K8s (n8) | TCP | Векторная БД (RAG) |
| 6379 | Redis | K8s (n8) | TCP | Rate Limiter |
| 31113 | PostgreSQL Gateway | K8s (n8) | TCP | Биллинг |
| 30300 | Grafana | n7 (NodePort) | TCP | Дашборды |
| 6443 | kube-apiserver | n8 | TCP+TLS | API Kubernetes |
| 9443 | BMC | n7 | TCP+TLS | Управление сервером |
| 19443 | socat BMC | VPS2 | TCP | Проброс BMC |
| 51820 | WireGuard | VPS1, VPS2 | UDP | VPN-туннель |
| 8472 | Flannel VXLAN | n7, n8 | UDP | Overlay-сеть K8s |

---

# Приложение E. Полная схема потоков данных

## E.1. Поток чат-запроса

![E.1. Поток чат-запроса](diagrams/04-appendices-labs-01.jpg)

*Схема E.1. Полный путь чат-запроса: 9 шагов от браузера до ответа модели.*

## E.2. Поток биллинга

![E.2. Поток биллинга](diagrams/04-appendices-labs-02.jpg)

*Схема E.2. Три шага биллинга: проверка лимита → инференс → списание.*

## E.3. Поток OAuth-авторизации

![E.3. Поток OAuth-авторизации](diagrams/04-appendices-labs-03.jpg)

*Схема E.3. OAuth 2.0 Authorisation Code Flow: 9 шагов.*

## E.4. Поток CI/CD деплоя

![E.4. Поток CI/CD деплоя]([Схема — ошибка рендеринга])

*Схема E.4. CI/CD pipeline: 6 шагов от push до уведомления.*

---

# Приложение F. Карта репозитория

```
aither-project/
│
├── 📁 gateway/                 ★ API Gateway (Python, 11 модулей)
│   ├── gateway.py              — точка входа, FastAPI, роутинг
│   ├── auth.py                 — JWT-аутентификация
│   ├── billing.py              — списание токенов, балансы
│   ├── catalog.py              — каталог моделей
│   ├── routing.py              — маршрутизация к vLLM
│   ├── dlp.py                  — DLP-фильтрация
│   ├── rag.py                  — RAG (ChromaDB)
│   ├── delegation.py           — JWT-подпись
│   ├── admin.py                — админ-API, очереди Redis
│   ├── usage-collector.py      — учёт использованных токенов
│   ├── reservation-reaper.py   — очистка резерваций
│   ├── Dockerfile              — сборка образа (python:3.12-slim)
│   └── requirements.txt        — Python-зависимости
│
├── 📁 portal/                  ★ Портал (SPA + BFF)
│   ├── server.ts               — BFF-сервер (Express, TypeScript)
│   ├── policies.ts             — права доступа
│   ├── security.ts             — безопасность (Helmet, CSP)
│   ├── package.json            — NPM-зависимости
│   ├── tsconfig.json           — настройки TypeScript
│   └── 📁 static/
│       ├── index.html          — чат-интерфейс
│       └── admin.html          — админ-панель
│
├── 📁 k8s/                     ★ Kubernetes-манифесты (живой кластер)
│   ├── 📁 gateway/             — Gateway Deployment + Service
│   ├── 📁 vllm-14b/            — vLLM 14B (TP=2, LoRA, n8)
│   ├── 📁 vllm-32b/            — vLLM 32B (GPTQ, n7)
│   ├── 📁 hpa/                 — Gateway HPA, vLLM HPA
│   └── 📁 monitoring/          — Prometheus, Grafana
│
├── 📁 configs/                 ★ Эталонные конфигурации
│   ├── 📁 vps1/                — nginx :10443, gateway-proxy
│   ├── 📁 vps2/                — BFF systemd, docker-compose
│   └── 📁 k8s/                 — gateway-code ConfigMap, catalog
│
├── 📁 offline-deploy/          ★ Пакет для закрытого контура v1.1.0
│   ├── Makefile                — make bundle/deploy/test
│   ├── 📁 playbooks/           — 10 Ansible playbooks
│   ├── 📁 k8s/                 — эталонные манифесты
│   ├── 📁 offline/             — docker/pip/npm зависимости
│   ├── 📁 scripts/             — эксплуатация
│   ├── 📁 configs/             — шаблоны конфигов
│   └── 📁 tests/               — приёмо-сдаточные тесты
│
├── 📁 fine-tuning/             ★ QLoRA-скрипты обучения
│
├── 📁 docs/
│   └── 📁 training-manual/     ★ Учебное пособие (этот документ)
│
├── 📁 scripts/                 Деплой, health-check, kickstart
├── 📁 db/migrations/           SQL-миграции (6-8)
├── 📁 delegation/              Ключи JWT-подписи
├── 📁 wiki/                    База знаний RAG
├── 📁 diagrams/                Архив схем (DOT, SVG, PNG)
├── 📁 references/              Справочные материалы
│
├── README.md                   — описание проекта + физическая схема
├── ROADMAP.md                  — дорожная карта
├── lab-journal.md              — лабораторный журнал
└── brief.md                    — исходное ТЗ
```

---

# Приложение G. Быстрый старт — памятка

1. **Установить ОС:** BMC → смонтировать ISO → Kickstart (`parsec=0`)
2. **Настроить сеть:** IP 10.129.13.78/77, DNS, iptables
3. **Установить драйверы:** `apt install nvidia-driver`, проверить `nvidia-smi`
4. **Kubernetes:** containerd (`SystemdCgroup=true`) → `kubeadm init` (n8) → Flannel → `kubeadm join` (n7)
5. **GPU Operator:** `helm install gpu-operator`, проверить `nvidia.com/gpu: 2`
6. **Модели:** скопировать в `/data/models/`, проверить `sha256sum`
7. **vLLM:** `kubectl apply -f k8s/vllm-*/`, `curl :32293/health`
8. **Gateway:** `docker build` → `docker push` → `kubectl apply`, `curl :30900/health`
9. **Портал:** `scp static/` + `systemctl restart aither-bff`
10. **Проверить:** `https://fb1.spb.ru:10443` → чат работает

---

# Приложение H. Чек-лист приёмо-сдаточных испытаний

| № | Проверка | Метод | Ожидаемый результат | Факт | Подпись |
|---|---|---|---|---|---|
| 1 | Все поды Running | `kubectl get pods -A` | Все 1/1 Running | | |
| 2 | GPU доступны | `kubectl describe node \| grep nvidia` | nvidia.com/gpu: 2 | | |
| 3 | vLLM 14B health | `curl :32293/health` | OK | | |
| 4 | vLLM 32B health | `curl :32294/health` | OK | | |
| 5 | Gateway health | `curl :30900/health` | `{"status":"ok"}` | | |
| 6 | BFF health | `curl https://.../health` | `{"status":"ok"}` | | |
| 7 | Список моделей | `curl :30900/v1/models` | ≥2 модели | | |
| 8 | Чат-запрос 14B | `curl :30900/v1/chat/completions` | HTTP 200 + ответ | | |
| 9 | Чат-запрос 32B | `curl :30900/v1/chat/completions` (model: 32b) | HTTP 200 + ответ | | |
| 10 | Биллинг | Запрос → проверка баланса | Баланс уменьшился | | |
| 11 | Rate Limiter | 301 запрос | 300×200, 1×429 | | |
| 12 | DLP | Запрос с паспортом | Блокировка | | |
| 13 | Портал | Браузер → `fb1.spb.ru:10443` | Чат-интерфейс | | |
| 14 | Grafana | `http://n7:30300` | Дашборды с метриками | | |
| 15 | Бэкап БД | `pg_dump` → файл > 0 байт | Успех | | |

---

# Лабораторный практикум (14 работ)

## ЛР 1. Linux: командная строка

**Цель:** освоить базовые команды Linux.

**Исходные данные:** сервер или ВМ с Astra Linux.

**Порядок выполнения:**
1. `whoami` — кто я?
2. `uname -a` — версия ядра
3. `df -h` — диски
4. `free -h` — память
5. `ip a` — сетевые интерфейсы
6. `ps aux` — процессы
7. `systemctl list-units --type=service` — службы
8. Создать папку `~/lab1`, файл `hello.txt`, записать `"Привет!"`
9. `chmod 600 hello.txt` — изменить права
10. `grep "error" /var/log/syslog` — найти ошибки

**Контрольные вопросы:**
- Чем отличаются `/root` и `/home`?
- Что делает `systemctl`?
- Как посмотреть список запущенных процессов?

**Форма отчёта:** скриншоты + вывод команд с пояснениями.

---

## ЛР 2. Установка Astra Linux через Kickstart

**Цель:** автоматически установить ОС.

**Исходные данные:** ВМ в Proxmox, ISO-образ Astra Linux, Kickstart-файл.

**Порядок:**
1. Создать Kickstart-файл с разметкой диска и `parsec=0`
2. Загрузить ВМ с ISO, передать `inst.ks=...`
3. Дождаться автоматической установки
4. Проверить: `uname -a`, `df -h`, `cat /proc/cmdline` (parsec=0)

**Контрольные вопросы:**
- Зачем `parsec=0`?
- Какие разделы созданы и зачем?

---

## ЛР 3. Docker: Dockerfile, сборка, запуск

**Цель:** создать Docker-образ и запустить контейнер.

**Порядок:**
1. Написать Dockerfile:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY app.py .
   CMD ["python3", "app.py"]
   ```
2. `app.py`: `print("Hello from Docker!")`
3. `docker build -t lab3 .`
4. `docker run lab3`
5. `docker run -d -p 8080:80 --name web nginx:alpine`
6. `curl localhost:8080`
7. `docker exec -it web sh` → `hostname`

**Контрольные вопросы:**
- Зачем кэшируются слои?
- Чем `CMD` отличается от `RUN`?

---

## ЛР 4. Kubernetes: мини-кластер

**Цель:** поднять K8s из двух узлов.

**Порядок:**
1. `apt install containerd` → `SystemdCgroup=true`
2. `kubeadm init --pod-network-cidr=10.244.0.0/16`
3. `kubectl apply -f kube-flannel.yml`
4. `kubeadm join ...` (второй узел)
5. `kubectl get nodes` → 2 Ready

**Контрольные вопросы:**
- Зачем Flannel?
- Что делает `kubeadm join`?

---

## ЛР 5. Деплой vLLM 14B

**Цель:** задеплоить модель и отправить первый запрос.

**Порядок:**
1. `kubectl apply -f k8s/vllm-14b/deployment.yaml`
2. `kubectl get pods -w` → дождаться Running
3. `kubectl logs vllm-...` → найти `Model loaded`
4. `curl :32293/v1/chat/completions -d '{"model":"qwen2.5-14b","messages":[...]}'`
5. Замерить время: `time curl ...`

**Контрольные вопросы:**
- Почему первый запрос медленный?
- Что такое prefill и decode?

---

## ЛР 6. Деплой Gateway

**Цель:** собрать образ, задеплоить, проверить биллинг.

**Порядок:**
1. `docker build -t gateway . -f gateway/Dockerfile`
2. `docker push` (или `docker tag` + локальный registry)
3. `kubectl create secret generic pg-url ...`
4. `kubectl apply -f k8s/gateway/`
5. `curl :30900/health`
6. Запрос с API-ключом → проверка `SELECT * FROM billing_accounts`

**Контрольные вопросы:**
- Зачем `kubectl set env` меняет переменные без рестарта?
- Что вернёт 301-й запрос?

---

## ЛР 7. Деплой портала

**Цель:** задеплоить портал на VPS2.

**Порядок:**
1. `scp portal/dist/* portal/static/* root@VPS2:/opt/aither/`
2. `ssh VPS2 systemctl restart aither-bff`
3. Браузер → `https://fb1.spb.ru:10443` → чат-интерфейс
4. Отправить сообщение → проверить toast о списании токенов

**Контрольные вопросы:**
- Почему статика обновляется без рестарта BFF?
- Где хранится баланс организации?

---

## ЛР 8. Развёртывание в закрытом контуре

**Цель:** полный цикл air-gap деплоя.

**Порядок:**
1. `make bundle` (на машине с интернетом)
2. Скопировать `offline-deploy/` на флешку
3. Перенести на целевую машину
4. `sha256sum -c checksums.sha256`
5. `make offline-load`
6. `make deploy`
7. `make test`

**Контрольные вопросы:**
- Зачем `sha256sum`?
- Сколько playbook-ов и зачем каждый?

---

## ЛР 9. Мониторинг: Grafana

**Цель:** изучить дашборды мониторинга.

**Порядок:**
1. Открыть `http://n7:30300`
2. GPU Overview: найти температуру и загрузку GPU
3. Gateway Dashboard: найти RPM и latency
4. vLLM Performance: найти скорость tok/s

**Контрольные вопросы:**
- Какая метрика показывает температуру GPU?
- Что значит p95 latency?

---

## ЛР 10. Инцидент: поиск неисправности

**Цель:** найти и устранить неисправность.

**Сценарий:** «Модель не отвечает».

**Порядок:**
1. `kubectl get pods` → vLLM в CrashLoopBackOff
2. `kubectl logs --previous` → `CUDA out of memory`
3. `kubectl edit deploy` → уменьшить `gpu-memory-utilization`
4. `kubectl rollout restart` → Running
5. Проверить `curl :32293/health`

**Контрольные вопросы:**
- По каким шагам вы шли?
- Как предотвратить повторение?

---

## ЛР 11. Резервное копирование

**Цель:** сделать бэкап и восстановить.

**Порядок:**
1. `pg_dump -U aither -d aither > backup.sql`
2. Удалить тестовую запись в БД
3. `psql -U aither -d aither < backup.sql`
4. Проверить, что запись восстановилась

**Контрольные вопросы:**
- Почему важно проверять бэкап восстановлением?

---

## ЛР 12. Доработка Gateway

**Цель:** добавить модель + тариф + DLP.

**Порядок:**
1. Добавить `qwen2.5-coder-14b` в `catalog.yaml`
2. `kubectl create configmap ... --dry-run | kubectl apply`
3. `kubectl set env deploy/gateway TOKEN_COST=*** `dlp.py`: добавить правило для карт
5. `docker build && docker push && kubectl set image`
6. Проверить: `/v1/models`, списание по новому тарифу, блокировка карты

---

## ЛР 13. Доработка портала

**Цель:** изменить фронтенд, добавить страницу.

**Порядок:**
1. Изменить тему в `index.html` (цвета Astra Linux)
2. Создать `api-keys.html`
3. Добавить роут в `server.ts`
4. `scp` + `systemctl restart`
5. Проверить в браузере

---

## ЛР 14. LoRA: обучение адаптера

**Цель:** обучить LoRA на своих данных.

**Порядок:**
1. Подготовить `dataset.jsonl` (10+ примеров)
2. `python3 train_lora_14b.py --dataset dataset.jsonl --output /models/lora-lab14`
3. Дождаться завершения (~10 мин)
4. Проверить: `ls /models/lora-lab14/adapter_model.safetensors`
5. Скопировать в `/data/models/`
6. Перезапустить vLLM с `--lora-modules`
7. `curl` с `model: "lab14"` → проверить ответ

---

**🎓 Учебное пособие завершено. Все 4 документа готовы.**