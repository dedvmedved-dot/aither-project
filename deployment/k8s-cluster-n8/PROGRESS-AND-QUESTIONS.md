# Прогресс по плану специалистов + вопросы

## Статус: 14 июля 2026, ~00:00 МСК

### ✅ Выполнено

| Шаг | Статус |
|---|---|
| Snapshot etcd | ✅ 10 MB, /root/k8s-recovery/ |
| Backups манифестов | ✅ /root/k8s-recovery/ |
| Аудит /etc/kubernetes/manifests | ✅ Чисто, 4 файла, без backup |
| Анализ причин падений etcd | ✅ **etcd: SIGTERM, exit 0, "signal: terminated"** |
| Анализ причин падений apiserver | ✅ **apiserver: SIGKILL, exit 137** (НЕ OOM — 736 GB free) |
| CRI/cgroup на n7 | ✅ systemd, cgroup2fs, CRI ok |
| Чистый join n7 | ✅ **ОБЕ НОДЫ READY!** |
| inotifywait на манифестах | ✅ запущен |

### 🔥 Текущее состояние

```
n8 (control-plane)  Ready  v1.33.5  containerd 1.7.28
n7 (worker)         Ready  v1.33.5  containerd 2.2.1
```

Все control-plane поды 1/1 Running. etcd attempt #47, apiserver attempt #55.

### 🔑 Ключевые находки

1. **etcd НЕ падает сам** — получает SIGTERM (exit 0, graceful shutdown). Причина: kubelet пересоздаёт sandbox → старый контейнер получает SIGTERM.

2. **apiserver убивают SIGKILL** (exit 137). Памяти полно (736 GB), OOM не обнаружен. Кто и почему — неясно.

3. **Join n7 удался только через ручной CSR.** Автоматический TLS bootstrap (kubeadm join) зависает на kubelet-check — kubelet не создаёт CSR сам.

## ❓ Вопросы специалистам

### Вопрос 1: etcd SIGTERM (exit 0)
`etcd` стабильно работает на SAS SSD (18ms health), проб нет, но каждые ~5-15 минут получает SIGTERM и перезапускается (attempt #47 за 5 часов). Кто посылает SIGTERM статическому поду etcd при неизменном манифесте? Может ли это быть связано с тем, что apiserver падает (SIGKILL) → kubelet пересоздаёт sandbox etcd?

### Вопрос 2: apiserver SIGKILL (exit 137)
`kube-apiserver` получает SIGKILL (exit 137) примерно раз в 10-30 минут. OOM killer исключён — 754 GB RAM, используется 18 GB. Какие ещё механизмы в K8s/containerd могут посылать SIGKILL?

### Вопрос 3: kubelet не создаёт CSR автоматически
При `kubeadm join` kubelet с bootstrap-конфигом (tls-bootstrap-token-user) получает ошибки Forbidden, но **не создаёт CSR**. При ручном создании CSR через `kubectl certificate approve` — всё работает. Почему kubelet пропускает шаг создания CSR? Это может быть связано с тем, что API server периодически недоступен?

### Вопрос 4: inotifywait на манифестах
Мониторинг `inotifywait -m /etc/kubernetes/manifests/` запущен. Есть ли риск что сам inotifywait вызывает ложные срабатывания, которые kubelet интерпретирует как изменение манифеста и перезапускает поды?

### Вопрос 5: containerd 1.7.28 → обновление
Специалисты рекомендовали обновить containerd на n8 до ≥1.7.30 для поддержки native CDI (NVIDIA). Достаточно ли `apt upgrade containerd` на Astra Linux 1.8, или нужна ручная замена?

### Вопрос 6: CoreDNS CrashLoopBackOff
Один из двух CoreDNS подов в CrashLoopBackOff после цикла перезапусков. Как лучше восстановить: `kubectl delete pod` или ждать self-healing?

## 📁 Файлы

- Snapshot etcd: `/root/k8s-recovery/etcd-*.db`
- Манифесты: `/root/k8s-recovery/*.yaml.*`
- inotifywait лог: `/tmp/inotify-manifests.log`
- Репозиторий: `aither-project/deployment/k8s-cluster-n8/`
