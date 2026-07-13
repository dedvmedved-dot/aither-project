# Обновление containerd 1.7.28 → 2.2.1.astra0 на n8

## Дата и время
2026-07-14, ~00:30 МСК

## Исходная проблема
containerd 1.7.28 терял pod sandbox, вызывая `SandboxChanged` → `StopContainer` → SIGKILL etcd и apiserver каждые 2-3 минуты.

## Выполненные шаги

1. **Проверка EventedPLEG** — выключен (как и ожидалось для K8s 1.33)
2. **Снят эталон с n7** — containerd 2.2.1.astra0, конфиг v3
3. **Проверка пакета на n8** — `apt-cache madison containerd` показал 2.2.1.astra0 доступным
4. **Dry-run** — только containerd обновляется, без удаления зависимостей
5. **Rollback-пакет** — сохранены .deb старой и новой версий в `/root/k8s-recovery/containerd-upgrade/`
6. **Snapshot etcd** — создан перед обновлением
7. **Установка** — `apt-get install containerd=2.2.1.astra0`
8. **Конфигурация** — адаптирован эталонный конфиг n7 (v3 формат):
   - `sandbox_image = registry.k8s.io/pause:3.10`
   - `SystemdCgroup = true`
   - `default_runtime_name = 'runc'`
   - Убран старый `[plugins."io.containerd.grpc.v1.cri"]` (несовместим с 2.x)
   - NVIDIA runtime не добавлен (GPU в K8s пока не используется)

## Неожиданные проблемы и решения

| Проблема | Причина | Решение |
|---|---|---|
| Два бинарника containerd | Старый 1.7.28 в `/usr/local/bin`, новый в `/usr/bin` | `rm /usr/local/bin/containerd*` |
| Systemd unit указывал на старый путь | `/etc/systemd/system/containerd.service` с `ExecStart=/usr/local/bin/containerd` | Удалён оверлейд-юнит |
| CRI не работал после старта | Старый v1 конфиг несовместим с 2.x | Заменён на v3-формат |
| sandbox image не загружался | `registry.astra.local` недоступен | Заменён на `registry.k8s.io/pause:3.10` |
| etcd CrashLoopBackOff | Старый mirror pod мешал | Удалён форсированно через `crictl rmp` |
| apiserver не запускался | Порт 6443 завис в старом netns | `systemctl restart kubelet` |

## Результат

| Метрика | До | После |
|---|---|---|
| containerd | 1.7.28 | **2.2.1.astra0** |
| SandboxChanged (15 мин) | 10+ | **0** |
| /livez | провалы 1-3 мин | **ok** |
| /readyz | провалы 1-3 мин | **ok** |
| etcd attempt | росло (57+) | **стабильно** |
| apiserver attempt | росло (64+) | **стабильно** |
| etcd health | 18ms | 17ms |

## Конфигурация containerd 2.2.1 (n8)

```toml
version = 3
imports = ['/etc/containerd/conf.d/*.toml']

[plugins.'io.containerd.cri.v1.runtime'.containerd]
  default_runtime_name = 'runc'
  [plugins.'io.containerd.cri.v1.runtime'.containerd.runtimes.runc]
    runtime_type = 'io.containerd.runc.v2'
    [plugins.'io.containerd.cri.v1.runtime'.containerd.runtimes.runc.options]
      SystemdCgroup = true

[plugins.'io.containerd.cri.v1.runtime'.cni]
  bin_dirs = ['/opt/cni/bin']
  conf_dir = '/etc/cni/net.d'

[plugins.'io.containerd.cri.v1.images']
  pinned_images = { sandbox = 'registry.k8s.io/pause:3.10' }
```

## Дальнейшие шаги

- [x] Обновить containerd
- [ ] Наблюдать 24 часа под watchdog
- [ ] Вернуть health probes в манифесты etcd/apiserver
- [ ] Настроить GPU device plugin (теперь 2.2.1 поддерживает CDI)
- [ ] Запустить vLLM 14B в K8s-поде
