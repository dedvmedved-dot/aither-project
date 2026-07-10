# Часть I. Теоретические основы

**Документ:** `01-part1-theory.md` · 7 глав · ~170 стр. · 32 схемы · 26 таблиц

> Можно читать без доступа к серверам. Все концепции, архитектура, «как это работает».

---

## Глава 1. Фундамент: компьютер, Linux, сеть (25 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 1.1 | Что такое сервер | 4 | 1 | 1 | Процессор: ядра/потоки, почему 2× Xeon 6258R (28C/56T). RAM: зачем 754 GB. Диск: SSD↔NVMe↔SAS, IOPS. GPU: CUDA-ядра, VRAM, почему RTX 6000 (24 GB ×2). Блок питания, BMC, IPMI |
| 1.2 | Операционная система Linux | 6 | 2 | 1 | Что такое ядро и userspace. Дистрибутивы: Debian→Astra Linux SE 1.8. Терминал: `ls`, `cd`, `pwd`, `cat`, `less`, `grep`. Файловая система: `/`, `/root`, `/etc`, `/var/log`, `/mnt`, `/proc`, `/sys`. Процессы: PID, PPID, `ps aux`, `top`, демоны, `systemd`, `journalctl`. Пользователи: UID/GID, `/etc/passwd`, `chmod`, `chown`, `sudo` |
| 1.3 | Компьютерные сети — от IP до HTTP | 8 | 2 | 1 | Модель OSI (упрощённо). IP: v4-адресация, маска, CIDR, шлюз, маршрутизация. DNS: A/AAAA/CNAME, `/etc/hosts`, `resolvectl`. Порты: TCP/UDP, `<1024` привилегированные, ephemeral. HTTP: метод, заголовки, статус-коды. HTTPS: TLS 1.3, сертификаты. WebSocket vs SSE |
| 1.4 | VPN, туннели и физическая сеть Aither | 5 | 1 | 1 | Зачем VPN. WireGuard: wg0↔wg1, ключи, конфиг. Cisco VPN: tun1. VLAN 308: изоляция GPU-серверов. Схема: VPS1↔VPS2↔Cisco815→n7/n8. BMC-проброс: `:9443→socat→:19443→:443`. Хоп за хопом |
| 1.5 | ✏️ Практикум: первые шаги в Linux | 2 | — | — | Терминал: `whoami`, `uname -a`, `df -h`, `free -h`, `ip a`. Создание файла, навигация, права |

**Схемы гл. 1:** (1) Устройство сервера YADRO VEGMAN S320 (блок-схема). (2) Файловая система Linux (дерево). (3) Модель OSI (упрощённая, 4 уровня). (4) Физическая сеть Aither (полная).  
**Таблицы гл. 1:** Характеристики серверов, основные команды Linux, коды HTTP.

---

## Глава 2. Виртуализация и контейнеризация (18 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 2.1 | Виртуальные машины | 4 | 1 | 1 | Гипервизор: тип 1 (KVM, ESXi) vs тип 2. Proxmox VE: как устроен у нас. QEMU/KVM: виртуальные диски, сеть, PCIe passthrough (GPU). ✏️ Создать ВМ в Proxmox |
| 2.2 | Контейнеры и Docker | 8 | 2 | 1 | Контейнер vs ВМ: разделяемое ядро, изоляция через namespaces/cgroups. Docker: архитектура (client→daemon→containerd→runc). Dockerfile: FROM, RUN, COPY, CMD, EXPOSE. Слои: кэширование, переиспользование. `docker build`, `docker run`, `docker ps`, `docker logs`, `docker exec`. Тома: bind mount vs volume. Сеть: bridge, host. Registry: Docker Hub, ghcr.io, локальный `registry:2` |
| 2.3 | Docker Compose | 3 | 1 | — | `docker-compose.yml`: services, ports, volumes, depends_on. Пример: nginx + PostgreSQL + BFF. Разбор `configs/vps2/remote-configs.txt` |
| 2.4 | containerd и nvidia-runtime | 2 | — | 1 | containerd: системный демон K8s. nvidia-container-toolkit: доступ GPU из контейнера. `crictl` — аналог docker для containerd |
| 2.5 | ✏️ Практикум: Docker | 1 | — | — | `docker run nginx`, свой Dockerfile, `docker compose up` |

**Схемы гл. 2:** (1) ВМ vs контейнер (сравнительная). (2) Архитектура Docker (client→daemon→containerd→runc). (3) Слои Docker-образа. (4) Docker Compose: сервисы и связи.  
**Таблицы гл. 2:** Команды Docker, команды Docker Compose, отличия ВМ/контейнер.

---

## Глава 3. Kubernetes: от Pod до кластера (28 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 3.1 | Зачем нужен Kubernetes | 3 | 1 | — | Проблема: 10 контейнеров на 2 серверах. Ручное управление vs оркестратор. Что даёт K8s: декларативность, самовосстановление, масштабирование, service discovery |
| 3.2 | Архитектура Kubernetes | 5 | 2 | 1 | Control Plane: kube-apiserver, etcd, controller-manager, scheduler. Worker Node: kubelet, kube-proxy, container runtime. Addons: Flannel (CNI), CoreDNS, Metrics Server. Как команда `kubectl apply` доходит до пода |
| 3.3 | Азбука Kubernetes — все примитивы | 10 | 2 | 2 | **Pod:** манифест, фазы (Pending→Running→Succeeded/Failed), `kubectl describe`. **Deployment:** replicas, selector, strategy (RollingUpdate/Recreate), rollout. **Service:** ClusterIP, NodePort, LoadBalancer. **ConfigMap/Secret:** создание, монтирование (volume/subPath). **Namespace:** default, kube-system, изоляция. **Volume/PVC:** hostPath, emptyDir, PV, PVC, StorageClass. **Ingress:** правила маршрутизации |
| 3.4 | YAML-манифесты — мастер-класс | 4 | — | 1 | Синтаксис: отступы (2 пробела!), списки (`- `), словари (`key:`). Структура: apiVersion, kind, metadata, spec. Построчный разбор 5 манифестов: deployment, service, configmap, secret, hpa |
| 3.5 | Кластер Aither — анатомия | 4 | 1 | 1 | 2 узла: n8 (control-plane), n7 (worker). Flannel VXLAN: 10.244.0.0/16, как под на n8 видит под на n7. NodePort: 30900, 32293, 32294, 30300. nodeSelector: привязка к серверу. Taints/Tolerations: почему control-plane не запускает обычные поды |
| 3.6 | ✏️ Практикум: K8s на бумаге и в Minikube | 2 | — | — | Рисуем кластер с подами. `kubectl run`, `kubectl expose`, `kubectl port-forward` |

**Схемы гл. 3:** (1) Проблема без оркестратора → решение с K8s. (2) Архитектура K8s: Control Plane + Worker. (3) Жизненный цикл Pod (фазы). (4) Service: ClusterIP, NodePort, LoadBalancer (сравнение). (5) Кластер Aither: n8/n7, поды, сервисы, Flannel. (6) YAML-манифест: аннотированная схема.  
**Таблицы гл. 3:** Примитивы K8s, команды kubectl, NodePort-ы кластера.

---

## Глава 4. Искусственный интеллект и LLM (24 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 4.1 | Что такое ИИ — без математики | 4 | 1 | — | Интеллект естественный vs искусственный. Машинное обучение: supervised, unsupervised, reinforcement. Нейросеть: нейрон, слой, веса, функция активации. Обучение: forward pass, loss, backpropagation, градиентный спуск. Аналогии: ребёнок учится на примерах |
| 4.2 | Большие языковые модели (LLM) | 6 | 2 | 1 | Transformer-архитектура: attention, «все слова видят друг друга». Параметры: 14B = 14 миллиардов весов. Почему размер имеет значение: эмерджентные способности. GPT, LLaMA, Qwen: кто есть кто. Qwen 2.5: почему выбрали именно её |
| 4.3 | Токены и контекст | 4 | 1 | 1 | Токенизация: BPE (Byte-Pair Encoding). «1000 токенов ≈ 750 слов» — почему приблизительно. Контекстное окно: 4096 vs 8192 vs 128K. Почему длинный контекст «дорогой» (O(n²) attention). Температура, top-p, top-k: управление генерацией |
| 4.4 | Квантизация: как сжать модель в 4 раза | 4 | 1 | 1 | Веса в bf16 (16 бит) → 4 бита. GPTQ, AWQ, bitsandbytes: методы квантизации. Калибровочный датасет. Потери качества: перплексия. Почему 32B-GPTQ занимает ~20 GB вместо 64 GB |
| 4.5 | LoRA и QLoRA: дообучение за копейки | 4 | 1 | 1 | Полное обучение (full fine-tune): ~1M $. LoRA: обучаем только маленькие матрицы (rank=8, 65 MB). QLoRA: квантизация + LoRA (влезает в 24 GB VRAM). Как применять: `adapter_config.json` + `adapter_model.safetensors`. Пример: astra-14b (доменные знания Astra Linux, K8s, YADRO, ГОСТ) |
| 4.6 | ✏️ Практикум: «поговори с моделью» | 2 | — | — | OpenAI API: `curl` запрос к GPT/Claude, разбор JSON-ответа. SSE: как выглядит поток токенов |

**Схемы гл. 4:** (1) Нейросеть: входной слой → скрытые слои → выход. (2) Transformer: attention, как слова «смотрят» друг на друга. (3) Токенизация: текст → токены → эмбеддинги. (4) Квантизация: bf16 → 4-bit (визуально). (5) LoRA: полные веса (заморожены) + LoRA-матрицы A×B.  
**Таблицы гл. 4:** Модели в Aither (14B, 32B), Параметры генерации, Методы квантизации.

---

## Глава 5. vLLM — движок инференса (22 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 5.1 | Зачем нужен vLLM | 3 | 1 | — | Запуск модели «руками»: Python, PyTorch, CUDA, батчинг. Проблемы: OOM, медленно, нет API. vLLM как решение: высокая пропускная способность, OpenAI-совместимый API, PagedAttention |
| 5.2 | Архитектура vLLM: как устроен внутри | 6 | 2 | 1 | PagedAttention: виртуальная память для KV-кэша (как в ОС). Continuous batching: динамическое добавление/удаление запросов. Prefill vs Decode: две фазы. Scheduler: очередь запросов, приоритеты. Почему prefill ~200 ms (55% времени) |
| 5.3 | Tensor Parallelism: модель на 2 GPU | 4 | 1 | 1 | Разрезание матриц весов по строкам/столбцам. All-reduce: синхронизация между GPU. Почему TP=2 (а не 4): ограничение памяти и NVLink. Практический эффект: 28 tok/s (14B, TP=2) vs 11 tok/s (1 GPU) |
| 5.4 | Параметры запуска — построчный разбор | 5 | — | 1 | Каждый параметр с объяснением «почему именно такое значение»: `--model`, `--dtype half`, `--max-model-len 4096/8192`, `--gpu-memory-utilization 0.90`, `--tensor-parallel-size 2`, `--enable-lora`, `--lora-modules`, `--max-lora-rank 8`, `--quantization gptq`, `VLLM_USE_V1=0`, `HF_HUB_OFFLINE=1`. Антипример: `--enforce-eager` (11 tok/s вместо 28) |
| 5.5 | vLLM в Kubernetes | 4 | 1 | 1 | deployment.yaml: построчно. nodeSelector, runtimeClassName, resources (limits/requests). Volume: hostPath для моделей. Service: ClusterIP + NodePort. Recreate vs RollingUpdate: почему Recreate для GPU-подов |
| 5.6 | ✏️ Практикум: диагностика vLLM | 2 | — | — | `kubectl logs`, `curl /health`, `curl /v1/models`. Замер tok/s, latency |

**Схемы гл. 5:** (1) Архитектура vLLM: Scheduler → PagedAttention → KV-cache → GPU. (2) Prefill vs Decode: временная диаграмма. (3) Tensor Parallelism: матрица весов, разрезанная на 2 GPU. (4) vLLM в K8s: Pod, Service, NodePort, Flannel.  
**Таблицы гл. 5:** Параметры vLLM, Метрики производительности, Сравнение 14B/32B.

---

## Глава 6. Портал — веб-интерфейс платформы (40 стр.) ★ Консолидированная

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| **6.A — Архитектура и теория** |
| 6.1 | Архитектура портала | 5 | 2 | 1 | SPA (Single-Page Application): один HTML, JavaScript рендерит всё. BFF (Backend For Frontend): почему не напрямую Gateway? Поток запроса: Браузер → nginx :10443 → VPS2 :3000 → VPS1 :30900 → Gateway → vLLM. nginx reverse-proxy: конфиг построчно. Статика vs API: разделение путей |
| 6.2 | База данных портала | 5 | 1 | 1 | PostgreSQL на VPS2: `portal_orgs`, `users`, `billing_accounts`, `api_keys`. Схема БД (ER-диаграмма). Миграции: `006_org_id_text.sql`, `007_subscription_tiers.sql`, `008_auth_tables_k8s.sql` — построчный разбор. Связь с Gateway DB (общий `org_id`). Проблема рассинхрона org между Portal DB и Gateway DB (как `toLocaleString` падал) |
| 6.3 | Аутентификация и авторизация | 5 | 1 | 1 | JWT: структура (header.payload.signature), выпуск, проверка, срок жизни. OAuth 2.0: Authorisation Code Flow. Провайдеры: GitHub, Google, Яндекс. `policies.ts`: права доступа (admin, user, org_admin). Куки, сессии, CORS |
| **6.B — BFF-сервер (Node.js/TypeScript)** |
| 6.4 | server.ts — точка входа | 6 | 1 | 1 | Построчный разбор всего файла: импорты, создание Express app, middleware (cors, cookie-parser, json), роуты. Роуты: `/api/chat` (прокси в Gateway), `/api/admin/*` (панель управления), `/auth/*` (OAuth), `/api/billing/*` (биллинг) |
| 6.5 | Безопасность портала | 3 | — | 1 | `security.ts` построчно: helmet, CSP, rate limiting на BFF, валидация ввода, защита от CSRF. `policies.ts`: матрица доступа. CORS: почему нельзя `*` |
| 6.6 | Списание токенов — механика | 4 | 1 | 1 | Как BFF считает токены: парсинг `usage.total_tokens` из финального SSE-чанка vLLM. POST `/api/billing/deduct` → Gateway → `UPDATE billing_accounts`. Toast-уведомление на фронтенде: `tokens_used`, `balance`. Обработка ошибок: что если Gateway недоступен |
| **6.C — Фронтенд (HTML/CSS/JS)** |
| 6.7 | index.html — чат-интерфейс | 5 | 1 | 1 | Структура HTML. CSS: фиксированная шапка, скроллируемая история, поле ввода. JavaScript: SSE-клиент (EventSource), рендеринг Markdown (marked.js), подсветка кода (highlight.js). Стриминг: токен за токеном. Отправка сообщения → ожидание → рендеринг ответа |
| 6.8 | admin.html — панель управления | 4 | 1 | 1 | Вкладки: организации, пользователи, API-ключи, пополнение баланса. Таблица `billing_accounts`: `org_id`, `balance`, `tokens_used`. Кнопка «+Начислить»: как работает, почему падало `toLocaleString` (отладка ошибки). Real-time обновление баланса |
| 6.9 | Деплой портала | 3 | 1 | — | `configs/vps2/aither-bff.service`: systemd-сервис построчно. `deploy.sh`: scp, ssh, restart. Docker Compose на VPS2: nginx (host-сеть), PostgreSQL. Как обновить фронтенд без перезапуска BFF (статика через nginx) |
| 6.10 | ✏️ Практикум: портал | 2 | — | — | Зайти как пользователь, отправить сообщение, проверить списание токенов в админке |

**Схемы гл. 6:** (1) Архитектура портала: браузер→nginx→BFF→Gateway→vLLM. (2) ER-диаграмма БД портала (portal_orgs, users, billing_accounts, api_keys). (3) JWT: выпуск и проверка. (4) BFF server.ts: карта роутов. (5) Поток списания токенов: SSE-чанк → BFF → Gateway → PostgreSQL. (6) index.html: структура DOM и CSS-сетка. (7) admin.html: вкладки, таблицы, кнопки. (8) Деплой: scp→ssh→systemctl.  
**Таблицы гл. 6:** Роуты BFF, Таблицы БД портала, Поля JWT, OAuth-провайдеры, Переменные окружения BFF.

---

## Глава 7. Безопасность и сетевая архитектура (22 стр.)

| # | Раздел | Стр. | Схем | Табл | Ключевое содержимое |
|---|---|---|---|---|---|
| 7.1 | Модель угроз Aither | 4 | 1 | 1 | Методика STRIDE. Активы: токены, API-ключи, модели, данные пользователей. Векторы: внешний злоумышленник (Интернет), внутренний (сотрудник), атака через модель (prompt injection). Матрица: угроза × актив × уязвимость × мера |
| 7.2 | Сетевая безопасность | 5 | 1 | 1 | Эшелонирование: Интернет → VPS1 (DMZ) → VPS2 → Cisco → VLAN 308 (GPU). WireGuard: шифрование, ключи, ротация. nginx: TLS 1.3, HSTS, сертификаты Let's Encrypt. BMC-проброс: цепочка :9443→socat→:19443→:443 — почему так, риски |
| 7.3 | Защита на уровне Gateway | 5 | 1 | 1 | Rate Limiter: алгоритм скользящего окна, Redis-ключи `rpm:{org}:{window}`, TPM, ответ 429. DLP: регулярные выражения для паспортов, ИНН, СНИЛС, email, телефонов. Prompt Injection Detection: чёрный список паттернов, canary-токены. JWT: HS256, срок 1 час, refresh |
| 7.4 | Безопасность в закрытом контуре | 3 | 1 | — | Air-gap: физическая изоляция, контроль USB-носителей, журнал вноса/выноса. `HF_HUB_OFFLINE=1`: модели не лезут в интернет. Отсутствие обновлений: компенсационные меры (статический анализ кода, ревью изменений) |
| 7.5 | Аудит и комплаенс | 3 | — | 1 | ГОСТ Р 57580.1-2017 (ЗО КИИ). Класс защищённости: УЗ-1 (почему). Аттестация: что нужно предоставить. Журнал событий: кто, когда, что делал |
| 7.6 | ✏️ Практикум: пентест | 2 | — | — | `curl` с превышением лимита, `curl` с DLP-нарушением, попытка инъекции |

**Схемы гл. 7:** (1) Модель угроз: диаграмма активов и векторов. (2) Эшелонирование сети: Интернет→DMZ→Cisco→GPU. (3) Rate Limiter: скользящее окно. (4) DLP: поток запроса через фильтры. (5) Air-gap: схема переноса данных в закрытый контур.  
**Таблицы гл. 7:** Матрица угроз STRIDE, DLP-правила, Классы защищённости (ГОСТ).

---

*Конец Части I*
