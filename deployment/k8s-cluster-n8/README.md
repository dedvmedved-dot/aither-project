# K8s Cluster on n8 — Working Configuration (13.07.2026)

## Состояние

Кластер K8s (v1.33.5) поднят на n8 (10.129.13.78), etcd на sdb2 (Samsung SAS SSD 1.7T).

## Ключевое решение: ОТКЛЮЧИТЬ ВСЕ PROBES

**Проблема**: etcd и apiserver падали каждые 1-10 минут. Причина — liveness/readiness probes kubelet убивают контейнеры при малейших задержках.

**Решение**: удалить `livenessProbe`, `readinessProbe`, `startupProbe` из манифестов etcd и apiserver.

```bash
python3 -c "
import yaml
for f in ['/etc/kubernetes/manifests/etcd.yaml', '/etc/kubernetes/manifests/kube-apiserver.yaml']:
    with open(f) as fh: d = yaml.safe_load(fh)
    for c in d['spec']['containers']:
        c.pop('livenessProbe', None)
        c.pop('readinessProbe', None)
        c.pop('startupProbe', None)
    d['spec']['terminationGracePeriodSeconds'] = 300
    with open(f,'w') as fh: yaml.dump(d, fh, default_flow_style=False)
"
systemctl restart kubelet
```

## Диск etcd

| Диск | Результат |
|------|-----------|
| sda (RAID HDD) | 90 сек |
| sdc (SSD через LVM) | 8-10 мин |
| **sdb2 (SAS SSD)** | **стабильно** |
| tmpfs (RAM) | стабильно, но теряется при ребуте |

Монтирование: `/dev/sdb2 → /var/lib/etcd (ext4, 1.7T)`

## Важные файлы

- `manifests/etcd.yaml` — без проб, с grace=300s
- `manifests/kube-apiserver.yaml` — без проб
- Скрипты восстановления — в `scripts/`

## Как восстановить после ребута

```bash
mount /dev/sdb2 /var/lib/etcd
cp manifests/*.yaml /etc/kubernetes/manifests/
systemctl start kubelet
```

## Текущие компоненты

| Компонент | Статус |
|-----------|--------|
| etcd | ✅ sdb2, без проб |
| apiserver | ✅ без проб |
| Flannel | ✅ |
| CoreDNS | ✅ |
| nvidia-device-plugin | ⏳ задеплоен |
| n7 worker | ⏳ не присоединён |
