# Приложения и Лабораторный практикум

> **Документ 4 из 5.** Справочные материалы и практические задания для закрепления навыков.

---

# Приложение A. Глоссарий

| Термин | EN | Определение |
|---|---|---|
| **Air-gap** | — | Физическая изоляция сети от Интернета |
| **API** | Application Programming Interface | Способ для программ общаться друг с другом |
| **BFF** | Backend For Frontend | Сервер-посредник между браузером и основным API |
| **BMC** | Baseboard Management Controller | Контроллер удалённого управления сервером |
| **CIDR** | Classless Inter-Domain Routing | Нотация IP-адресов: 10.0.0.0/24 |
| **CNI** | Container Network Interface | Плагин сети для Kubernetes (Flannel) |
| **CORS** | Cross-Origin Resource Sharing | Разрешение запросов с других доменов |
| **CPU** | Central Processing Unit | Центральный процессор |
| **CSRF** | Cross-Site Request Forgery | Атака с подделкой запроса |
| **CUDA** | Compute Unified Device Architecture | Технология вычислений на GPU от NVIDIA |
| **DLP** | Data Loss Prevention | Защита от утечек конфиденциальных данных |
| **DNS** | Domain Name System | Система преобразования имён в IP-адреса |
| **etcd** | /etc + distributed | Распределённое хранилище конфигурации K8s |
| **GPTQ** | Post-Training Quantization | Метод квантизации моделей (4-bit) |
| **GPU** | Graphics Processing Unit | Видеокарта / графический процессор |
| **HPA** | Horizontal Pod Autoscaler | Автомасштабирование подов |
| **HTTP** | HyperText Transfer Protocol | Протокол передачи веб-страниц |
| **HTTPS** | HTTP Secure | HTTP + шифрование TLS |
| **JWT** | JSON Web Token | Токен аутентификации (header.payload.signature) |
| **K8s** | Kubernetes | Оркестратор контейнеров |
| **KVM** | Kernel-based Virtual Machine | Гипервизор в ядре Linux |
| **LLM** | Large Language Model | Большая языковая модель |
| **LoRA** | Low-Rank Adaptation | Метод дообучения моделей (адаптер 65 MB) |
| **NodePort** | — | Тип сервиса K8s: порт на всех узлах (30000-32767) |
| **OAuth 2.0** | Open Authorization | Протокол делегирования доступа |
| **OOM** | Out Of Memory | Нехватка памяти → процесс убит |
| **PCIe** | Peripheral Component Interconnect Express | Шина подключения устройств |
| **PVC** | PersistentVolumeClaim | Запрос на постоянное хранилище в K8s |
| **QLoRA** | Quantized LoRA | LoRA + 4-bit квантизация (экономия VRAM) |
| **RAM** | Random Access Memory | Оперативная память |
| **RPM/TPM** | Requests/Tokens Per Minute | Лимиты частоты запросов |
| **SPA** | Single-Page Application | Одностраничное веб-приложение |
| **SSE** | Server-Sent Events | Потоковая передача данных от сервера |
| **SSL/TLS** | Secure Sockets Layer / Transport Layer Security | Протоколы шифрования |
| **TP** | Tensor Parallelism | Разрезание модели на несколько GPU |
| **UUID** | Universally Unique Identifier | Уникальный идентификатор |
| **VLAN** | Virtual Local Area Network | Виртуальная локальная сеть |
| **vLLM** | Very Large Language Model | Движок инференса языковых моделей |
| **VPN** | Virtual Private Network | Виртуальная частная сеть (шифрованный туннель) |
| **VRAM** | Video RAM | Видеопамять GPU |
| **VXLAN** | Virtual Extensible LAN | Протокол overlay-сетей |
| **XSS** | Cross-Site Scripting | Атака с внедрением скрипта |
| **YAML** | YAML Ain't Markup Language | Формат конфигурационных файлов |

---

# Приложение B. Шпаргалка по командам

### kubectl

```bash
kubectl get pods/nodes/svc/deploy -o wide
kubectl describe pod <name>
kubectl logs -f <pod> --tail=100
kubectl exec -it <pod> -- bash
kubectl apply -f file.yaml
kubectl delete -f file.yaml
kubectl rollout restart deploy/<name>
kubectl rollout undo deploy/<name>
kubectl rollout status deploy/<name>
kubectl scale --replicas=N deploy/<name>
kubectl set image deploy/<name> container=image:tag
kubectl set env deploy/<name> KEY=VALUE
kubectl top pods/nodes
kubectl port-forward svc/<name> local:remote
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl create secret generic <name> --from-literal=key=value
kubectl create configmap <name> --from-file=key=file
```

### Docker

```bash
docker build -t name:tag -f Dockerfile .
docker run -d -p host:container --name name image
docker ps / docker ps -a
docker logs -f name
docker exec -it name bash
docker stop/start/restart name
docker save -o file.tar image
docker load -i file.tar
docker push/pull image
docker compose up -d / down / logs
```

### systemd / journalctl

```bash
systemctl start/stop/restart <service>
systemctl status <service>
systemctl enable/disable <service>
systemctl daemon-reload
journalctl -u <unit> -f --no-pager
journalctl -u <unit> -p 3 --since "1 hour ago"
```

### Git

```bash
git clone url
git status / git diff
git add file / git commit -m "msg"
git push / git pull
git log --oneline
git checkout -b branch
```

---

# Приложение C. Типовые неисправности

| Симптом | Диагностика | Причина | Решение |
|---|---|---|---|
| Pod CrashLoopBackOff | `kubectl describe pod` | Ошибка в команде/аргументах | Проверить `command` и `args` |
| Pod OOMKilled | `kubectl describe pod \| grep OOM` | Превышен `limits.memory` | Увеличить `limits.memory` |
| ImagePullBackOff | `kubectl describe pod` | Образ не найден / registry недоступен | Проверить `image:` и `docker pull` |
| GPU не видна | `nvidia-smi`, `kubectl describe node \| grep nvidia` | Нет драйверов / runtime | Проверить `runtimeClassName: nvidia` |
| 502 Bad Gateway | `curl BFF:3000/health` | BFF не видит Gateway | Проверить `CORE_API`, сеть |
| 429 Too Many Requests | Логи Gateway | Превышен RPM/TPM | Увеличить лимиты или ждать |
| `toLocaleString` is undefined | Консоль браузера | Ответ API содержит `error` | Проверить `if (!d.error)` |
| WireGuard handshake failed | `wg show` | Ключи не совпадают / порт закрыт | Проверить конфиг, порт 51820 UDP |

---

# Приложение D. Порты и сервисы

| Порт | Сервис | Узел | Протокол |
|---|---|---|---|
| 10443 | nginx (HTTPS-вход) | VPS1 | TCP+TLS |
| 80 | nginx (портал) | VPS2 | TCP |
| 3000 | BFF (Node.js) | VPS2 | TCP |
| 5432 | Portal DB (PostgreSQL) | VPS2 | TCP |
| 8080 | Gateway (ClusterIP) | K8s | TCP |
| 30900 | Gateway (NodePort) | K8s→n7 | TCP |
| 8000 | vLLM (ClusterIP) | K8s | TCP |
| 32293 | vLLM 14B (NodePort) | n8 | TCP |
| 32294 | vLLM 32B (NodePort) | n7 | TCP |
| 30300 | Grafana (NodePort) | n7 | TCP |
| 6379 | Redis | K8s→n8 | TCP |
| 31113 | PostgreSQL (Gateway) | K8s→n8 | TCP |
| 8000 | ChromaDB | K8s→n8 | TCP |
| 6443 | kube-apiserver | n8 | TCP+TLS |
| 9443 | BMC n7 | n7 | TCP+TLS |
| 51820 | WireGuard | VPS1, VPS2 | UDP |

---

# Приложение E. Потоки данных (схемы)

**Поток 1: Чат-запрос**
Браузер → :10443 (TLS) → nginx VPS1 → WireGuard → VPS2 :80 → BFF :3000 → VPS1 :30900 → Gateway :8080 → vLLM :8000 → ответ → ... → браузер (SSE-стриминг)

**Поток 2: Биллинг**
Gateway → Redis (проверка лимита) → vLLM (инференс) → Gateway (парсинг `usage.total_tokens`) → PostgreSQL (`UPDATE balance`)

**Поток 3: OAuth-авторизация**
Браузер → BFF → GitHub → callback → BFF → JWT → cookie

**Поток 4: CI/CD**
Git push → GitHub Actions → docker build → docker push → kubectl set image → health check → Telegram

---

# Приложение F. Карта репозитория

```
aither-project/
├── gateway/          — API Gateway (Python, 11 модулей, Docker-образ)
├── portal/           — Портал (Node.js BFF + HTML/CSS/JS SPA)
├── k8s/              — K8s манифесты (gateway, vllm-14b, vllm-32b, hpa)
├── configs/          — Эталонные конфиги (vps1, vps2, k8s)
├── offline-deploy/   — Пакет для закрытого контура v1.1.0
├── docs/             — Документация и учебник
├── fine-tuning/      — QLoRA-скрипты обучения
├── scripts/          — Деплой, health-check, kickstart
├── db/migrations/    — SQL-миграции
└── wiki/             — База знаний (LLM Wiki)
```

---

# Приложение G. Быстрый старт (памятка)

1. **Установить ОС:** BMC → ISO → Kickstart
2. **Настроить сеть:** IP, DNS, iptables
3. **Установить драйверы:** `apt install nvidia-driver`
4. **Kubernetes:** `kubeadm init` (n8) → Flannel → `kubeadm join` (n7)
5. **GPU Operator:** `helm install gpu-operator`
6. **Модели:** `huggingface-cli download` → `/data/models/`
7. **vLLM:** `kubectl apply -f k8s/vllm-*/`
8. **Gateway:** `docker build` → `docker push` → `kubectl apply`
9. **Портал:** `scp` → `systemctl restart aither-bff`
10. **Проверить:** `curl https://fb1.spb.ru:10443/health` → OK

---

# Приложение H. Чек-лист приёмо-сдаточных испытаний

| № | Проверка | Метод | Ожидаемый результат |
|---|---|---|---|
| 1 | Все поды Running | `kubectl get pods -A` | Все 1/1 Running |
| 2 | GPU доступны | `kubectl describe node \| grep nvidia` | nvidia.com/gpu: 2 |
| 3 | vLLM 14B отвечает | `curl :32293/v1/chat/completions` | HTTP 200 + ответ модели |
| 4 | vLLM 32B отвечает | `curl :32294/v1/chat/completions` | HTTP 200 + ответ |
| 5 | Gateway health | `curl :30900/health` | `{"status":"ok"}` |
| 6 | Биллинг | Запрос → проверка баланса | Баланс уменьшился |
| 7 | Rate Limiter | 301 запрос | 300×200, 1×429 |
| 8 | DLP | Запрос с паспортом | Блокировка + сообщение |
| 9 | Портал HTTPS | Браузер → `fb1.spb.ru:10443` | Чат-интерфейс |
| 10 | Grafana | `http://n7:30300` | Дашборды с метриками |

---

# Лабораторный практикум (14 работ)

| ЛР | Тема | Часы | Ключевое действие |
|---|---|---|---|
| 1 | Linux: командная строка | 2 | `ls, cd, cat, grep, ps, systemctl` |
| 2 | Установка Astra Linux (Kickstart) | 3 | Kickstart-файл → BMC → ISO → готовая ОС |
| 3 | Docker: контейнеризация | 3 | `docker build`, `docker run`, Dockerfile |
| 4 | Kubernetes: мини-кластер | 4 | `kubeadm init/join`, Flannel, `kubectl get nodes` |
| 5 | vLLM 14B: деплой + запрос | 2 | `kubectl apply`, `curl`, замер tok/s |
| 6 | Gateway: сборка + биллинг | 3 | `docker build`, Secret, проверка списания |
| 7 | Портал: деплой на VPS2 | 3 | `scp`, `systemctl`, сквозной тест |
| 8 | Закрытый контур: air-gap | 4 | `make bundle` → флешка → `make deploy` |
| 9 | Мониторинг: Grafana | 2 | Дашборды GPU, Gateway, vLLM |
| 10 | Инцидент: поиск ошибки | 2 | CrashLoopBackOff → диагностика → fix |
| 11 | Бэкап и восстановление | 2 | `pg_dump`, `rsync`, восстановление |
| 12 | Доработка Gateway | 3 | Новая модель + тариф + DLP + деплой |
| 13 | Доработка портала | 3 | Новая страница + OAuth + тема |
| 14 | LoRA: обучение адаптера | 3 | Датасет → `train_lora_14b.py` → проверка |
| **Итого** | | **39 часов** | |

### Формат отчёта по ЛР

Каждая работа оформляется в Markdown:
```markdown
# ЛР N. Название
**Дата:** ...
**Исполнитель:** ...

## Цель
...

## Исходные данные
...

## Ход работы
(команды, скриншоты, пояснения)

## Результаты
...

## Выводы
...
```

---

**🎓 Учебное пособие завершено.**

Общий объём:
- **Часть I** (теория): 7 глав, 241 KB, 31 DOT-схема
- **Часть II** (развёртывание): 6 глав, 41 KB, 2 DOT-схемы
- **Часть III** (разработка): 5 глав, 14 KB
- **Приложения + Практикум**: 8 приложений, 14 ЛР, ~12 KB

**Итого: ~308 KB, 18 глав, 33 DOT-схемы, 14 лабораторных работ.**