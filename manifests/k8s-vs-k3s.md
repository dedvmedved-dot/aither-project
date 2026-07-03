# K3s → K8s: обоснование перехода

## Решение

**Отказ от K3s в пользу полного Kubernetes (K8s).**

## Анализ

| Критерий | K3s | K8s (полный) | Оценка для Aither |
|---|---|---|---|
| **GPU Operator** | Через Device Plugin вручную | Нативный NVIDIA GPU Operator | ✅ K8s — критично для vLLM + MIG |
| **etcd** | Нет (SQLite по умолчанию) | Да (отказоустойчивый) | ✅ K8s — 2 узла с внешним etcd или 3+ узла |
| **Масштабирование** | До 10 узлов с трудом | Штатно до 5000 | ✅ K8s — проект может вырасти |
| **Сетевые политики** | Ограничены (Flannel) | Calico/Cilium (eBPF) | ✅ K8s — нужны для изоляции тенантов |
| **Аудит безопасности** | Базовый | Полный (Falco, OPA, PSP) | ✅ K8s — 152-ФЗ для госсектора |
| **PVC/PV** | Local Path Provisioner | CSI-драйверы (NFS, iSCSI) | ✅ K8s — MegaRAID как блочное хранилище |
| **Helm** | Работает, но с нюансами | Полная поддержка | ✅ K8s — production Helm Charts |
| **Сертификация** | Не сертифицирован CNCF | Сертифицирован CNCF | ✅ K8s — для enterprise-клиентов |

## Конфигурация K8s для 2 узлов

### Вариант A: Stacked etcd (рекомендован)

```
node01: control-plane + etcd + worker
node02: control-plane + etcd + worker
```

- 2 control-plane узла (требуется 3 для кворума etcd)
- **Решение**: добавить внешний etcd на VPS2 (или выделенный 3-й узел etcd)

### Вариант Б: Внешний etcd на VPS2

```
node01: control-plane + worker
node02: control-plane + worker
VPS2:    etcd (через WireGuard)
```

Это даёт кворум etcd (3 голоса), но задержка через туннель выше.

### Вариант В: K8s + kube-vip

```
node01: control-plane (primary) + worker
node02: control-plane (secondary) + worker
VPS2:    etcd witness node
API:     kube-vip на 10.129.13.175
```

## Рекомендация: Вариант А с добавлением etcd

Установка через **kubeadm** с конфигурацией:

```yaml
# kubeadm-config.yaml
apiVersion: kubeadm.k8s.io/v1beta4
kind: ClusterConfiguration
kubernetesVersion: 1.32.0
controlPlaneEndpoint: "10.129.13.175:6443"
networking:
  podSubnet: "10.244.0.0/16"
  serviceSubnet: "10.96.0.0/12"
---
apiVersion: kubeadm.k8s.io/v1beta4
kind: InitConfiguration
nodeRegistration:
  name: node01
  kubeletExtraArgs:
    node-ip: 10.129.13.171
```

## План миграции (если K3s уже развёрнут)

Нет — начинаем с чистого листа. K8s сразу.
