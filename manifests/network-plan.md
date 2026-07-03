# Сетевая конфигурация — Aither Platform

## VLAN 308: Production

| Параметр | Значение |
|---|---|
| **VLAN ID** | 308 |
| **Подсеть** | 10.129.13.0/24 |
| **Шлюз** | 10.129.13.1 |
| **DNS** | 10.129.13.65 |
| **DHCP** | ❌ Отсутствует (статическая адресация) |

## IP-план

| IP | Назначение | Сервер |
|---|---|---|
| **10.129.13.171** | RED OS 8.0 (K8s control-plane) | node01 |
| **10.129.13.172** | RED OS 8.0 (K8s worker) | node02 |
| 10.129.13.173-180 | Резерв (будущие сервисы) | — |
| **10.129.40.50** | BMC (управление) | node01 |
| **10.129.40.51** | BMC (управление) | node02 |

## Виртуальные IP (keepalived)

| IP | Назначение |
|---|---|
| 10.129.13.170 | K8s API Server VIP |

## Порты K8s (node01 и node02)

| Порт | Протокол | Назначение |
|---|---|---|
| 6443 | TCP | K8s API Server |
| 2379-2380 | TCP | etcd |
| 10250 | TCP | Kubelet API |
| 10256 | TCP | kube-proxy health |
| 30000-32767 | TCP | NodePort Services |
| 8472 | UDP | Flannel VXLAN |
| 51820 | UDP | WireGuard (VPN-туннели) |

## Порты платформы

| Порт | Сервис |
|---|---|
| 443 | Portal BFF (HTTPS) |
| 8000 | vLLM API |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 9090 | Prometheus |
| 3000 | Grafana |

## Схема подключения

```
Internet ←→ [Cisco 815] ←→ VLAN 308 (10.129.13.0/24)
                              ├── 10.129.13.1  (шлюз)
                              ├── 10.129.13.65 (DNS)
                              ├── 10.129.13.171 (node01 — K8s control-plane)
                              └── 10.129.13.172 (node02 — K8s worker)

VPS1 (170.168.91.95) ←→ WireGuard ←→ VPS2 (130.17.1.90)
VPS2 ←→ Docker Cisco VPN ←→ 10.129.0.0/16 (тестовая зона)
                                ├── 10.129.40.50 (BMC node01)
                                └── 10.129.40.51 (BMC node02)
```
