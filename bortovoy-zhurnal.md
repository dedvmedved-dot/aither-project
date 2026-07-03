# Бортовой журнал — Aither Project

## 2026-07-03 — Старт проекта

### Контекст
- Hermes Agent v0.16.0 (VPS1) + v0.18.0 (VPS2, резерв)
- Провайдер: DeepSeek (deepseek-v4-pro, api.deepseek.com)
- Тестовая зона Cisco: доступна через VPS2 (Docker openconnect, tun1)
- HuaweiHP зона: доступна через VPS1 (tun0)
- WireGuard-мост VPS1↔VPS2: 10.99.0.0/24

### BMC серверы
- **10.129.40.50** — OpenBMC, Redfish 1.9.0, UUID c1b0a74d-...
- **10.129.40.51** — OpenBMC, Redfish 1.9.0, UUID 289530cf-...
- Доступ: web UI (https), учётка techvit (ограниченные права)
- SSH: недоступен (Permission denied)
- Redfish API: только root endpoint (/redfish/v1), остальное — 401

### Анализ доступа (2026-07-03 12:50 MSK)
- Проверены все Redfish endpoints: Systems, Chassis, Managers, SessionService
- Результат: 401 Unauthorized на всех, кроме корневого /redfish/v1
- SSH: ssh-rsa host key, permission denied (учётка без shell-доступа)
- Web UI: OpenBMC SPA, curl-логин через /login — Bad Request
- **Вывод:** учётка techvit = роль Operator/ReadOnly. Нужна Administrator.

### План после получения admin-доступа
1. `GET /redfish/v1/Systems/1` — модель, серийник, CPU, RAM
2. `GET /redfish/v1/Chassis/.../Thermal` — датчики, вентиляторы
3. `POST /redfish/v1/Managers/bmc/VirtualMedia/...` — mount ISO
4. `POST /redfish/v1/Systems/.../Reset` — reboot в boot once mode

### Задачи
- [ ] Получить admin-доступ к BMC
- [ ] Инвентаризация аппаратного обеспечения
- [ ] Настройка удалённого управления питанием
- [ ] Мониторинг температуры/вентиляторов
- [ ] Обновление прошивок

### Репозиторий
- https://github.com/dedvmedved-dot/aither-project (private)
- SSH Deploy Key: ~/.ssh/id_ed25519_aither

## 2026-07-03 14:00 — Анализ ТР и выбор ОС

### Технические решения
- **ТР №1 (Aither Architecture)**: Платформа Token-as-a-Service, 2× сервер, 4× Quadro RTX 6000, K3s + vLLM, Double-Entry биллинг (2998 строк)
- **ТР №2 (Портал Aither v6.0)**: Portal BFF (Fastify) + React SPA + Portal DB (PostgreSQL), OAuth, YooKassa/CloudPayments

### Выбор версии RED OS

| Параметр | RED OS 7.3.6 | RED OS 8.0.2 |
|---|---|---|
| Ядро Linux | 6.1.128 | **6.12.21** |
| NVIDIA driver | 535.113 | **570.144** |
| Docker | 24.x | **28.1** |
| Kubernetes | 1.28 | **1.32** |
| PostgreSQL | 15.x | **17.5** |

**Рекомендация: RED OS 8.0.2** — новейший драйвер NVIDIA 570.144, ядро 6.12 для GPU Operator, Docker 28.1 + K8s 1.32.

ISO: `redos-8-20250711.4-Everything-x86_64-DVD1.iso` (6.1 GB)

Альтернатива: RED OS 7.3.6 (`redos-MUROM-7.3.6-20250715.0-Everything-x86_64-DVD1.iso`, 5.1 GB) — если 8.0 несовместима.

### Задачи
- [x] Изучить оба ТР
- [x] Выбрать версию RED OS
- [x] Проверить доступность ISO-образов
- [x] Получить admin-доступ к BMC (учётка: **techvirt**, роль Administrator)
- [ ] Инвентаризация аппаратного обеспечения
- [ ] Настройка удалённого управления питанием
- [ ] Mount ISO → развёртывание RED OS 8.0

### Важно
- **Имя пользователя на BMC**: `techvirt` (а не `techvit`!)
- Роль уже была `Administrator` на обоих BMC
- Все Redfish-эндпоинты теперь доступны (200 OK)
- 2026-07-03 14:47 — запущена полная инвентаризация обоих BMC

---
*Журнал ведётся ассистентом Hermes в хронологическом порядке*
