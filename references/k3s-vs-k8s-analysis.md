# K3s vs Kubernetes: анализ для Aither Platform

## Исходные данные

- **2 сервера** YADRO VEGMAN S320 (идентичные)
- **2× Xeon Gold 6258R** (56c/112t) + **768 GB RAM** на каждом
- **2× Quadro RTX 6000** (24 GB VRAM, NVLink) на каждом
- **Сеть:** VLAN 308, 10.129.13.0/24

## Сравнение

| Критерий | K3s | Полный Kubernetes (kubeadm/RKE2) |
|---|---|---|
| **Размер бинарника** | <100 MB | >500 MB |
| **RAM overhead** | ~512 MB | ~2 GB |
| **Установка** | 1 команда (`curl | sh`) | kubeadm init + CNI + металлLB |
| **etcd** | Встроенный или SQLite | Требует etcd (3 ноды минимум) |
| **CNI** | Flannel из коробки | Выбор: Flannel/Calico/Cilium |
| **GPU Operator** | ✅ Полная поддержка NVIDIA GPU Operator | ✅ Полная поддержка |
| **Helm** | ✅ | ✅ |
| **RBAC** | ✅ | ✅ |
| **High Availability** | ✅ (с external DB) | ✅ |
| **Масштабирование до 5+ нод** | Возможно, но не рекомендовано | ✅ Родной дизайн |
| **Поддержка в РФ** | Rancher (SUSE) — доступен | Зависит от дистрибутива |
| **Сертификация K8s** | ✅ CNCF Certified | ✅ CNCF Certified |

## Рекомендация: K3s

**Для текущего масштаба (2 сервера, 4 GPU) K3s — оптимальный выбор.**

### Почему:

1. **Оверхед минимален.** 512 MB RAM против 2+ GB у полного K8s. На каждом сервере 768 GB — экономия 1.5 GB не критична, но важен cumulative overhead: etcd + controller-manager + scheduler + kube-proxy забирают CPU-ядра, которые нужны vLLM.

2. **Достаточно для production.** K3s — CNCF-certified, используется в production Civo Cloud, SUSE Edge, промышленных IoT. Не «облегчённая игрушка», а полноценный K8s с удалёнными неиспользуемыми компонентами.

3. **Простота развёртывания.** Одна команда на установку control plane + worker. При 2 серверах высокую доступность обеспечит external PostgreSQL (развернём на обоих серверах с Patroni).

4. **GPU Operator NVIDIA** — первичная интеграция с K3s, без дополнительных настроек.

### Когда переходить на полный K8s:

- При расширении до **5+ серверов**
- При необходимости **Multi-Master HA** с etcd (K3s с external DB решает это иначе)
- При требовании **ISTIO/Linkerd service mesh** (Cilium в K3s есть)
- При интеграции с корпоративным SSO/LDAP через OIDC (можно и в K3s)

### Альтернатива: RKE2

Если нужен «полный K8s с простой установкой» — RKE2 (Rancher Kubernetes Engine 2):

```bash
curl -sfL https://get.rke2.io | sh -
systemctl enable rke2-server
```

RKE2 ближе к полному K8s, но с удобным управлением от Rancher. Хороший компромисс, если K3s кажется «слишком лёгким».

## Итог

| Этап | Решение |
|---|---|
| **MVP / pilot** | **K3s** — быстрый старт, минимальный оверхед |
| **Production (2 сервера)** | **K3s** + external PostgreSQL для HA |
| **Рост до 5+ серверов** | Миграция на **RKE2** или полный K8s |

Миграция K3s → RKE2 безболезненна: Helm-чарты, манифесты и PVC не требуют изменений.
