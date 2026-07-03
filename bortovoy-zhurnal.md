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

---
*Журнал ведётся ассистентом Hermes в хронологическом порядке*
