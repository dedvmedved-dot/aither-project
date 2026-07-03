# K3s → K8s: обоснование перехода

## Решение: использовать полный Kubernetes (K8s) вместо K3s

### Сравнение

| Критерий | K3s | K8s (kubeadm) | Вывод |
|---|---|---|---|
| Хранилище | SQLite (по умолчанию) | etcd (3-5 узлов) | K8s — отказоустойчивость |
| GPU Operator | Ручная интеграция | Нативный NVIDIA GPU Operator | K8s — production-ready |
| Обновления кластера | Ограничено | Полный контроль (kubeadm upgrade) | K8s |
| Аудит безопасности | Нет | Audit Policy + Falco | K8s |
| Сетевая политика | Flannel (базово) | Calico/Cilium | K8s |
| Расширение > 10 нод | Больно | Штатно | K8s |
| 2 ноды | ✅ | ✅ | Равно |
| RBAC | Упрощённое | Полное | K8s |
| Сертификация | Частичная | CNCF Certified | K8s |

### Ключевые аргументы

**1. NVIDIA GPU Operator**

K8s (через kubeadm) поддерживает нативный NVIDIA GPU Operator без обходных путей:
```yaml
# K8s — одна команда
helm install nvidia-gpu-operator nvidia/gpu-operator
```
В K3s требуется ручная настройка containerd, nvidia-container-runtime и работа с cgroup v2.

**2. etcd вместо SQLite**

K3s по умолчанию использует SQLite — один бинарный файл. При падении control-plane возможна потеря состояния кластера. etcd обеспечивает Raft-консенсус (можно развернуть 3 экземпляра на двух нодах через внешний etcd).

**3. Будущее расширение**

ТР предусматривает развитие платформы. С K8s добавление нод — 2 команды (`kubeadm join`). С K3s — миграция на внешнюю БД, перенастройка.

**4. Production-эксплуатация**

K8s: Audit Policy, PodSecurityPolicies, Network Policies из коробки. K3s: требует ручного включения и настройки.

### План

| Этап | Действие |
|---|---|
| 1 | Установка RED OS 8.0 на оба сервера |
| 2 | Настройка сети (VLAN 308, IP 171/172) |
| 3 | Установка containerd + nvidia-container-toolkit |
| 4 | kubeadm init (node01) + join (node02) |
| 5 | Установка NVIDIA GPU Operator |
| 6 | Установка Calico (сетевой плагин) |
| 7 | Развёртывание vLLM, PostgreSQL, Redis |

### Примечание

ТР №1 указывает K3s — **это устаревшая информация**. Для 2× серверов с GPU и перспективой расширения K8s (kubeadm) — правильный выбор.
